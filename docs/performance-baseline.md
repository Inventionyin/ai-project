# Performance Baseline (Local)

## Purpose

`scripts/run_performance_baseline.ps1` provides a lightweight, repeatable local baseline for WeiTesting. It is intended for quick regression signal during development and PR checks.

This baseline is **not** a full load test, soak test, or production capacity benchmark.

## What it measures

Per target, over `N` iterations (`Iterations`, default `10`):

- `meanMs`
- `minMs`
- `p50Ms`
- `p90Ms`
- `p95Ms`
- `maxMs`
- `errorCount`
- `timeoutCount`
- `successRatePct`
- `errorRatePct`

Targets:

- Backend health endpoint: `GET {ApiBaseUrl}/health`
- Frontend root endpoint: `GET {FrontendUrl}`
- Business API paths: `GET {ApiBaseUrl}{BusinessPaths}`; default `GET /api/ops/health/summary`

Both can be skipped independently with `-SkipBackendSmoke` or `-SkipFrontendSmoke`.

Business paths are intended to sample real operator-facing API flows, not only pure liveness pings. Most WeiTesting business routes require authentication. Provide either a bearer token or the local/controlled-environment impersonation headers:

```powershell
$env:PERF_BASELINE_AUTHORIZATION="eyJ..."

# or, when AUTH_HEADER_IMPERSONATION_ENABLED=true in a non-production target:
$env:PERF_BASELINE_USER_ID="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
$env:PERF_BASELINE_TENANT_ID="11111111-1111-1111-1111-111111111111"
$env:PERF_BASELINE_ROLES="ADMIN"
```

Equivalent explicit flags are `-BusinessAuthorization`, `-BusinessUserId`, `-BusinessTenantId`, `-BusinessRoles`, and `-BusinessHeadersJson`.

## Defaults and thresholds

- Backend threshold: `p95 <= 1000ms`
- Frontend threshold: `p95 <= 2000ms`

Conclusion field in the report:

- `READY`: no threshold breach and no request errors
- `WARN`: threshold breach and/or request errors
- `BLOCKED`: no usable signal (for example both targets skipped, or a non-skipped target has zero successful samples)

## Usage

From repository root:

```powershell
.\scripts\run_performance_baseline.ps1
```

Example with explicit output and higher iteration count:

```powershell
.\scripts\run_performance_baseline.ps1 `
  -ApiBaseUrl "http://127.0.0.1:8000" `
  -FrontendUrl "http://127.0.0.1:4173" `
  -Iterations 20 `
  -BusinessPaths "/api/ops/health/summary,/api/projects/home-stats" `
  -OutputPath ".\artifacts\performance-baseline\baseline-$(Get-Date -Format yyyyMMdd-HHmmss).json"
```

Optional strict gate mode (CI-friendly):

```powershell
.\scripts\run_performance_baseline.ps1 -FailOnWarn
```

When `-FailOnWarn` is enabled, the script exits with code `2` if the conclusion is `WARN` or `BLOCKED`; otherwise exit code is `0`.

## Report schema (JSON)

The script writes one JSON file containing:

- `generatedAt`
- `targets`
  - `businessTargets`
  - `businessHeadersConfigured`
  - `businessAuthMode`
- `results`
  - `backend`
  - `frontend`
  - `business`
- `summary`
- `thresholds`
- `conclusion`
- `gate`
  - `failOnWarn`
  - `shouldFail`
  - `exitCode`
- `trend`
  - `path`
  - `historyCount`
  - `latest`
  - `comparison`
- `comparison`
  - previous run timestamp/path
  - backend/frontend p95/error/success deltas
  - per-business-path p95/error/success deltas
  - `regressionCount`

Each result includes samples and summary metrics so the file can be archived and compared later.

## Archiving guidance

Store timestamped output files under:

`artifacts/performance-baseline/`

Recommended practice:

1. Capture a baseline before major backend/frontend changes.
2. Capture again after changes.
3. Compare `summary.*.p95Ms`, `successRatePct`, `errorCount`, and `comparison.*Delta*`.
4. Attach both JSON files to the PR or CI job artifacts for traceability.

The script also appends `TrendPath` with the latest 100 runs. Operator output stays concise: report path, trend path, backend/frontend/business p95 and mean latency, success rate, errors, previous-run p95 delta when available, and final conclusion.
