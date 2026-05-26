#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${REPO_DIR:-/opt/weitesting/current}"
LOG_DIR="${LOG_DIR:-/var/log/weitesting}"
ARTIFACT_DIR="${ARTIFACT_DIR:-/opt/weitesting/artifacts}"
CRON_FILE="${CRON_FILE:-/etc/cron.d/weitesting-ops}"
USER_NAME="${USER_NAME:-ubuntu}"
RESTORE_DRILL_ENABLED="${RESTORE_DRILL_ENABLED:-true}"

usage() {
  cat <<'EOF'
Usage: deploy/ops/install_ops_cron.sh [options]

Options:
  --repo-dir <path>
  --log-dir <path>
  --artifact-dir <path>
  --cron-file <path>
  --user <name>
  --disable-restore-drill
  --help

Installs daily operations cron jobs for:
  - performance-baseline trend reports
  - production-readiness self-check reports
  - Jenkins restore drill reports

DingTalk notifications are inherited from environment variables when the
performance baseline script is run manually; cron intentionally avoids
hardcoding webhook secrets.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo-dir) REPO_DIR="$2"; shift 2 ;;
    --log-dir) LOG_DIR="$2"; shift 2 ;;
    --artifact-dir) ARTIFACT_DIR="$2"; shift 2 ;;
    --cron-file) CRON_FILE="$2"; shift 2 ;;
    --user) USER_NAME="$2"; shift 2 ;;
    --disable-restore-drill) RESTORE_DRILL_ENABLED="false"; shift ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage; exit 64 ;;
  esac
done

mkdir -p "$LOG_DIR" "$ARTIFACT_DIR/performance-baseline" "$ARTIFACT_DIR/production-readiness" "$ARTIFACT_DIR/jenkins-restore-drill"

if [[ "$EUID" -eq 0 ]]; then
  chown "$USER_NAME:$USER_NAME" "$LOG_DIR" "$ARTIFACT_DIR/performance-baseline" "$ARTIFACT_DIR/production-readiness" "$ARTIFACT_DIR/jenkins-restore-drill"
fi

if [[ ! -d "$REPO_DIR" ]]; then
  echo "Repository directory does not exist: $REPO_DIR" >&2
  exit 2
fi

if [[ "$EUID" -ne 0 && "$CRON_FILE" == /etc/cron.d/* ]]; then
  echo "Writing $CRON_FILE requires root. Re-run with sudo or set --cron-file to a writable path." >&2
  exit 2
fi

restore_line=""
if [[ "$RESTORE_DRILL_ENABLED" == "true" ]]; then
  restore_line="47 3 * * * $USER_NAME cd $REPO_DIR && bash deploy/jenkins/restore_drill_jenkins.sh --backup-dir /opt/weitesting/backups/jenkins --drill-dir $ARTIFACT_DIR/jenkins-restore-drill/drills --output-path $ARTIFACT_DIR/jenkins-restore-drill/latest.json >>$LOG_DIR/jenkins-restore-drill.log 2>&1"
fi

cat >"$CRON_FILE" <<EOF
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# WeiTesting daily performance baseline.
11 3 * * * $USER_NAME cd $REPO_DIR && if [[ -f scripts/run_performance_baseline.sh ]]; then bash scripts/run_performance_baseline.sh --api-base-url https://api.evanshine.me --frontend-url https://app.evanshine.me --business-paths "/api/ops/health/summary,/metrics" --iterations 20 --output-path "$ARTIFACT_DIR/performance-baseline/baseline-\$(date +\\%Y\\%m\\%d-\\%H\\%M\\%S).json" --trend-path "$ARTIFACT_DIR/performance-baseline/trend-summary.json" >>"$LOG_DIR/performance-baseline.log" 2>&1; elif command -v pwsh >/dev/null 2>&1; then pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/run_performance_baseline.ps1 -ApiBaseUrl https://api.evanshine.me -FrontendUrl https://app.evanshine.me -BusinessPaths "/api/ops/health/summary,/metrics" -Iterations 20 -OutputPath "$ARTIFACT_DIR/performance-baseline/baseline-\$(date +\\%Y\\%m\\%d-\\%H\\%M\\%S).json" -TrendPath "$ARTIFACT_DIR/performance-baseline/trend-summary.json" >>"$LOG_DIR/performance-baseline.log" 2>&1; else echo "performance baseline runner missing" >>"$LOG_DIR/performance-baseline.log"; fi

# WeiTesting production readiness report.
29 3 * * * $USER_NAME cd $REPO_DIR && bash scripts/verify_production_readiness.sh --app-url https://app.evanshine.me --api-base-url https://api.evanshine.me --grafana-url https://grafana.evanshine.me --jenkins-url https://jenkins.evanshine.me --prometheus-url http://127.0.0.1:9090 --jenkins-backup-dir /opt/weitesting/backups/jenkins --output-path "$ARTIFACT_DIR/production-readiness/readiness-\$(date +\\%Y\\%m\\%d-\\%H\\%M\\%S).json" >>"$LOG_DIR/production-readiness.log" 2>&1

# WeiTesting Jenkins restore drill.
$restore_line
EOF

chmod 0644 "$CRON_FILE"
echo "WeiTesting ops cron installed: $CRON_FILE"
echo "RESTORE_DRILL_ENABLED=$RESTORE_DRILL_ENABLED"
