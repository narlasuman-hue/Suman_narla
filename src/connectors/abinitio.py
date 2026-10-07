"""Ab Initio (Hadoop) graph connector.

Exposes Ab Initio graphs/plans that run on the Hadoop cluster, the datasets
each graph reads and writes (Teradata tables, mainframe files, HDFS paths,
Hive tables), and the scheduler entry that triggers it. It follows the same
connector shape as ``src/connectors/mainframe.py`` so a real integration
can be dropped in without touching the sync service, API routes, or UI.

``MockAbInitioConnector`` returns sample data shaped like what Ab Initio
Metadata Hub / Control>Center exposes for a graph run. A production
connector (Metadata Hub API, ``air`` command output, or a Control>Center
export) implements ``BaseAbInitioConnector`` the same way.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class BaseAbInitioConnector(ABC):
    """Abstract interface for retrieving Ab Initio graph metadata."""

    @abstractmethod
    def connect(self) -> None:
        """Establish the connection (or session) to the metadata source."""

    @abstractmethod
    def disconnect(self) -> None:
        """Tear down the connection."""

    @abstractmethod
    def is_connected(self) -> bool:
        """Whether the connector currently has a usable connection."""

    @abstractmethod
    def get_graphs(self) -> List[Dict[str, Any]]:
        """List known graphs with summary info."""

    @abstractmethod
    def get_graph_details(self, graph_name: str) -> Dict[str, Any]:
        """Get full details (including latest run) for a graph."""

    @abstractmethod
    def get_graph_datasets(self, graph_name: str) -> List[Dict[str, Any]]:
        """List the datasets a graph reads (INPUT) or writes (OUTPUT)."""

    @abstractmethod
    def get_graph_schedule(self, graph_name: str) -> Dict[str, Any]:
        """Get the scheduler-side schedule info for a graph."""

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()


def _ds(port: str, name: str, direction: str, dataset_type: str) -> Dict[str, Any]:
    return {
        "port": port,
        "dataset_name": name,
        "direction": direction,
        "dataset_type": dataset_type,
    }


class MockAbInitioConnector(BaseAbInitioConnector):
    """Sample-data Ab Initio connector for development and demos.

    Ab Initio graphs load Hadoop (Hive / HDFS) tables from feeds landed in
    HDFS; they form their own lineage, independent of the mainframe jobs
    that load Teradata.
    """

    def __init__(self):
        self._connected = False
        self._graphs = self._build_graphs()

    def connect(self) -> None:
        self._connected = True
        logger.info("Connected to mock Ab Initio metadata source")

    def disconnect(self) -> None:
        self._connected = False
        logger.info("Disconnected from mock Ab Initio metadata source")

    def is_connected(self) -> bool:
        return self._connected

    def get_graphs(self) -> List[Dict[str, Any]]:
        return [
            {
                "graph_name": g["graph_name"],
                "project": g["project"],
                "owner": g["owner"],
                "status": g["last_run_status"],
                "scheduler_system": g["schedule"]["scheduler_system"],
                "schedule_name": g["schedule"]["schedule_name"],
            }
            for g in self._graphs.values()
        ]

    def _get(self, graph_name: str) -> Dict[str, Any]:
        graph = self._graphs.get(graph_name)
        if not graph:
            raise KeyError(f"Unknown Ab Initio graph: {graph_name}")
        return graph

    def get_graph_details(self, graph_name: str) -> Dict[str, Any]:
        return {k: v for k, v in self._get(graph_name).items() if k != "datasets"}

    def get_graph_datasets(self, graph_name: str) -> List[Dict[str, Any]]:
        return self._get(graph_name)["datasets"]

    def get_graph_schedule(self, graph_name: str) -> Dict[str, Any]:
        return self._get(graph_name)["schedule"]

    @staticmethod
    def _build_graphs() -> Dict[str, Dict[str, Any]]:
        # Truncated to the hour so repeated syncs report the same run.
        now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)

        def graph(name, project, owner, description, status, ran_hours_ago, duration,
                  schedule, datasets, error=None):
            return {
                "graph_name": name,
                "project": project,
                "owner": owner,
                "description": description,
                "cluster": "hdp-prod-01",
                "last_run_status": status,
                "last_run": now - timedelta(hours=ran_hours_ago),
                "next_run": now + timedelta(hours=24 - ran_hours_ago % 24),
                "duration_seconds": duration,
                "error_message": error,
                "schedule": schedule,
                "datasets": datasets,
            }

        fin_daily = {
            "scheduler_system": "Control-M",
            "schedule_name": "HDP-FIN-DAILY",
            "frequency": "DAILY",
            "run_time": "04:00",
        }
        inv_daily = {
            "scheduler_system": "Control-M",
            "schedule_name": "HDP-INV-DAILY",
            "frequency": "DAILY",
            "run_time": "05:00",
        }
        bill_monthly = {
            "scheduler_system": "Autosys",
            "schedule_name": "HDP-BILL-MONTHEND",
            "frequency": "MONTHLY",
            "run_time": "06:00",
        }

        graphs = [
            graph(
                "ing_gl_postings.mp", "fin_ingest", "HADOOP_FIN_TEAM",
                "Load the GL postings feed into the Hadoop raw zone",
                "SUCCESS", 7, 1260, fin_daily,
                [
                    _ds("in0", "/data/landing/finance/gl_postings_feed", "INPUT", "HDFS"),
                    _ds("out0", "/data/raw/finance/gl_postings", "OUTPUT", "HDFS"),
                    _ds("out1", "fin_raw.gl_postings", "OUTPUT", "HIVE"),
                ],
            ),
            graph(
                "bld_fin_gl_summary.mp", "fin_mart", "HADOOP_FIN_TEAM",
                "Build daily GL summary by cost center",
                "SUCCESS", 6, 840, fin_daily,
                [
                    _ds("in0", "fin_raw.gl_postings", "INPUT", "HIVE"),
                    _ds("in1", "ref.cost_center", "INPUT", "HIVE"),
                    _ds("out0", "fin_mart.gl_daily_summary", "OUTPUT", "HIVE"),
                ],
            ),
            graph(
                "ing_inventory_recon.mp", "inv_ingest", "HADOOP_SUPPLY_TEAM",
                "Load the inventory reconciliation feed into Hive",
                "FAILED", 30, 180, inv_daily,
                [
                    _ds("in0", "/data/landing/inventory/recon_feed", "INPUT", "HDFS"),
                    _ds("out0", "inv_raw.inventory_recon", "OUTPUT", "HIVE"),
                ],
                error="Phase 1: Input file '/data/landing/inventory/recon_feed' not found",
            ),
            graph(
                "bld_supply_chain_kpi.mp", "analytics", "HADOOP_SUPPLY_TEAM",
                "Supply chain KPIs combining inventory and finance",
                "SUCCESS", 29, 1500, inv_daily,
                [
                    _ds("in0", "inv_raw.inventory_recon", "INPUT", "HIVE"),
                    _ds("in1", "fin_mart.gl_daily_summary", "INPUT", "HIVE"),
                    _ds("out0", "analytics.supply_chain_kpi", "OUTPUT", "HIVE"),
                ],
            ),
            graph(
                "ing_billing_stmts.mp", "bill_ingest", "HADOOP_BILLING_TEAM",
                "Load the month-end billing statements feed into HDFS",
                "RUNNING", 1, None, bill_monthly,
                [
                    _ds("in0", "/data/landing/billing/statements_feed", "INPUT", "HDFS"),
                    _ds("out0", "/data/raw/billing/statements", "OUTPUT", "HDFS"),
                ],
            ),
            graph(
                "bld_customer_360.mp", "analytics", "HADOOP_BILLING_TEAM",
                "Customer 360 view from billing statements",
                "FAILED", 26, 95, bill_monthly,
                [
                    _ds("in0", "/data/raw/billing/statements", "INPUT", "HDFS"),
                    _ds("out0", "analytics.customer_360", "OUTPUT", "HIVE"),
                ],
                error="Phase 2: Reformat 'norm_acct' rejected 1204 records (reject threshold 1000)",
            ),
        ]
        return {g["graph_name"]: g for g in graphs}
