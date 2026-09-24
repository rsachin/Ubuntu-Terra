"""
app/db.py

Thin psycopg2 connection helper. Kept deliberately simple (no ORM) to match
the rest of this hackathon build — see planning.md's "no unnecessary
abstraction" note in Code Quality.
"""
from dotenv import load_dotenv
load_dotenv()

import os

import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/ubuntu_terra"
)


def get_connection():
    """Returns a new connection with dict-style row access (row['col'])."""
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)