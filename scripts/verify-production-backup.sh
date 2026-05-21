#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/opt/weitesting/backups/postgres}"
BACKUP_FILE="${BACKUP_FILE:-}"

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  cat <<'USAGE'
Usage: verify-production-backup.sh [backup-file]

Verifies that a compressed PostgreSQL custom-format dump can be read by
pg_restore. This does not restore data; it only checks archive integrity and
prints the first archive entries.

Environment:
  BACKUP_DIR   Directory to search when backup-file is omitted.
               Default: /opt/weitesting/backups/postgres
  BACKUP_FILE  Explicit .dump.gz file to verify.
USAGE
  exit 0
fi

if [[ $# -gt 0 ]]; then
  BACKUP_FILE="$1"
fi

if [[ -z "$BACKUP_FILE" ]]; then
  BACKUP_FILE="$(find "$BACKUP_DIR" -maxdepth 1 -type f -name 'weitesting-*.dump.gz' -printf '%T@ %p\n' 2>/dev/null | sort -nr | awk 'NR==1 {print $2}')"
fi

if [[ -z "$BACKUP_FILE" || ! -f "$BACKUP_FILE" ]]; then
  echo "No backup file found. Set BACKUP_FILE or pass a .dump.gz path." >&2
  exit 2
fi

if ! command -v pg_restore >/dev/null 2>&1; then
  echo "pg_restore is required but was not found in PATH." >&2
  exit 3
fi

tmp_file="$(mktemp)"
cleanup() {
  rm -f "$tmp_file"
}
trap cleanup EXIT

gzip -cd "$BACKUP_FILE" > "$tmp_file"
pg_restore --list "$tmp_file" > /tmp/weitesting-backup-restore-list.txt

echo "Backup is readable: $BACKUP_FILE"
echo "Archive entries:"
head -n 20 /tmp/weitesting-backup-restore-list.txt
