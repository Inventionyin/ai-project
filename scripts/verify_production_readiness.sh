#!/usr/bin/env bash
set -euo pipefail

DRY_RUN=0
FAIL_ON_WARN=0
APP_URL="${WEITESTING_APP_URL:-https://app.evanshine.me}"
API_BASE_URL="${WEITESTING_API_URL:-https://api.evanshine.me}"
GRAFANA_URL="${WEITESTING_GRAFANA_URL:-https://grafana.evanshine.me}"
JENKINS_URL="${WEITESTING_JENKINS_URL:-https://jenkins.evanshine.me}"
PROMETHEUS_URL="${WEITESTING_PROMETHEUS_URL:-http://127.0.0.1:9090}"
JENKINS_BACKUP_DIR="${WEITESTING_JENKINS_BACKUP_DIR:-/opt/weitesting/backups/jenkins}"
OUTPUT_PATH="./artifacts/production-readiness/readiness-report.json"

usage() {
  cat <<'EOF'
Usage: ./scripts/verify_production_readiness.sh [options]

Options:
  --app-url <url>
  --api-base-url <url>
  --grafana-url <url>
  --jenkins-url <url>
  --prometheus-url <url>
  --jenkins-backup-dir <path>
  --output-path <path>
  --fail-on-warn
  --dry-run
  --help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --app-url) APP_URL="$2"; shift 2 ;;
    --api-base-url) API_BASE_URL="$2"; shift 2 ;;
    --grafana-url) GRAFANA_URL="$2"; shift 2 ;;
    --jenkins-url) JENKINS_URL="$2"; shift 2 ;;
    --prometheus-url) PROMETHEUS_URL="$2"; shift 2 ;;
    --jenkins-backup-dir) JENKINS_BACKUP_DIR="$2"; shift 2 ;;
    --output-path) OUTPUT_PATH="$2"; shift 2 ;;
    --fail-on-warn) FAIL_ON_WARN=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage; exit 64 ;;
  esac
done

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "[DryRun] AppUrl: $APP_URL"
  echo "[DryRun] ApiBaseUrl: $API_BASE_URL"
  echo "[DryRun] GrafanaUrl: $GRAFANA_URL"
  echo "[DryRun] JenkinsUrl: $JENKINS_URL"
  echo "[DryRun] PrometheusUrl: $PROMETHEUS_URL"
  echo "[DryRun] JenkinsBackupDir: $JENKINS_BACKUP_DIR"
  echo "[DryRun] OutputPath: $OUTPUT_PATH"
  echo "[DryRun] FailOnWarn: $FAIL_ON_WARN"
  exit 0
fi

python3 - "$APP_URL" "$API_BASE_URL" "$GRAFANA_URL" "$JENKINS_URL" "$PROMETHEUS_URL" "$JENKINS_BACKUP_DIR" "$OUTPUT_PATH" "$FAIL_ON_WARN" <<'PY'
import datetime as dt
import glob
import json
import os
import sys
import urllib.error
import urllib.request

APP_URL, API_BASE_URL, GRAFANA_URL, JENKINS_URL, PROMETHEUS_URL, JENKINS_BACKUP_DIR, OUTPUT_PATH, FAIL_ON_WARN = sys.argv[1:]
FAIL_ON_WARN = FAIL_ON_WARN == "1"


def join_url(base: str, path: str) -> str:
    return base.rstrip("/") + path


def check(name: str, status: str, message: str, details=None):
    return {
        "name": name,
        "status": status,
        "message": message,
        "details": details or {},
    }


def http_get(url: str):
    request = urllib.request.Request(url, headers={"User-Agent": "weitesting-production-readiness/1.0"})
    with urllib.request.urlopen(request, timeout=15) as response:
        body = response.read().decode("utf-8", errors="replace")
        return response.status, body


def test_http_endpoint(name: str, url: str, expected_statuses=(200,), required_content: str = ""):
    try:
        status, body = http_get(url)
        if status not in expected_statuses:
            return check(name, "BLOCKED", f"Unexpected HTTP status {status} from {url}", {
                "url": url,
                "statusCode": status,
                "expectedStatusCodes": list(expected_statuses),
            })
        if required_content and required_content not in body:
            return check(name, "WARN", "HTTP status was OK, but expected content was not found.", {
                "url": url,
                "statusCode": status,
                "requiredContent": required_content,
            })
        return check(name, "READY", "HTTP endpoint reachable.", {"url": url, "statusCode": status})
    except urllib.error.HTTPError as exc:
        return check(name, "BLOCKED", str(exc), {"url": url, "statusCode": exc.code})
    except Exception as exc:
        return check(name, "BLOCKED", str(exc), {"url": url, "statusCode": None})


def test_prometheus_targets(base_url: str):
    url = join_url(base_url, "/api/v1/targets?state=active")
    try:
        _, body = http_get(url)
        payload = json.loads(body)
        active_targets = payload.get("data", {}).get("activeTargets", [])
        by_job = {target.get("labels", {}).get("job"): target for target in active_targets}
        issues = []
        backend = by_job.get("weitesting-backend")
        jenkins = by_job.get("jenkins")
        if backend is None:
            issues.append("Prometheus target weitesting-backend is missing.")
        elif backend.get("health") != "up":
            issues.append(f"Prometheus target weitesting-backend is {backend.get('health')}.")
        if jenkins is None:
            issues.append("Prometheus target jenkins is missing.")
        elif jenkins.get("health") != "up":
            issues.append(
                f"Prometheus target jenkins is {jenkins.get('health')}. "
                "Verify Jenkins /prometheus returns 200 and that the Jenkins Prometheus plugin/permissions are configured."
            )
        status = "READY" if not issues else "WARN"
        message = "Prometheus targets are healthy." if not issues else " ".join(issues)
        return check(name="prometheus-targets", status=status, message=message, details={
            "url": url,
            "targetCount": len(active_targets),
            "targets": [
                {
                    "job": target.get("labels", {}).get("job"),
                    "health": target.get("health"),
                    "scrapeUrl": target.get("scrapeUrl"),
                    "lastError": target.get("lastError"),
                }
                for target in active_targets
            ],
        })
    except Exception as exc:
        return check("prometheus-targets", "WARN", str(exc), {"url": url})


def test_jenkins_backup(backup_dir: str):
    if not os.path.isdir(backup_dir):
        return check("jenkins-backup", "WARN", "Jenkins backup directory does not exist.", {"backupDir": backup_dir})
    backups = sorted(glob.glob(os.path.join(backup_dir, "jenkins-*.tgz")), key=os.path.getmtime, reverse=True)
    if not backups:
        return check("jenkins-backup", "WARN", "No Jenkins backup archive found.", {"backupDir": backup_dir})
    latest = backups[0]
    age_hours = round((dt.datetime.now(dt.timezone.utc).timestamp() - os.path.getmtime(latest)) / 3600, 2)
    status = "READY" if age_hours <= 36 else "WARN"
    message = "Recent Jenkins backup archive found." if status == "READY" else "Latest Jenkins backup is older than 36 hours."
    return check("jenkins-backup", status, message, {
        "backupDir": backup_dir,
        "latestBackup": latest,
        "sizeBytes": os.path.getsize(latest),
        "ageHours": age_hours,
    })


checks = [
    test_http_endpoint("app-public-url", APP_URL, required_content='<div id="app"></div>'),
    test_http_endpoint("api-health", join_url(API_BASE_URL, "/health"), required_content='"status":"ok"'),
    test_http_endpoint("grafana-health", join_url(GRAFANA_URL, "/api/health"), required_content='"database"'),
    test_http_endpoint("jenkins-login", join_url(JENKINS_URL, "/login"), required_content="Sign in to Jenkins"),
    test_prometheus_targets(PROMETHEUS_URL),
    test_jenkins_backup(JENKINS_BACKUP_DIR),
]

blocked = sum(1 for item in checks if item["status"] == "BLOCKED")
warn = sum(1 for item in checks if item["status"] == "WARN")
conclusion = "BLOCKED" if blocked else ("WARN" if warn else "READY")
recommended_actions = []
if any(item["name"] == "prometheus-targets" and item["status"] != "READY" for item in checks):
    recommended_actions.append("Verify Jenkins /prometheus returns 200; install/enable Jenkins Prometheus plugin and grant scrape access if Jenkins metrics are required.")
if any(item["name"] == "jenkins-backup" and item["status"] != "READY" for item in checks):
    recommended_actions.append("Run deploy/jenkins/backup_jenkins.sh and perform one restore drill before production cutover.")
recommended_actions.append("Keep Jenkins and Grafana behind strong login or Cloudflare Access before inviting external users.")
recommended_actions.append("Rotate external tokens that were shared during setup before treating this environment as production.")

report = {
    "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
    "targets": {
        "appUrl": APP_URL,
        "apiBaseUrl": API_BASE_URL,
        "grafanaUrl": GRAFANA_URL,
        "jenkinsUrl": JENKINS_URL,
        "prometheusUrl": PROMETHEUS_URL,
        "jenkinsBackupDir": JENKINS_BACKUP_DIR,
    },
    "checks": checks,
    "summary": {
        "conclusion": conclusion,
        "ready": sum(1 for item in checks if item["status"] == "READY"),
        "warn": warn,
        "blocked": blocked,
    },
    "recommendedActions": recommended_actions,
    "gate": {
        "failOnWarn": FAIL_ON_WARN,
        "shouldFail": FAIL_ON_WARN and conclusion in {"WARN", "BLOCKED"},
        "exitCode": 2 if FAIL_ON_WARN and conclusion in {"WARN", "BLOCKED"} else 0,
    },
}

directory = os.path.dirname(OUTPUT_PATH)
if directory:
    os.makedirs(directory, exist_ok=True)
with open(OUTPUT_PATH, "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=2, ensure_ascii=False)

print(f"Production readiness written to: {os.path.abspath(OUTPUT_PATH)}")
print(f"Conclusion: {conclusion}")
for item in checks:
    print(f"[{item['status']}] {item['name']}: {item['message']}")

if report["gate"]["shouldFail"]:
    print("Production readiness gate failed (FailOnWarn enabled).", file=sys.stderr)
    sys.exit(report["gate"]["exitCode"])
PY
