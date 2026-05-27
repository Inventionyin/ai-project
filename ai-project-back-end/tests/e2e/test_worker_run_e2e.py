from __future__ import annotations

import time

from fastapi.testclient import TestClient

from helpers import assert_success
from test_project_testcase_suite_e2e import _create_api_testcase, _create_project


def _create_environment(client: TestClient, headers: dict[str, str], project_id: str) -> dict:
    resp = client.post(
        f"/api/projects/{project_id}/environments",
        headers=headers,
        json={
            "name": "Smoke Env",
            "baseUrl": "https://api.example.test",
            "variables": {"tenant": "e2e"},
            "secrets": {},
        },
    )
    assert resp.status_code == 200
    return assert_success(resp.json())


def test_worker_polls_and_reports_direct_http_run(
    client: TestClient,
    auth_context: dict[str, str],
    auth_headers: dict[str, str],
) -> None:
    project = _create_project(client, auth_headers, auth_context["userId"])
    testcase = _create_api_testcase(client, auth_headers, project["id"])

    run_resp = client.post(
        "/api/runs/from-testcases-http",
        headers=auth_headers,
        json={
            "projectId": project["id"],
            "envId": None,
            "triggerType": "MANUAL",
            "meta": {"runnerType": "DEFAULT"},
            "concurrency": 1,
            "stopOnFailure": False,
            "items": [{"testcaseId": testcase["id"], "overrideParams": {}}],
        },
    )
    assert run_resp.status_code == 200
    run = assert_success(run_resp.json())
    assert run["status"] == "QUEUED"
    assert run["progress"]["total"] == 1

    worker_resp = client.post(
        "/api/workers/register",
        headers={"X-Tenant-Id": auth_context["tenantId"]},
        json={"name": "e2e-worker", "capabilities": ["API"], "slots": 1, "version": "1.0.0"},
    )
    assert worker_resp.status_code == 200
    worker = assert_success(worker_resp.json())
    worker_headers = {"Authorization": f"Bearer {worker['token']}"}

    heartbeat_resp = client.post(
        "/api/workers/heartbeat",
        headers=worker_headers,
        json={"workerId": worker["workerId"], "slotsFree": 1, "runningJobIds": [], "meta": {}},
    )
    assert heartbeat_resp.status_code == 200
    assert_success(heartbeat_resp.json())

    poll_resp = client.post(
        "/api/workers/poll",
        headers=worker_headers,
        json={"workerId": worker["workerId"], "capabilities": ["API"]},
    )
    assert poll_resp.status_code == 200
    poll_data = assert_success(poll_resp.json())
    job = poll_data["job"]
    assert job is not None
    assert job["runId"] == run["id"]
    assert job["items"][0]["testcaseId"] == testcase["id"]
    case_run_id = job["items"][0]["caseRunId"]

    now = int(time.time())
    report_resp = client.post(
        "/api/workers/report",
        headers=worker_headers,
        json={
            "workerId": worker["workerId"],
            "jobId": job["jobId"],
            "runId": job["runId"],
            "jobStatus": "DONE",
            "results": [
                {
                    "caseRunId": case_run_id,
                    "status": "PASSED",
                    "startAt": now,
                    "endAt": now + 1,
                    "logs": ["ok"],
                    "artifacts": [],
                    "metrics": {"durationMs": 1000},
                }
            ],
        },
    )
    assert report_resp.status_code == 200
    assert_success(report_resp.json())

    final_run_resp = client.get(f"/api/runs/{run['id']}", headers=auth_headers)
    final_run = assert_success(final_run_resp.json())
    assert final_run["status"] == "PASSED"
    assert final_run["progress"] == {"done": 1, "total": 1}

    case_runs_resp = client.get(f"/api/runs/{run['id']}/case-runs", headers=auth_headers)
    case_runs = assert_success(case_runs_resp.json())
    assert case_runs["items"][0]["caseRunId"] == case_run_id
    assert case_runs["items"][0]["status"] == "PASSED"


def test_worker_poll_enriches_suite_api_payload(
    client: TestClient,
    auth_context: dict[str, str],
    auth_headers: dict[str, str],
) -> None:
    project = _create_project(client, auth_headers, auth_context["userId"])
    testcase = _create_api_testcase(client, auth_headers, project["id"])
    env = _create_environment(client, auth_headers, project["id"])

    suite_resp = client.post(
        "/api/suites",
        headers=auth_headers,
        json={
            "projectId": project["id"],
            "name": "Suite Worker Payload",
            "defaultEnvId": env["id"],
            "config": {"timeoutSec": 30, "retryCount": 0, "failFast": False},
        },
    )
    assert suite_resp.status_code == 200
    suite = assert_success(suite_resp.json())

    items_resp = client.post(
        f"/api/suites/{suite['id']}/items",
        headers=auth_headers,
        json={"items": [{"testcaseId": testcase["id"], "orderNo": 1, "params": {"tenant": "e2e"}}]},
    )
    assert items_resp.status_code == 200
    assert_success(items_resp.json())

    run_resp = client.post(
        "/api/runs",
        headers=auth_headers,
        json={
            "projectId": project["id"],
            "suiteId": suite["id"],
            "envId": env["id"],
            "triggerType": "MANUAL",
            "meta": {"runnerType": "DEFAULT"},
        },
    )
    assert run_resp.status_code == 200
    run = assert_success(run_resp.json())
    assert run["status"] == "QUEUED"

    worker_resp = client.post(
        "/api/workers/register",
        headers={"X-Tenant-Id": auth_context["tenantId"]},
        json={"name": "suite-e2e-worker", "capabilities": ["API"], "slots": 1, "version": "1.0.0"},
    )
    assert worker_resp.status_code == 200
    worker = assert_success(worker_resp.json())
    worker_headers = {"Authorization": f"Bearer {worker['token']}"}

    poll_resp = client.post(
        "/api/workers/poll",
        headers=worker_headers,
        json={"workerId": worker["workerId"], "capabilities": ["API"]},
    )
    assert poll_resp.status_code == 200
    poll_data = assert_success(poll_resp.json())
    job = poll_data["job"]
    assert job is not None
    assert job["runId"] == run["id"]
    assert job["items"][0]["testcaseId"] == testcase["id"]
    assert job["items"][0]["apiMethod"] == "GET"
    assert job["items"][0]["apiUrl"] == "/health"
    assert job["items"][0]["expectedStatusCode"] == 200
