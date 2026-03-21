#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
# backup.sh — Dump PostgreSQL database to a timestamped file
# Run from the project root or via cron.
# Keeps the last 14 daily backups.
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail

APP_DIR="/opt/war-of-names"
BACKUP_DIR="$APP_DIR/backups"
RETENTION_DAYS=14

# Load env for DB credentials
set -a
source "$APP_DIR/.env"
set +a

DB_USER="${DB_USER:-postgres}"
DB_NAME="${DB_NAME:-war_of_names}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"

echo "→ Backing up $DB_NAME..."
docker compose -f "$APP_DIR/docker-compose.yml" exec -T db \
    pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$BACKUP_FILE"

SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "  ✓ Backup saved: $BACKUP_FILE ($SIZE)"

# Clean old backups
echo "→ Cleaning backups older than $RETENTION_DAYS days..."
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete
REMAINING=$(find "$BACKUP_DIR" -name "*.sql.gz" | wc -l)
echo "  ✓ $REMAINING backups retained"
