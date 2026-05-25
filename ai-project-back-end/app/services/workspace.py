from __future__ import annotations

import uuid

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, to_unix_ts
from app.models.api import ApiCollection, ApiRequest
from app.models.defect import Defect
from app.models.enums import CaseRunStatus, ProjectRole, RunStatus, TestCaseStatus
from app.models.project import Project, ProjectMember
from app.models.requirement import RequirementDoc, RequirementTestPoint
from app.models.run import CaseRun, Run
from app.models.suite import Suite
from app.models.testcase import TestCase
from app.schemas.workspace import (
    WorkspaceAssetSummary,
    WorkspaceAutomationSummary,
    WorkspaceCapabilitySummary,
    WorkspaceRiskSummary,
    WorkspaceSummaryData,
)
from app.services.dashboard import _get_project, _require_project_read
from app.services.defect import list_defect_risk_hints


def _is_admin(user: CurrentUser) -> bool:
    return "Admin" in user.roles or "ADMIN" in user.roles


async def _count_project_rows(db: AsyncSession, model: object, *, tenant_id: uuid.UUID, project_id: uuid.UUID) -> int:
    return int(
        (
            await db.execute(
                select(func.count())
                .select_from(model)
                .where(model.tenant_id == tenant_id, model.project_id == project_id)
            )
        ).scalar_one()
        or 0
    )


async def _count_api_requests(db: AsyncSession, *, tenant_id: uuid.UUID, project_id: uuid.UUID) -> int:
    return int(
        (
            await db.execute(
                select(func.count(ApiRequest.id))
                .join(ApiCollection, ApiCollection.id == ApiRequest.collection_id)
                .where(
                    ApiRequest.tenant_id == tenant_id,
                    ApiCollection.tenant_id == tenant_id,
                    ApiCollection.project_id == project_id,
                )
            )
        ).scalar_one()
        or 0
    )


async def _count_formal_cases(db: AsyncSession, *, tenant_id: uuid.UUID, project_id: uuid.UUID) -> int:
    return int(
        (
            await db.execute(
                select(func.count(TestCase.id)).where(
                    TestCase.tenant_id == tenant_id,
                    TestCase.project_id == project_id,
                    TestCase.status == TestCaseStatus.REVIEWED,
                )
            )
        ).scalar_one()
        or 0
    )


async def _get_automation_summary(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
) -> WorkspaceAutomationSummary:
    run_rows = (
        await db.execute(
            select(Run.status, func.count(Run.id))
            .where(Run.tenant_id == tenant_id, Run.project_id == project_id)
            .group_by(Run.status)
        )
    ).all()
    run_counts = {status: int(count or 0) for status, count in run_rows}
    passed = run_counts.get(RunStatus.PASSED, 0)
    failed = run_counts.get(RunStatus.FAILED, 0)
    finished = passed + failed
    total_runs = sum(run_counts.values())
    pass_rate = round((passed / finished) * 100, 1) if finished > 0 else 0.0

    executed_case_runs = int(
        (
            await db.execute(
                select(func.count(CaseRun.id))
                .join(Run, Run.id == CaseRun.run_id)
                .where(
                    CaseRun.tenant_id == tenant_id,
                    Run.tenant_id == tenant_id,
                    Run.project_id == project_id,
                    CaseRun.status.in_((CaseRunStatus.PASSED, CaseRunStatus.FAILED, CaseRunStatus.SKIPPED)),
                )
            )
        ).scalar_one()
        or 0
    )
    latest_run_at = (
        await db.execute(
            select(func.max(Run.start_at)).where(Run.tenant_id == tenant_id, Run.project_id == project_id)
        )
    ).scalar_one_or_none()
    return WorkspaceAutomationSummary(
        runs=total_runs,
        executedCaseRuns=executed_case_runs,
        passRate=pass_rate,
        latestRunAt=to_unix_ts(latest_run_at) if latest_run_at else None,
    )


async def _get_role(db: AsyncSession, *, user: CurrentUser, project: Project) -> str:
    if _is_admin(user):
        return "admin"
    if project.owner_id == user.id:
        return "owner"
    role = (
        await db.execute(
            select(ProjectMember.role).where(
                ProjectMember.tenant_id == user.tenant_id,
                ProjectMember.project_id == project.id,
                ProjectMember.user_id == user.id,
            )
        )
    ).scalar_one_or_none()
    if role in (ProjectRole.ADMIN, ProjectRole.OWNER):
        return "owner"
    if role == ProjectRole.EDITOR:
        return "editor"
    return "viewer"


def _capabilities_for_role(role: str) -> WorkspaceCapabilitySummary:
    can_write = role in ("admin", "owner", "editor")
    can_admin = role in ("admin", "owner")
    return WorkspaceCapabilitySummary(
        role=role,
        assets=True,
        ai=can_write,
        automation=can_write,
        settings=can_admin,
        ops=can_admin,
    )


async def get_workspace_summary(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
) -> WorkspaceSummaryData:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)

    requirement_docs = await _count_project_rows(db, RequirementDoc, tenant_id=user.tenant_id, project_id=project.id)
    testcases = await _count_project_rows(db, TestCase, tenant_id=user.tenant_id, project_id=project.id)
    formal_cases = await _count_formal_cases(db, tenant_id=user.tenant_id, project_id=project.id)
    test_points = await _count_project_rows(db, RequirementTestPoint, tenant_id=user.tenant_id, project_id=project.id)
    api_collections = await _count_project_rows(db, ApiCollection, tenant_id=user.tenant_id, project_id=project.id)
    api_requests = await _count_api_requests(db, tenant_id=user.tenant_id, project_id=project.id)
    suites = await _count_project_rows(db, Suite, tenant_id=user.tenant_id, project_id=project.id)

    defects = await _count_project_rows(db, Defect, tenant_id=user.tenant_id, project_id=project.id)
    p0_open = int(
        (
            await db.execute(
                select(func.count(Defect.id)).where(
                    Defect.tenant_id == user.tenant_id,
                    Defect.project_id == project.id,
                    Defect.severity == "P0",
                    Defect.status != "CLOSED",
                )
            )
        ).scalar_one()
        or 0
    )
    risk_hints = len(await list_defect_risk_hints(db, user=user, project_id=project.id))
    role = await _get_role(db, user=user, project=project)

    return WorkspaceSummaryData(
        assets=WorkspaceAssetSummary(
            requirementDocs=requirement_docs,
            testcases=testcases,
            formalCases=formal_cases,
            testPoints=test_points,
            apiCollections=api_collections,
            apiRequests=api_requests,
            suites=suites,
        ),
        automation=await _get_automation_summary(db, tenant_id=user.tenant_id, project_id=project.id),
        risks=WorkspaceRiskSummary(defects=defects, p0Open=p0_open, riskHints=risk_hints),
        capabilities=_capabilities_for_role(role),
    )
