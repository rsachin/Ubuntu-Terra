"""
seed_demo_fields.py

Seeds the 2-3 real demo field boundaries chosen for the Ubuntu Terra hackathon demo.

Demo region: the Gamtoos River Valley and neighbouring Sundays River Valley,
Eastern Cape — one of South Africa's most persistently water-stressed farming
regions. Farmers on the Gamtoos scheme (Patensie, Hankey) draw from the Kouga
Dam and have been under recurring agricultural water-use quotas (as low as 40%
of full allocation in drought years); the Sundays River Valley (Kirkwood) draws
from the Gariep Dam scheme via a longer, generally more reliable transfer
system. Using one field from each gives the demo a real "under stress" vs.
"comparatively secure" contrast.

IMPORTANT — boundary accuracy: exact cadastral (surveyed) field boundaries for
individual private farms are not public data. The polygons below are small
(~300m x 300m) representative rectangles centred on real, named farming
locations (real town coordinates, confirmed via public sources), NOT the
actual surveyed boundary of any specific farm. This is accurate enough for a
hackathon demo pulling real satellite/weather data for that location, but
should not be presented as an exact legal field boundary.

Run with:
    python seed_demo_fields.py
Requires DATABASE_URL to be set (see ../.env.example).
"""
from dotenv import load_dotenv
load_dotenv()

import os

import psycopg2
from psycopg2.extras import execute_values

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/ubuntu_terra"
)


def make_square_wkt(center_lat: float, center_lon: float, half_side_deg: float = 0.0015) -> str:
    """
    Build a small square polygon (WKT, lon/lat order for PostGIS) centred on
    the given point. ~0.0015 degrees ~= 150-170m at this latitude, so the
    square is roughly 300m x 300m — a plausible single-field size.
    """
    lat_min, lat_max = center_lat - half_side_deg, center_lat + half_side_deg
    lon_min, lon_max = center_lon - half_side_deg, center_lon + half_side_deg
    return (
        f"POLYGON(({lon_min} {lat_min}, {lon_max} {lat_min}, "
        f"{lon_max} {lat_max}, {lon_min} {lat_max}, {lon_min} {lat_min}))"
    )


# Real, named, publicly-documented farming locations. Coordinates are town-
# centre reference points for each location (confirmed via public sources);
# each field polygon is offset slightly from the town centre toward the
# surrounding farmland/irrigation scheme, not placed directly on the town.
DEMO_FIELDS = [
    {
        "name": "Patensie Citrus Block — Gamtoos Valley",
        "owner_id": "demo",
        # Patensie, Eastern Cape: -33.75889, 24.81472. Kouga Dam-fed, citrus/
        # tobacco/vegetables, recurring agricultural water quota restrictions.
        "center_lat": -33.7550,
        "center_lon": 24.8080,
    },
    {
        "name": "Hankey Vegetable Field — Gamtoos Valley",
        "owner_id": "demo",
        # Hankey, Eastern Cape: -33.83139, 24.88083. Also on the Kouga Dam
        # scheme; Gamtoos Valley vegetable production (potatoes, cauliflower,
        # lettuce, broccoli) has seen production cut sharply in drought years.
        "center_lat": -33.8280,
        "center_lon": 24.8750,
    },
    {
        "name": "Kirkwood Citrus Block — Sundays River Valley",
        "owner_id": "demo",
        # Kirkwood, Eastern Cape: -33.40028, 25.44250. Sundays River Valley,
        # fed by the Gariep Dam transfer scheme — comparatively more secure
        # water supply than the Gamtoos scheme. Used as the "healthier" field
        # for contrast in the demo.
        "center_lat": -33.4050,
        "center_lon": 25.4500,
    },
]


def main():
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn, conn.cursor() as cur:
            rows = [
                (f["name"], f["owner_id"], make_square_wkt(f["center_lat"], f["center_lon"]))
                for f in DEMO_FIELDS
            ]
            execute_values(
                cur,
                """
                INSERT INTO fields (name, owner_id, boundary)
                VALUES %s
                """,
                rows,
                template="(%s, %s, ST_GeomFromText(%s, 4326))",
            )
        print(f"Seeded {len(DEMO_FIELDS)} demo fields.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
