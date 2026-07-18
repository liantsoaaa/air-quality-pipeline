import os
import sys

import pandas as pd
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BUCKET_NAME = "raw-data"

REQUIRED_COLUMNS = ["city", "pays", "latitude", "longitude", "measurement_date", "aqi", "co", "no", "no2", "o3", "so2", "pm2_5", "pm10", "nh3"]

EXPECTED_CITIES = ["paris", "marseille", "lyon", "lille", "strasbourg"]


def get_client():
    if SUPABASE_URL == None or SUPABASE_KEY == None:
        print("SUPABASE_URL or SUPABASE_KEY missing")
        raise SystemExit(1)
    return create_client(SUPABASE_URL, SUPABASE_KEY)
