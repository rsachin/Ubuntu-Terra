"""
Synthetic demo NDVI fixture for the Ubuntu Terra hackathon.

This is intentionally separate from real satellite data and is clearly marked as
an artificial demonstration trigger, not a live NDVI reading from Copernicus or
any other remote source. It exists to exercise the Medium/High risk workflow in
showcase mode without relying on a production-quality remote feed.
"""
from __future__ import annotations

import datetime as dt
import os

import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/ubuntu_terra",
)


def demo_ndvi_rows(base_date: dt.date | None = None):
    base_date = base_date or dt.date.today()
    return [
        (base_date - dt.timedelta(days=4), 0.68, 18.0, 22.0),
        (base_date - dt.timedelta(days=3), 0.62, 16.0, 23.5),
        (base_date - dt.timedelta(days=2), 0.54, 9.0, 25.5),
        (base_date - dt.timedelta(days=1), 0.47, 4.0, 27.5),
        (base_date, 0.39, 1.0, 29.0),
    ]


def seed_demo_ndvi_trigger(field_name: str = "Demo Field — Gamtoos Valley Citrus Block") -> int:
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM fields WHERE name = %s",
                (field_name,),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Field named '{field_name}' not found")

            field_id = row[0]
            for row_date, ndvi, rainfall_mm, temp_c in demo_ndvi_rows():
                cur.execute(
                    """
                    INSERT INTO readings (field_id, date, ndvi_value, rainfall_mm, temp_c, source)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (field_id, date, source) DO UPDATE SET
                        ndvi_value = EXCLUDED.ndvi_value,
                        rainfall_mm = EXCLUDED.rainfall_mm,
                        temp_c = EXCLUDED.temp_c
                    """,
                    (field_id, row_date, ndvi, rainfall_mm, temp_c, "demo_trigger"),
                )
            conn.commit()
            return field_id
    finally:
        conn.close()


if __name__ == "__main__":
    field_id = seed_demo_ndvi_trigger()
    print(f"Seeded demo NDVI trigger for field id {field_id}.")
