"""Command-line interface for migration operations."""

import argparse
import logging
import sys
from pathlib import Path

from .aws_client import GlueClient, S3Client
from .config import MigrationConfig
from .extractor import TableExtractor
from .teradata_client import TeradataClient
from .validator import DataValidator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def extract_command(args: argparse.Namespace) -> int:
    """Handle extract command."""
    try:
        config = MigrationConfig(args.config)
        logger.info(f"Loaded configuration from {args.config}")

        # Initialize clients
        td_client = TeradataClient(config.teradata_config)
        td_client.connect()

        s3_client = S3Client(config.aws_config)
        extractor = TableExtractor(td_client, s3_client, config.config)

        # Extract specified table or all enabled tables
        if args.table:
            tables = [args.table]
        else:
            tables = [t["name"] for t in config.tables if t.get("enabled", True)]

        failed_tables = []
        for table_name in tables:
            success = extractor.extract_table(table_name, args.format)
            if not success:
                failed_tables.append(table_name)

        td_client.disconnect()

        if failed_tables:
            logger.error(f"Failed to extract {len(failed_tables)} table(s): {failed_tables}")
            return 1

        logger.info(f"Successfully extracted {len(tables) - len(failed_tables)}/{len(tables)} tables")
        return 0

    except Exception as e:
        logger.error(f"Extract command failed: {e}")
        return 1


def validate_command(args: argparse.Namespace) -> int:
    """Handle validate command."""
    try:
        config = MigrationConfig(args.config)
        logger.info(f"Loaded configuration from {args.config}")

        td_client = TeradataClient(config.teradata_config)
        td_client.connect()

        validator = DataValidator(td_client, config.config)

        if args.table:
            result = validator.validate_table(args.table)
        else:
            tables = [t["name"] for t in config.tables if t.get("enabled", True)]
            result = validator.validate_all(tables)

        td_client.disconnect()

        if result["status"] == "passed":
            logger.info("All validation checks passed")
            return 0
        else:
            logger.warning(f"Validation failed: {result}")
            return 1

    except Exception as e:
        logger.error(f"Validate command failed: {e}")
        return 1


def status_command(args: argparse.Namespace) -> int:
    """Handle status command."""
    try:
        config = MigrationConfig(args.config)

        td_client = TeradataClient(config.teradata_config)
        td_client.connect()

        logger.info("Migration Status Report")
        logger.info("=" * 50)

        for table in config.tables:
            if not table.get("enabled", True):
                logger.info(f"[DISABLED] {table['name']}")
                continue

            try:
                row_count = td_client.get_row_count(table["name"])
                logger.info(f"[ACTIVE] {table['name']}: {row_count:,} rows")
            except Exception as e:
                logger.error(f"[ERROR] {table['name']}: {e}")

        td_client.disconnect()
        return 0

    except Exception as e:
        logger.error(f"Status command failed: {e}")
        return 1


def main() -> int:
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description="Teradata to AWS Migration Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract all enabled tables
  python -m migration extract --config config/migration_config.yaml

  # Extract specific table
  python -m migration extract --table schema.table_name --config config/migration_config.yaml

  # Validate data
  python -m migration validate --config config/migration_config.yaml

  # Check migration status
  python -m migration status --config config/migration_config.yaml
        """
    )

    parser.add_argument(
        "--config",
        type=str,
        default="config/migration_config.yaml",
        help="Path to configuration file"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Extract subcommand
    extract_parser = subparsers.add_parser("extract", help="Extract data from Teradata")
    extract_parser.add_argument("--table", help="Specific table to extract (optional)")
    extract_parser.add_argument(
        "--format",
        choices=["parquet", "csv", "json"],
        default="parquet",
        help="Output format"
    )
    extract_parser.set_defaults(func=extract_command)

    # Validate subcommand
    validate_parser = subparsers.add_parser("validate", help="Validate extracted data")
    validate_parser.add_argument("--table", help="Specific table to validate (optional)")
    validate_parser.set_defaults(func=validate_command)

    # Status subcommand
    status_parser = subparsers.add_parser("status", help="Show migration status")
    status_parser.set_defaults(func=status_command)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
