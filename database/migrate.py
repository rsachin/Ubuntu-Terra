"""
database/migrate.py

Single ordered migration runner for Ubuntu Terra.

Applies all numbered SQL migrations in `migrations/` in ascending order.
Migrations are idempotent (`IF NOT EXISTS`) so re-running is safe.

Usage:
    python migrate.py              # apply all migrations
    python migrate.py --seed       # apply migrations and seed demo fields
    python migrate.py --reset      # drop + recreate the database, then migrate + seed

Requires DATABASE_URL to be set in the environment (see ../.env.example).
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv()

DEFAULT_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/ubuntu_terra"
DATABASE_URL = os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


def _list_migration_files() -> list[Path]:
    """Return migration .sql files sorted 001, 002, ..."""
    files = sorted(MIGRATIONS_DIR.glob("[0-9][0-9][0-9]_*.sql"))
    if not files:
        raise RuntimeError(f"No migration files found in {MIGRATIONS_DIR}")
    return files


def _run_sql_file(database_url: str, sql_path: Path) -> None:
    """Execute a single SQL file via psql so we can use psql-specific syntax if needed."""
    result = subprocess.run(
        ["psql", database_url, "-f", str(sql_path), "-v", "ON_ERROR_STOP=1"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"Migration failed: {sql_path}")
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        raise RuntimeError(f"Migration {sql_path.name} failed")
    print(f"Applied {sql_path.name}")


def _database_exists(database_url: str, db_name: str) -> bool:
    """Check whether a database exists by querying the postgres maintenance DB."""
    # Strip the path/db name from the URL to connect to the maintenance database.
    # DATABASE_URL looks like: postgresql://user:pass@host:port/dbname
    base_url = database_url.rsplit("/", 1)[0] + "/postgres"
    try:
        conn = psycopg2.connect(base_url)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (db_name,),
            )
            exists = cur.fetchone() is not None
        conn.close()
        return exists
    except Exception as e:
        print(f"Could not connect to maintenance database: {e}", file=sys.stderr)
        return False


def _create_database(database_url: str, db_name: str) -> None:
    base_url = database_url.rsplit("/", 1)[0] + "/postgres"
    conn = psycopg2.connect(base_url)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(f"CREATE DATABASE {db_name}")
    conn.close()
    print(f"Created database {db_name}")


def _drop_database(database_url: str, db_name: str) -> None:
    base_url = database_url.rsplit("/", 1)[0] + "/postgres"
    conn = psycopg2.connect(base_url)
    conn.autocommit = True
    with conn.cursor() as cur:
        # Terminate existing connections before dropping.
        cur.execute(
            """
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = %s AND pid <> pg_backend_pid()
            """,
            (db_name,),
        )
        cur.execute(f"DROP DATABASE IF EXISTS {db_name}")
    conn.close()
    print(f"Dropped database {db_name}")


def _seed_demo_fields() -> None:
    """Run the demo field seeder using the same Python interpreter."""
    seed_script = Path(__file__).resolve().parent / "seed_demo_fields.py"
    result = subprocess.run(
        [sys.executable, str(seed_script)],
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        raise RuntimeError("Demo field seeding failed")


def migrate(*, reset: bool = False, seed: bool = False) -> None:
    # Parse database name from DATABASE_URL
    db_name = DATABASE_URL.rsplit("/", 1)[-1]

    if reset:
        _drop_database(DATABASE_URL, db_name)
        _create_database(DATABASE_URL, db_name)

    # Ensure the database exists before applying migrations
    if not _database_exists(DATABASE_URL, db_name):
        print(f"Database {db_name} does not exist; creating it...")
        _create_database(DATABASE_URL, db_name)

    files = _list_migration_files()
    print(f"Applying {len(files)} migration(s) to {DATABASE_URL}")
    for sql_file in files:
        _run_sql_file(DATABASE_URL, sql_file)
    print("All migrations applied successfully.")

    if seed:
        print("Seeding demo fields...")
        _seed_demo_fields()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apply Ubuntu Terra database migrations in order."
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Seed demo fields after applying migrations",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop and recreate the database before migrating (destroys data)",
    )
    args = parser.parse_args()

    migrate(reset=args.reset, seed=args.seed)


if __name__ == "__main__":
    main()
