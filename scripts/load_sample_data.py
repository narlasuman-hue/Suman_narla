#!/usr/bin/env python
"""Load sample data from CSV files into SQLite database.

This script reads sample data from CSV files and inserts them into
the database tables.
"""

import sqlite3
import csv
from pathlib import Path
from typing import Optional
from datetime import datetime


def create_tables(conn: sqlite3.Connection) -> None:
    """Create database tables if they don't exist."""
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(255) NOT NULL UNIQUE,
            email VARCHAR(255) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title VARCHAR(255) NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_posts_user_id ON posts(user_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_comments_post_id ON comments(post_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_comments_user_id ON comments(user_id)
    """)

    conn.commit()


def load_users(conn: sqlite3.Connection, csv_file: Path) -> int:
    """Load users from CSV file."""
    cursor = conn.cursor()
    count = 0

    try:
        with open(csv_file, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    cursor.execute("""
                        INSERT INTO users (id, username, email, password_hash)
                        VALUES (?, ?, ?, ?)
                    """, (row["id"], row["username"], row["email"], row["password_hash"]))
                    count += 1
                except sqlite3.IntegrityError as e:
                    print(f"  Warning: Could not insert user {row['username']}: {e}")

        conn.commit()
    except FileNotFoundError:
        print(f"Error: File not found: {csv_file}")

    return count


def load_posts(conn: sqlite3.Connection, csv_file: Path) -> int:
    """Load posts from CSV file."""
    cursor = conn.cursor()
    count = 0

    try:
        with open(csv_file, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    cursor.execute("""
                        INSERT INTO posts (id, user_id, title, content)
                        VALUES (?, ?, ?, ?)
                    """, (row["id"], row["user_id"], row["title"], row["content"]))
                    count += 1
                except sqlite3.IntegrityError as e:
                    print(f"  Warning: Could not insert post {row['id']}: {e}")

        conn.commit()
    except FileNotFoundError:
        print(f"Error: File not found: {csv_file}")

    return count


def load_comments(conn: sqlite3.Connection, csv_file: Path) -> int:
    """Load comments from CSV file."""
    cursor = conn.cursor()
    count = 0

    try:
        with open(csv_file, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    cursor.execute("""
                        INSERT INTO comments (id, post_id, user_id, content)
                        VALUES (?, ?, ?, ?)
                    """, (row["id"], row["post_id"], row["user_id"], row["content"]))
                    count += 1
                except sqlite3.IntegrityError as e:
                    print(f"  Warning: Could not insert comment {row['id']}: {e}")

        conn.commit()
    except FileNotFoundError:
        print(f"Error: File not found: {csv_file}")

    return count


def get_table_stats(conn: sqlite3.Connection) -> dict:
    """Get record counts for all tables."""
    cursor = conn.cursor()
    stats = {}

    for table in ["users", "posts", "comments"]:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        stats[table] = cursor.fetchone()[0]

    return stats


def main() -> int:
    """Load sample data into database."""
    # Paths
    script_dir = Path(__file__).parent
    data_dir = script_dir.parent / "data" / "sample"
    db_path = "suman_narla.db"

    print(f"Loading sample data from: {data_dir}")
    print(f"Database: {db_path}\n")

    try:
        # Connect to database
        conn = sqlite3.connect(db_path)

        # Create tables
        print("Creating tables...")
        create_tables(conn)
        print("✓ Tables created/verified\n")

        # Load data
        print("Loading sample data...")
        users_count = load_users(conn, data_dir / "users.csv")
        print(f"✓ Loaded {users_count} users")

        posts_count = load_posts(conn, data_dir / "posts.csv")
        print(f"✓ Loaded {posts_count} posts")

        comments_count = load_comments(conn, data_dir / "comments.csv")
        print(f"✓ Loaded {comments_count} comments\n")

        # Display statistics
        stats = get_table_stats(conn)
        print("Database Statistics:")
        print(f"  Users:    {stats['users']}")
        print(f"  Posts:    {stats['posts']}")
        print(f"  Comments: {stats['comments']}")

        conn.close()
        print(f"\n✓ Sample data loaded successfully!")
        return 0

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
