#!/usr/bin/env python
"""Export duplicate records from database to file.

This script connects to a SQLite database, executes duplicate detection queries,
and writes results to both text and CSV files for easy analysis.
"""

import sqlite3
import csv
from pathlib import Path
from typing import List, Tuple
from datetime import datetime


def read_sql_file(filepath: str) -> str:
    """Read SQL queries from file."""
    with open(filepath, "r") as f:
        return f.read()


def split_queries(sql_content: str) -> List[str]:
    """Split SQL file into individual queries."""
    # Split by semicolons and filter empty queries
    queries = [q.strip() for q in sql_content.split(";") if q.strip()]
    return queries


def execute_duplicate_check(db_path: str, sql_file: str) -> dict:
    """Execute duplicate detection queries and collect results."""
    results = {}

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        sql_content = read_sql_file(sql_file)
        queries = split_queries(sql_content)

        for query in queries:
            try:
                cursor.execute(query)
                rows = cursor.fetchall()

                # Extract check type from first result if available
                if rows:
                    check_type = rows[0]["check_type"] if "check_type" in rows[0].keys() else "Unknown"
                    results[check_type] = [dict(row) for row in rows]

            except sqlite3.OperationalError as e:
                print(f"Warning: Query failed (table may not exist): {e}")

        conn.close()
        return results

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return {}


def write_results_to_file(results: dict, output_file: str) -> None:
    """Write duplicate results to text file."""
    with open(output_file, "w") as f:
        f.write(f"Duplicate Detection Report\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write("=" * 80 + "\n\n")

        if not results:
            f.write("No duplicates found in the database.\n")
            return

        for check_type, records in results.items():
            f.write(f"\n{check_type}\n")
            f.write("-" * 80 + "\n")

            if not records:
                f.write("No duplicates found for this check.\n")
            else:
                for record in records:
                    f.write(f"\n")
                    for key, value in record.items():
                        f.write(f"  {key}: {value}\n")

            f.write("\n")


def write_results_to_csv(results: dict, output_file: str) -> None:
    """Write duplicate results to CSV file."""
    with open(output_file, "w", newline="") as f:
        writer = csv.writer(f)

        # Write header
        writer.writerow(["Check Type", "Details", "Count", "Record IDs"])

        if results:
            for check_type, records in results.items():
                for record in records:
                    count = record.get("count", "N/A")
                    record_ids = record.get("user_ids") or record.get("post_ids") or record.get("comment_ids", "N/A")

                    # Build details string
                    details_parts = []
                    for key, value in record.items():
                        if key not in ["check_type", "count", "user_ids", "post_ids", "comment_ids"]:
                            details_parts.append(f"{key}={value}")

                    details = "; ".join(details_parts)

                    writer.writerow([check_type, details, count, record_ids])


def main() -> int:
    """Run duplicate detection and export results."""
    # Paths
    script_dir = Path(__file__).parent
    sql_file = script_dir / "find_duplicates.sql"
    db_path = "suman_narla.db"  # Adjust to your database path

    # Output files
    output_dir = script_dir / "duplicates_output"
    output_dir.mkdir(exist_ok=True)

    text_output = output_dir / f"duplicates_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    csv_output = output_dir / f"duplicates_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    print(f"Checking for duplicates in: {db_path}")
    print(f"Using SQL file: {sql_file}")

    if not sql_file.exists():
        print(f"Error: SQL file not found at {sql_file}")
        return 1

    # Execute duplicate detection
    results = execute_duplicate_check(db_path, str(sql_file))

    # Write results
    write_results_to_file(results, str(text_output))
    write_results_to_csv(results, str(csv_output))

    # Print summary
    print(f"\nResults exported to:")
    print(f"  Text: {text_output}")
    print(f"  CSV:  {csv_output}")

    total_duplicates = sum(len(records) for records in results.values())
    print(f"\nTotal duplicate groups found: {total_duplicates}")

    return 0


if __name__ == "__main__":
    exit(main())
