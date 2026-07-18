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

def load_clean_csv(local_path):
    if local_path != None:
        print("Loading local file:", local_path)
        df = pd.read_csv(local_path)
        return df

    client = get_client()
    print("Downloading clean/air_quality_clean.csv from Supabase Storage")
    raw_bytes = client.storage.from_(BUCKET_NAME).download("clean/air_quality_clean.csv")

    if not os.path.exists("data"):
        os.makedirs("data")

    tmp_path = "data/_validation_tmp.csv"
    f = open(tmp_path, "wb")
    f.write(raw_bytes)
    f.close()

    df = pd.read_csv(tmp_path)
    return df


if __name__ == "__main__":
    df = load_clean_csv(None)
    print(df.shape)

def check(label, condition, details=""):
    if condition:
        status = "PASS"
    else:
        status = "FAIL"

    if details != "":
        print("[" + status + "]", label, "-", details)
    else:
        print("[" + status + "]", label)

    return condition


def validate(df):
    results = []

    missing_cols = []
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            missing_cols.append(col)

    result1 = check("Required columns present", len(missing_cols) == 0, "missing: " + str(missing_cols))
    results.append(result1)

    null_count = df[REQUIRED_COLUMNS].isnull().sum().sum()
    result2 = check("No missing values", null_count == 0, str(null_count) + " null values found")
    results.append(result2)

    duplicates = df.duplicated(subset=["city", "measurement_date"]).sum()
    result3 = check("No duplicate city+hour combinations", duplicates == 0, str(duplicates) + " duplicates found")
    results.append(result3)

    return results


if __name__ == "__main__":
    df = load_clean_csv(None)
    print(df.shape)
    validate(df)
