#!/usr/bin/env bash
set -euo pipefail

API_BASE_URL="${API_BASE_URL:-https://api.evanshine.me}"
FRONTEND_URL="${FRONTEND_URL:-https://app.evanshine.me}"
OUTPUT_PATH="./artifacts/performance-baseline/baseline-report.json"
TREND_PATH="./artifacts/performance-baseline/trend-summary.json"
ITERATIONS=10
BUSINESS_PATHS="/api/ops/health/summary"
BUSINESS_HEADERS_JSON="${PERF_BASELINE_BUSINESS_HEADERS_JSON:-}"
BUSINESS_AUTHORIZATION="${PERF_BASELINE_AUTHORIZATION:-}"
BUSINESS_USER_ID="${PERF_BASELINE_USER_ID:-}"
BUSINESS_TENANT_ID="${PERF_BASELINE_TENANT_ID:-}"
BUSINESS_ROLES="${PERF_BASELINE_ROLES:-}"
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
  --business-headers-json <json object>
  --business-authorization <bearer token or raw token>
  --business-user-id <uuid>
  --business-tenant-id <uuid>
  --business-roles <comma-separated roles>
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
    --business-headers-json) BUSINESS_HEADERS_JSON="$2"; shift 2 ;;
    --business-authorization) BUSINESS_AUTHORIZATION="$2"; shift 2 ;;
    --business-user-id) BUSINESS_USER_ID="$2"; shift 2 ;;
    --business-tenant-id) BUSINESS_TENANT_ID="$2"; shift 2 ;;
    --business-roles) BUSINESS_ROLES="$2"; shift 2 ;;
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
  echo "[DryRun] BusinessHeadersConfigured: $([[ -n "$BUSINESS_HEADERS_JSON$BUSINESS_AUTHORIZATION$BUSINESS_USER_ID$BUSINESS_TENANT_ID" ]] && echo 1 || echo 0)"
  echo "[DryRun] FailOnWarn: $FAIL_ON_WARN"
  exit 0
fi

python3 - "$API_BASE_URL" "$FRONTEND_URL" "$OUTPUT_PATH" "$TREND_PATH" "$ITERATIONS" "$BUSINESS_PATHS" "$FAIL_ON_WARN" "$BUSINESS_HEADERS_JSON" "$BUSINESS_AUTHORIZATION" "$BUSINESS_USER_ID" "$BUSINESS_TENANT_ID" "$BUSINESS_ROLES" <<'PY'
import datetime as dt
import json
import math
import os
import sys
import time
import urllib.error
import urllib.request

(
    API_BASE_URL,
    FRONTEND_URL,
    OUTPUT_PATH,
    TREND_PATH,
    ITERATIONS,
    BUSINESS_PATHS,
    FAIL_ON_WARN,
    BUSINESS_HEADERS_JSON,
    BUSINESS_AUTHORIZATION,
    BUSINESS_USER_ID,
    BUSINESS_TENANT_ID,
    BUSINESS_ROLES,
) = sys.argv[1:]
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


def average(values):
    return round(sum(values) / len(values), 2) if values else None


def summarize(samples):
    successful = [sample for sample in samples if sample["success"]]
    latencies = [sample["latencyMs"] for sample in successful]
    sample_count = len(samples)
    error_count = sample_count - len(successful)
    return {
        "sampleCount": sample_count,
        "successfulSamples": len(successful),
        "successRatePct": round((len(successful) / sample_count) * 100, 2) if sample_count else None,
        "errorRatePct": round((error_count / sample_count) * 100, 2) if sample_count else None,
        "meanMs": average(latencies),
        "minMs": round(min(latencies), 2) if latencies else None,
        "p50Ms": percentile(latencies, 50),
        "p90Ms": percentile(latencies, 90),
        "p95Ms": percentile(latencies, 95),
        "maxMs": round(max(latencies), 2) if latencies else None,
        "errorCount": error_count,
        "timeoutCount": sum(1 for sample in samples if (sample.get("error") or "").lower().find("timed out") >= 0 or (sample.get("error") or "").lower().find("timeout") >= 0),
    }


def target_snapshot(result):
    return {
        "name": result["name"],
        "url": result["url"],
        "sampleCount": result["sampleCount"],
        "successfulSamples": result["successfulSamples"],
        "successRatePct": result["successRatePct"],
        "errorRatePct": result["errorRatePct"],
        "meanMs": result["meanMs"],
        "minMs": result["minMs"],
        "p50Ms": result["p50Ms"],
        "p90Ms": result["p90Ms"],
        "p95Ms": result["p95Ms"],
        "maxMs": result["maxMs"],
        "errorCount": result["errorCount"],
        "timeoutCount": result["timeoutCount"],
    }


def delta(current, previous, key):
    if previous is None or current.get(key) is None or previous.get(key) is None:
        return None
    value = current[key] - previous[key]
    return round(value, 2) if isinstance(value, float) else value


def compare_target(current, previous):
    if previous is None:
        return {
            "previousGeneratedAt": None,
            "previousReportPath": None,
            "p50DeltaMs": None,
            "p90DeltaMs": None,
            "p95DeltaMs": None,
            "meanDeltaMs": None,
            "maxDeltaMs": None,
            "successRateDeltaPct": None,
            "errorRateDeltaPct": None,
            "errorCountDelta": None,
            "timeoutCountDelta": None,
        }
    return {
        "previousGeneratedAt": previous.get("generatedAt"),
        "previousReportPath": previous.get("reportPath"),
        "p50DeltaMs": delta(current, previous, "p50Ms"),
        "p90DeltaMs": delta(current, previous, "p90Ms"),
        "p95DeltaMs": delta(current, previous, "p95Ms"),
        "meanDeltaMs": delta(current, previous, "meanMs"),
        "maxDeltaMs": delta(current, previous, "maxMs"),
        "successRateDeltaPct": delta(current, previous, "successRatePct"),
        "errorRateDeltaPct": delta(current, previous, "errorRatePct"),
        "errorCountDelta": delta(current, previous, "errorCount"),
        "timeoutCountDelta": delta(current, previous, "timeoutCount"),
    }


def business_headers():
    headers = {}
    if BUSINESS_AUTHORIZATION.strip():
        authorization = BUSINESS_AUTHORIZATION.strip()
        if not authorization.lower().startswith("bearer "):
            authorization = f"Bearer {authorization}"
        headers["Authorization"] = authorization
    if BUSINESS_USER_ID.strip() and BUSINESS_TENANT_ID.strip():
        headers["X-User-Id"] = BUSINESS_USER_ID.strip()
        headers["X-Tenant-Id"] = BUSINESS_TENANT_ID.strip()
        if BUSINESS_ROLES.strip():
            headers["X-Roles"] = BUSINESS_ROLES.strip()
    if BUSINESS_HEADERS_JSON.strip():
        custom = json.loads(BUSINESS_HEADERS_JSON)
        if not isinstance(custom, dict):
            raise ValueError("business headers json must be an object")
        headers.update({str(k): str(v) for k, v in custom.items()})
    return headers


def measure_endpoint(name: str, url: str, count: int, headers=None):
    request_headers = {"User-Agent": "weitesting-performance-baseline/1.0"}
    if headers:
        request_headers.update(headers)
    samples = []
    for iteration in range(1, count + 1):
        started = time.perf_counter()
        started_at = dt.datetime.now(dt.timezone.utc).isoformat()
        try:
            request = urllib.request.Request(url, headers=request_headers)
            with urllib.request.urlopen(request, timeout=10) as response:
                response.read()
                latency_ms = round((time.perf_counter() - started) * 1000, 2)
                samples.append({
                    "iteration": iteration,
                    "latencyMs": latency_ms,
                    "statusCode": response.status,
                    "success": True,
                    "error": None,
                    "method": "GET",
                    "startedAt": started_at,
                })
        except urllib.error.HTTPError as exc:
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            samples.append({
                "iteration": iteration,
                "latencyMs": latency_ms,
                "statusCode": exc.code,
                "success": False,
                "error": str(exc),
                "method": "GET",
                "startedAt": started_at,
            })
        except Exception as exc:
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            samples.append({
                "iteration": iteration,
                "latencyMs": latency_ms,
                "statusCode": None,
                "success": False,
                "error": str(exc),
                "method": "GET",
                "startedAt": started_at,
            })
    summary = summarize(samples)
    result = {
        "name": name,
        "url": url,
        "samples": samples,
        "skipped": False,
    }
    result.update(summary)
    return result


backend = measure_endpoint("backend-health", join_url(API_BASE_URL, "/health"), ITERATIONS)
frontend = measure_endpoint("frontend-root", FRONTEND_URL, ITERATIONS)
business_request_headers = business_headers()
business = []
for path in [item.strip() for item in BUSINESS_PATHS.split(",") if item.strip()]:
    normalized = path if path.startswith("/") else f"/{path}"
    business.append(measure_endpoint(f"business:{normalized}", join_url(API_BASE_URL, normalized), ITERATIONS, business_request_headers))

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
        "businessTargets": [{"name": item["name"], "url": item["url"]} for item in business],
        "businessHeadersConfigured": bool(business_request_headers),
        "businessAuthMode": "authorization" if "Authorization" in business_request_headers else ("impersonation" if "X-User-Id" in business_request_headers and "X-Tenant-Id" in business_request_headers else "none"),
        "iterations": ITERATIONS,
    },
    "results": {
        "backend": backend,
        "frontend": frontend,
        "business": business,
    },
    "summary": {
        "backend": target_snapshot(backend),
        "frontend": target_snapshot(frontend),
        "business": [target_snapshot(item) for item in business],
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
current_snapshot = {
    "generatedAt": report["generatedAt"],
    "reportPath": OUTPUT_PATH,
    "conclusion": conclusion,
    "backend": target_snapshot(backend),
    "frontend": target_snapshot(frontend),
    "business": [target_snapshot(item) for item in business],
}
previous_snapshot = history[-1] if history else None
business_comparison = []
for item in current_snapshot["business"]:
    previous_item = None
    if previous_snapshot:
        previous_item = next((candidate for candidate in previous_snapshot.get("business", []) if candidate.get("name") == item["name"]), None)
    business_comparison.append({
        "name": item["name"],
        "url": item["url"],
        "p95DeltaMs": delta(item, previous_item, "p95Ms"),
        "meanDeltaMs": delta(item, previous_item, "meanMs"),
        "errorCountDelta": delta(item, previous_item, "errorCount"),
        "successRateDeltaPct": delta(item, previous_item, "successRatePct"),
    })
comparison = {
    "previousGeneratedAt": previous_snapshot.get("generatedAt") if previous_snapshot else None,
    "previousReportPath": previous_snapshot.get("reportPath") if previous_snapshot else None,
    "backend": compare_target(current_snapshot["backend"], previous_snapshot.get("backend") if previous_snapshot else None),
    "frontend": compare_target(current_snapshot["frontend"], previous_snapshot.get("frontend") if previous_snapshot else None),
    "business": business_comparison,
    "regressionCount": sum(1 for item in business_comparison if (item["p95DeltaMs"] is not None and item["p95DeltaMs"] > 0) or (item["errorCountDelta"] is not None and item["errorCountDelta"] > 0)),
}
history.append(current_snapshot)
trend = {
    "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
    "latest": current_snapshot,
    "comparison": comparison,
    "history": history[-100:],
}
os.makedirs(os.path.dirname(TREND_PATH), exist_ok=True)
with open(TREND_PATH, "w", encoding="utf-8") as fh:
    json.dump(trend, fh, indent=2, ensure_ascii=False)
report["trend"] = {
    "path": TREND_PATH,
    "historyCount": len(trend["history"]),
    "latest": trend["latest"],
    "comparison": trend["comparison"],
}
report["comparison"] = comparison
with open(OUTPUT_PATH, "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=2, ensure_ascii=False)


def format_metric(value, suffix=""):
    return f"{value}{suffix}" if value is not None else "n/a"


def print_target(label, result, target_comparison=None):
    delta_text = ""
    if target_comparison and target_comparison.get("p95DeltaMs") is not None:
        delta_text = f", p95 {target_comparison['p95DeltaMs']:+.2f}ms"
    print(
        f"  {label:<16} p95 {format_metric(result['p95Ms'], 'ms')}, "
        f"mean {format_metric(result['meanMs'], 'ms')}, "
        f"success {format_metric(result['successRatePct'], '%')}, "
        f"errors {result['errorCount']}{delta_text}"
    )

print(f"Performance baseline written to: {os.path.abspath(OUTPUT_PATH)}")
print(f"Performance trend-summary written to: {os.path.abspath(TREND_PATH)}")
print("")
print("Performance baseline summary:")
print_target("backend", backend, comparison["backend"])
print_target("frontend", frontend, comparison["frontend"])
for item in business:
    item_comparison = next((candidate for candidate in comparison["business"] if candidate["name"] == item["name"]), None)
    print_target(item["name"], item, item_comparison)
if comparison["previousGeneratedAt"]:
    print(f"Trend comparison: previous run {comparison['previousGeneratedAt']}, regressions {comparison['regressionCount']}")
else:
    print("Trend comparison: no previous run yet")
print(f"Conclusion: {conclusion}")
if report["gate"]["shouldFail"]:
    print("Performance baseline gate failed (FailOnWarn enabled).", file=sys.stderr)
    sys.exit(report["gate"]["exitCode"])
PY
