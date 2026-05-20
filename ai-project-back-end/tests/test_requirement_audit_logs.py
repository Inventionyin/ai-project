from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.api.deps import CurrentUser
from app.models.requirement import RequirementAnalysis, RequirementTestPoint
from app.schemas.requirement import RequirementDocCreateRequest
from app.schemas.requirement_change import RequirementChangeSetCreateRequest
from app.services import requirement as requirement_service
from app.services import requirement_change as requirement_change_service


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def scalar_one_or_none(self):
        return self._rows[0] if self._rows else None

    def scalar_one(self):
        return self._rows[0] if self._rows else None

    def scalars(self):
        return self

    def all(self):
        return list(self._rows)


class _WriteDb:
    def __init__(self, *, analysis: RequirementAnalysis | None = None) -> None:
        self.analysis = analysis
        self.added = []
        self.now = datetime(2026, 5, 15, 10, 0, tzinfo=timezone.utc).replace(tzinfo=None)

    def add(self, row) -> None:
        self.added.append(row)

    async def flush(self) -> None:
        for row in self.added:
            if getattr(row, "id", None) is None:
                row.id = uuid.uuid4()
            if getattr(row, "created_at", None) is None:
                row.created_at = self.now
            if getattr(row, "updated_at", None) is None:
                row.updated_at = self.now

    async def scalar(self, _stmt):
        return self.analysis

    async def execute(self, _stmt):
        rows = [row for row in self.added if isinstance(row, RequirementTestPoint)]
        return _Result(rows)


@pytest.mark.anyio
async def test_create_requirement_doc_writes_audit_log(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    user_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    user = CurrentUser(id=user_id, tenant_id=tenant_id, roles=frozenset({"ADMIN"}))
    db = _WriteDb()
    calls = []

    async def _fake_get_project(_db, *, user, project_id):
        return SimpleNamespace(id=project_id, owner_id=user.id)

    async def _fake_require_write(_db, *, user, project):
        return None

    async def _fake_audit(_db, **kwargs):
        calls.append(kwargs)
        return SimpleNamespace(id=uuid.uuid4())

    monkeypatch.setattr(requirement_service, "_get_project", _fake_get_project)
    monkeypatch.setattr(requirement_service, "_require_project_write", _fake_require_write)
    monkeypatch.setattr(requirement_service, "create_audit_log", _fake_audit)

    detail = await requirement_service.create_requirement_doc(
        db,
        user=user,
        project_id=project_id,
        payload=RequirementDocCreateRequest(title="登录 PRD", sourceType="MARKDOWN", status="DRAFT", tags=["login"]),
    )

    assert calls
    audit = calls[0]
    assert audit["user"] is user
    assert audit["project_id"] == project_id
    assert audit["module"] == "REQUIREMENT"
    assert audit["action"] == "CREATE_DOC"
    assert audit["resource_type"] == "requirement_doc"
    assert audit["resource_id"] == detail.id
    assert audit["detail"]["title"] == "登录 PRD"


@pytest.mark.anyio
async def test_sync_requirement_test_points_writes_audit_log(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    analysis_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    user_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    user = CurrentUser(id=user_id, tenant_id=tenant_id, roles=frozenset({"ADMIN"}))
    now = datetime(2026, 5, 15, 10, 0, tzinfo=timezone.utc).replace(tzinfo=None)
    analysis = RequirementAnalysis(
        id=analysis_id,
        tenant_id=tenant_id,
        project_id=project_id,
        doc_id=uuid.UUID("44444444-4444-4444-4444-444444444444"),
        doc_version_id=uuid.UUID("55555555-5555-5555-5555-555555555555"),
        status="GENERATED",
        analysis_json={
            "testPoints": [
                {"title": "密码错误提示", "scenarioType": "NEGATIVE", "priority": "P1", "riskLevel": "HIGH"},
                {"title": "登录成功", "scenarioType": "POSITIVE", "priority": "P2", "riskLevel": "MEDIUM"},
            ]
        },
        summary="登录分析",
        risk_level="MEDIUM",
        coverage_score=0.8,
        ai_task_id=None,
        created_by=user_id,
        updated_by=None,
    )
    analysis.created_at = now
    analysis.updated_at = now
    db = _WriteDb(analysis=analysis)
    calls = []

    async def _fake_get_project(_db, *, user, project_id):
        return SimpleNamespace(id=project_id, owner_id=user.id)

    async def _fake_require_write(_db, *, user, project):
        return None

    async def _fake_audit(_db, **kwargs):
        calls.append(kwargs)
        return SimpleNamespace(id=uuid.uuid4())

    monkeypatch.setattr(requirement_service, "_get_project", _fake_get_project)
    monkeypatch.setattr(requirement_service, "_require_project_write", _fake_require_write)
    monkeypatch.setattr(requirement_service, "create_audit_log", _fake_audit)

    rows = await requirement_service.sync_requirement_test_points(db, user=user, project_id=project_id, analysis_id=analysis_id)

    assert len(rows) == 2
    assert calls[0]["module"] == "REQUIREMENT"
    assert calls[0]["action"] == "SYNC_TEST_POINTS"
    assert calls[0]["resource_type"] == "requirement_analysis"
    assert calls[0]["resource_id"] == str(analysis_id)
    assert calls[0]["detail"]["testPointCount"] == 2


@pytest.mark.anyio
async def test_create_requirement_change_set_writes_audit_log(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    doc_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    baseline_id = uuid.UUID("44444444-4444-4444-4444-444444444444")
    target_id = uuid.UUID("55555555-5555-5555-5555-555555555555")
    user_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    user = CurrentUser(id=user_id, tenant_id=tenant_id, roles=frozenset({"ADMIN"}))
    db = _WriteDb()
    calls = []

    async def _fake_get_project(_db, *, user, project_id):
        return SimpleNamespace(id=project_id, owner_id=user.id)

    async def _fake_require_write(_db, *, user, project):
        return None

    async def _fake_get_doc(_db, *, user, project_id, doc_id):
        return SimpleNamespace(id=doc_id)

    async def _fake_get_version(_db, *, user, project_id, doc_id, version_id):
        return SimpleNamespace(
            id=version_id,
            version=1 if version_id == baseline_id else 2,
            file_name="login.md",
            change_summary="新增验证码规则",
            effective_scope="登录",
            parsed_text_preview="新增验证码规则",
        )

    async def _fake_ai_job(_db, **_kwargs):
        return SimpleNamespace(id=uuid.uuid4())

    async def _fake_audit(_db, **kwargs):
        calls.append(kwargs)
        return SimpleNamespace(id=uuid.uuid4())

    monkeypatch.setattr(requirement_change_service, "_get_project", _fake_get_project)
    monkeypatch.setattr(requirement_change_service, "_require_project_write", _fake_require_write)
    monkeypatch.setattr(requirement_change_service, "_get_doc", _fake_get_doc)
    monkeypatch.setattr(requirement_change_service, "_get_version", _fake_get_version)
    monkeypatch.setattr(requirement_change_service, "create_ai_job_record", _fake_ai_job)
    monkeypatch.setattr(requirement_change_service, "create_audit_log", _fake_audit)

    detail = await requirement_change_service.create_requirement_change_set(
        db,
        user=user,
        project_id=project_id,
        doc_id=doc_id,
        payload=RequirementChangeSetCreateRequest(baselineVersionId=str(baseline_id), targetVersionId=str(target_id)),
    )

    assert calls
    assert calls[0]["module"] == "REQUIREMENT"
    assert calls[0]["action"] == "CREATE_CHANGE_SET"
    assert calls[0]["resource_type"] == "requirement_change_set"
    assert calls[0]["resource_id"] == detail.id
    assert calls[0]["detail"]["changeItemCount"] == len(detail.items)
