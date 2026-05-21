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

The script checks public app/API/Grafana/Jenkins URLs, Prometheus target health, and the latest Jenkins backup archive. It writes a JSON report to `artifacts/production-readiness/readiness-report.json`.

Use `-FailOnWarn` only when every optional production hardening item is expected to be complete. Jenkins Prometheus scrape failures are reported as `WARN`, because the app can operate without Jenkins metrics while the Jenkins Prometheus plugin/permissions are still being finalized.

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

## Observability

The backend exposes Prometheus text metrics at `/metrics`.

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

The business closure mode creates and cleans up a Jira issue and Zentao bug, and triggers a Jenkins build.

## Jenkins

Minimum production settings:

- Put Jenkins behind `jenkins.<domain>` with HTTPS.
- Disable anonymous access.
- Use API tokens, not passwords.
- Install the Prometheus plugin if Jenkins metrics are needed.
- Run `deploy/jenkins/backup_jenkins.sh` daily from cron.
- Keep Jenkins and Grafana behind strong login or Cloudflare Access before inviting external users.
- Rotate external tokens that were shared during setup before treating this environment as production.

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
