import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/ubuntu_terra")

with psycopg2.connect(DATABASE_URL) as conn:
    with conn.cursor() as cur:
        with open("migrations/005_owner_tokens.sql") as f:
            cur.execute(f.read())
    conn.commit()
print("Migration 005 applied successfully.")
