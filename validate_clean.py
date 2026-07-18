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


def main():
    if len(sys.argv) > 1:
        local_path = sys.argv[1]
    else:
        local_path = None

    df = load_clean_csv(local_path)
    print("")
    print("Loaded", len(df), "rows,", len(df.columns), "columns")
    print("")

    print("Running validation checks:")
    print("")
    is_valid = validate(df)

    print("")
    print("")
    if is_valid:
        print("VALIDATION PASSED")
        sys.exit(0)
    else:
        print("VALIDATION FAILED")
        sys.exit(1)


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

    cities_found = df["city"].unique().tolist()
    all_cities_ok = True
    for city in EXPECTED_CITIES:
        if city not in cities_found:
            all_cities_ok = False

    result4 = check("All 5 expected cities present", all_cities_ok, "found: " + str(cities_found))
    results.append(result4)

    df_sorted_check = df.sort_values(["city", "measurement_date"])
    df_sorted_check = df_sorted_check.reset_index(drop=True)
    df_reset = df.reset_index(drop=True)
    is_sorted = df_reset.equals(df_sorted_check)
    result5 = check("Sorted chronologically by city", is_sorted)
    results.append(result5)

    aqi_bad = df[(df["aqi"] < 1) | (df["aqi"] > 5)]
    aqi_valid = len(aqi_bad) == 0
    result6 = check("AQI values within valid range (1-5)", aqi_valid, str(len(aqi_bad)) + " invalid values")
    results.append(result6)

    pollutant_cols = ["co", "no", "no2", "o3", "so2", "pm2_5", "pm10", "nh3"]
    negative_found = False
    for col in pollutant_cols:
        bad_rows = df[df[col] < 0]
        if len(bad_rows) > 0:
            negative_found = True

    result7 = check("No negative pollutant concentrations", not negative_found)
    results.append(result7)

    lat_ok = df["latitude"].between(-90, 90).all()
    lon_ok = df["longitude"].between(-180, 180).all()
    coords_valid = lat_ok and lon_ok
    result8 = check("Coordinates within valid geographic range", coords_valid)
    results.append(result8)

    print("")
    print("Total rows:", len(df))
    print("Rows per city:")
    print(df["city"].value_counts())

    all_passed = True
    for r in results:
        if r == False:
            all_passed = False

    return all_passed


if __name__ == "__main__":
    main()