from __future__ import annotations

import uuid
import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.sql import visitors

from app.api.deps import CurrentUser, get_current_user
from app.api.v1.endpoints import ops as ops_endpoint
from app.core.database import get_db
from app.schemas.ops import OpsHealthCheck, OpsHealthSummaryData
from app.services.ops_health import _ci_tokens_check, _workers_check, build_ops_health_summary


@dataclass
class _DummySession:
    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(ops_endpoint.router, prefix="/api")

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


def test_ops_health_summary_endpoint_monkeypatch() -> None:
    generated_at = datetime.now(timezone.utc)

    async def _fake_summary(db, user):
        return OpsHealthSummaryData(
            overallStatus="WARN",
            generatedAt=generated_at,
            checks=[
                OpsHealthCheck(
                    key="database",
                    label="Database",
                    status="READY",
                    detail="ok",
                    metric={"ok": True},
                    recommendation="No action required.",
                ),
                OpsHealthCheck(
                    key="workers",
                    label="Workers",
                    status="WARN",
                    detail="1 stale worker",
                    metric={"staleCount": 1},
                    recommendation="Inspect worker heartbeat.",
                ),
            ],
        )

    setattr(ops_endpoint, "build_ops_health_summary", _fake_summary)

    client = TestClient(_build_app())
    response = client.get(
        "/api/ops/health/summary",
        headers={
            "X-User-Id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "X-Tenant-Id": "11111111-1111-1111-1111-111111111111",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 0
    assert payload["data"]["overallStatus"] == "WARN"
    assert {item["key"] for item in payload["data"]["checks"]} == {"database", "workers"}


class _FakeDb:
    def __init__(self, results: list[object], fail_on_calls: set[int] | None = None) -> None:
        self._results = results
        self._index = 0
        self._fail_on_calls = fail_on_calls or set()

    async def scalar(self, _statement):
        self._index += 1
        if self._index in self._fail_on_calls:
            raise RuntimeError("forced query error")
        return self._results[self._index - 1]


def test_build_ops_health_summary_warn_and_blocked() -> None:
    asyncio.run(_assert_build_ops_health_summary_warn_and_blocked())


async def _assert_build_ops_health_summary_warn_and_blocked() -> None:
    # Query order:
    # 1 db ping
    # 2 outbox failed, 3 outbox queued
    # 4 workers stale, 5 workers total
    # 6 devops pending
    # 7 plugins installed
    # 8 legacy ci active, 9 named ci active projects
    db = _FakeDb(results=[1, 2, 5, 1, 3, 1, 0, 0, 0], fail_on_calls={6})
    user = CurrentUser(
        id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        roles=frozenset({"ADMIN"}),
    )

    summary = await build_ops_health_summary(db, user)
    checks_by_key = {item.key: item for item in summary.checks}

    assert summary.overallStatus == "BLOCKED"
    assert checks_by_key["database"].status == "READY"
    assert checks_by_key["notificationOutbox"].status == "WARN"
    assert checks_by_key["notificationOutbox"].metric["failedCount"] == 2
    assert checks_by_key["workers"].status == "WARN"
    assert checks_by_key["devopsRuns"].status == "BLOCKED"
    assert checks_by_key["plugins"].status == "WARN"
    assert checks_by_key["ciTokens"].status == "WARN"


def test_workers_check_uses_naive_utc_cutoff_for_naive_worker_column() -> None:
    asyncio.run(_assert_workers_check_uses_naive_utc_cutoff_for_naive_worker_column())


async def _assert_workers_check_uses_naive_utc_cutoff_for_naive_worker_column() -> None:
    class _InspectingDb:
        def __init__(self) -> None:
            self.calls = 0
            self.cutoff: datetime | None = None

        async def scalar(self, statement):
            self.calls += 1
            if self.calls == 1:
                for node in visitors.iterate(statement):
                    value = getattr(node, "value", None)
                    if isinstance(value, datetime):
                        self.cutoff = value
                        break
            return 0

    db = _InspectingDb()

    check = await _workers_check(db, uuid.UUID("11111111-1111-1111-1111-111111111111"))

    assert check.status == "WARN"
    assert db.cutoff is not None
    assert db.cutoff.tzinfo is None


def test_ci_tokens_check_counts_named_active_token_projects() -> None:
    asyncio.run(_assert_ci_tokens_check_counts_named_active_token_projects())


async def _assert_ci_tokens_check_counts_named_active_token_projects() -> None:
    db = _FakeDb(results=[0, 2])

    check = await _ci_tokens_check(db, uuid.UUID("11111111-1111-1111-1111-111111111111"))

    assert check.status == "READY"
    assert check.metric["activeProjectCount"] == 2
