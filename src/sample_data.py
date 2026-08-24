"""
Sample data generator for Database Metadata Catalog testing.
Populates the database with realistic test data.
"""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from src.catalog.database import SessionLocal
from src.catalog.models import (
    Database,
    Table,
    Column,
    View,
    Job,
    JobExecution,
    Lineage,
    AssetLifecycle,
    UsageMetrics,
    AssetTag,
    AssetStatus,
    AssetTier,
)


def create_sample_databases(db: Session) -> dict:
    """Create sample databases."""
    databases = [
        Database(
            name="analytics_db",
            owner="analytics_team",
            description="Central analytics and reporting database",
            status=AssetStatus.ACTIVE,
            last_synced=datetime.utcnow(),
        ),
        Database(
            name="raw_data",
            owner="data_engineering",
            description="Raw data ingestion and staging database",
            status=AssetStatus.ACTIVE,
            last_synced=datetime.utcnow(),
        ),
        Database(
            name="customer_db",
            owner="customer_team",
            description="Customer data and CRM database",
            status=AssetStatus.ACTIVE,
            last_synced=datetime.utcnow(),
        ),
        Database(
            name="legacy_warehouse",
            owner="legacy_team",
            description="Legacy data warehouse (deprecated)",
            status=AssetStatus.DEPRECATED,
            last_synced=datetime.utcnow(),
        ),
    ]

    for database in databases:
        db.add(database)
    db.commit()

    return {db.id: db for db in databases}


def create_sample_tables(db_session: Session, databases: dict) -> dict:
    """Create sample tables."""
    tables = [
        # Analytics tables
        Table(
            database_id=databases[1].id,
            name="customers_table",
            type="PERMANENT",
            status=AssetStatus.ACTIVE,
            description="Customer information including contact details and demographics",
            created_at=datetime.utcnow() - timedelta(days=365),
            last_accessed=datetime.utcnow() - timedelta(hours=2),
            row_count=5000000,
            size_mb=2048,
        ),
        Table(
            database_id=databases[1].id,
            name="orders_table",
            type="PERMANENT",
            status=AssetStatus.ACTIVE,
            description="Order transactions and history",
            created_at=datetime.utcnow() - timedelta(days=730),
            last_accessed=datetime.utcnow() - timedelta(hours=1),
            row_count=50000000,
            size_mb=15360,
        ),
        Table(
            database_id=databases[1].id,
            name="analytics_summary",
            type="PERMANENT",
            status=AssetStatus.ACTIVE,
            description="Daily aggregated analytics metrics",
            created_at=datetime.utcnow() - timedelta(days=180),
            last_accessed=datetime.utcnow() - timedelta(minutes=30),
            row_count=1000,
            size_mb=256,
        ),
        # Raw data tables
        Table(
            database_id=databases[2].id,
            name="raw_events",
            type="PERMANENT",
            status=AssetStatus.ACTIVE,
            description="Raw event stream from application",
            created_at=datetime.utcnow() - timedelta(days=90),
            last_accessed=datetime.utcnow() - timedelta(minutes=5),
            row_count=100000000,
            size_mb=40960,
        ),
        Table(
            database_id=databases[2].id,
            name="staging_orders",
            type="TEMPORARY",
            status=AssetStatus.ACTIVE,
            description="Staging table for order data transformation",
            created_at=datetime.utcnow() - timedelta(days=60),
            last_accessed=datetime.utcnow() - timedelta(hours=6),
            row_count=5000000,
            size_mb=2048,
        ),
        # Customer tables
        Table(
            database_id=databases[3].id,
            name="customer_profiles",
            type="PERMANENT",
            status=AssetStatus.ACTIVE,
            description="Customer master data and profiles",
            created_at=datetime.utcnow() - timedelta(days=365),
            last_accessed=datetime.utcnow() - timedelta(hours=4),
            row_count=10000000,
            size_mb=4096,
        ),
        Table(
            database_id=databases[3].id,
            name="customer_transactions",
            type="PERMANENT",
            status=AssetStatus.INACTIVE,
            description="Customer transaction history (archived)",
            created_at=datetime.utcnow() - timedelta(days=1095),
            last_accessed=datetime.utcnow() - timedelta(days=180),
            row_count=30000000,
            size_mb=12288,
        ),
        # Legacy tables
        Table(
            database_id=databases[4].id,
            name="old_customer_data",
            type="PERMANENT",
            status=AssetStatus.DEPRECATED,
            description="Legacy customer data (use customers_table instead)",
            created_at=datetime.utcnow() - timedelta(days=2000),
            last_accessed=datetime.utcnow() - timedelta(days=360),
            row_count=2000000,
            size_mb=1024,
        ),
    ]

    for table in tables:
        db_session.add(table)
    db_session.commit()

    return {f"{table.database_id}_{table.name}": table for table in tables}


def create_sample_columns(db_session: Session, tables: dict) -> None:
    """Create sample columns."""
    column_definitions = {
        # customers_table columns
        "1_customers_table": [
            ("customer_id", "INTEGER", False, False, "Primary key for customer"),
            ("first_name", "VARCHAR(100)", False, False, "Customer first name"),
            ("last_name", "VARCHAR(100)", False, False, "Customer last name"),
            ("email", "VARCHAR(255)", False, True, "Customer email address"),
            ("phone", "VARCHAR(20)", True, True, "Customer phone number"),
            ("created_at", "TIMESTAMP", False, False, "Account creation timestamp"),
            ("last_login", "TIMESTAMP", True, False, "Last login timestamp"),
        ],
        # orders_table columns
        "1_orders_table": [
            ("order_id", "INTEGER", False, False, "Primary key for order"),
            ("customer_id", "INTEGER", False, False, "Foreign key to customers"),
            ("order_date", "DATE", False, False, "Date of order"),
            ("total_amount", "DECIMAL(12,2)", False, False, "Total order amount"),
            ("status", "VARCHAR(50)", False, False, "Order status"),
            ("created_at", "TIMESTAMP", False, False, "Order creation time"),
        ],
        # analytics_summary columns
        "1_analytics_summary": [
            ("metric_date", "DATE", False, False, "Date of metric"),
            ("total_orders", "INTEGER", False, False, "Total orders for day"),
            ("total_revenue", "DECIMAL(15,2)", False, False, "Total revenue for day"),
            ("unique_customers", "INTEGER", False, False, "Unique customers"),
            ("avg_order_value", "DECIMAL(12,2)", False, False, "Average order value"),
        ],
        # raw_events columns
        "2_raw_events": [
            ("event_id", "BIGINT", False, False, "Unique event ID"),
            ("event_type", "VARCHAR(50)", False, False, "Type of event"),
            ("user_id", "VARCHAR(255)", False, False, "User identifier"),
            ("event_data", "VARCHAR(4000)", True, False, "JSON event payload"),
            ("timestamp", "TIMESTAMP", False, False, "Event timestamp"),
            ("processed", "BOOLEAN", False, False, "Whether event is processed"),
        ],
        # staging_orders columns
        "2_staging_orders": [
            ("staging_id", "INTEGER", False, False, "Staging record ID"),
            ("order_id", "INTEGER", False, False, "Order ID"),
            ("customer_id", "INTEGER", False, False, "Customer ID"),
            ("amount", "DECIMAL(12,2)", False, False, "Order amount"),
            ("status", "VARCHAR(50)", False, False, "Status"),
        ],
        # customer_profiles columns
        "3_customer_profiles": [
            ("profile_id", "INTEGER", False, False, "Profile ID"),
            ("customer_id", "INTEGER", False, False, "Customer ID"),
            ("tier", "VARCHAR(50)", False, False, "Customer tier"),
            ("lifetime_value", "DECIMAL(15,2)", False, False, "Lifetime value"),
            ("last_update", "TIMESTAMP", False, False, "Last update time"),
        ],
        # customer_transactions columns
        "3_customer_transactions": [
            ("txn_id", "BIGINT", False, False, "Transaction ID"),
            ("customer_id", "INTEGER", False, False, "Customer ID"),
            ("amount", "DECIMAL(15,2)", False, False, "Transaction amount"),
            ("date", "DATE", False, False, "Transaction date"),
            ("status", "VARCHAR(50)", False, False, "Transaction status"),
        ],
        # old_customer_data columns
        "4_old_customer_data": [
            ("customer_id", "INTEGER", False, False, "Legacy customer ID"),
            ("cust_name", "VARCHAR(255)", False, False, "Customer name"),
            ("cust_email", "VARCHAR(255)", False, True, "Customer email"),
            ("create_date", "DATE", False, False, "Creation date"),
        ],
    }

    position = 1
    for table_key, columns in column_definitions.items():
        table = tables.get(table_key)
        if not table:
            continue

        for idx, (name, data_type, nullable, sensitive, description) in enumerate(
            columns, 1
        ):
            column = Column(
                table_id=table.id,
                name=name,
                data_type=data_type,
                nullable=nullable,
                sensitive=sensitive,
                description=description,
                position=idx,
            )
            db_session.add(column)

    db_session.commit()


def create_sample_views(db_session: Session, databases: dict) -> None:
    """Create sample views."""
    views = [
        View(
            database_id=databases[1].id,
            name="customer_summary_view",
            description="Materialized view of customer summary metrics",
            created_at=datetime.utcnow() - timedelta(days=180),
            definition="SELECT customer_id, COUNT(*) as order_count, SUM(total_amount) as revenue FROM orders_table GROUP BY customer_id",
        ),
        View(
            database_id=databases[1].id,
            name="daily_analytics_view",
            description="View of daily analytics metrics",
            created_at=datetime.utcnow() - timedelta(days=90),
            definition="SELECT metric_date, total_orders, total_revenue FROM analytics_summary WHERE metric_date >= CURRENT_DATE - INTERVAL '90' DAY",
        ),
    ]

    for view in views:
        db_session.add(view)
    db_session.commit()


def create_sample_jobs(db_session: Session) -> dict:
    """Create sample jobs."""
    jobs = [
        Job(
            name="daily_analytics_sync",
            description="Daily job to sync analytics data",
            frequency="DAILY",
            schedule="0 2 * * *",
            owner="data_team",
            status="ACTIVE",
            created_at=datetime.utcnow() - timedelta(days=365),
        ),
        Job(
            name="customer_segment_update",
            description="Update customer segmentation data",
            frequency="DAILY",
            schedule="0 3 * * *",
            owner="analytics_team",
            status="ACTIVE",
            created_at=datetime.utcnow() - timedelta(days=180),
        ),
        Job(
            name="data_quality_check",
            description="Run data quality validation checks",
            frequency="HOURLY",
            schedule="0 * * * *",
            owner="data_quality_team",
            status="ACTIVE",
            created_at=datetime.utcnow() - timedelta(days=90),
        ),
        Job(
            name="legacy_data_archival",
            description="Archive old data from legacy warehouse",
            frequency="WEEKLY",
            schedule="0 1 * * 0",
            owner="legacy_team",
            status="INACTIVE",
            created_at=datetime.utcnow() - timedelta(days=500),
        ),
    ]

    for job in jobs:
        db_session.add(job)
    db_session.commit()

    return {job.id: job for job in jobs}


def create_sample_job_executions(db_session: Session, jobs: dict) -> None:
    """Create sample job executions."""
    executions = [
        JobExecution(
            job_id=jobs[1].id,
            status="SUCCESS",
            started_at=datetime.utcnow() - timedelta(hours=22),
            completed_at=datetime.utcnow() - timedelta(hours=22, minutes=15),
            rows_processed=50000000,
        ),
        JobExecution(
            job_id=jobs[1].id,
            status="SUCCESS",
            started_at=datetime.utcnow() - timedelta(hours=46),
            completed_at=datetime.utcnow() - timedelta(hours=46, minutes=12),
            rows_processed=50000000,
        ),
        JobExecution(
            job_id=jobs[2].id,
            status="SUCCESS",
            started_at=datetime.utcnow() - timedelta(hours=3),
            completed_at=datetime.utcnow() - timedelta(hours=3, minutes=5),
            rows_processed=10000000,
        ),
        JobExecution(
            job_id=jobs[3].id,
            status="FAILED",
            started_at=datetime.utcnow() - timedelta(hours=1),
            completed_at=datetime.utcnow() - timedelta(minutes=55),
            error_message="Data quality check failed: 500 null values in customer_id",
        ),
    ]

    for execution in executions:
        db_session.add(execution)
    db_session.commit()


def create_sample_lineage(db_session: Session, tables: dict) -> None:
    """Create sample lineage relationships."""
    lineages = [
        Lineage(
            source_type="TABLE",
            source_name="raw_events",
            target_type="TABLE",
            target_name="analytics_summary",
            relationship_type="INPUT",
            job_id=1,
            description="Raw events feed into analytics summary",
        ),
        Lineage(
            source_type="TABLE",
            source_name="orders_table",
            target_type="TABLE",
            target_name="analytics_summary",
            relationship_type="INPUT",
            job_id=1,
            description="Orders feed into analytics",
        ),
        Lineage(
            source_type="TABLE",
            source_name="customers_table",
            target_type="VIEW",
            target_name="customer_summary_view",
            relationship_type="INPUT",
            description="Customer data feeds into summary view",
        ),
        Lineage(
            source_type="TABLE",
            source_name="staging_orders",
            target_type="TABLE",
            target_name="orders_table",
            relationship_type="TRANSFORMATION",
            job_id=2,
            description="Staging orders transformed into orders table",
        ),
    ]

    for lineage in lineages:
        db_session.add(lineage)
    db_session.commit()


def create_sample_lifecycle(db_session: Session, tables: dict) -> None:
    """Create sample asset lifecycle records."""
    # This assumes we have database sessions for tables
    # In a real scenario, we'd iterate through tables and create lifecycle records
    for table_key, table in tables.items():
        lifecycle = AssetLifecycle(
            asset_id=table.id,
            asset_type="TABLE",
            status=table.status,
            owner=table.database.owner if table.database else "unknown",
            tier=AssetTier.STANDARD if table.status == AssetStatus.ACTIVE else AssetTier.BRONZE,
            created_at=table.created_at,
            deprecated_at=None
            if table.status == AssetStatus.ACTIVE
            else datetime.utcnow() - timedelta(days=30),
            decommissioned_at=None,
        )
        db_session.add(lifecycle)
    db_session.commit()


def create_sample_usage_metrics(db_session: Session, tables: dict) -> None:
    """Create sample usage metrics."""
    for table_key, table in tables.items():
        usage = UsageMetrics(
            asset_id=table.id,
            asset_type="TABLE",
            access_count=100 if table.status == AssetStatus.ACTIVE else 5,
            last_accessed=table.last_accessed,
            query_count=50 if table.status == AssetStatus.ACTIVE else 0,
            modification_count=10 if table.status == AssetStatus.ACTIVE else 0,
        )
        db_session.add(usage)
    db_session.commit()


def create_sample_tags(db_session: Session, tables: dict) -> None:
    """Create sample asset tags."""
    tags = [
        ("1_customers_table", "tier", "critical"),
        ("1_customers_table", "pii", "true"),
        ("1_orders_table", "tier", "critical"),
        ("1_orders_table", "reporting", "true"),
        ("1_analytics_summary", "reporting", "true"),
        ("2_raw_events", "tier", "high"),
        ("2_raw_events", "raw_data", "true"),
        ("3_customer_profiles", "pii", "true"),
        ("4_old_customer_data", "deprecated", "true"),
        ("4_old_customer_data", "legacy", "true"),
    ]

    for table_key, tag_key, tag_value in tags:
        table = tables.get(table_key)
        if table:
            tag = AssetTag(
                asset_id=table.id,
                asset_type="TABLE",
                tag_key=tag_key,
                tag_value=tag_value,
            )
            db_session.add(tag)
    db_session.commit()


def populate_sample_data():
    """Main function to populate all sample data."""
    db = SessionLocal()

    try:
        print("Creating sample databases...")
        databases = create_sample_databases(db)

        print("Creating sample tables...")
        tables = create_sample_tables(db, databases)

        print("Creating sample columns...")
        create_sample_columns(db, tables)

        print("Creating sample views...")
        create_sample_views(db, databases)

        print("Creating sample jobs...")
        jobs = create_sample_jobs(db)

        print("Creating sample job executions...")
        create_sample_job_executions(db, jobs)

        print("Creating sample lineage...")
        create_sample_lineage(db, tables)

        print("Creating sample lifecycle records...")
        create_sample_lifecycle(db, tables)

        print("Creating sample usage metrics...")
        create_sample_usage_metrics(db, tables)

        print("Creating sample tags...")
        create_sample_tags(db, tables)

        print("\n✅ Sample data populated successfully!")
        print(f"  - {len(databases)} databases")
        print(f"  - {len(tables)} tables")
        print(f"  - {len(jobs)} jobs")

    except Exception as e:
        print(f"❌ Error populating sample data: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    populate_sample_data()
