from __future__ import annotations

import uuid
from dataclasses import dataclass

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import CurrentUser, get_current_user
from app.api.v1.endpoints import executors as executors_endpoint
from app.core.database import get_db


@dataclass
class _DummySession:
    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(executors_endpoint.router, prefix="/api")

    async def _override_db():
        yield _DummySession()

    async def _override_user() -> CurrentUser:
        return CurrentUser(
            id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            roles=frozenset({"ADMIN"}),
        )

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _override_user
    return app


def test_create_executor(monkeypatch: pytest.MonkeyPatch) -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")

    async def _fake_create(db, *, user, project_id, name, executor_type, **kwargs):
        from app.schemas.executor import ExecutorDetail
        return ExecutorDetail(
            id="33333333-3333-3333-3333-333333333333",
            projectId=str(project_id),
            name=name,
            executorType=executor_type,
            enabled=True,
            createdAt=1700000000,
            updatedAt=1700000000,
        )

    monkeypatch.setattr(executors_endpoint, "create_executor", _fake_create)
    app = _build_app()
    client = TestClient(app)
    resp = client.post(
        f"/api/projects/{project_id}/executors",
        json={"name": "JMeter Runner", "executorType": "JMETER"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["executorType"] == "JMETER"


def test_list_executors(monkeypatch: pytest.MonkeyPatch) -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")

    async def _fake_list(db, *, user, project_id, page, page_size):
        return 0, []

    monkeypatch.setattr(executors_endpoint, "list_executors", _fake_list)
    app = _build_app()
    client = TestClient(app)
    resp = client.get(f"/api/projects/{project_id}/executors")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["total"] == 0
