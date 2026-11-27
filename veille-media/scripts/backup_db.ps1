# Sauvegarde de la base (PowerShell) :  .\scripts\backup_db.ps1
$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path backups | Out-Null
$file = "backups\veille_{0}.sql" -f (Get-Date -Format "yyyyMMdd_HHmmss")
# Redirection via cmd pour éviter la conversion d'encodage de PowerShell
cmd /c "docker compose exec -T db sh -c ""pg_dump -U `$POSTGRES_USER `$POSTGRES_DB"" > $file"
Write-Host "Sauvegarde créée : $file"
# Restauration : cmd /c "docker compose exec -T db sh -c ""psql -U `$POSTGRES_USER `$POSTGRES_DB"" < backups\FICHIER.sql"
