from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.health import router
from app.core.database import get_db


class _HealthyDb:
    async def execute(self, _stmt):
        return object()


class _BrokenDb:
    async def execute(self, _stmt):
        raise RuntimeError("database unavailable")


def _build_app(db) -> FastAPI:
    app = FastAPI()
    app.include_router(router)

    async def _override_db():
        yield db

    app.dependency_overrides[get_db] = _override_db
    return app


def test_health_returns_ok_when_database_probe_succeeds() -> None:
    client = TestClient(_build_app(_HealthyDb()))

    resp = client.get("/health")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_health_returns_503_when_database_probe_fails() -> None:
    client = TestClient(_build_app(_BrokenDb()))

    resp = client.get("/health")

    assert resp.status_code == 503
    assert resp.json()["detail"] == "db_unavailable"
