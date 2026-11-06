"""Tests for the ServiceNow incident assistant."""

from unittest.mock import MagicMock

import pytest
import requests

from src.servicenow_assist import (
    IncidentAssistant,
    ServiceNowClient,
    ServiceNowConfig,
    ServiceNowError,
)
from src.servicenow_assist.cli import format_recommendation, main
from src.servicenow_assist.client import sanitize_query_text, table_for_number
from src.servicenow_assist.matcher import SimilarityIndex, keywords, tokenize
from src.servicenow_assist.steps import extract_steps, merge_steps

SYS_ID = "a" * 32

RESOLVED = [
    {
        "sys_id": SYS_ID, "number": "INC0000101", "_table": "incident",
        "short_description": "VPN keeps disconnecting on laptop",
        "description": "Cisco AnyConnect drops every few minutes",
        "category": "Network",
        "close_code": "Solved (Permanently)", "resolved_at": "2026-09-01 10:00:00",
        "close_notes": "1. Uninstall AnyConnect\n2. Install AnyConnect 5.1 from Software Center"
                       "\n3. Reboot the laptop\nUser confirmed working.",
    },
    {
        "sys_id": "b" * 32, "number": "INC0000102", "_table": "incident",
        "short_description": "VPN disconnects frequently on laptop",
        "description": "AnyConnect VPN dropping", "category": "Network",
        "close_code": "Solved (Permanently)", "resolved_at": "2026-09-10 10:00:00",
        "close_notes": "- Uninstall AnyConnect\n- Install AnyConnect 5.1 from Software Center\n"
                       "- Clear the DNS cache with ipconfig /flushdns",
    },
    {
        "sys_id": "c" * 32, "number": "INC0000103", "_table": "incident",
        "short_description": "Printer on floor 3 jammed",
        "description": "", "category": "Hardware",
        "close_notes": "Cleared paper jam in tray 2.",
    },
]


class FakeClient:
    """Stands in for ServiceNowClient; returns canned records."""

    def __init__(self, records, work_notes=None):
        self.records = records
        self.work_notes = work_notes or {}
        self.searches = []

    def get_record(self, number):
        return next((dict(r) for r in self.records if r["number"] == number), None)

    def search_resolved(self, table, text, limit=50, exclude_number=None):
        self.searches.append((table, text))
        words = text.lower().split()
        return [dict(r) for r in self.records
                if r["_table"] == table and r.get("close_notes") is not None
                and r["number"] != exclude_number
                and any(w in r["short_description"].lower() for w in words)]

    def get_work_notes(self, sys_id, limit=20):
        return self.work_notes.get(sys_id, [])


# -- config -------------------------------------------------------------------------

def test_config_from_env_expands_instance_name():
    cfg = ServiceNowConfig.from_env(
        {"SERVICENOW_INSTANCE": "acme", "SERVICENOW_TOKEN": "t"})
    assert cfg.instance_url == "https://acme.service-now.com"


def test_config_requires_credentials():
    with pytest.raises(ValueError, match="SERVICENOW_TOKEN"):
        ServiceNowConfig.from_env({"SERVICENOW_INSTANCE": "acme"})


def test_config_rejects_plain_http():
    with pytest.raises(ValueError, match="https"):
        ServiceNowConfig(instance_url="http://acme.example.com", token="t")


# -- client -------------------------------------------------------------------------

def _client(response_json=None, status=200):
    session = MagicMock(spec=requests.Session)
    session.headers = {}
    resp = MagicMock(status_code=status, ok=200 <= status < 300, text="boom")
    resp.json.return_value = response_json or {"result": []}
    session.get.return_value = resp
    cfg = ServiceNowConfig(instance_url="https://acme.service-now.com", token="secret")
    return ServiceNowClient(cfg, session=session), session


def test_table_for_number_maps_prefixes():
    assert table_for_number("inc0012345") == "incident"
    assert table_for_number("RITM0012345") == "sc_req_item"
    with pytest.raises(ValueError):
        table_for_number("INC001^ORnumber=1")


def test_sanitize_query_text_strips_encoded_query_operators():
    assert sanitize_query_text("vpn^ORactive=true\nstate=1") == "vpn ORactive true state 1"


def test_client_get_record_queries_by_number():
    client, session = _client({"result": [{"number": "INC0012345"}]})
    record = client.get_record("INC0012345")
    assert record["_table"] == "incident"
    url = session.get.call_args.args[0]
    params = session.get.call_args.kwargs["params"]
    assert url == "https://acme.service-now.com/api/now/table/incident"
    assert params["sysparm_query"] == "number=INC0012345"
    assert session.headers["Authorization"] == "Bearer secret"


def test_client_search_resolved_builds_keyword_query():
    client, session = _client({"result": [{"number": "INC1"}]})
    client.search_resolved("incident", "vpn^drops", exclude_number="INC0000001")
    query = session.get.call_args.kwargs["params"]["sysparm_query"]
    assert query.startswith("stateIN6,7^123TEXTQUERY321=vpn drops^number!=INC0000001")


def test_client_raises_on_auth_failure():
    client, _ = _client(status=401)
    with pytest.raises(ServiceNowError, match="credentials"):
        client.get_record("INC0012345")


def test_client_wraps_connection_errors():
    client, session = _client()
    session.get.side_effect = requests.ConnectionError("down")
    with pytest.raises(ServiceNowError, match="reach"):
        client.get_record("INC0012345")


def test_client_work_notes_validates_sys_id():
    client, _ = _client()
    with pytest.raises(ValueError):
        client.get_work_notes("1^ORactive=true")


# -- matcher ------------------------------------------------------------------------

def test_tokenize_normalises_synonyms_and_stopwords():
    assert tokenize("Unable to login, my PWD is locked") == ["logon", "password", "lockout"]


def test_keywords_keep_words_as_typed():
    assert keywords("Unable to login to Outlook") == ["login", "outlook"]


def test_similarity_ranks_same_issue_first():
    index = SimilarityIndex(["printer jammed", "vpn disconnecting on laptop", "outlook crash"])
    best, score = index.query("VPN disconnects on my laptop")[0]
    assert best == 1 and score > 0.5


# -- steps --------------------------------------------------------------------------

def test_extract_steps_from_numbered_list_drops_admin_lines():
    notes = "1. Reset the password in AD\n2) Unlock the account\nClosing ticket."
    assert extract_steps(notes) == ["Reset the password in AD", "Unlock the account"]


def test_extract_steps_from_prose():
    notes = "Cleared the browser cache. Re-registered MFA device. User confirmed fixed."
    assert extract_steps(notes) == ["Cleared the browser cache", "Re-registered MFA device"]


def test_merge_steps_counts_repeats_and_keeps_order():
    merged = merge_steps({"INC1": ["Reboot laptop", "Clear cache"],
                          "INC2": ["Reboot  laptop.", "Reinstall app"]})
    assert [s.text for s in merged] == ["Reboot laptop", "Clear cache", "Reinstall app"]
    assert merged[0].sources == ["INC1", "INC2"]


# -- assistant ----------------------------------------------------------------------

def test_recommend_for_text_finds_same_issue_and_merges_steps():
    rec = IncidentAssistant(FakeClient(RESOLVED)).recommend_for_text(
        "VPN keeps disconnecting on my laptop")
    assert [m.number for m in rec.matches] == ["INC0000101", "INC0000102"]
    assert rec.steps[0].text == "Uninstall AnyConnect"
    assert rec.steps[0].count == 2
    assert all("confirmed" not in s.text.lower() for s in rec.steps)


def test_recommend_for_ticket_excludes_itself():
    open_ticket = {"number": "INC0000200", "_table": "incident", "close_notes": None,
                   "short_description": "VPN disconnecting on laptop again"}
    client = FakeClient(RESOLVED + [open_ticket])
    rec = IncidentAssistant(client).recommend_for_ticket("INC0000200")
    assert rec.source_number == "INC0000200"
    assert "INC0000200" not in [m.number for m in rec.matches]
    assert rec.found


def test_recommend_for_ticket_missing_raises():
    with pytest.raises(LookupError):
        IncidentAssistant(FakeClient(RESOLVED)).recommend_for_ticket("INC9999999")


def test_unrelated_problem_returns_no_matches():
    rec = IncidentAssistant(FakeClient(RESOLVED)).recommend_for_text("Excel macro error")
    assert not rec.found and rec.steps == []


def test_falls_back_to_work_notes_when_close_notes_empty():
    record = {**RESOLVED[0], "close_notes": "Resolved."}
    client = FakeClient([record], work_notes={SYS_ID: [
        "Asked user for logs.", "1. Removed stale VPN profile\n2. Re-imported VPN profile"]})
    rec = IncidentAssistant(client).recommend_for_text("VPN disconnecting laptop")
    assert [s.text for s in rec.steps] == ["Removed stale VPN profile", "Re-imported VPN profile"]


def test_broadens_search_when_no_hits():
    client = FakeClient([])
    IncidentAssistant(client).recommend_for_text(
        "outlook calendar sync failing mobile iphone exchange")
    assert [len(t.split()) for _, t in client.searches] == [6, 3, 2] * 2


# -- cli ----------------------------------------------------------------------------

def test_format_recommendation_lists_steps_and_sources():
    rec = IncidentAssistant(FakeClient(RESOLVED)).recommend_for_text("VPN disconnecting laptop")
    out = format_recommendation(rec)
    assert "1. Uninstall AnyConnect  [used in 2/2]" in out
    assert "INC0000101" in out


def test_cli_reports_missing_config(monkeypatch, capsys):
    monkeypatch.delenv("SERVICENOW_INSTANCE", raising=False)
    assert main(["search", "vpn"]) == 2
    assert "SERVICENOW_INSTANCE" in capsys.readouterr().err
