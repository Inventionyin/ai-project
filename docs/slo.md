# WeiTesting SLO

This document defines the trial-operation SLOs that map repository metrics, scripts, and external dashboards into production acceptance evidence.

## Availability

- Public app URL returns a usable shell for 99.5% of 5-minute windows during trial operation.
- API `/health` returns `200` with `status=ok` for 99.5% of 5-minute windows.
- Prometheus `up{job="weitesting-backend"}` should stay at `1`; `WeiTestingApiDown` fires after 2 minutes down.

## Latency

- Backend `/health` p95 should stay under `1000ms` in `run_performance_baseline`.
- Frontend root p95 should stay under `2000ms`.
- Business API paths should stay under the configured `BusinessThresholdP95Ms`, default `2000ms`.
- A longer load profile can set stricter route-level thresholds after real data volume is known.

## Error Budget

- API 5xx rate should remain below 2% over 5 minutes.
- `WeiTestingHighServerErrorRate` warns when the rate stays above the threshold for 10 minutes.
- Any sustained 5xx burst during acceptance must attach the request ID, route, status class, and baseline report.

## Notification Outbox

- Failed notification deliveries should be zero before a production demo.
- Queued or failed outbox growth is a warning even when the API is healthy.
- DingTalk/Jenkins/Jira/Zentao real closure reports should be attached to acceptance records when external credentials are available.

## CI Token

- Each automation surface should use a Named CI Token with a clear owner and scope.
- Tokens used by Jenkins, GitHub Actions, or external runners need expiry and rotation evidence.
- Leaked or obsolete tokens must be revoked before the environment is treated as production.

## Review Rhythm

- Run `scripts/verify_production_readiness.ps1` after domain, TLS, Jenkins, Grafana, or Prometheus changes.
- Run `scripts/run_performance_baseline.ps1` before and after large merges.
- Treat the repo-local checks as code readiness, and external Prometheus/Grafana/Jenkins checks as deployment readiness.
