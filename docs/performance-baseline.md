# Performance Baseline (Local)

## Purpose

`scripts/run_performance_baseline.ps1` provides a lightweight, repeatable local baseline for WeiTesting. It is intended for quick regression signal during development and PR checks.

This baseline is **not** a full load test, soak test, or production capacity benchmark.

## What it measures

Per target, over `N` iterations (`Iterations`, default `10`):

- `p50Ms`
- `p95Ms`
- `maxMs`
- `errorCount`

Targets:

- Backend health endpoint: `GET {ApiBaseUrl}/health`
- Frontend root endpoint: `GET {FrontendUrl}`

Both can be skipped independently with `-SkipBackendSmoke` or `-SkipFrontendSmoke`.

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
- `results`
  - `backend`
  - `frontend`
- `thresholds`
- `conclusion`
- `gate`
  - `failOnWarn`
  - `shouldFail`
  - `exitCode`

Each result includes samples and summary metrics so the file can be archived and compared later.

## Archiving guidance

Store timestamped output files under:

`artifacts/performance-baseline/`

Recommended practice:

1. Capture a baseline before major backend/frontend changes.
2. Capture again after changes.
3. Compare `p95Ms`, `maxMs`, and `errorCount`.
4. Attach both JSON files to the PR or CI job artifacts for traceability.
