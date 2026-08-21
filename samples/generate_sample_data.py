#!/usr/bin/env python
"""Generate sample data for testing migration."""

import argparse
import csv
import json
import random
from datetime import datetime, timedelta
from pathlib import Path


class SampleDataGenerator:
    """Generate realistic sample data for testing."""

    FIRST_NAMES = ["John", "Jane", "Bob", "Alice", "Charlie", "Diana", "Eve", "Frank"]
    LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis"]
    DOMAINS = ["gmail.com", "company.com", "example.com", "acme.com", "corp.net"]
    COUNTRIES = ["USA", "Canada", "UK", "Germany", "France", "Japan", "Australia", "India"]
    STATES = ["CA", "NY", "TX", "FL", "IL", "PA", "OH", "GA", "NC", "MI"]
    CITIES = {"USA": ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix"],
              "Canada": ["Toronto", "Vancouver", "Montreal", "Calgary", "Ottawa"],
              "UK": ["London", "Manchester", "Birmingham", "Leeds", "Glasgow"]}
    STATUSES = ["ACTIVE", "SUSPENDED", "INACTIVE", "PENDING"]
    ORDER_STATUSES = ["DELIVERED", "IN_TRANSIT", "PENDING", "CANCELLED"]
    PAYMENT_METHODS = ["WIRE_TRANSFER", "CREDIT_CARD", "BANK_TRANSFER", "CHECK"]

    def __init__(self, seed=42):
        """Initialize generator with optional seed for reproducibility."""
        random.seed(seed)

    def generate_customers(self, count=1000, filename="sample_customers.csv"):
        """Generate sample customer records."""
        print(f"Generating {count} customer records...")

        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'customer_id', 'customer_name', 'email', 'phone', 'country',
                'city', 'state', 'postal_code', 'created_date', 'updated_date',
                'account_status', 'credit_limit', 'total_purchases'
            ])
            writer.writeheader()

            base_date = datetime(2020, 1, 1)

            for i in range(1, count + 1):
                first_name = random.choice(self.FIRST_NAMES)
                last_name = random.choice(self.LAST_NAMES)
                country = random.choice(self.COUNTRIES)
                city = random.choice(self.CITIES.get(country, ["Unknown"]))
                state = random.choice(self.STATES) if country == "USA" else ""
                created_days_ago = random.randint(100, 1600)
                created_date = base_date + timedelta(days=created_days_ago)
                updated_date = created_date + timedelta(days=random.randint(0, 200))

                writer.writerow({
                    'customer_id': i,
                    'customer_name': f"{first_name} {last_name}",
                    'email': f"{first_name.lower()}.{last_name.lower()}@{random.choice(self.DOMAINS)}",
                    'phone': f"555-{random.randint(1000, 9999)}",
                    'country': country,
                    'city': city,
                    'state': state,
                    'postal_code': f"{random.randint(10000, 99999)}",
                    'created_date': created_date.strftime('%Y-%m-%d'),
                    'updated_date': updated_date.strftime('%Y-%m-%d'),
                    'account_status': random.choice(self.STATUSES),
                    'credit_limit': round(random.uniform(50000, 2000000), 2),
                    'total_purchases': round(random.uniform(0, 5000000), 2) if random.random() > 0.05 else None
                })

        print(f"✓ Generated {filename}")

    def generate_orders(self, count=5000, filename="sample_orders.csv", customer_count=1000):
        """Generate sample order records."""
        print(f"Generating {count} order records...")

        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'order_id', 'customer_id', 'order_date', 'delivery_date',
                'order_amount', 'tax_amount', 'total_amount', 'order_status',
                'payment_method', 'shipping_address', 'notes'
            ])
            writer.writeheader()

            base_date = datetime(2024, 1, 1)

            for i in range(1, count + 1):
                order_date = base_date + timedelta(days=random.randint(0, 200))
                order_status = random.choice(self.ORDER_STATUSES)
                delivery_date = order_date + timedelta(days=random.randint(3, 7)) if order_status != "PENDING" else None

                order_amount = round(random.uniform(1000, 100000), 2)
                tax_amount = round(order_amount * 0.1, 2)
                total_amount = round(order_amount + tax_amount, 2)

                writer.writerow({
                    'order_id': 10000 + i,
                    'customer_id': random.randint(1, customer_count),
                    'order_date': order_date.strftime('%Y-%m-%d'),
                    'delivery_date': delivery_date.strftime('%Y-%m-%d') if delivery_date else None,
                    'order_amount': order_amount,
                    'tax_amount': tax_amount,
                    'total_amount': total_amount,
                    'order_status': order_status,
                    'payment_method': random.choice(self.PAYMENT_METHODS),
                    'shipping_address': f"{random.choice(self.CITIES['USA'])} {random.choice(self.STATES)}",
                    'notes': random.choice(["Priority", "Rush", "Standard", None])
                })

        print(f"✓ Generated {filename}")

    def generate_extraction_metadata(self, table_name="sales.customers", row_count=1000,
                                    batch_count=10, filename="extraction_metadata.json"):
        """Generate extraction metadata."""
        print(f"Generating extraction metadata for {table_name}...")

        batch_size = row_count // batch_count
        batches = []

        for i in range(1, batch_count + 1):
            rows_in_batch = batch_size if i < batch_count else (row_count - (batch_count - 1) * batch_size)
            batches.append({
                "batch_number": i,
                "row_count": rows_in_batch,
                "file_size_bytes": rows_in_batch * random.randint(100, 300),
                "s3_key": f"raw/{table_name}/batch_{i:05d}.parquet",
                "checksum": f"{random.getrandbits(128):032x}"
            })

        metadata = {
            "table_name": table_name,
            "extraction_timestamp": datetime.utcnow().isoformat() + "Z",
            "total_rows": row_count,
            "total_batches": batch_count,
            "format": "parquet",
            "compression": "snappy",
            "batch_details": batches,
            "schema": {
                "id": "INTEGER",
                "name": "VARCHAR(255)",
                "amount": "DECIMAL(15,2)",
                "date": "DATE",
                "status": "VARCHAR(20)"
            },
            "extraction_duration_seconds": random.randint(30, 3600),
            "rows_per_second": row_count / random.randint(30, 3600),
            "validation_results": {
                "row_count_match": True,
                "schema_match": True,
                "data_quality_score": round(random.uniform(95, 100), 1)
            }
        }

        with open(filename, 'w') as f:
            json.dump(metadata, f, indent=2)

        print(f"✓ Generated {filename}")

    def generate_all(self, output_dir="samples"):
        """Generate all sample data files."""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        print(f"Generating sample data in {output_dir}/")
        print("-" * 50)

        # Generate main data files
        self.generate_customers(count=100, filename=str(output_path / "generated_customers.csv"))
        self.generate_orders(count=500, filename=str(output_path / "generated_orders.csv"), customer_count=100)

        # Generate metadata
        self.generate_extraction_metadata(
            "sales.customers",
            row_count=100,
            batch_count=5,
            filename=str(output_path / "generated_customers_metadata.json")
        )
        self.generate_extraction_metadata(
            "sales.orders",
            row_count=500,
            batch_count=10,
            filename=str(output_path / "generated_orders_metadata.json")
        )

        print("-" * 50)
        print("✓ Sample data generation complete!")
        print(f"  Files created in: {output_dir}/")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate sample data for migration testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate default sample data
  python generate_sample_data.py

  # Generate with custom output directory
  python generate_sample_data.py --output custom_dir

  # Generate specific dataset
  python generate_sample_data.py --customers 5000
  python generate_sample_data.py --orders 10000 --customers 1000

  # Generate with different random seed (for variety)
  python generate_sample_data.py --seed 12345
        """
    )

    parser.add_argument(
        "--output", "-o",
        default="samples",
        help="Output directory for generated files (default: samples)"
    )
    parser.add_argument(
        "--customers", "-c",
        type=int,
        default=None,
        help="Number of customer records to generate"
    )
    parser.add_argument(
        "--orders",
        type=int,
        default=None,
        help="Number of order records to generate"
    )
    parser.add_argument(
        "--seed", "-s",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)"
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Generate all data types (default)"
    )

    args = parser.parse_args()

    generator = SampleDataGenerator(seed=args.seed)

    # Create output directory
    Path(args.output).mkdir(exist_ok=True)

    if args.all or (args.customers is None and args.orders is None):
        # Generate all default
        generator.generate_all(args.output)
    else:
        # Generate specific data
        if args.customers:
            generator.generate_customers(
                count=args.customers,
                filename=str(Path(args.output) / "generated_customers.csv")
            )

        if args.orders:
            customer_count = args.customers or 1000
            generator.generate_orders(
                count=args.orders,
                filename=str(Path(args.output) / "generated_orders.csv"),
                customer_count=customer_count
            )


if __name__ == "__main__":
    main()
