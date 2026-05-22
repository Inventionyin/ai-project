# Production Readiness

This checklist turns the current local/CI setup into an operator-ready deployment.

## Production Readiness Gate

Run the production self-check after deployment or domain changes:

```powershell
.\scripts\verify_production_readiness.ps1 `
  -AppUrl https://app.example.com `
  -ApiBaseUrl https://api.example.com `
  -GrafanaUrl https://grafana.example.com `
  -JenkinsUrl https://jenkins.example.com `
  -PrometheusUrl http://127.0.0.1:9090 `
  -JenkinsBackupDir /opt/weitesting/backups/jenkins
```

On Linux servers, use the Bash equivalent:

```bash
bash ./scripts/verify_production_readiness.sh \
  --app-url https://app.example.com \
  --api-base-url https://api.example.com \
  --grafana-url https://grafana.example.com \
  --jenkins-url https://jenkins.example.com \
  --prometheus-url http://127.0.0.1:9090 \
  --jenkins-backup-dir /opt/weitesting/backups/jenkins
```

The script checks public app/API URLs, repo-local backend observability (`/health` and `/metrics`), Grafana/Jenkins reachability, Prometheus target health, and the latest Jenkins backup archive. It writes a JSON report to `artifacts/production-readiness/readiness-report.json`.

Use `-FailOnWarn` only when every optional production hardening item is expected to be complete. The backend `/metrics` endpoint is a repo-local readiness check. Prometheus target health, Grafana dashboards, and Jenkins Prometheus scrape health are external infrastructure checks and can remain `WARN` while those systems are being finalized.

## Domains

Point these DNS A records at the Oracle host:

- `app.<domain>` -> frontend static site
- `api.<domain>` -> FastAPI backend
- `jenkins.<domain>` -> Jenkins
- `grafana.<domain>` -> Grafana

Render `deploy/nginx/weitesting.conf.template`, install it under `/etc/nginx/sites-available/weitesting`, then enable HTTPS with certbot:

```bash
sudo certbot --nginx -d app.example.com -d api.example.com -d jenkins.example.com -d grafana.example.com
```

The app domain must also serve same-origin API calls. `https://app.<domain>/api/projects` should return a backend JSON envelope such as `{"code":40101,...}` when unauthenticated, not the frontend `index.html`. The nginx template includes a `/api/` proxy before the SPA fallback for this reason. If production uses Cloudflare Tunnel plus the Python SPA server instead of nginx, keep the same rule in that server: proxy `/api/*` to `http://127.0.0.1:8000` before falling back to `index.html`.

## Observability

The backend exposes repo-local observability without extra services:

- `GET /health` returns the public database-backed health signal.
- `GET /metrics` returns Prometheus text metrics with normalized request IDs in logs/headers, route-safe request labels, request count, duration sum/count/max, server error count, in-flight gauge, process uptime, and `weitesting_observability_ready`.
- `GET /api/ops/health/summary` returns the authenticated operator summary for database, outbox, workers, DevOps runs, plugins, and CI token coverage.

Prometheus and Grafana are still external infrastructure. Prometheus must scrape `/metrics` and Grafana/Alertmanager must provide dashboards and alert routing.

Start Prometheus and Grafana:

```bash
docker compose -f docker-compose.observability.yml up -d
```

Set `GRAFANA_ADMIN_PASSWORD` before first start.

## External Business Closure

Connectivity smoke remains the default. Reversible business closure checks require an explicit switch:

```powershell
.\scripts\verify_external_integrations.ps1 `
  -Targets Jira,Zentao,Jenkins,DingTalk `
  -EnableSmoke `
  -EnableBusinessClosure `
  -FailOnSmokeError
```

The business closure mode creates and cleans up a Jira issue and Zentao bug, and triggers a Jenkins build. Cleanup failures now count as business-closure failures so the probe reflects whether the loop really closed.

## Jenkins

Minimum production settings:

- Put Jenkins behind `jenkins.<domain>` with HTTPS.
- Disable anonymous access.
- Use API tokens, not passwords.
- Install the Prometheus plugin if Jenkins metrics are needed.
- Run `deploy/jenkins/backup_jenkins.sh` daily from cron.
- Keep Jenkins and Grafana behind strong login or Cloudflare Access before inviting external users.
- Rotate external tokens that were shared during setup before treating this environment as production.
- Run `deploy/jenkins/restore_drill_jenkins.sh` regularly to prove backups can be extracted.

## Performance Baseline

The baseline script now measures `/health`, frontend root, configurable API business paths, and appends a trend summary:

```powershell
.\scripts\run_performance_baseline.ps1 `
  -ApiBaseUrl https://api.example.com `
  -FrontendUrl https://app.example.com `
  -BusinessPaths "/api/ops/health/summary,/api/projects" `
  -TrendPath ".\artifacts\performance-baseline\trend-summary.json" `
  -FailOnWarn
```

On Linux servers, `scripts/run_performance_baseline.sh` provides the same trend report without requiring PowerShell.

## Operations Cron

Install recurring operations reports on Ubuntu:

```bash
sudo REPO_DIR=/opt/weitesting/current \
  LOG_DIR=/var/log/weitesting \
  ARTIFACT_DIR=/opt/weitesting/artifacts \
  USER_NAME=ubuntu \
  bash deploy/ops/install_ops_cron.sh
```

This creates `/etc/cron.d/weitesting-ops` with daily performance baseline, production readiness, and Jenkins restore drill jobs.
