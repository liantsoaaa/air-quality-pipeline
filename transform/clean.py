import os
import json
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv
from supabase import create_client

import time 

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BUCKET_NAME = "raw-data"

CITY_INFO = {
    "paris": {"pays": "France", "latitude": 48.8566, "longitude": 2.3522},
    "marseille": {"pays": "France", "latitude": 43.2965, "longitude": 5.3698},
    "lyon": {"pays": "France", "latitude": 45.7640, "longitude": 4.8357},
    "lille": {"pays": "France", "latitude": 50.6292, "longitude": 3.0573},
    "strasbourg": {"pays": "France", "latitude": 48.5734, "longitude": 7.7521},
}


def get_client():
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("SUPABASE_URL or SUPABASE_KEY missing")
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def list_all_files(client, folder: str, max_retries: int = 3) -> list[str]:
    files = []
    offset = 0
    limit = 100
    while True:
        batch = None
        for attempt in range(max_retries):
            try:
                batch = client.storage.from_(BUCKET_NAME).list(
                    folder, {"limit": limit, "offset": offset}
                )
                break
            except Exception as e:
                print(f"  retry {attempt + 1}/{max_retries} for {folder}: {e}")
                time.sleep(2)
        if batch is None:
            raise RuntimeError(f"Failed to list {folder} after {max_retries} attempts")

        if not batch:
            break
        files.extend(f["name"] for f in batch)
        if len(batch) < limit:
            break
        offset += limit
    return files
    
def parse_hourly_file(city: str, content: dict) -> list[dict]:
    return [{
        "city": content.get("city", city),
        "measurement_date": content.get("measurement_date"),
        "aqi": content.get("aqi"),
        "co": content.get("co"),
        "no": content.get("no"),
        "no2": content.get("no2"),
        "o3": content.get("o3"),
        "so2": content.get("so2"),
        "pm2_5": content.get("pm2_5"),
        "pm10": content.get("pm10"),
        "nh3": content.get("nh3"),
    }]


def parse_backfill_file(city: str, content: dict) -> list[dict]:
    rows = []
    for entry in content.get("list", []):
        components = entry.get("components", {})
        rows.append({
            "city": city,
            "measurement_date": datetime.fromtimestamp(entry["dt"]).isoformat(),
            "aqi": entry.get("main", {}).get("aqi"),
            "co": components.get("co"),
            "no": components.get("no"),
            "no2": components.get("no2"),
            "o3": components.get("o3"),
            "so2": components.get("so2"),
            "pm2_5": components.get("pm2_5"),
            "pm10": components.get("pm10"),
            "nh3": components.get("nh3"),
        })
    return rows


def read_raw_data() -> pd.DataFrame:
    client = get_client()
    all_rows = []

    for city in CITY_INFO:
        folder = f"raw/{city}"
        filenames = list_all_files(client, folder)
        print(f"{city}: {len(filenames)} files found")

        for filename in filenames:
            path = f"{folder}/{filename}"
            raw_bytes = client.storage.from_(BUCKET_NAME).download(path)
            content = json.loads(raw_bytes)

            if filename.startswith("backfill_"):
                rows = parse_backfill_file(city, content)
            else:
                rows = parse_hourly_file(city, content)

            all_rows.extend(rows)

    return pd.DataFrame(all_rows)


if __name__ == "__main__":
    df = read_raw_data()
    print(df.shape)
    print(df.head())