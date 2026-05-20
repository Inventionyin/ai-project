from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from types import SimpleNamespace

import anyio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql.elements import BindParameter

from app.api.deps import CurrentUser, get_current_user
from app.api.v1.endpoints import requirement_changes as requirement_changes_endpoint
from app.core.database import get_db
from app.models.requirement import RequirementCaseLink, RequirementChangeItem, RequirementChangeSet, RequirementRegressionCase, RequirementRegressionSet
from app.services import requirement_change as requirement_change_service
from app.schemas.requirement_change import (
    RequirementChangeSetDetail,
    RequirementRegressionSetDetail,
)
from app.schemas.knowledge import RecommendationEvaluateResponse


@dataclass
class _DummySession:
    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(requirement_changes_endpoint.router, prefix="/api")

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


def _change_set(project_id: uuid.UUID, doc_id: uuid.UUID, change_set_id: uuid.UUID) -> RequirementChangeSetDetail:
    return RequirementChangeSetDetail(
        id=str(change_set_id),
        projectId=str(project_id),
        docId=str(doc_id),
        baselineVersionId="44444444-4444-4444-4444-444444444444",
        targetVersionId="55555555-5555-5555-5555-555555555555",
        summary="检测到新增登录限制规则",
        status="GENERATED",
        items=[],
        createdBy="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        createdAt=1710000000,
        updatedAt=1710000001,
    )


def _regression_set(project_id: uuid.UUID, regression_set_id: uuid.UUID, change_set_id: uuid.UUID) -> RequirementRegressionSetDetail:
    return RequirementRegressionSetDetail(
        id=str(regression_set_id),
        projectId=str(project_id),
        changeSetId=str(change_set_id),
        summary="共需回归 2 条用例",
        status="GENERATED",
        cases=[],
        createdBy="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        createdAt=1710000300,
        updatedAt=1710000301,
    )


def test_change_set_and_regression_set_endpoints(monkeypatch) -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    doc_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    change_set_id = uuid.UUID("66666666-6666-6666-6666-666666666666")
    regression_set_id = uuid.UUID("77777777-7777-7777-7777-777777777777")

    async def _fake_create_change_set(db, *, user, project_id, doc_id, payload):
        return _change_set(project_id, doc_id, change_set_id)

    async def _fake_list_change_sets(db, *, user, project_id, doc_id):
        return [_change_set(project_id, doc_id, change_set_id)]

    async def _fake_get_change_set(db, *, user, project_id, change_set_id):
        return _change_set(project_id, doc_id, change_set_id)

    async def _fake_create_regression_set(db, *, user, project_id, change_set_id):
        return _regression_set(project_id, regression_set_id, change_set_id)

    async def _fake_get_regression_set_by_change_set(db, *, user, project_id, change_set_id):
        return _regression_set(project_id, regression_set_id, change_set_id)

    async def _fake_get_regression_set(db, *, user, project_id, regression_set_id):
        return _regression_set(project_id, regression_set_id, change_set_id)

    monkeypatch.setattr(requirement_changes_endpoint, "create_requirement_change_set", _fake_create_change_set)
    monkeypatch.setattr(requirement_changes_endpoint, "list_requirement_change_sets", _fake_list_change_sets)
    monkeypatch.setattr(requirement_changes_endpoint, "get_requirement_change_set", _fake_get_change_set)
    monkeypatch.setattr(requirement_changes_endpoint, "create_requirement_regression_set", _fake_create_regression_set)
    monkeypatch.setattr(requirement_changes_endpoint, "get_requirement_regression_set_by_change_set", _fake_get_regression_set_by_change_set)
    monkeypatch.setattr(requirement_changes_endpoint, "get_requirement_regression_set", _fake_get_regression_set)

    client = TestClient(_build_app())

    create_resp = client.post(
        f"/api/projects/{project_id}/requirements/docs/{doc_id}/change-sets",
        json={"baselineVersionId": "44444444-4444-4444-4444-444444444444", "targetVersionId": "55555555-5555-5555-5555-555555555555"},
    )
    assert create_resp.status_code == 200
    assert create_resp.json()["data"]["id"] == str(change_set_id)

    list_resp = client.get(f"/api/projects/{project_id}/requirements/docs/{doc_id}/change-sets")
    assert list_resp.status_code == 200
    assert list_resp.json()["data"][0]["summary"] == "检测到新增登录限制规则"

    get_resp = client.get(f"/api/projects/{project_id}/requirements/change-sets/{change_set_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["docId"] == str(doc_id)

    create_reg_resp = client.post(f"/api/projects/{project_id}/requirements/change-sets/{change_set_id}/regression-set")
    assert create_reg_resp.status_code == 200
    assert create_reg_resp.json()["data"]["id"] == str(regression_set_id)

    get_reg_by_change_resp = client.get(f"/api/projects/{project_id}/requirements/change-sets/{change_set_id}/regression-set")
    assert get_reg_by_change_resp.status_code == 200
    assert get_reg_by_change_resp.json()["data"]["id"] == str(regression_set_id)

    get_reg_resp = client.get(f"/api/projects/{project_id}/requirements/regression-sets/{regression_set_id}")
    assert get_reg_resp.status_code == 200
    assert get_reg_resp.json()["data"]["changeSetId"] == str(change_set_id)


def test_change_set_knowledge_recommendations_endpoint(monkeypatch) -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    change_set_id = uuid.UUID("66666666-6666-6666-6666-666666666666")

    async def _fake_evaluate(db, *, user, project_id, payload):
        assert payload.targetType == "CHANGE_SET"
        assert payload.targetId == str(change_set_id)
        assert payload.topK == 3
        return RecommendationEvaluateResponse(
            targetType="CHANGE_SET",
            targetId=payload.targetId,
            recommendations=[
                {
                    "id": "44444444-4444-4444-4444-444444444444",
                    "content": "优先复查新增登录风控场景",
                    "score": 0.88,
                    "type": "TESTCASE",
                    "status": "PENDING",
                }
            ],
        )

    monkeypatch.setattr(requirement_changes_endpoint, "evaluate_recommendations", _fake_evaluate)
    client = TestClient(_build_app())
    resp = client.get(
        f"/api/projects/{project_id}/requirements/change-sets/{change_set_id}/knowledge-recommendations?topK=3"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["targetType"] == "CHANGE_SET"
    assert body["data"]["recommendations"][0]["score"] == 0.88


def test_create_regression_set_scopes_case_links_to_target_version(monkeypatch) -> None:
    tenant_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    user_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    change_set_id = uuid.UUID("66666666-6666-6666-6666-666666666666")
    doc_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    target_version_id = uuid.UUID("55555555-5555-5555-5555-555555555555")

    user = CurrentUser(id=user_id, tenant_id=tenant_id, roles=frozenset({"ADMIN"}))
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    def _where_value(stmt, column_name: str):
        for criterion in stmt._where_criteria:
            left = getattr(criterion, "left", None)
            right = getattr(criterion, "right", None)
            if getattr(left, "name", None) == column_name and isinstance(right, BindParameter):
                return right.value
        return None

    class _ScalarResult:
        def __init__(self, rows):
            self._rows = rows

        def all(self):
            return self._rows

    class _Result:
        def __init__(self, rows):
            self._rows = rows

        def scalars(self):
            return _ScalarResult(self._rows)

        def all(self):
            return self._rows

    class _DB:
        def __init__(self):
            self.added = []

        def add(self, row):
            if getattr(row, "id", None) is None:
                row.id = uuid.uuid4()
            if getattr(row, "created_at", None) is None:
                row.created_at = now
            if getattr(row, "updated_at", None) is None:
                row.updated_at = now
            self.added.append(row)

        async def flush(self):
            return None

        def begin_nested(self):
            db = self

            class _NestedTx:
                async def __aenter__(self_nonlocal):
                    return db

                async def __aexit__(self_nonlocal, exc_type, exc, tb):
                    return False

            return _NestedTx()

        async def scalar(self, stmt):
            entity = stmt.column_descriptions[0]["entity"]
            if entity is RequirementChangeSet:
                return SimpleNamespace(
                    id=change_set_id,
                    project_id=project_id,
                    tenant_id=tenant_id,
                    doc_id=doc_id,
                    target_version_id=target_version_id,
                )
            return None

        async def execute(self, stmt):
            primary_entity = stmt.column_descriptions[0]["entity"]
            if primary_entity is RequirementChangeItem:
                return _Result(
                    [
                        SimpleNamespace(
                            id=uuid.uuid4(),
                            impact_level="HIGH",
                            source_path="target:v2:1",
                            created_at=now,
                        )
                    ]
                )
            if primary_entity is RequirementCaseLink:
                tc1 = uuid.UUID("99999999-9999-9999-9999-999999999991")
                tc2 = uuid.UUID("99999999-9999-9999-9999-999999999992")
                if _where_value(stmt, "doc_version_id") == target_version_id:
                    return _Result(
                        [
                            (
                                SimpleNamespace(testcase_id=tc1, created_at=now, id=uuid.uuid4()),
                                "case-target",
                            )
                        ]
                    )
                return _Result(
                    [
                        (SimpleNamespace(testcase_id=tc1, created_at=now, id=uuid.uuid4()), "case-target"),
                        (SimpleNamespace(testcase_id=tc2, created_at=now, id=uuid.uuid4()), "case-history"),
                    ]
                )
            return _Result([])

    async def _fake_get_project(db, *, user, project_id):
        return SimpleNamespace(id=project_id, owner_id=user.id)

    async def _fake_require_project_write(db, *, user, project):
        return None

    monkeypatch.setattr(requirement_change_service, "_get_project", _fake_get_project)
    monkeypatch.setattr(requirement_change_service, "_require_project_write", _fake_require_project_write)

    db = _DB()
    detail = anyio.run(
        lambda: requirement_change_service.create_requirement_regression_set(
            db,
            user=user,
            project_id=project_id,
            change_set_id=change_set_id,
        )
    )

    assert len(detail.cases) == 1
    assert detail.cases[0].testcaseTitle == "case-target"


def test_create_regression_set_is_idempotent_for_same_change_set(monkeypatch) -> None:
    tenant_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    user_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    change_set_id = uuid.UUID("66666666-6666-6666-6666-666666666666")
    regression_set_id = uuid.UUID("77777777-7777-7777-7777-777777777777")
    testcase_id = uuid.UUID("99999999-9999-9999-9999-999999999999")
    user = CurrentUser(id=user_id, tenant_id=tenant_id, roles=frozenset({"ADMIN"}))
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    class _Result:
        def __init__(self, rows):
            self._rows = rows

        def scalars(self):
            class _ScalarResult:
                def __init__(self, rows):
                    self._rows = rows

                def all(self):
                    return self._rows

            return _ScalarResult(self._rows)

        def all(self):
            return self._rows

    class _DB:
        def __init__(self):
            self.added = []

        def add(self, row):
            self.added.append(row)

        async def flush(self):
            return None

        async def scalar(self, stmt):
            entity = stmt.column_descriptions[0]["entity"]
            if entity is RequirementChangeSet:
                return SimpleNamespace(id=change_set_id, project_id=project_id, tenant_id=tenant_id, doc_id=uuid.uuid4())
            if entity is RequirementRegressionSet:
                return SimpleNamespace(
                    id=regression_set_id,
                    project_id=project_id,
                    change_set_id=change_set_id,
                    summary="共需回归 1 条用例",
                    status="GENERATED",
                    created_by=user_id,
                    created_at=now,
                    updated_at=now,
                    tenant_id=tenant_id,
                )
            return None

        async def execute(self, stmt):
            primary_entity = stmt.column_descriptions[0]["entity"]
            if primary_entity is RequirementRegressionCase:
                return _Result(
                    [
                        (
                            SimpleNamespace(
                                id=uuid.uuid4(),
                                testcase_id=testcase_id,
                                priority="P1",
                                reason="需求版本变更关联的追溯用例",
                                source_paths_json=["target:v2:1"],
                            ),
                            "existing-case",
                        )
                    ]
                )
            return _Result([])

    async def _fake_get_project(db, *, user, project_id):
        return SimpleNamespace(id=project_id, owner_id=user.id)

    async def _fake_require_project_write(db, *, user, project):
        return None

    monkeypatch.setattr(requirement_change_service, "_get_project", _fake_get_project)
    monkeypatch.setattr(requirement_change_service, "_require_project_write", _fake_require_project_write)

    db = _DB()
    detail = anyio.run(
        lambda: requirement_change_service.create_requirement_regression_set(
            db,
            user=user,
            project_id=project_id,
            change_set_id=change_set_id,
        )
    )

    assert detail.id == str(regression_set_id)
    assert detail.cases[0].testcaseTitle == "existing-case"
    assert db.added == []


def test_create_regression_set_handles_unique_conflict_and_returns_existing(monkeypatch) -> None:
    tenant_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    user_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    change_set_id = uuid.UUID("66666666-6666-6666-6666-666666666666")
    regression_set_id = uuid.UUID("77777777-7777-7777-7777-777777777777")
    target_version_id = uuid.UUID("55555555-5555-5555-5555-555555555555")
    testcase_id = uuid.UUID("99999999-9999-9999-9999-999999999999")
    user = CurrentUser(id=user_id, tenant_id=tenant_id, roles=frozenset({"ADMIN"}))
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    class _ScalarResult:
        def __init__(self, rows):
            self._rows = rows

        def all(self):
            return self._rows

    class _Result:
        def __init__(self, rows):
            self._rows = rows

        def scalars(self):
            return _ScalarResult(self._rows)

        def all(self):
            return self._rows

    class _DB:
        def __init__(self):
            self.rollback_called = False
            self.flush_calls = 0
            self.regression_set_scalar_calls = 0
            self.begin_nested_called = 0

        def add(self, row):
            if getattr(row, "id", None) is None:
                row.id = uuid.uuid4()

        async def rollback(self):
            self.rollback_called = True

        def begin_nested(self):
            db = self

            class _NestedTx:
                async def __aenter__(self_nonlocal):
                    db.begin_nested_called += 1
                    return db

                async def __aexit__(self_nonlocal, exc_type, exc, tb):
                    return False

            return _NestedTx()

        async def flush(self):
            self.flush_calls += 1
            if self.flush_calls == 1:
                raise IntegrityError("INSERT", {}, Exception("duplicate key value violates unique constraint"))
            return None

        async def scalar(self, stmt):
            entity = stmt.column_descriptions[0]["entity"]
            if entity is RequirementChangeSet:
                return SimpleNamespace(
                    id=change_set_id,
                    project_id=project_id,
                    tenant_id=tenant_id,
                    doc_id=uuid.uuid4(),
                    target_version_id=target_version_id,
                )
            if entity is RequirementRegressionSet:
                self.regression_set_scalar_calls += 1
                if self.regression_set_scalar_calls == 1:
                    return None
                return SimpleNamespace(
                    id=regression_set_id,
                    project_id=project_id,
                    change_set_id=change_set_id,
                    summary="共需回归 1 条用例",
                    status="GENERATED",
                    created_by=user_id,
                    created_at=now,
                    updated_at=now,
                    tenant_id=tenant_id,
                )
            return None

        async def execute(self, stmt):
            primary_entity = stmt.column_descriptions[0]["entity"]
            if primary_entity is RequirementChangeItem:
                return _Result(
                    [SimpleNamespace(id=uuid.uuid4(), impact_level="HIGH", source_path="target:v2:1", created_at=now)]
                )
            if primary_entity is RequirementCaseLink:
                return _Result(
                    [(SimpleNamespace(testcase_id=testcase_id, created_at=now, id=uuid.uuid4()), "created-case")]
                )
            if primary_entity is RequirementRegressionCase:
                return _Result(
                    [
                        (
                            SimpleNamespace(
                                id=uuid.uuid4(),
                                testcase_id=testcase_id,
                                priority="P1",
                                reason="需求版本变更关联的追溯用例",
                                source_paths_json=["target:v2:1"],
                            ),
                            "existing-case",
                        )
                    ]
                )
            return _Result([])

    async def _fake_get_project(db, *, user, project_id):
        return SimpleNamespace(id=project_id, owner_id=user.id)

    async def _fake_require_project_write(db, *, user, project):
        return None

    monkeypatch.setattr(requirement_change_service, "_get_project", _fake_get_project)
    monkeypatch.setattr(requirement_change_service, "_require_project_write", _fake_require_project_write)

    db = _DB()
    detail = anyio.run(
        lambda: requirement_change_service.create_requirement_regression_set(
            db,
            user=user,
            project_id=project_id,
            change_set_id=change_set_id,
        )
    )

    assert db.begin_nested_called == 1
    assert db.rollback_called is False
    assert detail.id == str(regression_set_id)
    assert detail.cases[0].testcaseTitle == "existing-case"


def test_load_regression_set_detail_filters_cases_by_project(monkeypatch) -> None:
    tenant_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    user_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    change_set_id = uuid.UUID("66666666-6666-6666-6666-666666666666")
    regression_set_id = uuid.UUID("77777777-7777-7777-7777-777777777777")
    user = CurrentUser(id=user_id, tenant_id=tenant_id, roles=frozenset({"ADMIN"}))
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    class _Result:
        def __init__(self, rows):
            self._rows = rows

        def all(self):
            return self._rows

    class _DB:
        async def scalar(self, stmt):
            entity = stmt.column_descriptions[0]["entity"]
            if entity is RequirementRegressionSet:
                return SimpleNamespace(
                    id=regression_set_id,
                    project_id=project_id,
                    change_set_id=change_set_id,
                    summary="共需回归 1 条用例",
                    status="GENERATED",
                    created_by=user_id,
                    created_at=now,
                    updated_at=now,
                    tenant_id=tenant_id,
                )
            return None

        async def execute(self, stmt):
            where_sql = str(stmt.whereclause)
            assert "requirement_regression_cases.project_id" in where_sql
            return _Result([])

    db = _DB()
    detail = anyio.run(
        lambda: requirement_change_service._load_regression_set_detail_by_change_set(
            db,
            user=user,
            project_id=project_id,
            change_set_id=change_set_id,
        )
    )

    assert detail is not None


def test_build_change_item_payloads_includes_updated() -> None:
    baseline = SimpleNamespace(
        version=1,
        change_summary="登录失败超过5次锁定账号",
        effective_scope="账号安全",
        parsed_text_preview="用户连续输错密码5次后锁定30分钟",
        file_name="baseline.md",
    )
    target = SimpleNamespace(
        version=2,
        change_summary="登录失败超过3次锁定账号",
        effective_scope="账号安全",
        parsed_text_preview="用户连续输错密码3次后锁定60分钟",
        file_name="target.md",
    )

    payloads = requirement_change_service._build_change_item_payloads(baseline, target)
    change_types = {item["change_type"] for item in payloads}

    assert "UPDATED" in change_types
