import os
import json
import time
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

HISTORY_URL = "http://api.openweathermap.org/data/2.5/air_pollution/history"
BUCKET_NAME = "raw-data"

CITIES = {
    "paris": {"lat": 48.8566, "lon": 2.3522},
    "marseille": {"lat": 43.2965, "lon": 5.3698},
    "lyon": {"lat": 45.7640, "lon": 4.8357},
    "lille": {"lat": 50.6292, "lon": 3.0573},
    "strasbourg": {"lat": 48.5734, "lon": 7.7521},
}

START_DATE = datetime(2025, 7, 1, tzinfo=timezone.utc)
END_DATE = datetime(2026, 7, 1, tzinfo=timezone.utc)


def month_ranges(start: datetime, end: datetime):
    current = start
    while current < end:
        if current.month == 12:
            next_month = current.replace(year=current.year + 1, month=1)
        else:
            next_month = current.replace(month=current.month + 1)
        month_end = min(next_month, end)
        label = current.strftime("%Y-%m")
        yield current, month_end, label
        current = next_month


def fetch_history(lat: float, lon: float, start: datetime, end: datetime) -> dict | None:
    if not OPENWEATHER_API_KEY:
        raise ValueError("OPENWEATHER_API_KEY missing")

    params = {
        "lat": lat,
        "lon": lon,
        "start": int(start.timestamp()),
        "end": int(end.timestamp()),
        "appid": OPENWEATHER_API_KEY,
    }
    response = requests.get(HISTORY_URL, params=params, timeout=30)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"API error - status {response.status_code} for lat={lat}, lon={lon}")
        return None


def upload_backfill_month(city: str, label: str, data: dict) -> str:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("SUPABASE_URL or SUPABASE_KEY missing")

    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    path = f"raw/{city}/backfill_{label}.json"
    content = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")

    client.storage.from_(BUCKET_NAME).upload(
        path=path,
        file=content,
        file_options={"content-type": "application/json", "upsert": "true"},
    )
    return path


def main():
    for city, coords in CITIES.items():
        print(f"\nBackfill for {city}...")

        for month_start, month_end, label in month_ranges(START_DATE, END_DATE):
            print(f"  {label}...")
            data = fetch_history(coords["lat"], coords["lon"], month_start, month_end)

            if data is None or not data.get("list"):
                print(f"    -> no data, skipped")
                continue

            path = upload_backfill_month(city, label, data)
            print(f"    -> uploaded: {path} ({len(data['list'])} records)")

            time.sleep(1)


if __name__ == "__main__":
    main()
