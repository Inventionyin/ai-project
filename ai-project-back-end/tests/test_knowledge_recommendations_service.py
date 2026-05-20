from __future__ import annotations

import uuid
from datetime import datetime

import anyio

from app.api.deps import CurrentUser
from app.models.knowledge import KnowledgeRecommendation, KnowledgeRule
from app.schemas.knowledge import RecommendationEvaluateRequest
from app.services import knowledge as knowledge_service


class _DummyProject:
    def __init__(self) -> None:
        self.id = uuid.UUID("22222222-2222-2222-2222-222222222222")
        self.tenant_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
        self.owner_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


class _ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class _RowsResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class _DummySession:
    def __init__(self) -> None:
        self._project = _DummyProject()
        self._rules = [
            KnowledgeRule(
                id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
                tenant_id=self._project.tenant_id,
                project_id=self._project.id,
                name="登录复盘测试建议",
                trigger_type="RETROSPECTIVE",
                condition_json={"targetType": "RETROSPECTIVE"},
                action_json={"type": "TESTCASE", "content": "补充登录链路租户隔离回归用例", "score": 0.9},
                enabled=True,
                created_by=self._project.owner_id,
                updated_by=self._project.owner_id,
            )
        ]
        self._recommendations: list[KnowledgeRecommendation] = []

    async def scalar(self, stmt):
        text = str(stmt)
        if "FROM projects" in text:
            return self._project
        if "FROM knowledge_recommendations" in text:
            if not self._recommendations:
                return None
            has_status_filter = "knowledge_recommendations.status =" in text
            if has_status_filter:
                for row in self._recommendations:
                    if row.status == "PENDING":
                        return row
                return None
            return self._recommendations[0]
        return None

    async def execute(self, stmt):
        text = str(stmt)
        if "project_members.role" in text:
            return _ScalarResult(None)
        if "FROM knowledge_rules" in text:
            return _RowsResult(self._rules)
        return _RowsResult([])

    def add(self, row) -> None:
        if getattr(row, "created_at", None) is None:
            row.created_at = datetime.utcnow()
        if getattr(row, "updated_at", None) is None:
            row.updated_at = datetime.utcnow()
        self._recommendations.append(row)

    async def flush(self) -> None:
        return None


def test_evaluate_recommendations_match_and_deduplicate() -> None:
    db = _DummySession()
    user = CurrentUser(
        id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        roles=frozenset(),
    )
    payload = RecommendationEvaluateRequest(
        targetType="RETROSPECTIVE",
        targetId="44444444-4444-4444-4444-444444444444",
        topK=10,
    )

    first = anyio.run(
        lambda: knowledge_service.evaluate_recommendations(
            db,
            user=user,
            project_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
            payload=payload,
        )
    )
    second = anyio.run(
        lambda: knowledge_service.evaluate_recommendations(
            db,
            user=user,
            project_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
            payload=payload,
        )
    )

    assert len(db._recommendations) == 1
    assert first.recommendations[0].type == "TESTCASE"
    assert first.recommendations[0].content == "补充登录链路租户隔离回归用例"
    assert second.recommendations[0].id == first.recommendations[0].id


def test_evaluate_recommendations_deduplicate_after_status_changed() -> None:
    db = _DummySession()
    user = CurrentUser(
        id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        roles=frozenset(),
    )
    payload = RecommendationEvaluateRequest(
        targetType="RETROSPECTIVE",
        targetId="44444444-4444-4444-4444-444444444444",
        topK=10,
    )

    first = anyio.run(
        lambda: knowledge_service.evaluate_recommendations(
            db,
            user=user,
            project_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
            payload=payload,
        )
    )
    assert len(db._recommendations) == 1

    db._recommendations[0].status = "ADOPTED"

    second = anyio.run(
        lambda: knowledge_service.evaluate_recommendations(
            db,
            user=user,
            project_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
            payload=payload,
        )
    )

    assert len(db._recommendations) == 1
    assert second.recommendations[0].id == first.recommendations[0].id
    assert second.recommendations[0].status == "ADOPTED"
