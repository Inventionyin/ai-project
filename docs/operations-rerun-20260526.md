# Operations Rerun Record - 2026-05-26

This record captures the first post-acceptance operations rerun after `docs/post-acceptance-operations-sop.md` was added.

## Context

- Repo branch: `master`
- Commit before rerun: `4f78b1a`
- Host: local Windows workstation
- PowerShell: `7.6.2`
- Target app: `https://app.evanshine.me`
- Target API: `https://api.evanshine.me`
- Target Grafana: `https://grafana.evanshine.me`
- Target Jenkins: `https://jenkins.evanshine.me`

## Production Readiness

Command:

```powershell
.\scripts\verify_production_readiness.ps1 `
  -AppUrl "https://app.evanshine.me" `
  -ApiBaseUrl "https://api.evanshine.me" `
  -GrafanaUrl "https://grafana.evanshine.me" `
  -JenkinsUrl "https://jenkins.evanshine.me" `
  -OutputPath ".\artifacts\production-readiness\readiness-20260526-120219.json"
```

Result:

- Conclusion: `WARN`
- READY: 7
- WARN: 2
- BLOCKED: 0

READY checks:

- App public URL
- App same-origin API proxy
- API `/health`
- API `/metrics`
- Grafana `/api/health`
- Jenkins `/login`
- Observability rule files

WARN checks:

- `prometheus-targets`: local workstation cannot reach `http://127.0.0.1:9090`.
- `jenkins-backup`: local workstation does not have `/opt/weitesting/backups/jenkins`.

Interpretation:

The public HTTPS endpoints are reachable. The two WARN items are expected when running the production readiness script from a Windows workstation instead of the production server. Server-side evidence remains `artifacts/server-verification/production-readiness-server-20260525-101244.json`.

## Performance Baseline

Command:

```powershell
.\scripts\run_performance_baseline.ps1 `
  -ApiBaseUrl "https://api.evanshine.me" `
  -FrontendUrl "https://app.evanshine.me" `
  -BusinessPaths "/health,/metrics" `
  -Iterations 10 `
  -OutputPath ".\artifacts\performance-baseline\baseline-20260526-120252.json" `
  -TrendPath ".\artifacts\performance-baseline\trend-summary.json"
```

Result:

- Conclusion: `WARN`
- Backend health: p95 `1254.74ms`, success `100%`, errors `0`
- Frontend root: p95 `1461.03ms`, success `100%`, errors `0`
- Business `/health`: p95 `834.59ms`, success `100%`, errors `0`
- Business `/metrics`: p95 `1076.08ms`, success `100%`, errors `0`
- Trend regressions: `1`

Interpretation:

The service is reachable and error-free. The `WARN` is caused by p95 threshold/trend regression, not by failed requests. Keep this as an observation item. If the same backend or `/metrics` p95 regression repeats in the next scheduled run, create a performance investigation task.

## External Integration Dry Run

Command:

```powershell
.\scripts\verify_external_integrations.ps1 -DryRun
```

Result:

- DingTalk: `MISSING`
- GitHub Actions: `MISSING`
- Jenkins: `MISSING`
- Jira: `MISSING`
- Zentao: `MISSING`

Interpretation:

The local PowerShell session does not contain the external integration environment variables. This does not invalidate the existing GitHub Actions and server evidence:

- `docs/production-closure-evidence-20260525-run98.md`
- `docs/final-signoff-evidence-index-20260525.md`

For a live local smoke, inject the required environment variables in the current shell or run the GitHub Actions workflow with repository secrets.

## Follow-Up

- Run production readiness from the server when validating Prometheus targets and Jenkins backup age.
- Run another performance baseline after server/network conditions settle.
- Use GitHub Actions or a prepared local shell for external integration smoke.
- Continue importing real data through the UI and save acceptance snapshots per batch.

