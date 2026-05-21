#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/opt/weitesting/backups/postgres}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
DATABASE_URL="${DATABASE_URL:-}"

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  cat <<'USAGE'
Usage: weitesting-backup-postgres

Environment:
  DATABASE_URL      PostgreSQL URL. If omitted, backend .env is used.
  BACKUP_DIR        Backup directory. Default: /opt/weitesting/backups/postgres
  RETENTION_DAYS    Delete backups older than this many days. Default: 14
USAGE
  exit 0
fi

if [[ -z "$DATABASE_URL" ]]; then
  if [[ -f /opt/weitesting/backend/.env ]]; then
    DATABASE_URL="$(grep -E '^DATABASE_URL=' /opt/weitesting/backend/.env | tail -n 1 | cut -d= -f2- | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")"
  fi
fi

if [[ -z "$DATABASE_URL" ]]; then
  if [[ -f /opt/weitesting/current/ai-project-back-end/.env ]]; then
    DATABASE_URL="$(grep -E '^DATABASE_URL=' /opt/weitesting/current/ai-project-back-end/.env | tail -n 1 | cut -d= -f2- | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")"
  fi
fi

if [[ -z "$DATABASE_URL" ]]; then
  echo "DATABASE_URL is required. Export it or put it in backend .env." >&2
  exit 2
fi

PG_DUMP_URL="${DATABASE_URL/postgresql+asyncpg:/postgresql:}"

mkdir -p "$BACKUP_DIR"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
target="$BACKUP_DIR/weitesting-${timestamp}.dump"

pg_dump "$PG_DUMP_URL" --format=custom --no-owner --no-privileges --file="$target"
gzip -f "$target"

find "$BACKUP_DIR" -type f -name 'weitesting-*.dump.gz' -mtime +"$RETENTION_DAYS" -delete

echo "Backup written: ${target}.gz"
