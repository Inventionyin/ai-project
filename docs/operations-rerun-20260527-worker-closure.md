# Operations Rerun Record - 2026-05-27 Worker Closure

This record captures the production hotfix and authenticated rerun that closed the remaining execution gap in the WeiTesting production environment.

## Context

- Repo branch: `master`
- Workspace host: local Windows workstation
- Target app: `https://app.evanshine.me`
- Target API: `https://api.evanshine.me`
- Target Jenkins: `https://jenkins.evanshine.me`
- Target Grafana: `https://grafana.evanshine.me`
- Production server: Oracle Ubuntu `217.142.224.236`

## Problems Found Before Hotfix

- `POST /api/projects/{projectId}/executors` returned service error `50001`.
- Collection quick run against `/health` returned `403 Forbidden` through backend `urllib`.
- Ops health summary reported workers as `READY` even while real suite runs stayed in `QUEUED`.
- Production server only had a fake worker heartbeat timer; there was no real worker polling `/api/workers/poll`.

## Code and Service Changes

- Fixed executor endpoint transaction handling and executor audit log module value.
- Added custom `User-Agent` for collection quick run HTTP execution.
- Added `executionQueue` diagnostics to ops health summary.
- Added `DEFAULT` HTTP runner for worker-side API execution.
- Enriched worker poll payload so suite API jobs include `apiMethod`, `apiUrl`, headers, params, and assertions.
- Added `ai-project-back-end/scripts/run_api_worker.py`.
- Added `ops/systemd/weitesting-worker.service`.
- Disabled the fake timer service `weitesting-worker-heartbeat.timer`.
- Enabled the real long-running worker service `weitesting-worker.service`.
- Cleaned up historical stale worker rows after exporting a backup snapshot:
  - `/opt/weitesting/artifacts/worker-cleanup-20260527-015027.json`

## Local Verification

Command:

```powershell
cd ai-project-back-end
$env:PYTHONPATH='.'
python -m py_compile app/services/runner_default_http.py scripts/run_api_worker.py
pytest tests/test_executors_api.py `
  tests/test_collection_quick_run_service.py `
  tests/test_ops_health_api.py `
  tests/test_collections_api.py `
  tests/test_runner_default_http.py `
  tests/test_worker_payload_service.py `
  tests/test_run_api_worker_script.py `
  tests/test_runner_newman.py `
  tests/test_runner_url_param.py -q
```

Result:

- `30 passed`

## Production Authenticated Verification

Authenticated production checks were rerun against a temporary smoke account and project.

### Executor API

- Executor creation now succeeds.
- Example production executor id: `75c56696-0eca-4a7e-95f4-ada322e73832`

### Collection Quick Run

- Collection request quick run against `/health` now succeeds.
- Result summary:
  - `ok=true`
  - `status=200`
  - `response.body={"status":"ok"}`

### Queue Diagnostics

After the hotfix, ops health summary reported queue backlog truthfully during investigation, and returned to healthy once the real worker was installed.

### Real Suite Execution Closure

The smoke suite was rerun after the worker service was enabled.

- Historical stuck run was canceled: `b0e9c56c-1983-4019-a9fe-b7688b727c79`
- Retry run reached terminal state: `0a334407-076f-443c-9e88-36130a9ba207`
- Smoke testcase expectation text was corrected from a narrative description to the real response fragment `ok`
- Final real suite rerun:
  - Run id: `5e1f867a-ce97-4cc1-9fb3-9d8960d28181`
  - Final status: `PASSED`
  - Progress: `1 / 1`

## Final Production Health Snapshot

Authenticated call to `GET /api/ops/health/summary` after worker stabilization returned:

- `overallStatus=READY`
- `workers.status=READY`
  - `staleCount=0`
  - `totalCount=1`
- `executionQueue.status=READY`
  - `stuckQueuedCount=0`
  - `queuedCount=0`
  - `runningCount=0`

## Conclusion

The remaining production gap was not a frontend rendering issue or a public availability issue. It was an execution-plane problem: fake worker heartbeats without a real poll/report worker. After replacing that with a real API worker service, production now supports:

- authenticated executor management
- authenticated collection quick debug
- real suite run dispatch
- real suite run terminal completion
- truthful operations health reporting
