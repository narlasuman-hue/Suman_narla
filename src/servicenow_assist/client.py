"""Thin client over the ServiceNow REST Table API."""

from __future__ import annotations

import logging
import re
from typing import Any

import requests

from .config import ServiceNowConfig

logger = logging.getLogger(__name__)

# Ticket number prefix -> table it lives in.
TABLE_BY_PREFIX = {
    "INC": "incident",
    "RITM": "sc_req_item",
    "REQ": "sc_request",
    "PRB": "problem",
}

# Encoded-query fragment that selects "resolved/closed" records, per table.
RESOLVED_FILTER = {
    "incident": "stateIN6,7",  # 6 = Resolved, 7 = Closed
    "sc_req_item": "state=3",  # 3 = Closed Complete
    "sc_request": "request_state=closed_complete",
    "problem": "stateIN106,107",  # Resolved, Closed
}

RECORD_FIELDS = [
    "sys_id",
    "number",
    "short_description",
    "description",
    "category",
    "subcategory",
    "cmdb_ci",
    "assignment_group",
    "state",
    "close_code",
    "close_notes",
    "resolved_at",
    "sys_updated_on",
]

_NUMBER_RE = re.compile(r"^(INC|RITM|REQ|PRB)\d{5,}$")
_SYS_ID_RE = re.compile(r"^[0-9a-f]{32}$")


class ServiceNowError(RuntimeError):
    """Raised when ServiceNow returns an error or an unexpected response."""


def table_for_number(number: str) -> str:
    """Return the table for a ticket number such as ``INC0012345``."""
    number = number.strip().upper()
    if not _NUMBER_RE.match(number):
        raise ValueError(f"Not a recognised ticket number: {number!r}")
    prefix = re.match(r"[A-Z]+", number).group(0)  # type: ignore[union-attr]
    return TABLE_BY_PREFIX[prefix]


def sanitize_query_text(text: str) -> str:
    """Strip characters that would let free text alter an encoded query.

    ``^`` separates encoded-query clauses and ``=`` / ``\\n`` could start new ones,
    so user text is reduced to words before being embedded in a query.
    """
    words = re.findall(r"[A-Za-z0-9_\-.@]+", text)
    return " ".join(words)[:200]


class ServiceNowClient:
    """Reads incidents, requests and work notes from ServiceNow."""

    def __init__(self, config: ServiceNowConfig, session: requests.Session | None = None):
        self.config = config
        self.session = session or requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        if config.token:
            self.session.headers["Authorization"] = f"Bearer {config.token}"
        else:
            self.session.auth = (config.username or "", config.password or "")

    # -- low level -----------------------------------------------------------------

    def _get(self, table: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        url = f"{self.config.instance_url}/api/now/table/{table}"
        params = {"sysparm_display_value": "true", "sysparm_exclude_reference_link": "true",
                  **params}
        try:
            resp = self.session.get(
                url, params=params, timeout=self.config.timeout, verify=self.config.verify_ssl
            )
        except requests.RequestException as exc:
            raise ServiceNowError(f"Could not reach ServiceNow: {exc}") from exc
        if resp.status_code == 401:
            raise ServiceNowError("ServiceNow rejected the credentials (401)")
        if resp.status_code == 403:
            raise ServiceNowError(f"No read access to table {table!r} (403)")
        if not resp.ok:
            raise ServiceNowError(f"ServiceNow returned {resp.status_code}: {resp.text[:200]}")
        try:
            return resp.json().get("result", [])
        except ValueError as exc:
            raise ServiceNowError("ServiceNow returned a non-JSON response") from exc

    # -- records -------------------------------------------------------------------

    def get_record(self, number: str) -> dict[str, Any] | None:
        """Fetch one incident/request by its number, or ``None`` if not found."""
        number = number.strip().upper()
        table = table_for_number(number)
        rows = self._get(table, {
            "sysparm_query": f"number={number}",
            "sysparm_fields": ",".join(RECORD_FIELDS),
            "sysparm_limit": 1,
        })
        if not rows:
            return None
        record = rows[0]
        record["_table"] = table
        return record

    def search_resolved(
        self, table: str, text: str, limit: int = 50, exclude_number: str | None = None
    ) -> list[dict[str, Any]]:
        """Return resolved/closed records on ``table`` whose text matches ``text``.

        Uses ServiceNow's keyword index (``123TEXTQUERY321``) so it behaves like the
        global search box; results are re-ranked locally afterwards.
        """
        if table not in RESOLVED_FILTER:
            raise ValueError(f"Unsupported table: {table!r}")
        keywords = sanitize_query_text(text)
        if not keywords:
            return []
        query = f"{RESOLVED_FILTER[table]}^123TEXTQUERY321={keywords}"
        if exclude_number:
            query += f"^number!={sanitize_query_text(exclude_number)}"
        query += "^ORDERBYDESCsys_updated_on"
        rows = self._get(table, {
            "sysparm_query": query,
            "sysparm_fields": ",".join(RECORD_FIELDS),
            "sysparm_limit": int(limit),
        })
        for row in rows:
            row["_table"] = table
        logger.debug("search_resolved(%s, %r) -> %d rows", table, keywords, len(rows))
        return rows

    def get_work_notes(self, sys_id: str, limit: int = 20) -> list[str]:
        """Return work notes and comments for a record, oldest first."""
        if not _SYS_ID_RE.match(sys_id):
            raise ValueError(f"Invalid sys_id: {sys_id!r}")
        rows = self._get("sys_journal_field", {
            "sysparm_query": f"element_id={sys_id}^elementINwork_notes,comments"
                             "^ORDERBYsys_created_on",
            "sysparm_fields": "value,element,sys_created_on",
            "sysparm_limit": int(limit),
        })
        return [r.get("value", "") for r in rows if r.get("value")]
