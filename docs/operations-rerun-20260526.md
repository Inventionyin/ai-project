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

- Server-side production readiness was rerun after the local workstation check. Result: `READY`, `8 READY / 0 WARN / 0 BLOCKED`, output `/opt/weitesting/artifacts/production-readiness/readiness-20260526-server.json`.
- Server-side Jenkins restore drill was rerun. Result: `READY`, output `/opt/weitesting/artifacts/jenkins-restore-drill/latest-20260526.json`.
- Server-side performance baseline was rerun. Result: `READY`, backend p95 `714.3ms`, frontend p95 `737.86ms`, `/health` p95 `694.72ms`, `/metrics` p95 `775.41ms`, output `/opt/weitesting/artifacts/performance-baseline/baseline-20260526-server.json`.
- The restore drill script was hardened to use a unique `mktemp` listing file instead of a fixed `/tmp/weitesting-jenkins-restore-drill-listing.txt` path.
- Recurring operations cron was reinstalled on the Oracle Ubuntu server at `/etc/cron.d/weitesting-ops`.
- The Jenkins restore drill cron now writes temporary restore drills under `/opt/weitesting/artifacts/jenkins-restore-drill/drills`, avoiding the previous non-writable `/opt/weitesting/restore-drills/jenkins` path.
- The cron installer now makes the log and artifact directories writable by the configured runtime user when installed as root.
- Cron log write access was verified for user `ubuntu` under `/var/log/weitesting`.
- GitHub Actions external integration smoke was rerun against repository secrets. Run `26436370005` completed successfully with DingTalk, Jenkins, Jira, and Zentao all `READY`.
- GitHub Actions external business closure was rerun with `includeExternalBusinessClosure=true`. Run `26436722263` completed successfully:
  - DingTalk, Jenkins, Jira, and Zentao configuration checks were all `READY`.
  - DingTalk accepted the webhook smoke message.
  - Jenkins accepted the reversible build trigger.
  - Jira created and deleted test issue `AIT-17`.
  - Zentao created and deleted test bug `11`.
  - Final result: `[OK] External integration configuration is READY.`
- A later GitHub Actions real customer environment rerun was triggered after final data confirmation. Run `26447416031` / run number `#115` completed successfully:
  - Workflow URL: <https://github.com/Inventionyin/ai-project/actions/runs/26447416031>.
  - DingTalk, Jenkins, Jira, and Zentao configuration checks were all `READY`.
  - DingTalk accepted the webhook smoke message.
  - Jenkins accepted the reversible build trigger.
  - Jira created and deleted test issue `AIT-18`.
  - Zentao created and deleted test bug `12`.
  - Final result: `[OK] External integration configuration is READY.`
- Local workstation production readiness was rerun at `2026-05-26 18:38`:
  - Output: `artifacts/production-readiness/readiness-20260526-183857.json`.
  - Result: `WARN`, with `7 READY / 2 WARN / 0 BLOCKED`.
  - Public HTTPS endpoints for app, API, Grafana, and Jenkins were all reachable.
  - The WARN items are workstation visibility limits for server-local Prometheus and Jenkins backup paths; server-side readiness below remains the authoritative production result.
- Local workstation performance baseline was rerun at `2026-05-26 18:38`:
  - Output: `artifacts/performance-baseline/baseline-20260526-183858.json`.
  - Result: `WARN`, with `100%` success and `0` errors across app/API business paths.
  - Backend p95 `1282.87ms`, frontend p95 `984.43ms`, `/health` p95 `988.6ms`, `/metrics` p95 `830.98ms`.
  - Keep the workstation WARN as a trend observation; server-side baseline remains `READY`.
- Server-side PostgreSQL formal backup restore drill was executed on Oracle Ubuntu:
  - Output: `artifacts/server-verification/postgres-restore-drill-20260526.json`.
  - Source backup: `/opt/weitesting/backups/postgres/weitesting-20260526T021501Z.dump.gz`.
  - Result: `READY`, restored into disposable database `weitesting_restore_drill_20260526T104810Z`.
  - Validation: `tableCount=56`, `schemaCount=1`.
  - Cleanup verified: disposable restore database count is `0`; production database was not modified.
- Final acceptance data status: product owner / upstream confirmed the current imported dataset is the final acceptance dataset.
- Access strategy remains unchanged for this acceptance pass:
  - Formal domain and HTTPS are enabled on `app.evanshine.me`, `api.evanshine.me`, `jenkins.evanshine.me`, and `grafana.evanshine.me`.
  - Jenkins and Grafana stay behind their own login controls.
  - Cloudflare Access is not a mandatory gate for this internal acceptance pass; enable it before wider external exposure if required by the launch policy.
- Use GitHub Actions or a prepared local shell for external integration smoke.
- Continue importing real data through the UI and save acceptance snapshots per batch.
