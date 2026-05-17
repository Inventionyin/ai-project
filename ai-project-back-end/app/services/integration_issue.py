from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, to_unix_ts
from app.models.enums import ProjectRole
from app.models.integration import IssueLink
from app.models.project import Project, ProjectMember
from app.models.run import CaseRun, Run
from app.schemas.integration_issue import IntegrationIssueCreateRequest, IntegrationIssueDetail
from app.services.provider_registry import resolve_issue_provider


def _is_admin(user: CurrentUser) -> bool:
    return "Admin" in user.roles or "ADMIN" in user.roles


async def _get_project(db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID) -> Project:
    project = await db.scalar(select(Project).where(Project.id == project_id, Project.tenant_id == user.tenant_id))
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


async def _get_member_role(db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID) -> ProjectRole | None:
    return (
        await db.execute(
            select(ProjectMember.role).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user.id,
                ProjectMember.tenant_id == user.tenant_id,
            )
        )
    ).scalar_one_or_none()


async def _require_project_read(db: AsyncSession, *, user: CurrentUser, project: Project) -> None:
    if _is_admin(user) or project.owner_id == user.id:
        return
    role = await _get_member_role(db, user=user, project_id=project.id)
    if role in (ProjectRole.ADMIN, ProjectRole.OWNER, ProjectRole.EDITOR, ProjectRole.VIEWER):
        return
    raise HTTPException(status_code=403, detail="No access to this project")


async def _require_project_write(db: AsyncSession, *, user: CurrentUser, project: Project) -> None:
    if _is_admin(user) or project.owner_id == user.id:
        return
    role = await _get_member_role(db, user=user, project_id=project.id)
    if role in (ProjectRole.ADMIN, ProjectRole.OWNER, ProjectRole.EDITOR):
        return
    raise HTTPException(status_code=403, detail="Only Owner/Editor can modify this project")


def _parse_uuid(value: str, *, field_name: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"invalid_{field_name}") from exc


def _normalize_provider(value: str) -> str:
    normalized = str(value or "").strip().upper()
    if not normalized:
        raise HTTPException(status_code=400, detail="invalid_provider")
    return normalized[:64]


def _to_issue_detail(row: IssueLink) -> IntegrationIssueDetail:
    return IntegrationIssueDetail(
        id=str(row.id),
        runId=str(row.run_id),
        caseRunId=str(row.case_run_id) if row.case_run_id else None,
        provider=row.provider,
        issueKey=row.issue_key,
        url=row.url,
        createdAt=to_unix_ts(row.created_at),
    )


async def _ensure_run_belongs_project(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    run_id: uuid.UUID,
) -> Run:
    run = await db.scalar(
        select(Run).where(
            Run.id == run_id,
            Run.project_id == project_id,
            Run.tenant_id == user.tenant_id,
        )
    )
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


async def _ensure_case_run_belongs_run(
    db: AsyncSession,
    *,
    user: CurrentUser,
    run_id: uuid.UUID,
    case_run_id: uuid.UUID,
) -> CaseRun:
    case_run = await db.scalar(
        select(CaseRun).where(
            CaseRun.id == case_run_id,
            CaseRun.run_id == run_id,
            CaseRun.tenant_id == user.tenant_id,
        )
    )
    if case_run is None:
        raise HTTPException(status_code=404, detail="Case run not found")
    return case_run


async def create_issue_link(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    payload: IntegrationIssueCreateRequest,
) -> IntegrationIssueDetail:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)

    provider = _normalize_provider(payload.provider)
    run_id = _parse_uuid(payload.runId, field_name="run_id")
    run = await _ensure_run_belongs_project(db, user=user, project_id=project.id, run_id=run_id)

    case_run_id: uuid.UUID | None = None
    if payload.caseRunId:
        case_run_id = _parse_uuid(payload.caseRunId, field_name="case_run_id")
        await _ensure_case_run_belongs_run(db, user=user, run_id=run.id, case_run_id=case_run_id)

    issue_provider = resolve_issue_provider(provider)
    if issue_provider is None:
        raise HTTPException(status_code=400, detail="invalid_provider")
    issue_result = issue_provider(
        provider,
        title=payload.title,
        description=payload.description,
        url=payload.url,
        project_id=str(project.id),
        run_id=str(run.id),
        case_run_id=(str(case_run_id) if case_run_id is not None else None),
    )

    row = IssueLink(
        tenant_id=user.tenant_id,
        run_id=run.id,
        case_run_id=case_run_id,
        provider=provider,
        issue_key=issue_result.issue_key,
        url=issue_result.url,
    )
    db.add(row)
    await db.flush()
    return _to_issue_detail(row)


async def list_issue_links(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    run_id: uuid.UUID | None = None,
    case_run_id: uuid.UUID | None = None,
    provider: str | None = None,
) -> list[IntegrationIssueDetail]:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)

    stmt = (
        select(IssueLink)
        .join(Run, Run.id == IssueLink.run_id)
        .where(
            IssueLink.tenant_id == user.tenant_id,
            Run.tenant_id == user.tenant_id,
            Run.project_id == project.id,
        )
    )
    if run_id is not None:
        stmt = stmt.where(IssueLink.run_id == run_id)
    if case_run_id is not None:
        stmt = stmt.where(IssueLink.case_run_id == case_run_id)
    if provider:
        stmt = stmt.where(IssueLink.provider == _normalize_provider(provider))

    rows = (await db.execute(stmt.order_by(desc(IssueLink.created_at), desc(IssueLink.id)))).scalars().all()
    return [_to_issue_detail(row) for row in rows]
