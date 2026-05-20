# WeiTesting Verification Scripts

Run from the repository root.

## One-click local startup

```bat
start-dev.bat
start-dev.bat --dry-run
```

What it does:

- checks Docker availability (non-blocking check)
- probes local PostgreSQL (`localhost:5432`, user `postgres`) when `psql` exists
- runs backend migrations against `DATABASE_URL` (defaults to local `ai_test_platform`)
- installs frontend deps with `npm ci` when `node_modules` is missing
- starts backend on `8000` and frontend dev server on `5173`

For the PostgreSQL-backed E2E database, use `.\scripts\verify_real_e2e.ps1`; that script creates/migrates the `ai_test_platform_e2e` database before tests.

Stop local services:

```bat
stop-dev.bat
```

It stops listening processes on ports `8000`, `5173`, and `4173`.

## Local performance baseline (no external systems)

```powershell
.\scripts\run_performance_baseline.ps1
```

Quick help / dry-run:

```powershell
.\scripts\run_performance_baseline.ps1 -Help
.\scripts\run_performance_baseline.ps1 -DryRun
```

This script is a repeatable local smoke baseline, not a full load or stress test. It measures simple request latency to:

- backend `GET /health`
- frontend root URL

Default behavior:

- `Iterations=10`
- backend threshold: `p95 <= 1000ms`
- frontend threshold: `p95 <= 2000ms`
- output: `.\artifacts\performance-baseline\baseline-report.json`

Optional flags:

```powershell
.\scripts\run_performance_baseline.ps1 `
  -ApiBaseUrl "http://127.0.0.1:8000" `
  -FrontendUrl "http://127.0.0.1:4173" `
  -OutputPath ".\artifacts\performance-baseline\baseline-$(Get-Date -Format yyyyMMdd-HHmmss).json" `
  -SkipFrontendSmoke `
  -Iterations 20
```

DingTalk notification (optional, via env vars; do not hardcode token):

```powershell
$env:DINGTALK_WEBHOOK_URL="https://oapi.dingtalk.com/robot/send?access_token=***"
$env:DINGTALK_WEBHOOK_SECRET="***"
.\scripts\run_performance_baseline.ps1
```

For trend tracking, keep timestamped JSON reports under `artifacts/performance-baseline/` and attach them to PRs or CI artifacts when comparing regressions.

## Default gate

```powershell
.\scripts\verify_real_e2e.ps1
```

Quick help / dry-run:

```powershell
.\scripts\verify_real_e2e.ps1 -Help
.\scripts\verify_real_e2e.ps1 -DryRun
```

This runs:

- backend E2E database setup/migrations
- backend `pytest tests -q`
- frontend `npm run build`
- frontend generated Playwright E2E: `npx playwright test tests/ui/generated --reporter=line --workers=1`

The backend test run includes `tests/e2e`, so PostgreSQL must be reachable. By default it uses:

```text
postgresql+asyncpg://postgres:postgres@localhost:5432/ai_test_platform_e2e
```

The script refuses database names that do not contain `test` or `e2e`.

Generated E2E defaults to one worker for repeatability on Windows machines with tight CPU/RAM. Override only when the machine has enough headroom:

```powershell
.\scripts\verify_real_e2e.ps1 -GeneratedE2EWorkers 4
```

## Backend-only mode

```powershell
.\scripts\verify_real_e2e.ps1 -BackendE2EOnly
```

This is the fast local command when you only need backend real E2E coverage:

- backend `pytest tests/e2e -v`
- skips frontend build
- skips generated frontend Playwright E2E

## Include frontend real E2E

Start the backend first, then run:

```powershell
.\scripts\verify_real_e2e.ps1 -WithFrontendRealE2E
```

Defaults:

- backend health: `http://127.0.0.1:8000/health`
- frontend Playwright server: `http://127.0.0.1:4173`

Override when needed:

```powershell
.\scripts\verify_real_e2e.ps1 `
  -WithFrontendRealE2E `
  -ApiBaseUrl "http://127.0.0.1:8000" `
  -FrontendUrl "http://127.0.0.1:4173"
```

DingTalk notification (optional, via env vars; do not hardcode token):

```powershell
$env:DINGTALK_WEBHOOK_URL="https://oapi.dingtalk.com/robot/send?access_token=***"
$env:DINGTALK_WEBHOOK_SECRET="***"
.\scripts\verify_real_e2e.ps1 -WithFrontendRealE2E
```

Generated and real Playwright reports are written to different folders:

- `ai-project_front_end/tests/ui/reports/html`
- `ai-project_front_end/tests/ui/reports/real-html`

## CI workflow

GitHub Actions workflow: `.github/workflows/real-e2e.yml`

Triggers:

- `pull_request`
- `push` to `dev`, `main`, or `master`
- `workflow_dispatch` (manual)
- nightly `schedule`

Default CI phases (same gate as local script):

1. Python + Node setup
2. Backend deps install (`pip install -r requirements.txt`)
3. Frontend deps install (`npm ci`)
4. Playwright Chromium install
5. `.\scripts\verify_real_e2e.ps1` (backend pytest, frontend build, generated Playwright E2E)

PostgreSQL service is provided in CI as:

```text
postgresql+asyncpg://postgres:postgres@localhost:5432/ai_test_platform_e2e
```

### Frontend real E2E in CI

The workflow includes input `includeFrontendRealE2E` for `workflow_dispatch`.

When enabled, or when the nightly schedule runs:

- starts backend (`uvicorn app.main:app`) and frontend preview (`npm run preview`)
- runs:

```powershell
.\scripts\verify_real_e2e.ps1 -SkipBackend -SkipFrontendBuild -SkipGeneratedE2E -WithFrontendRealE2E
```

This keeps frontend real E2E out of every PR by default while still giving you a repeatable manual run and a scheduled mainline safety net.

Useful `gh` commands:

```powershell
gh workflow run real-e2e --repo Inventionyin/ai-project --ref dev -f includeFrontendRealE2E=false
gh workflow run real-e2e --repo Inventionyin/ai-project --ref dev -f includeFrontendRealE2E=true
gh run list --repo Inventionyin/ai-project --workflow real-e2e --limit 10
gh run watch <run-id> --repo Inventionyin/ai-project --exit-status
gh run view <run-id> --repo Inventionyin/ai-project --log-failed
gh run rerun <run-id> --repo Inventionyin/ai-project --failed
```
