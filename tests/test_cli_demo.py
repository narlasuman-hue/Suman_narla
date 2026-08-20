"""Demonstration of CLI functionality with sample data."""

import json
import logging
from unittest.mock import MagicMock, patch

from migration.cli import extract_command, status_command, validate_command
from migration.config import MigrationConfig


# Configure logging for demo
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)


class CLIDemo:
    """Demonstrate CLI functionality with mock data."""

    @staticmethod
    def mock_teradata_client():
        """Create a mock Teradata client with sample data."""
        client = MagicMock()

        # Mock table schemas
        client.get_table_schema.side_effect = lambda table: {
            "sales.customers": {
                "customer_id": "INTEGER",
                "customer_name": "VARCHAR(255)",
                "email": "VARCHAR(255)",
                "country": "VARCHAR(50)",
                "credit_limit": "DECIMAL(15,2)",
                "created_date": "DATE"
            },
            "sales.orders": {
                "order_id": "INTEGER",
                "customer_id": "INTEGER",
                "order_date": "DATE",
                "order_amount": "DECIMAL(15,2)",
                "order_status": "VARCHAR(20)",
                "total_amount": "DECIMAL(15,2)"
            },
            "reference.products": {
                "product_id": "INTEGER",
                "product_name": "VARCHAR(255)",
                "price": "DECIMAL(10,2)",
                "category": "VARCHAR(50)"
            }
        }.get(table, {})

        # Mock row counts
        client.get_row_count.side_effect = lambda table: {
            "sales.customers": 125000,
            "sales.orders": 50000,
            "reference.products": 5000,
            "reference.warehouses": 500,
            "reference.currencies": 200,
            "finance.invoices": 10000,
            "finance.payments": 20000,
            "analytics.daily_sales_summary": 5000,
        }.get(table, 0)

        return client

    @staticmethod
    def demo_status_command():
        """Demonstrate status command."""
        print("\n" + "="*70)
        print("DEMO: Status Command")
        print("="*70)

        logger.info("Loading configuration from samples/sample_config.yaml")
        config = MigrationConfig("samples/sample_config.yaml")

        logger.info("Checking table status...")
        print(f"\n{'Table Name':<30} {'Status':<12} {'Row Count':<15}")
        print("-" * 70)

        with patch('migration.cli.TeradataClient') as MockClient:
            MockClient.return_value = CLIDemo.mock_teradata_client()

            # Display each table
            for table in config.tables:
                status = "ENABLED" if table.get("enabled", True) else "DISABLED"
                client = MockClient.return_value
                row_count = client.get_row_count(table["name"])

                print(f"{table['name']:<30} {status:<12} {row_count:>12,} rows")

        logger.info("Status check complete")

    @staticmethod
    def demo_validate_command():
        """Demonstrate validate command."""
        print("\n" + "="*70)
        print("DEMO: Validate Command")
        print("="*70)

        logger.info("Loading configuration...")
        config = MigrationConfig("samples/sample_config.yaml")

        print("\nValidation Results:")
        print("-" * 70)

        with patch('migration.cli.TeradataClient') as MockClient:
            MockClient.return_value = CLIDemo.mock_teradata_client()

            validation_results = {
                "sales.customers": {
                    "row_count": 125000,
                    "columns": 13,
                    "status": "✓ PASSED"
                },
                "sales.orders": {
                    "row_count": 50000,
                    "columns": 11,
                    "status": "✓ PASSED"
                },
                "reference.products": {
                    "row_count": 5000,
                    "columns": 8,
                    "status": "✓ PASSED"
                },
                "reference.warehouses": {
                    "row_count": 500,
                    "columns": 6,
                    "status": "✓ PASSED"
                }
            }

            for table, result in validation_results.items():
                print(f"\n{table}")
                print(f"  Row Count: {result['row_count']:,}")
                print(f"  Columns: {result['columns']}")
                print(f"  Status: {result['status']}")

        logger.info("Validation complete")

    @staticmethod
    def demo_extract_summary():
        """Demonstrate extraction summary."""
        print("\n" + "="*70)
        print("DEMO: Extraction Summary")
        print("="*70)

        logger.info("Loading extraction metadata...")

        with open("samples/sample_extraction_metadata.json") as f:
            metadata = json.load(f)

        print(f"\nTable: {metadata['table_name']}")
        print(f"Total Rows: {metadata['total_rows']:,}")
        print(f"Batches: {metadata['total_batches']}")
        print(f"Duration: {metadata['extraction_duration_seconds']} seconds")
        print(f"Throughput: {metadata['rows_per_second']:.1f} rows/sec")
        print(f"Compression: {metadata['compression']}")

        print(f"\nBatch Details:")
        print("-" * 70)
        print(f"{'Batch':<8} {'Rows':<12} {'Size':<15} {'S3 Key':<35}")
        print("-" * 70)

        for batch in metadata['batch_details']:
            size_mb = batch['file_size_bytes'] / (1024 * 1024)
            print(f"{batch['batch_number']:<8} {batch['row_count']:<12,} {size_mb:>6.2f} MB      "
                  f"{batch['s3_key']}")

        print(f"\nSchema:")
        print("-" * 70)
        for col, dtype in metadata['schema'].items():
            print(f"  {col:<20} {dtype}")

        print(f"\nQuality Metrics:")
        print("-" * 70)
        for col, stats in metadata['column_statistics'].items():
            if 'null_percentage' in stats:
                print(f"  {col:<20} Null: {stats['null_percentage']:.1f}%")

        logger.info("Extraction summary complete")

    @staticmethod
    def demo_migration_progress():
        """Demonstrate migration progress report."""
        print("\n" + "="*70)
        print("DEMO: Migration Progress Report")
        print("="*70)

        with open("samples/migration_status_report.txt") as f:
            report = f.read()

        # Show key sections
        lines = report.split('\n')

        # Find and display summary
        in_summary = False
        summary_lines = []
        for line in lines:
            if "SUMMARY" in line:
                in_summary = True
            elif "COMPLETED TABLES" in line:
                break
            elif in_summary and line.strip():
                summary_lines.append(line)

        for line in summary_lines[:10]:
            print(line)

        logger.info("Migration progress report displayed")

    @staticmethod
    def demo_configuration():
        """Demonstrate configuration loading."""
        print("\n" + "="*70)
        print("DEMO: Configuration Loading")
        print("="*70)

        logger.info("Loading configuration from samples/sample_config.yaml")
        config = MigrationConfig("samples/sample_config.yaml")

        print("\nTeradata Configuration:")
        print("-" * 70)
        for key, value in config.teradata_config.items():
            if key != "password":
                print(f"  {key:<20} {value}")
            else:
                print(f"  {key:<20} ****")

        print("\nAWS Configuration:")
        print("-" * 70)
        for key, value in config.aws_config.items():
            print(f"  {key:<20} {value}")

        print("\nMigration Settings:")
        print("-" * 70)
        for key, value in config.migration_config.items():
            print(f"  {key:<20} {value}")

        print(f"\nTables to Migrate: {len(config.tables)}")
        print("-" * 70)
        enabled = sum(1 for t in config.tables if t.get("enabled", True))
        print(f"  Enabled: {enabled}")
        print(f"  Disabled: {len(config.tables) - enabled}")

        logger.info("Configuration loaded successfully")

    @staticmethod
    def run_all_demos():
        """Run all demonstrations."""
        print("\n\n")
        print("╔" + "="*68 + "╗")
        print("║" + " "*68 + "║")
        print("║" + "  TERADATA TO AWS MIGRATION - CLI DEMONSTRATION  ".center(68) + "║")
        print("║" + " "*68 + "║")
        print("╚" + "="*68 + "╝")

        # Run each demo
        CLIDemo.demo_configuration()
        CLIDemo.demo_status_command()
        CLIDemo.demo_validate_command()
        CLIDemo.demo_extract_summary()
        CLIDemo.demo_migration_progress()

        # Summary
        print("\n" + "="*70)
        print("DEMO SUMMARY")
        print("="*70)
        print("""
The CLI provides three main commands:

1. STATUS COMMAND
   └─ Shows migration status for all tables
   └─ Displays row counts and table information

2. VALIDATE COMMAND
   └─ Validates extracted data quality
   └─ Checks row counts and schemas

3. EXTRACT COMMAND
   └─ Extracts Teradata tables to S3
   └─ Saves metadata and validates results

Example Usage:
   python -m migration --config config/migration_config.yaml status
   python -m migration --config config/migration_config.yaml validate
   python -m migration --config config/migration_config.yaml extract
   python -m migration --config config/migration_config.yaml extract --table sales.customers

For more information, see:
   - docs/API_REFERENCE.md - Complete API documentation
   - docs/OPERATIONS.md - Operational procedures
   - samples/README.md - Sample data guide
""")

        logger.info("All demonstrations complete!")


if __name__ == "__main__":
    CLIDemo.run_all_demos()
