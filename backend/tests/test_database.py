"""
Integration test for the database schema and seed data. Requires a running
Postgres instance with the migration applied and fields seeded (see
database/migrations/001_initial_schema.sql and database/seed_demo_fields.py).

This is deliberately NOT run as part of the default unit-test suite (it needs
a live DB), but should be run manually after any schema or seed change.
"""
import os

import psycopg2
import pytest

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/ubuntu_terra"
)


@pytest.fixture
def db_conn():
    conn = psycopg2.connect(DATABASE_URL)
    yield conn
    conn.close()


def test_all_tables_exist(db_conn):
    with db_conn.cursor() as cur:
        cur.execute(
            """
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
            """
        )
        tables = {row[0] for row in cur.fetchall()}
    assert {"fields", "readings", "risk_scores", "alerts"}.issubset(tables)


def test_three_demo_fields_seeded_with_valid_boundaries(db_conn):
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT name, ST_IsValid(boundary), ST_Area(boundary::geography) FROM fields ORDER BY id"
        )
        rows = cur.fetchall()
    assert len(rows) == 3
    for name, is_valid, area_m2 in rows:
        assert is_valid is True
        # Roughly a 300m x 300m field -> ~90,000 m^2; allow a wide margin
        assert 10_000 < area_m2 < 200_000, f"{name} boundary area looks wrong: {area_m2} m^2"
