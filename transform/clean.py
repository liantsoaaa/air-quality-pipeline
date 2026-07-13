import os
import json
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv
from supabase import create_client

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


def list_all_files(client, folder: str) -> list[str]:
    files = []
    offset = 0
    limit = 100
    while True:
        batch = client.storage.from_(BUCKET_NAME).list(
            folder, {"limit": limit, "offset": offset}
        )
        if not batch:
            break
        files.extend(f["name"] for f in batch)
        if len(batch) < limit:
            break
        offset += limit
    return files


if __name__ == "__main__":
    client = get_client()
    for city in CITY_INFO:
        files = list_all_files(client, f"raw/{city}")
        print(f"{city}: {len(files)} files found")