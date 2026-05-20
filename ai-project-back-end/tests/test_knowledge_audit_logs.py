from __future__ import annotations

import uuid
from datetime import datetime

import anyio

from app.api.deps import CurrentUser
from app.schemas.knowledge import RetrospectiveRecordCreateRequest
from app.services import knowledge as knowledge_service


class _DummyProject:
    def __init__(self) -> None:
        self.id = uuid.UUID("22222222-2222-2222-2222-222222222222")
        self.tenant_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
        self.owner_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


class _DummySession:
    def __init__(self) -> None:
        self._project = _DummyProject()
        self.added = []

    async def scalar(self, stmt):
        text = str(stmt)
        if "FROM projects" in text:
            return self._project
        return None

    async def execute(self, stmt):
        class _Result:
            def scalar_one_or_none(self):
                return None

        return _Result()

    def add(self, row) -> None:
        if hasattr(row, "created_at") and getattr(row, "created_at", None) is None:
            row.created_at = datetime.utcnow()
        if hasattr(row, "updated_at") and getattr(row, "updated_at", None) is None:
            row.updated_at = datetime.utcnow()
        self.added.append(row)

    async def flush(self) -> None:
        return None


def test_create_retrospective_writes_audit_log(monkeypatch) -> None:
    db = _DummySession()
    user = CurrentUser(
        id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        roles=frozenset(),
    )
    calls: list[dict] = []

    async def _fake_audit(_db, **kwargs):
        calls.append(kwargs)
        return None

    monkeypatch.setattr(knowledge_service, "create_audit_log", _fake_audit)

    payload = RetrospectiveRecordCreateRequest(
        title="登录链路发布回顾",
        sourceType="PRD",
        status="DRAFT",
    )
    anyio.run(
        lambda: knowledge_service.create_retrospective_record(
            db,
            user=user,
            project_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
            payload=payload,
        )
    )

    assert len(calls) == 1
    assert calls[0]["module"] == "KNOWLEDGE"
    assert calls[0]["action"] == "CREATE_RETROSPECTIVE"
    assert calls[0]["resource_type"] == "retrospective_record"
