from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import CurrentUser, get_current_user
from app.api.v1.endpoints import performance_tests as performance_tests_endpoint
from app.core.database import get_db
from app.schemas.performance import PerformanceTestDetail


@dataclass
class _DummySession:
    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


_USER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_TENANT_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
_PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
_TEST_ID = uuid.UUID("88888888-8888-8888-8888-888888888888")


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(
        performance_tests_endpoint.router,
        prefix="/api",
    )

    async def _override_db():
        yield _DummySession()

    async def _override_user() -> CurrentUser:
        return CurrentUser(
            id=_USER_ID,
            tenant_id=_TENANT_ID,
            roles=frozenset({"ADMIN"}),
        )

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _override_user
    return app


def _make_detail(name: str = "Load Test", test_type: str = "LOAD") -> PerformanceTestDetail:
    return PerformanceTestDetail(
        id=str(_TEST_ID),
        projectId=str(_PROJECT_ID),
        name=name,
        description="",
        testType=test_type,
        targetUrl="https://example.com",
        config={},
        scriptContent="",
        status="DRAFT",
        tags=[],
        createdBy=str(_USER_ID),
        createdAt=1710000000,
        updatedAt=1710000000,
    )


def test_create_performance_test(monkeypatch) -> None:
    async def _fake_create(db, *, user, project_id, name, test_type="LOAD", description="",
                           target_url="", config=None, script_content="", tags=None):
        return _make_detail(name=name, test_type=test_type)

    monkeypatch.setattr(performance_tests_endpoint, "create_test", _fake_create)

    client = TestClient(_build_app())
    resp = client.post(
        f"/api/projects/{_PROJECT_ID}/performance-tests",
        json={
            "name": "Load Test",
            "testType": "LOAD",
            "targetUrl": "https://example.com",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["name"] == "Load Test"
    assert body["data"]["testType"] == "LOAD"
    assert body["data"]["targetUrl"] == "https://example.com"


def test_create_performance_test_stress_type(monkeypatch) -> None:
    async def _fake_create(db, *, user, project_id, name, test_type="LOAD", description="",
                           target_url="", config=None, script_content="", tags=None):
        return _make_detail(name=name, test_type=test_type)

    monkeypatch.setattr(performance_tests_endpoint, "create_test", _fake_create)

    client = TestClient(_build_app())
    resp = client.post(
        f"/api/projects/{_PROJECT_ID}/performance-tests",
        json={
            "name": "Stress Test",
            "testType": "STRESS",
            "targetUrl": "https://example.com",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["name"] == "Stress Test"
    assert body["data"]["testType"] == "STRESS"


def test_list_performance_tests_empty(monkeypatch) -> None:
    async def _fake_list(db, *, user, project_id, page, page_size):
        return (0, [])

    monkeypatch.setattr(performance_tests_endpoint, "list_tests", _fake_list)

    client = TestClient(_build_app())
    resp = client.get(f"/api/projects/{_PROJECT_ID}/performance-tests")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["items"] == []
    assert body["data"]["total"] == 0


def test_list_performance_tests_with_data(monkeypatch) -> None:
    async def _fake_list(db, *, user, project_id, page, page_size):
        return (1, [_make_detail()])

    monkeypatch.setattr(performance_tests_endpoint, "list_tests", _fake_list)

    client = TestClient(_build_app())
    resp = client.get(f"/api/projects/{_PROJECT_ID}/performance-tests")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["name"] == "Load Test"


def test_get_performance_test(monkeypatch) -> None:
    async def _fake_get(db, *, user, project_id, test_id):
        return _make_detail()

    monkeypatch.setattr(performance_tests_endpoint, "get_test", _fake_get)

    client = TestClient(_build_app())
    resp = client.get(f"/api/projects/{_PROJECT_ID}/performance-tests/{_TEST_ID}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["id"] == str(_TEST_ID)


def test_update_performance_test(monkeypatch) -> None:
    async def _fake_update(db, *, user, project_id, test_id, name=None, description=None,
                           test_type=None, target_url=None, config=None, script_content=None, tags=None):
        return _make_detail(name=name or "Updated")

    monkeypatch.setattr(performance_tests_endpoint, "update_test", _fake_update)

    client = TestClient(_build_app())
    resp = client.put(
        f"/api/projects/{_PROJECT_ID}/performance-tests/{_TEST_ID}",
        json={"name": "Updated"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["name"] == "Updated"


def test_delete_performance_test(monkeypatch) -> None:
    async def _fake_delete(db, *, user, project_id, test_id):
        return None

    monkeypatch.setattr(performance_tests_endpoint, "delete_test", _fake_delete)

    client = TestClient(_build_app())
    resp = client.delete(f"/api/projects/{_PROJECT_ID}/performance-tests/{_TEST_ID}")
    assert resp.status_code == 200
