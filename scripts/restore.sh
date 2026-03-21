#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
# restore.sh — Restore PostgreSQL from a backup file
# Usage: ./scripts/restore.sh backups/war_of_names_20260321_030000.sql.gz
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail

if [ -z "${1:-}" ]; then
    echo "Usage: $0 <backup_file.sql.gz>"
    echo ""
    echo "Available backups:"
    ls -lh /opt/war-of-names/backups/*.sql.gz 2>/dev/null || echo "  No backups found"
    exit 1
fi

BACKUP_FILE="$1"
APP_DIR="/opt/war-of-names"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "✗ File not found: $BACKUP_FILE"
    exit 1
fi

set -a
source "$APP_DIR/.env"
set +a

DB_USER="${DB_USER:-postgres}"
DB_NAME="${DB_NAME:-war_of_names}"

echo "⚠  WARNING: This will DROP and RECREATE the database '$DB_NAME'."
echo "   Backup file: $BACKUP_FILE"
read -p "   Continue? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Aborted."
    exit 0
fi

echo "→ Stopping API to release connections..."
docker compose -f "$APP_DIR/docker-compose.yml" stop api frontend

echo "→ Dropping and recreating database..."
docker compose -f "$APP_DIR/docker-compose.yml" exec -T db \
    psql -U "$DB_USER" -c "DROP DATABASE IF EXISTS $DB_NAME;"
docker compose -f "$APP_DIR/docker-compose.yml" exec -T db \
    psql -U "$DB_USER" -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"

echo "→ Restoring from backup..."
gunzip -c "$BACKUP_FILE" | docker compose -f "$APP_DIR/docker-compose.yml" exec -T db \
    psql -U "$DB_USER" "$DB_NAME"

echo "→ Restarting services..."
docker compose -f "$APP_DIR/docker-compose.yml" up -d

echo "✓ Restore complete"
