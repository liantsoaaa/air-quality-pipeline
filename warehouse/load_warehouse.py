import os

import pandas as pd
from dotenv import load_dotenv
from supabase import create_client
import psycopg2
from psycopg2.extras import execute_values

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
BUCKET_NAME = "raw-data"

CITY_INFO = {
    "paris": {"pays": "France", "lat": 48.8566, "lon": 2.3522},
    "marseille": {"pays": "France", "lat": 43.2965, "lon": 5.3698},
    "lyon": {"pays": "France", "lat": 45.7640, "lon": 4.8357},
    "lille": {"pays": "France", "lat": 50.6292, "lon": 3.0573},
    "strasbourg": {"pays": "France", "lat": 48.5734, "lon": 7.7521},
}


def download_clean_csv():
    if SUPABASE_URL == None or SUPABASE_KEY == None:
        print("SUPABASE_URL or SUPABASE_KEY missing")
        raise SystemExit(1)

    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    raw_bytes = client.storage.from_(BUCKET_NAME).download("clean/air_quality_clean.csv")

    if not os.path.exists("data"):
        os.makedirs("data")

    f = open("data/_tmp_clean.csv", "wb")
    f.write(raw_bytes)
    f.close()

    df = pd.read_csv("data/_tmp_clean.csv")
    return df


def get_connection():
    if DATABASE_URL == None:
        print("DATABASE_URL missing")
        raise SystemExit(1)
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def load_dim_ville(conn):
    rows = []
    for city in CITY_INFO:
        info = CITY_INFO[city]
        rows.append((city, info["pays"], info["lat"], info["lon"]))

    cur = conn.cursor()
    execute_values(cur, "INSERT INTO dim_ville (nom_ville, pays, latitude, longitude) VALUES %s ON CONFLICT (nom_ville) DO NOTHING", rows)
    conn.commit()
    cur.close()

    cur = conn.cursor()
    cur.execute("SELECT id_ville, nom_ville FROM dim_ville")
    result = cur.fetchall()
    cur.close()

    ville_ids = {}
    for id_ville, nom in result:
        ville_ids[nom] = id_ville

    return ville_ids

def load_dim_temps(conn, timestamps):
    rows = []
    for ts in timestamps:
        dt = pd.to_datetime(ts)
        jour_semaine = dt.day_name()
        est_weekend = dt.weekday() >= 5
        rows.append((dt.to_pydatetime(), dt.date(), dt.hour, dt.day, dt.month, dt.year, jour_semaine, est_weekend))

    cur = conn.cursor()
    execute_values(cur, "INSERT INTO dim_temps (date_complete, date, heure, jour, mois, annee, jour_semaine, est_weekend) VALUES %s ON CONFLICT (date_complete) DO NOTHING", rows)
    conn.commit()
    cur.close()

    cur = conn.cursor()
    cur.execute("SELECT id_temps, date_complete FROM dim_temps")
    result = cur.fetchall()
    cur.close()

    temps_ids = {}
    for id_temps, date_complete in result:
        temps_ids[pd.Timestamp(date_complete).isoformat()] = id_temps

    return temps_ids

if __name__ == "__main__":
    df = download_clean_csv()
    print(df.shape)

    conn = get_connection()
    ville_ids = load_dim_ville(conn)
    print("dim_ville:", len(ville_ids), "cities")

    timestamps = df["measurement_date"].unique().tolist()
    temps_ids = load_dim_temps(conn, timestamps)
    print("dim_temps:", len(temps_ids), "timestamps")
    conn.close()