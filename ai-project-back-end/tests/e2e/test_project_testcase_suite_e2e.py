from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from helpers import assert_success


def _create_project(client: TestClient, headers: dict[str, str], owner_id: str) -> dict:
    suffix = uuid.uuid4().hex[:8]
    resp = client.post(
        "/api/projects",
        headers=headers,
        json={"name": f"E2E Project {suffix}", "description": "project lifecycle", "ownerId": owner_id},
    )
    assert resp.status_code == 200
    return assert_success(resp.json())


def _create_api_testcase(client: TestClient, headers: dict[str, str], project_id: str) -> dict:
    resp = client.post(
        "/api/testcases",
        headers=headers,
        json={
            "projectId": project_id,
            "title": "Health API",
            "type": "API",
            "priority": "P2",
            "status": "DRAFT",
            "tags": ["e2e"],
            "contentMd": "GET /health should return ok",
            "feature": "health",
            "apiMethod": "GET",
            "apiUrl": "/health",
            "apiParams": {},
            "apiHeaders": {},
            "expectedStatusCode": 200,
            "expectedResult": "ok",
        },
    )
    assert resp.status_code == 200
    return assert_success(resp.json())


def test_project_testcase_suite_lifecycle(
    client: TestClient,
    auth_context: dict[str, str],
    auth_headers: dict[str, str],
) -> None:
    project = _create_project(client, auth_headers, auth_context["userId"])
    project_id = project["id"]

    list_resp = client.get("/api/projects", headers=auth_headers)
    list_data = assert_success(list_resp.json())
    assert any(item["id"] == project_id for item in list_data["items"])

    testcase = _create_api_testcase(client, auth_headers, project_id)
    testcase_id = testcase["id"]
    assert testcase["apiMethod"] == "GET"
    assert testcase["apiUrl"] == "/health"

    cases_resp = client.get(f"/api/testcases?projectId={project_id}", headers=auth_headers)
    cases_data = assert_success(cases_resp.json())
    assert any(item["id"] == testcase_id for item in cases_data["items"])

    suite_resp = client.post(
        "/api/suites",
        headers=auth_headers,
        json={
            "projectId": project_id,
            "name": "Smoke Suite",
            "defaultEnvId": None,
            "config": {
                "timeoutSec": 120,
                "concurrency": 2,
                "retryCount": 0,
                "retryOnlyOn": ["NETWORK"],
                "failFast": False,
                "variables": {"scope": "e2e"},
            },
        },
    )
    assert suite_resp.status_code == 200
    suite = assert_success(suite_resp.json())
    suite_id = suite["id"]

    items_resp = client.post(
        f"/api/suites/{suite_id}/items",
        headers=auth_headers,
        json={"items": [{"testcaseId": testcase_id, "orderNo": 1, "params": {"env": "test"}}]},
    )
    assert items_resp.status_code == 200
    suite_items = assert_success(items_resp.json())
    assert suite_items[0]["testcaseId"] == testcase_id
    assert suite_items[0]["testcaseTitle"] == "Health API"

    fetched_items_resp = client.get(f"/api/suites/{suite_id}/items", headers=auth_headers)
    fetched_items = assert_success(fetched_items_resp.json())
    assert fetched_items[0]["params"]["env"] == "test"
