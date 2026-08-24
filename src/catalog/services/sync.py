"""Metadata synchronization service."""

from datetime import datetime
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import logging

from src.catalog.models import (
    Database,
    Table,
    Column,
    View,
    AssetStatus,
    AssetLifecycle,
    AssetTier,
    UsageMetrics,
)
from src.connectors.teradata import TeradataConnector

logger = logging.getLogger(__name__)


class MetadataSyncService:
    """Service for synchronizing metadata from Teradata to catalog."""

    def __init__(self, db: Session, connector: TeradataConnector):
        """Initialize sync service."""
        self.db = db
        self.connector = connector
        self.sync_stats = {
            "databases_created": 0,
            "databases_updated": 0,
            "tables_created": 0,
            "tables_updated": 0,
            "columns_created": 0,
            "columns_updated": 0,
            "views_created": 0,
            "views_updated": 0,
            "errors": [],
        }

    def sync_all_metadata(self) -> Dict[str, Any]:
        """Sync all metadata from Teradata."""
        logger.info("Starting full metadata synchronization")
        self.sync_stats = {
            "databases_created": 0,
            "databases_updated": 0,
            "tables_created": 0,
            "tables_updated": 0,
            "columns_created": 0,
            "columns_updated": 0,
            "views_created": 0,
            "views_updated": 0,
            "errors": [],
        }

        try:
            # Sync databases
            self._sync_databases()

            # Commit after each major operation
            self.db.commit()
            logger.info(f"Synced {self.sync_stats['databases_created'] + self.sync_stats['databases_updated']} databases")

            # Sync tables and columns for each database
            databases = self.db.query(Database).filter(
                Database.status == AssetStatus.ACTIVE
            ).all()

            for database in databases:
                try:
                    self._sync_tables_for_database(database)
                    self._sync_views_for_database(database)
                    self._sync_table_stats(database)
                except Exception as e:
                    error_msg = f"Error syncing database {database.name}: {str(e)}"
                    logger.error(error_msg)
                    self.sync_stats["errors"].append(error_msg)

            self.db.commit()
            logger.info("Metadata synchronization completed successfully")

        except Exception as e:
            logger.error(f"Fatal error during metadata sync: {e}")
            self.db.rollback()
            self.sync_stats["errors"].append(f"Fatal error: {str(e)}")

        return self.sync_stats

    def _sync_databases(self) -> None:
        """Sync databases from Teradata."""
        logger.info("Syncing databases from Teradata")

        try:
            teradata_databases = self.connector.get_databases()
            logger.info(f"Found {len(teradata_databases)} databases in Teradata")

            for db_name in teradata_databases:
                try:
                    existing_db = self.db.query(Database).filter(
                        Database.name == db_name
                    ).first()

                    if existing_db:
                        existing_db.last_synced = datetime.utcnow()
                        self.sync_stats["databases_updated"] += 1
                    else:
                        new_db = Database(
                            name=db_name,
                            status=AssetStatus.ACTIVE,
                            last_synced=datetime.utcnow(),
                        )
                        self.db.add(new_db)
                        self.sync_stats["databases_created"] += 1

                except Exception as e:
                    error_msg = f"Error syncing database {db_name}: {str(e)}"
                    logger.error(error_msg)
                    self.sync_stats["errors"].append(error_msg)

        except Exception as e:
            error_msg = f"Error fetching databases from Teradata: {str(e)}"
            logger.error(error_msg)
            self.sync_stats["errors"].append(error_msg)

    def _sync_tables_for_database(self, database: Database) -> None:
        """Sync tables for a specific database."""
        logger.info(f"Syncing tables for database: {database.name}")

        try:
            teradata_tables = self.connector.get_tables(database.name)
            logger.info(f"Found {len(teradata_tables)} tables in {database.name}")

            for table_info in teradata_tables:
                try:
                    self._sync_single_table(database, table_info)
                except Exception as e:
                    error_msg = f"Error syncing table {table_info.get('TableName')}: {str(e)}"
                    logger.error(error_msg)
                    self.sync_stats["errors"].append(error_msg)

        except Exception as e:
            error_msg = f"Error fetching tables for {database.name}: {str(e)}"
            logger.error(error_msg)
            self.sync_stats["errors"].append(error_msg)

    def _sync_single_table(self, database: Database, table_info: Dict[str, Any]) -> None:
        """Sync a single table and its columns."""
        table_name = table_info.get("TableName")

        # Get or create table
        existing_table = self.db.query(Table).filter(
            Table.db_id == database.id,
            Table.name == table_name,
        ).first()

        if existing_table:
            existing_table.last_modified = table_info.get("LastAlterTimeStamp")
            existing_table.last_synced = datetime.utcnow()
            table = existing_table
            self.sync_stats["tables_updated"] += 1
        else:
            table = Table(
                db_id=database.id,
                name=table_name,
                table_type=table_info.get("TableKind", "T"),
                created_at=table_info.get("CreateTimeStamp"),
                status=AssetStatus.ACTIVE,
                last_synced=datetime.utcnow(),
            )
            self.db.add(table)
            self.sync_stats["tables_created"] += 1

        self.db.flush()  # Ensure table is inserted before syncing columns

        # Sync columns
        self._sync_columns_for_table(database.name, table)

        # Create lifecycle record if not exists
        if not existing_table and not table.lifecycle:
            lifecycle = AssetLifecycle(
                table_id=table.id,
                asset_type="TABLE",
                created_date=table.created_at or datetime.utcnow(),
                status=AssetStatus.ACTIVE,
                owner=None,
                tier=AssetTier.TIER_2,
            )
            self.db.add(lifecycle)

        # Create usage metrics if not exists
        if not existing_table and not table.usage:
            usage = UsageMetrics(
                table_id=table.id,
                access_count_7d=0,
                access_count_30d=0,
                access_count_90d=0,
            )
            self.db.add(usage)

    def _sync_columns_for_table(self, database_name: str, table: Table) -> None:
        """Sync columns for a table."""
        try:
            teradata_columns = self.connector.get_columns(database_name, table.name)

            # Delete old columns not in Teradata
            existing_column_names = {c.name for c in table.columns}
            teradata_column_names = {c.get("ColumnName") for c in teradata_columns}

            for col in table.columns:
                if col.name not in teradata_column_names:
                    self.db.delete(col)

            # Add/update columns
            for col_info in teradata_columns:
                col_name = col_info.get("ColumnName")
                existing_col = next(
                    (c for c in table.columns if c.name == col_name), None
                )

                if existing_col:
                    existing_col.data_type = col_info.get("ColumnType")
                    existing_col.nullable = col_info.get("Nullable", True)
                    existing_col.position = col_info.get("ColumnPosition")
                    existing_col.last_synced = datetime.utcnow()
                    self.sync_stats["columns_updated"] += 1
                else:
                    column = Column(
                        table_id=table.id,
                        name=col_name,
                        data_type=col_info.get("ColumnType"),
                        nullable=col_info.get("Nullable", True),
                        position=col_info.get("ColumnPosition"),
                        last_synced=datetime.utcnow(),
                    )
                    self.db.add(column)
                    self.sync_stats["columns_created"] += 1

        except Exception as e:
            error_msg = f"Error syncing columns for {table.name}: {str(e)}"
            logger.error(error_msg)
            self.sync_stats["errors"].append(error_msg)

    def _sync_views_for_database(self, database: Database) -> None:
        """Sync views for a specific database."""
        logger.info(f"Syncing views for database: {database.name}")

        try:
            teradata_views = self.connector.get_views(database.name)
            logger.info(f"Found {len(teradata_views)} views in {database.name}")

            for view_info in teradata_views:
                try:
                    view_name = view_info.get("ViewName")

                    existing_view = self.db.query(View).filter(
                        View.db_id == database.id,
                        View.name == view_name,
                    ).first()

                    if existing_view:
                        existing_view.last_synced = datetime.utcnow()
                        self.sync_stats["views_updated"] += 1
                    else:
                        view = View(
                            db_id=database.id,
                            name=view_name,
                            view_type="STANDARD",
                            created_at=view_info.get("CreateTimeStamp"),
                            status=AssetStatus.ACTIVE,
                            last_synced=datetime.utcnow(),
                        )
                        self.db.add(view)
                        self.sync_stats["views_created"] += 1

                except Exception as e:
                    error_msg = f"Error syncing view {view_info.get('ViewName')}: {str(e)}"
                    logger.error(error_msg)
                    self.sync_stats["errors"].append(error_msg)

        except Exception as e:
            error_msg = f"Error fetching views for {database.name}: {str(e)}"
            logger.error(error_msg)
            self.sync_stats["errors"].append(error_msg)

    def _sync_table_stats(self, database: Database) -> None:
        """Sync table statistics (size, row count, last accessed)."""
        logger.info(f"Syncing table statistics for database: {database.name}")

        try:
            tables = self.db.query(Table).filter(
                Table.db_id == database.id,
                Table.status == AssetStatus.ACTIVE,
            ).all()

            for table in tables:
                try:
                    stats = self.connector.get_table_stats(database.name, table.name)

                    if stats:
                        table.size_mb = (stats.get("size_bytes", 0) or 0) / (1024 * 1024)
                        table.row_count = stats.get("row_count")
                        if stats.get("last_accessed"):
                            table.last_accessed = stats.get("last_accessed")

                except Exception as e:
                    # Log but don't fail - stats are secondary
                    logger.debug(f"Could not get stats for {table.name}: {e}")

        except Exception as e:
            error_msg = f"Error fetching table stats for {database.name}: {str(e)}"
            logger.error(error_msg)
            self.sync_stats["errors"].append(error_msg)


def create_sync_service(db: Session, connector: TeradataConnector) -> MetadataSyncService:
    """Factory function to create sync service."""
    return MetadataSyncService(db, connector)
