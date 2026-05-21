#!/usr/bin/env bash
set -euo pipefail

API_BASE_URL="${API_BASE_URL:-https://api.evanshine.me}"
FRONTEND_URL="${FRONTEND_URL:-https://app.evanshine.me}"
OUTPUT_PATH="./artifacts/performance-baseline/baseline-report.json"
TREND_PATH="./artifacts/performance-baseline/trend-summary.json"
ITERATIONS=10
BUSINESS_PATHS="/api/ops/health/summary"
FAIL_ON_WARN=0
DRY_RUN=0

usage() {
  cat <<'EOF'
Usage: ./scripts/run_performance_baseline.sh [options]

Options:
  --api-base-url <url>
  --frontend-url <url>
  --output-path <path>
  --trend-path <path>
  --iterations <n>
  --business-paths <comma-separated paths>
  --fail-on-warn
  --dry-run
  --help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --api-base-url) API_BASE_URL="$2"; shift 2 ;;
    --frontend-url) FRONTEND_URL="$2"; shift 2 ;;
    --output-path) OUTPUT_PATH="$2"; shift 2 ;;
    --trend-path) TREND_PATH="$2"; shift 2 ;;
    --iterations) ITERATIONS="$2"; shift 2 ;;
    --business-paths) BUSINESS_PATHS="$2"; shift 2 ;;
    --fail-on-warn) FAIL_ON_WARN=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage; exit 64 ;;
  esac
done

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "[DryRun] ApiBaseUrl: $API_BASE_URL"
  echo "[DryRun] FrontendUrl: $FRONTEND_URL"
  echo "[DryRun] OutputPath: $OUTPUT_PATH"
  echo "[DryRun] TrendPath: $TREND_PATH"
  echo "[DryRun] Iterations: $ITERATIONS"
  echo "[DryRun] BusinessPaths: $BUSINESS_PATHS"
  echo "[DryRun] FailOnWarn: $FAIL_ON_WARN"
  exit 0
fi

python3 - "$API_BASE_URL" "$FRONTEND_URL" "$OUTPUT_PATH" "$TREND_PATH" "$ITERATIONS" "$BUSINESS_PATHS" "$FAIL_ON_WARN" <<'PY'
import datetime as dt
import json
import math
import os
import statistics
import sys
import time
import urllib.error
import urllib.request

API_BASE_URL, FRONTEND_URL, OUTPUT_PATH, TREND_PATH, ITERATIONS, BUSINESS_PATHS, FAIL_ON_WARN = sys.argv[1:]
ITERATIONS = int(ITERATIONS)
FAIL_ON_WARN = FAIL_ON_WARN == "1"
BACKEND_THRESHOLD_P95_MS = 1000
FRONTEND_THRESHOLD_P95_MS = 2000


def join_url(base: str, path: str) -> str:
    return base.rstrip("/") + path


def percentile(values, percentile_value):
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil((percentile_value / 100) * len(ordered)) - 1))
    return round(ordered[index], 2)


def measure_endpoint(name: str, url: str, count: int):
    samples = []
    latencies = []
    error_count = 0
    for iteration in range(1, count + 1):
        started = time.perf_counter()
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "weitesting-performance-baseline/1.0"})
            with urllib.request.urlopen(request, timeout=10) as response:
                response.read()
                latency_ms = round((time.perf_counter() - started) * 1000, 2)
                latencies.append(latency_ms)
                samples.append({
                    "iteration": iteration,
                    "latencyMs": latency_ms,
                    "statusCode": response.status,
                    "success": True,
                    "error": None,
                })
        except urllib.error.HTTPError as exc:
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            error_count += 1
            samples.append({
                "iteration": iteration,
                "latencyMs": latency_ms,
                "statusCode": exc.code,
                "success": False,
                "error": str(exc),
            })
        except Exception as exc:
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            error_count += 1
            samples.append({
                "iteration": iteration,
                "latencyMs": latency_ms,
                "statusCode": None,
                "success": False,
                "error": str(exc),
            })
    return {
        "name": name,
        "url": url,
        "sampleCount": count,
        "successfulSamples": len(latencies),
        "p50Ms": percentile(latencies, 50),
        "p95Ms": percentile(latencies, 95),
        "maxMs": round(max(latencies), 2) if latencies else None,
        "errorCount": error_count,
        "samples": samples,
        "skipped": False,
    }


backend = measure_endpoint("backend-health", join_url(API_BASE_URL, "/health"), ITERATIONS)
frontend = measure_endpoint("frontend-root", FRONTEND_URL, ITERATIONS)
business = []
for path in [item.strip() for item in BUSINESS_PATHS.split(",") if item.strip()]:
    normalized = path if path.startswith("/") else f"/{path}"
    business.append(measure_endpoint(f"business:{normalized}", join_url(API_BASE_URL, normalized), ITERATIONS))

conclusion = "READY"
if backend["successfulSamples"] == 0 or frontend["successfulSamples"] == 0:
    conclusion = "BLOCKED"
elif backend["errorCount"] > 0 or frontend["errorCount"] > 0:
    conclusion = "WARN"
elif any(item["errorCount"] > 0 or item["successfulSamples"] == 0 for item in business):
    conclusion = "WARN"
elif (backend["p95Ms"] is not None and backend["p95Ms"] > BACKEND_THRESHOLD_P95_MS) or (
    frontend["p95Ms"] is not None and frontend["p95Ms"] > FRONTEND_THRESHOLD_P95_MS
):
    conclusion = "WARN"

report = {
    "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
    "targets": {
        "apiBaseUrl": API_BASE_URL,
        "backendHealthUrl": join_url(API_BASE_URL, "/health"),
        "frontendUrl": FRONTEND_URL,
        "businessPaths": [item.strip() for item in BUSINESS_PATHS.split(",") if item.strip()],
        "iterations": ITERATIONS,
    },
    "results": {
        "backend": backend,
        "frontend": frontend,
        "business": business,
    },
    "thresholds": {
        "backendP95Ms": BACKEND_THRESHOLD_P95_MS,
        "frontendP95Ms": FRONTEND_THRESHOLD_P95_MS,
    },
    "conclusion": conclusion,
    "gate": {
        "failOnWarn": FAIL_ON_WARN,
        "shouldFail": FAIL_ON_WARN and conclusion in {"WARN", "BLOCKED"},
        "exitCode": 2 if FAIL_ON_WARN and conclusion in {"WARN", "BLOCKED"} else 0,
    },
}

os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
with open(OUTPUT_PATH, "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=2, ensure_ascii=False)

history = []
if os.path.exists(TREND_PATH):
    try:
        with open(TREND_PATH, encoding="utf-8") as fh:
            existing = json.load(fh)
        history = existing.get("history", [])
    except Exception:
        history = []
history.append({
    "generatedAt": report["generatedAt"],
    "reportPath": OUTPUT_PATH,
    "conclusion": conclusion,
    "backendP95Ms": backend["p95Ms"],
    "frontendP95Ms": frontend["p95Ms"],
    "businessCount": len(business),
    "businessWarnCount": sum(1 for item in business if item["errorCount"] > 0 or item["successfulSamples"] == 0),
})
trend = {
    "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
    "history": history[-100:],
}
os.makedirs(os.path.dirname(TREND_PATH), exist_ok=True)
with open(TREND_PATH, "w", encoding="utf-8") as fh:
    json.dump(trend, fh, indent=2, ensure_ascii=False)

print(f"Performance baseline written to: {os.path.abspath(OUTPUT_PATH)}")
print(f"Performance trend-summary written to: {os.path.abspath(TREND_PATH)}")
print(f"Conclusion: {conclusion}")
if report["gate"]["shouldFail"]:
    print("Performance baseline gate failed (FailOnWarn enabled).", file=sys.stderr)
    sys.exit(report["gate"]["exitCode"])
PY
