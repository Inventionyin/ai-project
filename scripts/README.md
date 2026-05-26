# WeiTesting Verification Scripts

Run from the repository root.

## Unified operations entry point

For daily development, acceptance checks, and handover operations, prefer the
wrapper below. It keeps the individual scripts available while giving operators
one command surface:

```powershell
.\scripts\operate.ps1 -Action help
```

Common actions:

```powershell
.\scripts\operate.ps1 -Action start
.\scripts\operate.ps1 -Action stop
.\scripts\operate.ps1 -Action local-gate
.\scripts\operate.ps1 -Action backend-e2e
.\scripts\operate.ps1 -Action frontend-build
.\scripts\operate.ps1 -Action performance
.\scripts\operate.ps1 -Action production
.\scripts\operate.ps1 -Action external -ExternalTargets Jira,Zentao,Jenkins,DingTalk
.\scripts\operate.ps1 -Action delivery-check
.\scripts\operate.ps1 -Action all-dry-run
```

Use `delivery-check` before a handover or demo. It checks the delivery evidence
documents and runs non-invasive dry-runs for production readiness, external
integration diagnostics, and performance baseline wiring.

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

Linux/server equivalent:

```bash
bash ./scripts/run_performance_baseline.sh
```

Quick help / dry-run:

```powershell
.\scripts\run_performance_baseline.ps1 -Help
.\scripts\run_performance_baseline.ps1 -DryRun
```

```bash
bash ./scripts/run_performance_baseline.sh --help
bash ./scripts/run_performance_baseline.sh --dry-run
```

This script is a repeatable local smoke baseline, not a full load or stress test. It measures request latency to:

- backend `GET /health`
- frontend root URL
- configurable business API paths such as `GET /api/ops/health/summary` and `GET /api/projects/home-stats`

Default behavior:

- `Iterations=10`
- backend threshold: `p95 <= 1000ms`
- frontend threshold: `p95 <= 2000ms`
- output: `.\artifacts\performance-baseline\baseline-report.json`
- trend output: `.\artifacts\performance-baseline\trend-summary.json`
- concise console summary: p95, mean, success rate, errors, and previous-run p95 delta when available

Optional flags:

```powershell
.\scripts\run_performance_baseline.ps1 `
  -ApiBaseUrl "http://127.0.0.1:8000" `
  -FrontendUrl "http://127.0.0.1:4173" `
  -OutputPath ".\artifacts\performance-baseline\baseline-$(Get-Date -Format yyyyMMdd-HHmmss).json" `
  -BusinessPaths "/api/ops/health/summary,/api/projects/home-stats" `
  -SkipFrontendSmoke `
  -Iterations 20
```

Business paths should represent real operator flows. When the target requires auth, provide either a bearer token or controlled-environment impersonation headers:

```powershell
$env:PERF_BASELINE_AUTHORIZATION="eyJ..."
$env:PERF_BASELINE_USER_ID="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
$env:PERF_BASELINE_TENANT_ID="11111111-1111-1111-1111-111111111111"
$env:PERF_BASELINE_ROLES="ADMIN"
```

Equivalent Linux flags:

```bash
bash ./scripts/run_performance_baseline.sh \
  --business-paths "/api/ops/health/summary,/api/projects/home-stats" \
  --business-authorization "$PERF_BASELINE_AUTHORIZATION"
```

DingTalk notification (optional, via env vars; do not hardcode token):

```powershell
$env:DINGTALK_WEBHOOK_URL="https://oapi.dingtalk.com/robot/send?access_token=***"
$env:DINGTALK_WEBHOOK_SECRET="***"
.\scripts\run_performance_baseline.ps1
```

For trend tracking, keep timestamped JSON reports under `artifacts/performance-baseline/` and attach them to PRs or CI artifacts when comparing regressions. The report includes `summary`, `trend.latest`, and `comparison` fields for p95, mean, success-rate, error-count, and timeout deltas.

## Operations cron and restore drill

Install daily server-side operations jobs on Ubuntu:

```bash
sudo REPO_DIR=/opt/weitesting/current \
  LOG_DIR=/var/log/weitesting \
  ARTIFACT_DIR=/opt/weitesting/artifacts \
  USER_NAME=ubuntu \
  bash deploy/ops/install_ops_cron.sh
```

This installs `/etc/cron.d/weitesting-ops` with daily jobs for:

- performance baseline trend reports
- production readiness reports
- Jenkins restore drill reports

Run a Jenkins restore drill manually:

```bash
sudo bash deploy/jenkins/restore_drill_jenkins.sh \
  --backup-dir /opt/weitesting/backups/jenkins \
  --drill-dir /opt/weitesting/restore-drills/jenkins \
  --output-path /opt/weitesting/artifacts/jenkins-restore-drill/latest.json
```

The restore drill extracts the backup to a disposable directory and checks required Jenkins home paths. It never writes into the live `JENKINS_HOME`.

## Production readiness self-check

```powershell
.\scripts\verify_production_readiness.ps1
```

Linux/server equivalent:

```bash
bash ./scripts/verify_production_readiness.sh
```

Quick help / dry-run:

```powershell
.\scripts\verify_production_readiness.ps1 -Help
.\scripts\verify_production_readiness.ps1 -DryRun
```

```bash
bash ./scripts/verify_production_readiness.sh --help
bash ./scripts/verify_production_readiness.sh --dry-run
```

This script checks the deployed environment after domain, tunnel, observability, or Jenkins changes:

- public frontend URL
- public backend health URL
- backend `/metrics` endpoint with the repo-local `weitesting_observability_ready` metric
- Grafana health endpoint
- Jenkins login endpoint
- Prometheus active targets for `weitesting-backend` and `jenkins`
- latest Jenkins backup archive

Backend `/health` and `/metrics` are repo-local observability checks. Prometheus targets, Grafana health, Jenkins login, Jenkins scrape access, and backup freshness are external infrastructure checks.

Default targets are the current Oracle/Cloudflare deployment:

```text
https://app.evanshine.me
https://api.evanshine.me
https://grafana.evanshine.me
https://jenkins.evanshine.me
http://127.0.0.1:9090
/opt/weitesting/backups/jenkins
```

Override them when checking a different deployment:

```powershell
.\scripts\verify_production_readiness.ps1 `
  -AppUrl "https://app.example.com" `
  -ApiBaseUrl "https://api.example.com" `
  -GrafanaUrl "https://grafana.example.com" `
  -JenkinsUrl "https://jenkins.example.com" `
  -PrometheusUrl "http://127.0.0.1:9090" `
  -JenkinsBackupDir "/opt/weitesting/backups/jenkins" `
  -OutputPath ".\artifacts\production-readiness\readiness-$(Get-Date -Format yyyyMMdd-HHmmss).json"
```

```bash
bash ./scripts/verify_production_readiness.sh \
  --app-url "https://app.example.com" \
  --api-base-url "https://api.example.com" \
  --grafana-url "https://grafana.example.com" \
  --jenkins-url "https://jenkins.example.com" \
  --prometheus-url "http://127.0.0.1:9090" \
  --jenkins-backup-dir "/opt/weitesting/backups/jenkins" \
  --output-path "./artifacts/production-readiness/readiness-$(date +%Y%m%d-%H%M%S).json"
```

Use `-FailOnWarn` only after optional hardening is expected to be complete. For example, Jenkins Prometheus `403` is reported as `WARN` because the app can operate while Jenkins metrics are still being enabled.

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
postgresql+asyncpg://postgres:123456@localhost:5432/ai_test_platform_e2e
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
6. `.\scripts\run_performance_baseline.ps1 -DryRun`
7. `.\scripts\verify_production_readiness.ps1 -DryRun` and `bash ./scripts/verify_production_readiness.sh --dry-run`
8. `.\scripts\verify_external_integrations.ps1 -DryRun`

PostgreSQL service is provided in CI as:

```text
postgresql+asyncpg://postgres:123456@localhost:5432/ai_test_platform_e2e
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

### External integration smoke in CI

The workflow includes input `includeExternalSmoke` for `workflow_dispatch`.

When enabled, the workflow injects repository Secrets/Variables and runs the targets from `externalSmokeTargets`, which defaults to `Jira`:

```powershell
.\scripts\verify_external_integrations.ps1 -Targets Jira -EnableSmoke -FailOnSmokeError
```

This keeps live third-party calls out of pull request, push, and nightly CI by default. Use it only after the target external systems have complete repository Secrets/Variables.

Useful `gh` commands:

```powershell
gh workflow run real-e2e --repo Inventionyin/ai-project --ref dev -f includeFrontendRealE2E=false
gh workflow run real-e2e --repo Inventionyin/ai-project --ref dev -f includeFrontendRealE2E=true
gh workflow run real-e2e --repo Inventionyin/ai-project --ref dev -f includeFrontendRealE2E=false -f includeExternalSmoke=true -f externalSmokeTargets=Jira
gh run list --repo Inventionyin/ai-project --workflow real-e2e --limit 10
gh run watch <run-id> --repo Inventionyin/ai-project --exit-status
gh run view <run-id> --repo Inventionyin/ai-project --log-failed
gh run rerun <run-id> --repo Inventionyin/ai-project --failed
```
