from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import CurrentUser, get_current_user
from app.api.v1.endpoints import executors as executors_endpoint
from app.core.database import get_db
from app.services import executor as executor_service


@dataclass
class _DummySession:
    commit_calls: int = 0
    rollback_calls: int = 0

    async def commit(self) -> None:
        self.commit_calls += 1
        return None

    async def rollback(self) -> None:
        self.rollback_calls += 1
        return None


def _build_app(session: _DummySession | None = None) -> FastAPI:
    app = FastAPI()
    app.include_router(executors_endpoint.router, prefix="/api")
    db_session = session or _DummySession()

    async def _override_db():
        yield db_session

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


def test_create_executor_commits_transaction(monkeypatch: pytest.MonkeyPatch) -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    session = _DummySession()

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
    client = TestClient(_build_app(session))
    resp = client.post(
        f"/api/projects/{project_id}/executors",
        json={"name": "Newman Runner", "executorType": "POSTMAN"},
    )

    assert resp.status_code == 200
    assert session.commit_calls == 1
    assert session.rollback_calls == 0


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


def test_update_executor_commits_transaction(monkeypatch: pytest.MonkeyPatch) -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    executor_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    session = _DummySession()

    async def _fake_update(db, *, user, project_id, executor_id, **kwargs):
        from app.schemas.executor import ExecutorDetail

        return ExecutorDetail(
            id=str(executor_id),
            projectId=str(project_id),
            name="Runner v2",
            executorType="POSTMAN",
            enabled=False,
            createdAt=1700000000,
            updatedAt=1700001234,
        )

    monkeypatch.setattr(executors_endpoint, "update_executor", _fake_update)
    client = TestClient(_build_app(session))
    resp = client.put(
        f"/api/projects/{project_id}/executors/{executor_id}",
        json={"description": "disable for smoke", "enabled": False},
    )

    assert resp.status_code == 200
    assert session.commit_calls == 1
    assert session.rollback_calls == 0


def test_delete_executor_commits_transaction(monkeypatch: pytest.MonkeyPatch) -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    executor_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    session = _DummySession()

    async def _fake_delete(db, *, user, project_id, executor_id):
        return None

    monkeypatch.setattr(executors_endpoint, "delete_executor", _fake_delete)
    client = TestClient(_build_app(session))
    resp = client.delete(f"/api/projects/{project_id}/executors/{executor_id}")

    assert resp.status_code == 200
    assert session.commit_calls == 1
    assert session.rollback_calls == 0


class _CreateExecutorDb:
    def __init__(self, *, project_obj) -> None:
        self.project_obj = project_obj
        self.added_rows = []
        self.flushed = False

    async def scalar(self, stmt):
        if "FROM projects" in str(stmt):
            return self.project_obj
        return None

    def add(self, row) -> None:
        self.added_rows.append(row)

    async def flush(self) -> None:
        for row in self.added_rows:
            if getattr(row, "created_at", None) is None:
                row.created_at = datetime.fromtimestamp(1700000000)
            if getattr(row, "updated_at", None) is None:
                row.updated_at = datetime.fromtimestamp(1700000000)
        self.flushed = True


@pytest.mark.anyio
async def test_create_executor_writes_executor_module_audit_log(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    user_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    project = SimpleNamespace(id=project_id, tenant_id=tenant_id, owner_id=user_id)
    user = CurrentUser(id=user_id, tenant_id=tenant_id, roles=frozenset({"VIEWER"}))
    db = _CreateExecutorDb(project_obj=project)
    calls: list[dict] = []

    async def _fake_audit(_db, *, module, **kwargs):
        calls.append({"module": module, **kwargs})
        return SimpleNamespace(id=uuid.uuid4())

    monkeypatch.setattr(executor_service, "create_audit_log", _fake_audit)

    detail = await executor_service.create_executor(
        db,
        user=user,
        project_id=project_id,
        name="Prod Smoke Executor",
        executor_type="POSTMAN",
        description="created in smoke check",
        config={"baseUrl": "https://api.evanshine.me"},
        version="1.0.0",
    )

    assert detail.name == "Prod Smoke Executor"
    assert db.flushed is True
    assert calls
    assert calls[0]["module"] == "EXECUTOR"
    assert calls[0]["action"] == "CREATE_EXECUTOR"
