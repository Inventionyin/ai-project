#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/opt/weitesting/backups/jenkins}"
DRILL_DIR="${DRILL_DIR:-/opt/weitesting/restore-drills/jenkins}"
OUTPUT_PATH="${OUTPUT_PATH:-/opt/weitesting/artifacts/jenkins-restore-drill/latest.json}"
LATEST_BACKUP=""

usage() {
  cat <<'EOF'
Usage: deploy/jenkins/restore_drill_jenkins.sh [options]

Options:
  --backup-dir <path>    Directory containing jenkins-*.tgz archives.
  --backup-file <path>   Specific backup archive to test.
  --drill-dir <path>     Temporary extraction directory.
  --output-path <path>   JSON report path.
  --help                 Show this message.

This drill never writes into JENKINS_HOME. It extracts into a disposable
directory and checks that key Jenkins home artifacts are present.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --backup-dir) BACKUP_DIR="$2"; shift 2 ;;
    --backup-file) LATEST_BACKUP="$2"; shift 2 ;;
    --drill-dir) DRILL_DIR="$2"; shift 2 ;;
    --output-path) OUTPUT_PATH="$2"; shift 2 ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage; exit 64 ;;
  esac
done

if [[ -z "$LATEST_BACKUP" ]]; then
  if [[ ! -d "$BACKUP_DIR" ]]; then
    echo "Backup directory does not exist: $BACKUP_DIR" >&2
    exit 2
  fi
  LATEST_BACKUP="$(find "$BACKUP_DIR" -maxdepth 1 -type f -name 'jenkins-*.tgz' -printf '%T@ %p\n' | sort -nr | awk 'NR==1 {print $2}')"
fi

if [[ -z "$LATEST_BACKUP" || ! -f "$LATEST_BACKUP" ]]; then
  echo "No Jenkins backup archive found." >&2
  exit 2
fi

mkdir -p "$DRILL_DIR" "$(dirname "$OUTPUT_PATH")"
RUN_DIR="$DRILL_DIR/restore-$(date -u +%Y%m%d-%H%M%S)"
mkdir -p "$RUN_DIR"

LISTING_FILE="$(mktemp "${TMPDIR:-/tmp}/weitesting-jenkins-restore-drill-listing.XXXXXX")"
trap 'rm -f "$LISTING_FILE"' EXIT
tar -tzf "$LATEST_BACKUP" >"$LISTING_FILE"
tar -xzf "$LATEST_BACKUP" -C "$RUN_DIR"

status="READY"
missing=()
for required in config.xml jobs plugins; do
  if [[ ! -e "$RUN_DIR/$required" ]]; then
    status="BLOCKED"
    missing+=("$required")
  fi
done

backup_size="$(stat -c '%s' "$LATEST_BACKUP")"
file_count="$(find "$RUN_DIR" -mindepth 1 | wc -l | tr -d ' ')"

python3 - "$OUTPUT_PATH" "$status" "$LATEST_BACKUP" "$RUN_DIR" "$backup_size" "$file_count" "${missing[@]}" <<'PY'
import datetime as dt
import json
import os
import sys

output_path, status, backup_file, run_dir, backup_size, file_count, *missing = sys.argv[1:]
report = {
    "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
    "restoreDrill": {
        "status": status,
        "backupFile": backup_file,
        "drillDir": run_dir,
        "backupSizeBytes": int(backup_size),
        "extractedFileCount": int(file_count),
        "missingRequiredPaths": missing,
        "note": "This drill never writes into JENKINS_HOME.",
    },
}
os.makedirs(os.path.dirname(output_path), exist_ok=True)
with open(output_path, "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=2, ensure_ascii=False)
PY

echo "Jenkins restore drill written: $OUTPUT_PATH"
echo "Restore drill status: $status"
if [[ "$status" != "READY" ]]; then
  echo "Missing required paths: ${missing[*]}" >&2
  exit 2
fi
