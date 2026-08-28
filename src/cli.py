"""Command-line interface for metadata catalog management."""

import click
import logging
from datetime import datetime

from src.config import settings
from src.catalog.database import init_db, get_session
from src.catalog.services.sync import create_sync_service
from src.catalog.utils import (
    get_unused_assets,
    get_decommissioning_candidates,
    get_asset_summary,
    mark_asset_for_decommissioning,
    decommission_asset,
)
from src.connectors.teradata import TeradataConnector
from src.connectors.mainframe import MockMainframeConnector
from src.catalog.services.mainframe_sync import create_mainframe_sync_service

# Configure logging
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@click.group()
def cli():
    """Database Metadata Catalog CLI."""
    pass


@cli.command()
def init():
    """Initialize the catalog database."""
    try:
        click.echo("Initializing catalog database...")
        init_db()
        click.echo(click.style("✓ Database initialized successfully", fg="green"))
    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg="red"), err=True)
        exit(1)


@cli.command()
@click.option(
    "--days",
    default=90,
    help="Number of days of inactivity to consider as unused (default: 90)",
)
def unused_assets(days):
    """List assets not accessed for specified days."""
    try:
        db = get_session()
        result = get_unused_assets(db, days)
        db.close()

        click.echo(f"\nAssets unused for {days} days (threshold: {result['threshold_date'].date()}):")
        click.echo(f"Found {result['unused_table_count']} unused tables\n")

        if result["unused_tables"]:
            for table in result["unused_tables"]:
                click.echo(f"  {table['database']}.{table['name']}")
                click.echo(f"    Created: {table['created_at']}")
                click.echo(f"    Last accessed: {table['last_accessed'] or 'Never'}")
    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg="red"), err=True)
        exit(1)


@cli.command()
@click.option(
    "--days",
    default=180,
    help="Number of days of inactivity to consider as decommissioning candidate (default: 180)",
)
def decommissioning_candidates(days):
    """List candidates for decommissioning."""
    try:
        db = get_session()
        result = get_decommissioning_candidates(db, days)
        db.close()

        click.echo(f"\nAssets unused for {days} days (threshold: {result['threshold_date'].date()}):")
        click.echo(f"Found {result['candidate_count']} decommissioning candidates\n")

        if result["candidates"]:
            for candidate in result["candidates"]:
                click.echo(f"  {candidate['database']}.{candidate['name']}")
                click.echo(f"    Created: {candidate['created_at']}")
                click.echo(f"    Last accessed: {candidate['last_accessed'] or 'Never'}")
                click.echo(f"    Size: {candidate['size_mb']:.2f} MB" if candidate["size_mb"] else "    Size: Unknown")
                click.echo(f"    Rows: {candidate['row_count']}" if candidate["row_count"] else "    Rows: Unknown")
                click.echo()
    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg="red"), err=True)
        exit(1)


@cli.command()
def summary():
    """Get catalog summary statistics."""
    try:
        db = get_session()
        stats = get_asset_summary(db)
        db.close()

        click.echo("\n" + click.style("Catalog Summary", bold=True))
        click.echo("=" * 40)
        click.echo(f"Total Tables: {stats['total_tables']}")
        click.echo(f"  Active: {stats['active_tables']}")
        click.echo(f"  Inactive: {stats['inactive_tables']}")
        click.echo(f"  Deprecated: {stats['deprecated_tables']}")
        click.echo(f"  Decommissioned: {stats['decommissioned_tables']}")
        click.echo(f"\nTotal Storage: {stats['total_size_mb']:.2f} MB")
        click.echo()
    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg="red"), err=True)
        exit(1)


@cli.command()
@click.option("--no-stats", is_flag=True, help="Skip table statistics collection")
def sync(no_stats):
    """Sync metadata from Teradata."""
    try:
        click.echo("Connecting to Teradata...")
        connector = TeradataConnector(
            host=settings.teradata_host,
            port=settings.teradata_port,
            user=settings.teradata_user,
            password=settings.teradata_password,
            database=settings.teradata_database,
        )
        connector.connect()
        click.echo(click.style("✓ Connected to Teradata", fg="green"))

        db = get_session()

        click.echo("\nStarting metadata synchronization...")
        sync_service = create_sync_service(db, connector)
        stats = sync_service.sync_all_metadata()

        click.echo(click.style("\n✓ Synchronization completed", fg="green"))
        click.echo(f"\nResults:")
        click.echo(f"  Databases: {stats['databases_created']} created, {stats['databases_updated']} updated")
        click.echo(f"  Tables: {stats['tables_created']} created, {stats['tables_updated']} updated")
        click.echo(f"  Columns: {stats['columns_created']} created, {stats['columns_updated']} updated")
        click.echo(f"  Views: {stats['views_created']} created, {stats['views_updated']} updated")

        if stats["errors"]:
            click.echo(f"\n" + click.style(f"⚠ {len(stats['errors'])} errors encountered:", fg="yellow"))
            for error in stats["errors"][:5]:  # Show first 5 errors
                click.echo(f"  - {error}")
            if len(stats["errors"]) > 5:
                click.echo(f"  ... and {len(stats['errors']) - 5} more")

        connector.disconnect()
        db.close()

    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg="red"), err=True)
        exit(1)


@cli.command()
def mainframe_sync():
    """Sync jobs, files, and schedules from the mainframe."""
    try:
        click.echo("Connecting to mainframe data source...")
        connector = MockMainframeConnector()
        connector.connect()
        click.echo(click.style("✓ Connected", fg="green"))

        db = get_session()

        click.echo("\nStarting mainframe job synchronization...")
        sync_service = create_mainframe_sync_service(db, connector)
        stats = sync_service.sync_all_jobs()

        click.echo(click.style("\n✓ Synchronization completed", fg="green"))
        click.echo(f"\nResults:")
        click.echo(f"  Jobs: {stats['jobs_created']} created, {stats['jobs_updated']} updated")
        click.echo(f"  Files synced: {stats['files_synced']}")

        if stats["errors"]:
            click.echo(f"\n" + click.style(f"⚠ {len(stats['errors'])} errors encountered:", fg="yellow"))
            for error in stats["errors"][:5]:
                click.echo(f"  - {error}")

        connector.disconnect()
        db.close()

    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg="red"), err=True)
        exit(1)


@cli.command()
@click.argument("table_id", type=int)
@click.option("--reason", help="Reason for decommissioning")
def deprecate(table_id, reason):
    """Mark a table for decommissioning."""
    try:
        db = get_session()
        if mark_asset_for_decommissioning(db, table_id, reason):
            click.echo(click.style(f"✓ Table {table_id} marked for decommissioning", fg="green"))
        else:
            click.echo(click.style(f"✗ Table {table_id} not found", fg="red"), err=True)
        db.close()
    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg="red"), err=True)
        exit(1)


@cli.command()
@click.argument("table_id", type=int)
@click.option("--reason", help="Reason for decommissioning")
def decommission(table_id, reason):
    """Decommission a table."""
    if not click.confirm(f"Are you sure you want to decommission table {table_id}?"):
        click.echo("Cancelled.")
        return

    try:
        db = get_session()
        if decommission_asset(db, table_id, reason):
            click.echo(click.style(f"✓ Table {table_id} decommissioned", fg="green"))
        else:
            click.echo(click.style(f"✗ Table {table_id} not found", fg="red"), err=True)
        db.close()
    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg="red"), err=True)
        exit(1)


if __name__ == "__main__":
    cli()
