import os
import json
from datetime import datetime

import requests
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

BASE_URL = "http://api.openweathermap.org/data/2.5/air_pollution"
BUCKET_NAME = "raw-data"

CITIES = {
    "paris": {"lat": 48.8566, "lon": 2.3522},
    "marseille": {"lat": 43.2965, "lon": 5.3698},
    "lyon": {"lat": 45.7640, "lon": 4.8357},
    "lille": {"lat": 50.6292, "lon": 3.0573},
    "strasbourg": {"lat": 48.5734, "lon": 7.7521},
}


def extract(lat: float, lon: float) -> dict | None:
    if not OPENWEATHER_API_KEY:
        raise ValueError("OPENWEATHER_API_KEY missing")

    params = {"lat": lat, "lon": lon, "appid": OPENWEATHER_API_KEY}
    response = requests.get(BASE_URL, params=params, timeout=10)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"API error status {response.status_code} for lat={lat}, lon={lon}")
        return None


def parse_response(city: str, raw_data: dict) -> dict:
    measurement = raw_data["list"][0]
    components = measurement["components"]

    return {
        "city": city,
        "extraction_date": datetime.now().isoformat(),
        "measurement_date": datetime.fromtimestamp(measurement["dt"]).isoformat(),
        "aqi": measurement["main"]["aqi"],
        "co": components.get("co"),
        "no": components.get("no"),
        "no2": components.get("no2"),
        "o3": components.get("o3"),
        "so2": components.get("so2"),
        "pm2_5": components.get("pm2_5"),
        "pm10": components.get("pm10"),
        "nh3": components.get("nh3"),
    }


def load_csv_local(df: pd.DataFrame) -> str:
    os.makedirs("data", exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    filepath = f"data/air_quality_{today}.csv"
    df.to_csv(filepath, index=False)
    return filepath


def load_raw_supabase(city: str, row: dict) -> str:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("SUPABASE_URL or SUPABASE_KEY missing")

    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    timestamp = datetime.now().strftime("%Y-%m-%dT%Hh")
    path = f"raw/{city}/{timestamp}.json"
    content = json.dumps(row, ensure_ascii=False, indent=2).encode("utf-8")

    client.storage.from_(BUCKET_NAME).upload(
        path=path,
        file=content,
        file_options={"content-type": "application/json", "upsert": "true"},
    )
    return path


def main():
    rows = []

    for city, coords in CITIES.items():
        print(f"Extracting {city}")
        raw = extract(coords["lat"], coords["lon"])

        if raw is None:
            print(f" skipped ({city})")
            continue

        row = parse_response(city, raw)
        rows.append(row)

        path = load_raw_supabase(city, row)
        print(f" uploaded to Supabase : {path}")

    if not rows:
        print("No data retrieved, stopping")
        return

    df = pd.DataFrame(rows)
    print("\nDataFrame preview :")
    print(df)

    filepath = load_csv_local(df)
    print(f"\nCSV saved locally : {filepath}")

if __name__ == "__main__":
    main()