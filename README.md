# Air Quality Pipeline

Pipeline de données automatisé collectant la qualité de l'air pour 5 villes françaises, toutes les heures, sans intervention manuelle, depuis l'extraction jusqu'au data warehouse.

Voir `ARCHITECTURE.md` pour le détail et la justification des choix techniques, et `README_gestion_projet.md` pour la méthode de travail et les défis rencontrés.

## Prérequis

- Python 3.12
- Un compte [OpenWeather](https://openweathermap.org/) (clé API gratuite)
- Un compte [Supabase](https://supabase.com/) (gratuit, sans carte bancaire)
- Un compte GitHub avec accès au repo

## Installation locale

```bash
git clone https://github.com/liantsoaaa/air-quality-pipeline.git
cd air-quality-pipeline

python3 -m venv venv
source venv/bin/activate   # Windows : venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

## Configuration

Copier le fichier d'exemple et le remplir avec vos propres clés :

```bash
cp .env.example .env
```

Contenu attendu de `.env` :
```
OPENWEATHER_API_KEY=votre_cle_openweather
SUPABASE_URL=https://votre_projet.supabase.co
SUPABASE_KEY=votre_secret_key_supabase
DATABASE_URL=votre_chaine_de_connexion_postgres
```

## Lancer le pipeline manuellement

```bash
python extraction/extract_air_quality.py
python transform/clean.py
python validate_clean.py
python warehouse/load_warehouse.py
```

Chaque script peut aussi être lancé indépendamment pour tester une étape précise.

## Automatisation en production

Le pipeline tourne automatiquement, sans action manuelle, grâce à :

1. **GitHub Actions** (`.github/workflows/extraction_horaire.yml`) : exécute les 4 étapes du pipeline (extraction, transformation, validation, chargement warehouse)
2. **cron-job.org** : déclenche le workflow GitHub toutes les heures via l'API GitHub (`workflow_dispatch`), en complément du cron natif de GitHub Actions, moins fiable en délai (voir `ARCHITECTURE.md`)

### Configurer les secrets GitHub (pour un nouveau déploiement)

Repo GitHub → **Settings** → **Secrets and variables** → **Actions**, ajouter :
- `OPENWEATHER_API_KEY`
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `DATABASE_URL`

### Configurer le déclenchement externe (cron-job.org)

1. Créer un Personal Access Token GitHub (scope `workflow`)
2. Créer un compte sur [cron-job.org](https://cron-job.org)
3. Créer un cronjob avec :
   - URL : `https://api.github.com/repos/liantsoaaa/air-quality-pipeline/actions/workflows/extraction_horaire.yml/dispatches`
   - Méthode : POST
   - Headers : `Authorization: Bearer VOTRE_TOKEN` et `Accept: application/vnd.github+json`
   - Body : `{"ref": "main"}`
   - Fréquence : toutes les heures

## Structure du projet

```
extraction/          scripts d'extraction et de backfill des données brutes
screenshoots/         screenshoots des captures de l'historique d'exécutions de l'orchestration
transform/            script de nettoyage des données
warehouse/            schéma SQL et script de chargement du data warehouse
validate_clean.py     script de validation du contrat de données
.github/workflows/    workflow d'automatisation GitHub Actions
data/                 fichiers CSV locaux (non versionnés)
```

## Villes couvertes

| Ville | Pays | Latitude | Longitude |
|---|---|---|---|
| Paris | France | 48.8566 | 2.3522 |
| Marseille | France | 43.2965 | 5.3698 |
| Lyon | France | 45.7640 | 4.8357 |
| Lille | France | 50.6292 | 3.0573 |
| Strasbourg | France | 48.5734 | 7.7521 |

## Colonnes de clean/air_quality_clean.csv

| Colonne | Unité / format | Description |
|---|---|---|
| city | texte | nom de la ville (minuscules) |
| pays | texte | pays |
| latitude, longitude | degrés décimaux | coordonnées GPS de la ville |
| measurement_date | ISO 8601 | date et heure de la mesure |
| aqi | entier, échelle 1-5 | indice de qualité de l'air (OpenWeather) |
| co | µg/m³ | monoxyde de carbone |
| no | µg/m³ | monoxyde d'azote |
| no2 | µg/m³ | dioxyde d'azote |
| o3 | µg/m³ | ozone |
| so2 | µg/m³ | dioxyde de soufre |
| pm2_5 | µg/m³ | particules fines < 2.5 µm |
| pm10 | µg/m³ | particules fines < 10 µm |
| nh3 | µg/m³ | ammoniac |

Le fichier contient une ligne par ville et par heure, trié chronologiquement par ville, sans doublons, conforme au contrat de données validé par `validate_clean.py`.

## Backfill historique

Le script `extraction/backfill.py` récupère l'historique des 12 derniers mois pour les 5 villes, découpé mois par mois, et l'upload dans `raw/{ville}/backfill_{YYYY-MM}.json`. Le script est rejouable sans risque de doublon (upload en `upsert`).

## Schéma du data warehouse

Base PostgreSQL hébergée sur Supabase, modélisation en étoile :

**Table de faits `fait_mesures_qualite_air`**
| Colonne | Description |
|---|---|
| id_mesure | clé primaire |
| id_ville | clé étrangère vers dim_ville |
| id_temps | clé étrangère vers dim_temps |
| aqi, co, no, no2, o3, so2, pm2_5, pm10, nh3 | mesures |

**Dimension `dim_ville`**
| Colonne | Description |
|---|---|
| id_ville | clé primaire |
| nom_ville, pays, latitude, longitude | descriptif de la ville |

**Dimension `dim_temps`**
| Colonne | Description |
|---|---|
| id_temps | clé primaire |
| date_complete, date, heure, jour, mois, annee, jour_semaine, est_weekend | descriptif temporel |

Script `warehouse/schema.sql` pour la création des tables, `warehouse/load_warehouse.py` pour le chargement, rejouable (upsert sur ville + heure).

## Période couverte

Juillet 2025 à aujourd'hui, avec collecte automatique continue toutes les heures depuis la mise en production du pipeline.

## Cohérence des données

La table de faits contient 44 285 lignes, réparties de façon égale entre les 5 villes (8 857 lignes chacune), correspondant à environ 12 mois de collecte horaire par ville (backfill + collecte automatique continue).

## Trous connus

Aucun trou significatif identifié à ce jour. Un déséquilibre initial entre villes (dû à une interruption du script de backfill) a été détecté et corrigé - voir `README_gestion_projet.md` pour le détail.

## Connexion à la base de données

Un accès en lecture seule est disponible pour vérification :

```
postgresql://mirado_readonly.dzpbdkgxalihdzozhzct:MiradoLecture2026!@aws-0-eu-west-1.pooler.supabase.com:6543/postgres
```

Pour vous connecter, copier directement cette requete :

```
psql 'postgresql://mirado_readonly.dzpbdkgxalihdzozhzct:MiradoLecture2026!@aws-0-eu-west-1.pooler.supabase.com:6543/postgres'
```

Ce compte permet uniquement des requêtes SELECT sur les tables `dim_ville`, `dim_temps` et `fait_mesures_qualite_air` (sécurisé via Row Level Security).

Exemple de requête de vérification :
```sql
SELECT v.nom_ville, COUNT(*)
FROM fait_mesures_qualite_air f
JOIN dim_ville v ON f.id_ville = v.id_ville
GROUP BY v.nom_ville;
```