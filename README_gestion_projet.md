# Gestion du projet

## Équipe

- **STD24003**
- **STD24166**

## Méthode de travail

### Git / GitHub

- Branche `main` : toujours stable
- Une branche `feature/nom-de-la-tache` par fonctionnalité

### Répartition des tâches

Le script d'extraction (`extract_air_quality.py`), incluant l'intégration avec Supabase Storage, a été développé entièrement par une personne, sur une branche dédiée relue et approuvée par l'autre avant fusion dans `main`.

Le script de backfill historique (`backfill.py`) a également été développé entièrement par une seule personne, selon le même principe : une branche dédiée, avec revue de code avant fusion.

Le script de transformation (`clean.py`) a lui aussi été développé entièrement par une personne (lecture des données brutes, nettoyage, enrichissement, sauvegarde), sur une branche dédiée relue et approuvée par l'autre avant fusion.

Le script de validation (`validate_clean.py`) a été développé entièrement par l'autre personne, sur sa propre branche, avec revue croisée avant fusion.

Le schéma de la base de données (`warehouse/schema.sql`) et le script de chargement du data warehouse (`warehouse/load_warehouse.py`) ont été développés par une personne, également relus par l'autre avant fusion.

## Défis rencontrés

### 1. Blocage carte bancaire (AWS/GCP)

**Problème** : l'architecture initialement prévue (Apache Airflow déployé sur une VM AWS EC2, stockage S3) nécessitait un compte AWS, qui exige une carte bancaire même pour rester dans le free tier. Aucun membre de l'équipe n'y avait donc accès.

**Solution** : pivot vers une architecture équivalente sans carte bancaire :
- GitHub Actions à la place d'Airflow (l'énoncé autorisait explicitement une alternative type "cron")
- Supabase (Storage + PostgreSQL) à la place d'AWS S3 + RDS

Ce changement a nécessité de revoir l'ensemble du planning et de réapprendre certains outils en cours de route, mais a permis de respecter l'exigence centrale du projet (automatisation réelle, sans intervention manuelle) sans dépendance financière.

### 2. Fiabilité du cron GitHub Actions

**Problème** : une fois le workflow GitHub Actions en place avec un déclenchement `schedule: cron` toutes les heures, des écarts de 2 à 3 heures entre les exécutions ont été observés au lieu d'une cadence horaire régulière.

**Diagnostic** : ce comportement est documenté comme un problème connu de GitHub Actions, les workflows planifiés peuvent être retardés de façon significative en période de forte charge sur l'infrastructure partagée, sans garantie de délai.

**Solution** : mise en place d'un déclenchement externe via cron-job.org, qui appelle l'API GitHub (`workflow_dispatch`) précisément toutes les heures, en complément du cron natif conservé comme filet de sécurité.

### 3. Incohérence de dépendances entre environnement local et CI

**Problème** : le script fonctionnait en local mais échouait sur GitHub Actions.

**Solution** : génération d'un `requirements.txt` avec versions figées (`pip freeze`) plutôt que des noms de paquets sans version, garantissant que l'environnement GitHub Actions installe exactement les mêmes versions que celles testées en local. Montée de version Python (3.11 vers 3.12) en complément.

### 4. Timeouts réseau lors des appels à Supabase

**Problème** : plusieurs scripts doivent lister ou télécharger un grand nombre de fichiers depuis Supabase Storage ; des erreurs de type timeout réseau sont apparues ponctuellement lors de ces appels, aussi bien pendant la transformation que pendant le chargement du data warehouse.

**Solution** : ajout d'une logique de nouvelle tentative (plusieurs essais avec une courte pause entre chaque) sur les appels réseau les plus sensibles, pour absorber les aléas temporaires sans faire échouer tout le script.

### 5. Répartition incomplète des données de backfill entre les villes

**Problème** : une vérification manuelle du nombre de fichiers présents dans `raw/` par ville a révélé que certaines villes ne disposaient pas de l'historique complet sur 12 mois, contrairement à d'autres.

**Diagnostic** : le script de backfill traite les villes une par une dans l'ordre ; une partie de l'historique n'avait pas pu être généré jusqu'au bout pour les dernières villes de la liste.

**Solution** : le script étant conçu avec des uploads en `upsert`, il a suffi de le relancer entièrement pour compléter les données manquantes, sans créer de doublons pour les villes déjà traitées. Une nouvelle exécution de la transformation a ensuite confirmé un nombre de mesures parfaitement équilibré entre les 5 villes.

### 6. Format de chaîne de connexion incompatible avec psycopg2

**Problème** : la chaîne de connexion PostgreSQL fournie par Supabase pour le pooler de transactions inclut un paramètre additionnel (`pgbouncer=true`) destiné à certains ORM, mais que la librairie `psycopg2` ne reconnaît pas, provoquant une erreur de connexion.

**Solution** : suppression de ce paramètre dans la chaîne de connexion utilisée par le script Python, sans impact sur le fonctionnement du pooler côté Supabase.

### 7. Quota GitHub Actions dépassé
 
**Problème** : après plusieurs jours d'exécution horaire automatique et de nombreux tests manuels, GitHub Actions a bloqué les nouveaux runs avec le message "recent account payments have failed or your spending limit needs to be increased". Vu que le dépôt était privé, il était soumis à une limite de 2000 minutes gratuites par mois, largement dépassée par le volume de runs accumulés.
 
**Solution** : passage du dépôt en public, ce qui donne un accès illimité et gratuit aux minutes GitHub Actions sur les dépôts publics.
