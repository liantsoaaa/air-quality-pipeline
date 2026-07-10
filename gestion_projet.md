# Gestion du projet
 
## Équipe
 
- **STD24003**
- **STD24166**
## Méthode de travail
 
### Git / GitHub
 
- Branche `main` : toujours stable
- Une branche `feature/nom-de-la-tache` par fonctionnalité

### Répartition des tâches
 
Le script d'extraction (`extract_air_quality.py`) a été développé en deux temps sur la même branche : une première personne a écrit la logique d'appel à l'API et de structuration des données (Extract + Parse), la seconde a complété avec la logique de sauvegarde (Load : CSV local et upload vers Supabase Storage).
 
Le script de backfill historique (`backfill.py`) a été développé selon le même principe de collaboration sur une branche dédiée, avec revue de code croisée avant fusion dans `main`.
 
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
