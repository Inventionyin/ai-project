from __future__ import annotations

import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import CurrentUser, get_current_user
from app.api.v1.endpoints import workspace as workspace_endpoint
from app.core.database import get_db
from app.schemas.workspace import (
    WorkspaceAssetSummary,
    WorkspaceAutomationSummary,
    WorkspaceCapabilitySummary,
    WorkspaceRiskSummary,
    WorkspaceSummaryData,
)


class _DummySession:
    pass


_USER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_TENANT_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
_PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(workspace_endpoint.router, prefix="/api")

    async def _override_db():
        yield _DummySession()

    async def _override_user() -> CurrentUser:
        return CurrentUser(id=_USER_ID, tenant_id=_TENANT_ID, roles=frozenset({"ADMIN"}))

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _override_user
    return app


def test_get_workspace_summary(monkeypatch) -> None:
    async def _fake_summary(db, *, user, project_id):
        assert project_id == _PROJECT_ID
        assert user.id == _USER_ID
        return WorkspaceSummaryData(
            assets=WorkspaceAssetSummary(
                requirementDocs=31,
                testcases=5899,
                formalCases=27,
                testPoints=5872,
                apiCollections=3,
                apiRequests=128,
                suites=12,
            ),
            automation=WorkspaceAutomationSummary(
                runs=27,
                executedCaseRuns=27,
                passRate=81.5,
                latestRunAt=1710000000,
            ),
            risks=WorkspaceRiskSummary(
                defects=460,
                p0Open=22,
                riskHints=460,
            ),
            capabilities=WorkspaceCapabilitySummary(
                role="admin",
                assets=True,
                ai=True,
                automation=True,
                settings=True,
                ops=True,
            ),
        )

    monkeypatch.setattr(workspace_endpoint, "get_workspace_summary", _fake_summary)

    client = TestClient(_build_app())
    resp = client.get(f"/api/projects/{_PROJECT_ID}/workspace/summary")

    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["assets"]["testcases"] == 5899
    assert body["data"]["automation"]["passRate"] == 81.5
    assert body["data"]["risks"]["p0Open"] == 22
    assert body["data"]["capabilities"]["settings"] is True
