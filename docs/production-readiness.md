# Production Readiness

This checklist turns the current local/CI setup into an operator-ready deployment.

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
