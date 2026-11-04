"""Tests for the All platforms view: every platform in one graph, joined by platform_links.csv."""

from pathlib import Path

import pytest

from src.api.routes import job_lineage as routes
from src.catalog.platform_links import (
    PlatformLinkError,
    load_platform_links,
    read_platform_links_file,
)
from src.catalog.services.column_lineage import ColumnLineageService
from src.catalog.services.job_lineage import ALL_PLATFORMS, JobLineageService

DEMO_DIR = Path(__file__).resolve().parent.parent / "demo_data" / "lineage"
LINKS_HEADER = "source_dataset,target_dataset,method,description\n"


@pytest.fixture
def synced(db, monkeypatch):
    """All demo platforms synced, reading the demo lineage folder."""
    monkeypatch.setattr(routes.settings, "lineage_data_dir", str(DEMO_DIR))
    import asyncio

    asyncio.run(routes.sync_job_lineage(db))


def by_name(nodes):
    return {n["name"]: n for n in nodes}


# ---------- platform_links.csv ----------


def test_no_links_file_means_no_links(tmp_path):
    assert load_platform_links(str(tmp_path)) == []


def test_shipped_links_file():
    links = load_platform_links(str(DEMO_DIR))
    assert [(link.source_dataset, link.target_dataset) for link in links] == [
        ("PROD.CARDS.TXN.DAILY", "/data/landing/cards/auth_feed"),
        ("PROD.CIF.CUSTOMER.EXTRACT", "/data/landing/customer/profile_feed"),
    ]
    assert links[0].method == "NDM file transfer"


@pytest.mark.parametrize(
    "rows, message",
    [
        ("A.B,,NDM,\n", "target_dataset is empty"),
        (",A.B,NDM,\n", "source_dataset is empty"),
        ("A.B,A.B,NDM,\n", "links a dataset to itself"),
        ("A.B,/x/y,NDM,\nC.D,/x/y,NDM,\n", "already linked"),
    ],
)
def test_links_file_validation(tmp_path, rows, message):
    path = tmp_path / "platform_links.csv"
    path.write_text(LINKS_HEADER + rows)
    with pytest.raises(PlatformLinkError, match=message):
        read_platform_links_file(path)


def test_links_file_missing_column(tmp_path):
    path = tmp_path / "platform_links.csv"
    path.write_text("source_dataset,method\nA.B,NDM\n")
    with pytest.raises(PlatformLinkError, match="missing column"):
        read_platform_links_file(path)


# ---------- the All platforms graph ----------


def test_all_platforms_graph_has_every_platform(db, synced):
    graph = JobLineageService(db).get_graph(ALL_PLATFORMS)
    jobs = [n for n in graph["nodes"] if n["type"] == "job"]
    assert graph["summary"]["jobs"] == 58
    assert {j["platform"] for j in jobs} == {
        "MAINFRAME", "HADOOP_ABINITIO", "INFORMATICA_ORACLE",
        "AIRFLOW_SNOWFLAKE", "DATASTAGE_DB2", "ASTRONOMER_AWS",
    }
    nodes = by_name(graph["nodes"])
    assert nodes["CRDTXN01"]["platform_label"] == "Mainframe → Teradata"
    assert nodes["CRDTXN01"]["platform_key"] == "mainframe"
    assert nodes["ing_cards_auth.mp"]["platform_key"] == "abinitio"


def test_linked_datasets_become_one_node(db, synced):
    nodes = by_name(JobLineageService(db).get_graph(ALL_PLATFORMS)["nodes"])
    handoff = nodes["PROD.CARDS.TXN.DAILY"]
    assert handoff["also_known_as"] == ["/data/landing/cards/auth_feed"]
    assert handoff["transfer_method"] == "NDM file transfer"
    assert set(handoff["platforms"]) == {"MAINFRAME", "HADOOP_ABINITIO"}
    assert "/data/landing/cards/auth_feed" not in nodes


def test_blast_radius_crosses_platforms(db, synced):
    service = JobLineageService(db)
    nodes = by_name(service.get_graph(ALL_PLATFORMS)["nodes"])
    impact = service.get_impact(ALL_PLATFORMS, nodes["CRDTXN01"]["id"])
    impacted = {j["name"] for j in impact["impacted_jobs"]}
    # Mainframe jobs, as before ...
    assert {"TDCRDLD1", "TDCRDPST", "TDFRAUD1"} <= impacted
    # ... and now the Ab Initio graphs fed by the same file
    assert {"ing_cards_auth.mp", "bld_cards_txn_enriched.mp", "score_fraud_model.mp"} <= impacted
    assert nodes["ing_cards_auth.mp"]["impacted"]
    assert "CRDTXN01" in nodes["ing_cards_auth.mp"]["impacted_by"]


def test_single_platform_views_are_unchanged(db, synced):
    service = JobLineageService(db)
    mainframe = by_name(service.get_graph("MAINFRAME")["nodes"])
    impact = service.get_impact("MAINFRAME", mainframe["CRDTXN01"]["id"])
    assert all(j["platform"] == "MAINFRAME" for j in impact["impacted_jobs"])
    assert "also_known_as" not in mainframe["PROD.CARDS.TXN.DAILY"]
    abinitio = by_name(service.get_graph("HADOOP_ABINITIO")["nodes"])
    assert "/data/landing/cards/auth_feed" in abinitio
    assert not abinitio["ing_cards_auth.mp"]["impacted"]


def test_sla_blocked_by_crosses_platforms(db, synced):
    rows = {r["name"]: r for r in JobLineageService(db).get_sla(ALL_PLATFORMS)["jobs"]}
    blockers = [b["name"] for b in rows["bld_fraud_features.mp"]["blocked_by"]]
    assert "bld_cards_txn_enriched.mp" in blockers  # Ab Initio failure, as before
    assert "CRDTXN01" in blockers  # and the mainframe abend upstream of it


def test_column_search_across_platforms(db, synced):
    found = ColumnLineageService(db).search_columns(ALL_PLATFORMS, "customer_id", exact=True)
    tables = {r["dataset_name"]: r for r in found}
    expected = {
        "CUSTOMER_DB.CUSTOMER_MASTER",  # Teradata
        "cust_raw.customer_profile",  # Hive
        "analytics.fct_orders",  # Redshift
    }
    assert expected <= tables.keys()
    assert all(tables[name]["loaded_by"] for name in expected)  # with the job that loads it


def test_unknown_platform_still_rejected(db, synced):
    with pytest.raises(ValueError, match="Unknown platform"):
        JobLineageService(db).get_graph("NOPE")


# ---------- routes ----------


@pytest.mark.asyncio
async def test_platforms_route_can_include_all(db, synced):
    plain = await routes.list_job_lineage_platforms(db=db, include_all=False)
    assert ALL_PLATFORMS not in [p["id"] for p in plain]

    platforms = await routes.list_job_lineage_platforms(db=db, include_all=True)
    everything = platforms[-1]
    assert everything["id"] == ALL_PLATFORMS
    assert everything["key"] == "all"
    assert everything["name"] == "All platforms"
    assert everything["summary"]["jobs"] == 58
    assert everything["summary"]["failed"] == sum(p["summary"]["failed"] for p in plain)


@pytest.mark.asyncio
async def test_graph_route_accepts_all(db, synced):
    graph = await routes.get_job_lineage_graph(
        db=db, platform=ALL_PLATFORMS, focus=None, direction="both", depth=None
    )
    assert graph["platform"] == ALL_PLATFORMS
    assert graph["summary"]["jobs"] == 58
