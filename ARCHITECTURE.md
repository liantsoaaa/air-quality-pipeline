# Architecture du projet

## Vue d'ensemble

Pipeline de données automatisé collectant les données de qualité de l'air pour 5 villes françaises (Paris, Marseille, Lyon, Lille, Strasbourg), toutes les heures, sans intervention manuelle, depuis l'extraction jusqu'au data warehouse.

## Source de données

**OpenWeather Air Pollution API**

Choisie parmi les API de qualité de l'air disponibles car :
- Historique disponible depuis novembre 2020, couvrant largement la période demandée (juillet 2025 - juillet 2026)

## Extraction

Script `extraction/extract_air_quality.py`, exécuté automatiquement toutes les heures.

Logique en 3 étapes :
- **Extract** : appel de l'API OpenWeather pour chacune des 5 villes (données actuelles)
- **Parse** : extraction des champs pertinents (AQI, composants polluants, date de mesure) depuis la réponse JSON brute
- **Load** : sauvegarde d'une copie locale en CSV, et upload du JSON brut vers Supabase Storage

Convention de nommage : `raw/{ville}/{YYYY-MM-DDTHHh}.json`

## Backfill historique

Script `extraction/backfill.py`, exécuté ponctuellement pour constituer l'historique de données requis (juillet 2025 - juillet 2026), en complément de la collecte automatique horaire.

**Approche** : la période est découpée mois par mois (12 tranches), et pour chaque ville, une requête est envoyée à l'endpoint historique de l'API (`/air_pollution/history`) avec une plage de dates. Chaque réponse contient l'ensemble des mesures horaires du mois demandé, regroupées et uploadées en un seul fichier par ville par mois.

Convention de nommage : `raw/{ville}/backfill_{YYYY-MM}.json`

Ce découpage par mois (plutôt qu'un fichier par heure comme pour la collecte automatique) limite le nombre de requêtes et d'uploads nécessaires (5 villes x 12 mois = 60 fichiers au total) tout en respectant les limites du free tier de l'API. Le script est rejouable sans risque : les uploads utilisent `upsert=true`, donc relancer le backfill ne crée jamais de doublons.

## Transformation

Script `transform/clean.py`, produisant un unique fichier `clean/air_quality_clean.csv`, reconstruit entièrement depuis `raw/` à chaque exécution (aucune donnée brute n'est jamais modifiée, `raw/` reste la source de vérité).

**Lecture** : parcours de tous les fichiers présents dans `raw/{ville}/` pour les 5 villes, avec deux formats à gérer différemment :
- fichiers horaires (une mesure par fichier)
- fichiers de backfill (une liste de mesures par fichier)

Les deux formats sont uniformisés en un seul DataFrame avant nettoyage.

**Nettoyage** :
- Normalisation des noms de colonnes
- `dropna()` : suppression des valeurs manquantes
- `drop_duplicates(subset=["city", "measurement_date"])` : une seule ligne par ville et par heure, conformément au contrat de données
- Filtre de valeurs physiquement impossibles : AQI hors de l'échelle 1-5, concentrations de polluants négatives
- `pd.to_datetime()` : normalisation du format des dates
- Enrichissement avec pays, latitude et longitude pour chaque ville (exigé par le contrat de données de `clean/`)
- Tri chronologique par ville

**Sauvegarde** : le fichier `clean/air_quality_clean.csv` est déposé à la fois en local (pour vérification) et sur Supabase Storage, en écrasant systématiquement la version précédente à chaque exécution.

## Validation

Script `validate_clean.py`, exécuté après la transformation pour vérifier que `clean/air_quality_clean.csv` respecte le contrat de données attendu.

Vérifications effectuées :
- Présence de toutes les colonnes requises (ville, pays, coordonnées, horodatage, AQI, polluants)
- Absence de valeurs manquantes
- Absence de doublons (même ville + même heure)
- Présence des 5 villes attendues
- Tri chronologique correct
- AQI dans l'échelle valide (1 à 5)
- Aucune concentration de polluant négative
- Coordonnées géographiquement valides

Le script peut être exécuté sur le fichier téléchargé depuis Supabase Storage, ou sur une copie locale passée en argument.

## Data Warehouse

Base PostgreSQL hébergée sur Supabase (même projet que le stockage). Modélisation en étoile, conforme aux règles vues en cours (table de faits sans colonnes descriptives, dimensions sans mesures) :

- **dim_ville** : nom de ville, pays, latitude, longitude
- **dim_temps** : date complète, date, heure, jour, mois, année, jour de la semaine, weekend ou non
- **fait_mesures_qualite_air** : clés vers les deux dimensions, AQI et les 8 polluants mesurés

Script `warehouse/schema.sql` pour la création des tables, exécuté directement dans l'éditeur SQL de Supabase.

Script `warehouse/load_warehouse.py` pour le chargement, rejouable à chaque exécution : les dimensions sont insérées avec `ON CONFLICT DO NOTHING` (pas de doublons), et la table de faits utilise `ON CONFLICT DO UPDATE` (upsert par ville + heure), permettant de relancer le script sans jamais dupliquer les mesures.

## Stockage brut (Data Lake) : Supabase Storage

**Choix initial** : AWS S3.

**Choix final** : Supabase Storage.

**Pourquoi ce changement** : AWS (et Google Cloud) exigent une carte bancaire pour créer un compte, même pour rester dans le free tier. N'ayant pas accès à une carte bancaire, nous avons cherché une alternative sans cette contrainte. Supabase offre un stockage de fichiers (S3-compatible) et une base PostgreSQL managée, entièrement gratuits, sans carte bancaire requise.

## Orchestration : GitHub Actions + cron-job.org

**Solution retenue** : GitHub Actions avec un workflow planifié (`schedule: cron`), complété par un déclenchement externe via **cron-job.org** (service gratuit, sans carte bancaire) qui appelle l'API GitHub (`workflow_dispatch`) toutes les heures.

**Pourquoi ce complément était nécessaire** : le cron natif de GitHub Actions est documenté comme sujet à des délais variables (parfois plusieurs heures) en période de forte charge sur l'infrastructure partagée de GitHub. Pour garantir une exécution réellement horaire, un déclenchement externe fiable (cron-job.org -> API GitHub -> workflow_dispatch) a été mis en place en complément.

Le workflow exécute désormais quatre étapes à chaque déclenchement : extraction, transformation, validation, puis chargement dans le data warehouse.

## Versionning et environnement

- Python 3.12
- Dépendances figées via `pip freeze > requirements.txt` (nécessaire pour garantir la reproductibilité entre l'environnement local et l'environnement d'exécution GitHub Actions)