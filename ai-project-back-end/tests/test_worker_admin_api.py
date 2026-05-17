from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import CurrentUser, get_current_user
from app.api.v1.endpoints import worker as worker_endpoint
from app.core.database import get_db
from app.schemas.worker import WorkerAdminDetailData, WorkerAdminListItem


@dataclass
class _DummySession:
    pass


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(worker_endpoint.router, prefix="/api")

    async def _override_db():
        yield _DummySession()

    async def _override_user() -> CurrentUser:
        return CurrentUser(
            id=uuid.uuid4(),
            tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            roles=frozenset({"ADMIN"}),
        )

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _override_user
    return app


def test_list_workers_calls_service_and_returns_page(monkeypatch) -> None:
    async def _fake_list_workers(db, *, tenant_id, page, page_size, status):
        assert tenant_id == uuid.UUID("11111111-1111-1111-1111-111111111111")
        assert page == 2
        assert page_size == 5
        assert status == "ONLINE"
        return (
            1,
            [
                WorkerAdminListItem(
                    id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                    name="worker-a",
                    status="ONLINE",
                    slots=4,
                    capabilities=["API", "UI"],
                    lastSeenAt=1710000000,
                    version="1.2.3",
                    updatedAt=1710000100,
                )
            ],
        )

    monkeypatch.setattr(worker_endpoint, "list_workers_admin", _fake_list_workers)
    client = TestClient(_build_app())
    resp = client.get("/api/workers?page=2&pageSize=5&status=ONLINE")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["id"] == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


def test_get_worker_detail_calls_service_and_returns_data(monkeypatch) -> None:
    target_id = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"

    async def _fake_get_worker(db, *, tenant_id, worker_id):
        assert tenant_id == uuid.UUID("11111111-1111-1111-1111-111111111111")
        assert worker_id == uuid.UUID(target_id)
        return WorkerAdminDetailData(
            id=target_id,
            name="worker-b",
            status="OFFLINE",
            slots=2,
            capabilities=["PERF"],
            lastSeenAt=None,
            version="2.0.0",
            updatedAt=1710000200,
        )

    monkeypatch.setattr(worker_endpoint, "get_worker_admin", _fake_get_worker)
    client = TestClient(_build_app())
    resp = client.get(f"/api/workers/{target_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["id"] == target_id
    assert body["data"]["status"] == "OFFLINE"
