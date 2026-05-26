# Post-Acceptance Operations SOP

This SOP explains how to keep WeiTesting useful after final acceptance: import new data, keep performance evidence fresh, prove backup recoverability, and run real projects through the platform.

## Scope

Current acceptance baseline:

- App: `https://app.evanshine.me`
- API: `https://api.evanshine.me`
- Grafana: `https://grafana.evanshine.me`
- Jenkins: `https://jenkins.evanshine.me`
- Final signoff evidence: `docs/final-signoff-evidence-index-20260525.md`
- Short weekly checklist: `docs/ops-weekly-checklist.md`

Cloudflare Access is not a blocker for the internal acceptance release. Add it before inviting external users to Jenkins, Grafana, or production administration pages.

## Cadence

| Cadence | Owner | Action | Evidence |
|---|---|---|---|
| Per new data batch | Test owner | Import requirements, testcases, defects, and execution results | Platform import records and acceptance snapshot |
| Daily on server | Ops | Performance baseline, production readiness, Jenkins restore drill | `/opt/weitesting/artifacts/*` |
| Weekly | Project owner | Review trial operation dashboard, P0/P1 defects, suite runs | Acceptance report Markdown snapshot |
| Monthly | Ops + project owner | Review trend, backup restore drill, external integration smoke | Latest JSON reports and GitHub Actions run |
| Before external demo | Tech owner | Re-run production readiness and real external smoke | Fresh report URLs and screenshots |

## 1. Continuous Data Import

Use the platform UI for normal batches. Do not edit the database directly.

1. Open `https://app.evanshine.me`.
2. Log in with an internal account.
3. Open the target project.
4. Import or update data from these areas:
   - Requirements: `/projects/:projectId/requirements/docs`
   - Testcases and governance: `/projects/:projectId/trial-operation`
   - Testcase assets: `/projects/:projectId/assets/testcases`
   - API collections: `/projects/:projectId/assets/apis`
   - Defects: `/projects/:projectId/defects`
   - Runs and execution results: `/projects/:projectId/runs`
5. After import, open `/projects/:projectId/trial-operation`.
6. Check:
   - Total requirements, testcases, defects, and executions changed as expected.
   - Duplicate and low-value testcase suggestions are reviewed.
   - P0/P1 defect grouping is explainable.
   - Acceptance summary reflects the new batch.
7. Save or export a new acceptance report snapshot from the acceptance center:
   - `/projects/:projectId/settings/acceptance`

Recommended batch naming:

```text
YYYYMMDD-source-scope
20260526-customer-regression-batch01
20260526-requirement-change-payment
```

Data quality rules:

- Keep source files unchanged in a dated folder before import.
- If AI governance suggests changes, review and apply them explicitly.
- Do not delete historical batches only to make metrics look better.
- If a P0 defect is business data rather than a platform bug, record that decision in the acceptance report.

## 2. Performance Baseline

The server cron should run this daily. If cron is not installed yet, install it on Ubuntu:

```bash
sudo REPO_DIR=/opt/weitesting/current \
  LOG_DIR=/var/log/weitesting \
  ARTIFACT_DIR=/opt/weitesting/artifacts \
  USER_NAME=ubuntu \
  bash deploy/ops/install_ops_cron.sh
```

Manual server run:

```bash
cd /opt/weitesting/current
bash scripts/run_performance_baseline.sh \
  --api-base-url https://api.evanshine.me \
  --frontend-url https://app.evanshine.me \
  --business-paths "/health,/metrics" \
  --iterations 20 \
  --output-path "/opt/weitesting/artifacts/performance-baseline/baseline-$(date +%Y%m%d-%H%M%S).json" \
  --trend-path "/opt/weitesting/artifacts/performance-baseline/trend-summary.json"
```

Local Windows run:

```powershell
.\scripts\run_performance_baseline.ps1 `
  -ApiBaseUrl "https://api.evanshine.me" `
  -FrontendUrl "https://app.evanshine.me" `
  -BusinessPaths "/health,/metrics" `
  -Iterations 20 `
  -OutputPath ".\artifacts\performance-baseline\baseline-$(Get-Date -Format yyyyMMdd-HHmmss).json" `
  -TrendPath ".\artifacts\performance-baseline\trend-summary.json"
```

Action rule:

- `READY`: archive the report.
- `WARN`: compare `trend-summary.json`; if the same target regresses twice, create a platform defect.
- `BLOCKED`: check DNS, HTTPS, backend service, database, and server load before continuing demo or acceptance activities.

## 3. Backup and Restore Drill

Jenkins backup script:

```bash
cd /opt/weitesting/current
bash deploy/jenkins/backup_jenkins.sh
```

Jenkins restore drill:

```bash
cd /opt/weitesting/current
bash deploy/jenkins/restore_drill_jenkins.sh \
  --backup-dir /opt/weitesting/backups/jenkins \
  --drill-dir /opt/weitesting/restore-drills/jenkins \
  --output-path /opt/weitesting/artifacts/jenkins-restore-drill/latest.json
```

PostgreSQL backup:

```bash
cd /opt/weitesting/current
bash scripts/backup-production-postgres.sh
```

PostgreSQL backup verification:

```bash
cd /opt/weitesting/current
bash scripts/verify-production-backup.sh
```

Action rule:

- Backup must be recent enough for the agreed recovery point.
- Restore drill must be `READY`.
- If restore drill fails, stop claiming production readiness until a fresh backup can be extracted and required paths are present.

## 4. Production Readiness Recheck

Run after domain, HTTPS, Nginx, Cloudflare, Jenkins, Grafana, Prometheus, or deployment changes.

Server:

```bash
cd /opt/weitesting/current
bash scripts/verify_production_readiness.sh \
  --app-url https://app.evanshine.me \
  --api-base-url https://api.evanshine.me \
  --grafana-url https://grafana.evanshine.me \
  --jenkins-url https://jenkins.evanshine.me \
  --prometheus-url http://127.0.0.1:9090 \
  --jenkins-backup-dir /opt/weitesting/backups/jenkins \
  --output-path "/opt/weitesting/artifacts/production-readiness/readiness-$(date +%Y%m%d-%H%M%S).json"
```

Windows:

```powershell
.\scripts\verify_production_readiness.ps1 `
  -AppUrl "https://app.evanshine.me" `
  -ApiBaseUrl "https://api.evanshine.me" `
  -GrafanaUrl "https://grafana.evanshine.me" `
  -JenkinsUrl "https://jenkins.evanshine.me" `
  -OutputPath ".\artifacts\production-readiness\readiness-$(Get-Date -Format yyyyMMdd-HHmmss).json"
```

Use `-FailOnWarn` or `--fail-on-warn` only for strict production gates.

## 5. External Integration Closure

Dry-run configuration check:

```powershell
.\scripts\verify_external_integrations.ps1 -DryRun
```

Connectivity smoke:

```powershell
.\scripts\verify_external_integrations.ps1 `
  -Targets Jira,Zentao,Jenkins,DingTalk `
  -EnableSmoke `
  -FailOnSmokeError
```

Reversible business closure:

```powershell
.\scripts\verify_external_integrations.ps1 `
  -Targets Jira,Zentao,Jenkins,DingTalk `
  -EnableSmoke `
  -EnableBusinessClosure `
  -FailOnSmokeError
```

Run business closure only when the external systems are expected to accept test records. The script creates and cleans up Jira and Zentao records where supported, triggers Jenkins, and sends DingTalk.

## 6. Real Project Usage Loop

For each real project cycle:

1. Import or update requirements.
2. Import or generate testcases.
3. Bind API requests to important testcases.
4. Add stable regression cases into suites.
5. Configure default environment for each suite.
6. Run the suite.
7. Open the run detail page and create Jira/Zentao issues for failures that need external tracking.
8. Review reports and trial operation dashboard.
9. Export acceptance or weekly progress snapshot.

Minimum weekly review:

- New requirements without testcases.
- P0/P1 defects and owner/status.
- Duplicate or low-value testcases.
- Suites without default environment.
- Failed runs without linked defect.
- External integration diagnostics.
- Ops health and production readiness summary.

## 7. Evidence Locations

Server artifacts:

```text
/opt/weitesting/artifacts/performance-baseline/
/opt/weitesting/artifacts/production-readiness/
/opt/weitesting/artifacts/jenkins-restore-drill/
```

Repository artifacts:

```text
artifacts/performance-baseline/
artifacts/production-readiness/
artifacts/server-verification/
docs/final-signoff-evidence-index-20260525.md
docs/production-closure-evidence-20260525-run98.md
```

GitHub Actions:

```text
https://github.com/Inventionyin/ai-project/actions
```

## 8. Escalation Rules

- Data import mismatch: keep source files, export the import preview/result, and create a platform defect.
- Performance `WARN` twice on the same path: create a performance investigation task.
- Restore drill failure: treat as production readiness blocker.
- External smoke failure: check token expiry, VPN, base URL, and permissions before blaming platform code.
- Cloudflare Access request from stakeholders: enable it before external exposure, but do not retroactively block the internal acceptance release.
