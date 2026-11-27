#!/usr/bin/env bash
# Sauvegarde de la base : ./scripts/backup_db.sh  -> backups/veille_YYYYmmdd_HHMMSS.sql.gz
set -euo pipefail
mkdir -p backups
FILE="backups/veille_$(date +%Y%m%d_%H%M%S).sql.gz"
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' | gzip > "$FILE"
echo "Sauvegarde créée : $FILE"
# Restauration : gunzip -c FICHIER | docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" "$POSTGRES_DB"'
