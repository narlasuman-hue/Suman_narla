"""Scheduled tasks for metadata collection and updates."""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
import logging

from src.config import settings
from src.catalog.database import get_session
from src.catalog.services.sync import create_sync_service
from src.connectors.teradata import TeradataConnector

logger = logging.getLogger(__name__)


class MetadataCollector:
    """Handles metadata collection from source systems."""

    def __init__(self):
        """Initialize collector."""
        self.scheduler = None
        self.teradata_connector = None

    def connect_teradata(self) -> bool:
        """Establish Teradata connection."""
        try:
            self.teradata_connector = TeradataConnector(
                host=settings.teradata_host,
                port=settings.teradata_port,
                user=settings.teradata_user,
                password=settings.teradata_password,
                database=settings.teradata_database,
            )
            self.teradata_connector.connect()
            logger.info("Teradata connector initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Teradata connector: {e}")
            return False

    def sync_metadata(self) -> None:
        """Sync metadata from Teradata to catalog database."""
        if not self.teradata_connector or not self.teradata_connector.is_connected():
            logger.warning("Teradata connector not available, skipping metadata sync")
            return

        db = None
        try:
            db = get_session()
            logger.info("Starting metadata sync from Teradata")

            # Create sync service and perform sync
            sync_service = create_sync_service(db, self.teradata_connector)
            stats = sync_service.sync_all_metadata()

            # Log statistics
            logger.info(
                f"Metadata sync completed - "
                f"Databases: {stats['databases_created']} created, {stats['databases_updated']} updated | "
                f"Tables: {stats['tables_created']} created, {stats['tables_updated']} updated | "
                f"Columns: {stats['columns_created']} created, {stats['columns_updated']} updated | "
                f"Views: {stats['views_created']} created, {stats['views_updated']} updated"
            )

            if stats["errors"]:
                logger.warning(f"Sync completed with {len(stats['errors'])} errors:")
                for error in stats["errors"]:
                    logger.warning(f"  - {error}")

        except Exception as e:
            logger.error(f"Fatal error during metadata sync: {e}", exc_info=True)
        finally:
            if db:
                db.close()

    def update_usage_stats(self) -> None:
        """Update usage statistics from query logs."""
        db = None
        try:
            db = get_session()
            logger.info("Starting usage statistics update")

            if not self.teradata_connector or not self.teradata_connector.is_connected():
                logger.warning("Teradata connector not available for usage update")
                return

            # TODO: Implement query log parsing and usage metrics update
            # This will:
            # 1. Query Teradata query logs (DBC.QryLogV)
            # 2. Parse for table access patterns
            # 3. Update UsageMetrics with access counts
            # 4. Update last_accessed timestamps

            logger.info("Usage statistics update completed")

        except Exception as e:
            logger.error(f"Error updating usage statistics: {e}", exc_info=True)
        finally:
            if db:
                db.close()

    def start(self) -> None:
        """Start background scheduler."""
        if not settings.scheduler_enabled:
            logger.info("Scheduler is disabled")
            return

        if not self.connect_teradata():
            logger.error("Failed to connect to Teradata, scheduler not started")
            return

        self.scheduler = BackgroundScheduler(timezone=settings.scheduler_timezone)

        # Add jobs
        self.scheduler.add_job(
            self.sync_metadata,
            trigger=IntervalTrigger(seconds=settings.metadata_sync_interval),
            id="sync_metadata",
            name="Sync metadata from source systems",
            replace_existing=True,
        )

        self.scheduler.add_job(
            self.update_usage_stats,
            trigger=IntervalTrigger(seconds=settings.usage_stats_interval),
            id="update_usage_stats",
            name="Update usage statistics",
            replace_existing=True,
        )

        self.scheduler.start()
        logger.info("Metadata scheduler started")

    def stop(self) -> None:
        """Stop background scheduler."""
        if self.scheduler:
            self.scheduler.shutdown()
            logger.info("Metadata scheduler stopped")

        if self.teradata_connector:
            self.teradata_connector.disconnect()


# Global collector instance
collector = MetadataCollector()
