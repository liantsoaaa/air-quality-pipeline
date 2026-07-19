CREATE TABLE IF NOT EXISTS dim_ville (
    id_ville SERIAL PRIMARY KEY,
    nom_ville TEXT NOT NULL UNIQUE,
    pays TEXT NOT NULL,
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_temps (
    id_temps SERIAL PRIMARY KEY,
    date_complete TIMESTAMP NOT NULL UNIQUE,
    date DATE NOT NULL,
    heure INT NOT NULL,
    jour INT NOT NULL,
    mois INT NOT NULL,
    annee INT NOT NULL,
    jour_semaine TEXT NOT NULL,
    est_weekend BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS fait_mesures_qualite_air (
    id_mesure SERIAL PRIMARY KEY,
    id_ville INT NOT NULL REFERENCES dim_ville(id_ville),
    id_temps INT NOT NULL REFERENCES dim_temps(id_temps),
    aqi INT,
    co FLOAT,
    no FLOAT,
    no2 FLOAT,
    o3 FLOAT,
    so2 FLOAT,
    pm2_5 FLOAT,
    pm10 FLOAT,
    nh3 FLOAT,
    UNIQUE(id_ville, id_temps)
);