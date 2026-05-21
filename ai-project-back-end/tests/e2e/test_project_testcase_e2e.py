"""E2E tests: project → testcase → suite lifecycle against real DB."""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_create_project_and_list(client: AsyncClient, auth_headers: dict[str, str]):
    """Create a project, then list it."""
    name = f"proj_{uuid.uuid4().hex[:8]}"

    resp = await client.post("/api/projects", json={
        "name": name, "description": "E2E test project",
    }, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    project_id = body["data"]["id"]

    # List projects.
    resp = await client.get("/api/projects", headers=auth_headers)
    assert resp.status_code == 200
    projects = resp.json()["data"]
    assert any(p["id"] == project_id for p in projects)


@pytest.mark.anyio
async def test_create_testcase_in_project(client: AsyncClient, auth_headers: dict[str, str]):
    """Create a project then add a testcase."""
    # Create project.
    resp = await client.post("/api/projects", json={
        "name": f"tc_proj_{uuid.uuid4().hex[:8]}",
    }, headers=auth_headers)
    project_id = resp.json()["data"]["id"]

    # Create testcase.
    resp = await client.post("/api/testcases", json={
        "projectId": project_id,
        "title": "E2E Login Test",
        "priority": "P0",
        "preconditions": "User exists",
        "steps": ["Navigate to login page", "Enter credentials", "Click login"],
        "expectedResults": ["Dashboard is shown"],
    }, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["title"] == "E2E Login Test"
    tc_id = body["data"]["id"]

    # Fetch testcase.
    resp = await client.get(f"/api/testcases/{tc_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == tc_id


@pytest.mark.anyio
async def test_create_suite_with_cases(client: AsyncClient, auth_headers: dict[str, str]):
    """Create a project, testcase, and suite."""
    resp = await client.post("/api/projects", json={
        "name": f"suite_proj_{uuid.uuid4().hex[:8]}",
    }, headers=auth_headers)
    project_id = resp.json()["data"]["id"]

    # Create testcases.
    tc_ids = []
    for i in range(3):
        resp = await client.post("/api/testcases", json={
            "projectId": project_id,
            "title": f"Suite Case {i}",
            "priority": "P1",
        }, headers=auth_headers)
        tc_ids.append(resp.json()["data"]["id"])

    # Create suite.
    resp = await client.post("/api/suites", json={
        "projectId": project_id,
        "name": "E2E Regression Suite",
        "description": "Automated E2E suite",
        "caseIds": tc_ids,
    }, headers=auth_headers)
    assert resp.status_code == 200
    suite = resp.json()["data"]
    assert suite["name"] == "E2E Regression Suite"
    assert len(suite.get("caseIds", [])) == 3
