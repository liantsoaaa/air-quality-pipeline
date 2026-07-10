# Architecture du projet
 
## Vue d'ensemble
 
Pipeline de données automatisé collectant les données de qualité de l'air pour 5 villes françaises (Paris, Marseille, Lyon, Lille, Strasbourg), toutes les heures, sans intervention manuelle, depuis l'extraction jusqu'au data warehouse.
 
## Source de données
 
**OpenWeather Air Pollution API**
 
Choisie parmi les API de qualité de l'air disponibles pour plusieurs raisons :
- Historique disponible depuis novembre 2020, couvrant largement la période demandée (juillet 2025 - juillet 2026)
- Free tier généreux (1 000 000 d'appels/mois), largement suffisant pour 5 villes x 24 appels/jour
- Un seul endpoint simple par ville, données structurées (AQI + composants : CO, NO, NO2, O3, SO2, PM2.5, PM10, NH3)
**Contrainte technique** : l'API nécessite des coordonnées latitude/longitude (pas de nom de ville en paramètre), contrairement à l'API météo classique. D'où le choix de 5 villes avec coordonnées fixes plutôt qu'une recherche dynamique par nom.
 
## Extraction
 
Script `extraction/extract_air_quality.py`, exécuté automatiquement toutes les heures.
 
Logique en 3 étapes :
- **Extract** : appel de l'API OpenWeather pour chacune des 5 villes (données actuelles)
- **Parse** : extraction des champs pertinents (AQI, composants polluants, date de mesure) depuis la réponse JSON brute
- **Load** : sauvegarde d'une copie locale en CSV, et upload du JSON brut vers Supabase Storage
Convention de nommage : `raw/{ville}/{YYYY-MM-DDTHHh}.json`
 
## Backfill historique
 
Script `extraction/backfill.py`, exécuté ponctuellement pour constituer l'historique de données requis (juillet 2025 - juillet 2026), en complément de la collecte automatique horaire.
 
**Approche** : la période est découpée mois par mois (13 tranches), et pour chaque ville, une requête est envoyée à l'endpoint historique de l'API (`/air_pollution/history`) avec une plage de dates. Chaque réponse contient l'ensemble des mesures horaires du mois demandé (~700-750 entrées), regroupées et uploadées en un seul fichier par ville par mois.
 
Convention de nommage : `raw/{ville}/backfill_{YYYY-MM}.json`
 
Ce découpage par mois (plutôt qu'un fichier par heure comme pour la collecte automatique) limite le nombre de requêtes et d'uploads nécessaires (5 villes x 13 mois = 65 fichiers au total) tout en respectant les limites du free tier de l'API.
 
## Stockage brut (Data Lake) : Supabase Storage
 
**Choix initial** : AWS S3.
 
**Choix final** : Supabase Storage.
 
**Pourquoi ce changement** : AWS (et Google Cloud) exigent une carte bancaire pour créer un compte, même pour rester dans le free tier. N'ayant pas accès à une carte bancaire, nous avons cherché une alternative sans cette contrainte. Supabase offre un stockage de fichiers (S3-compatible) et une base PostgreSQL managée, entièrement gratuits, sans carte bancaire requise.
 
## Orchestration : GitHub Actions + cron-job.org
 
**Solution retenue** : GitHub Actions avec un workflow planifié (`schedule: cron`), complété par un déclenchement externe via **cron-job.org** (service gratuit, sans carte bancaire) qui appelle l'API GitHub (`workflow_dispatch`) toutes les heures.
 
**Pourquoi ce complément était nécessaire** : le cron natif de GitHub Actions est documenté comme sujet à des délais variables (parfois plusieurs heures) en période de forte charge sur l'infrastructure partagée de GitHub. Pour garantir une exécution réellement horaire, un déclenchement externe fiable (cron-job.org -> API GitHub -> workflow_dispatch) a été mis en place en complément.
 
## Versionning et environnement
 
- Python 3.12
- Dépendances figées via `pip freeze > requirements.txt` (nécessaire pour garantir la reproductibilité entre l'environnement local et l'environnement d'exécution GitHub Actions)
 

