from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.models.audit import AuditLog
from app.models.enums import ProjectRole
from app.models.platform_record import AiJobRecord
from app.models.project import Project, ProjectMember
from app.schemas.platform_record import (
    AiJobRecordListItem,
    AuditLogListItem,
    TrialOperationImportRecordCreateRequest,
    TrialOperationImportRecordItem,
)


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


async def create_ai_job_record(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    job_type: str,
    status: str,
    trigger_source: str,
    summary: str | None,
    detail: dict | None = None,
) -> AiJobRecord:
    row = AiJobRecord(
        tenant_id=user.tenant_id,
        project_id=project_id,
        job_type=job_type,
        status=status,
        trigger_source=trigger_source,
        summary=summary,
        detail_json=dict(detail or {}),
        created_by=user.id,
    )
    db.add(row)
    await db.flush()
    return row


async def create_audit_log(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID | None,
    module: str | None,
    action: str,
    resource_type: str,
    resource_id: str,
    summary: str | None,
    detail: dict | None = None,
) -> AuditLog:
    row = AuditLog(
        tenant_id=user.tenant_id,
        project_id=project_id,
        user_id=user.id,
        module=module,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        summary=summary,
        detail_json=dict(detail or {}),
    )
    db.add(row)
    await db.flush()
    return row


async def list_ai_job_records(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    page: int,
    page_size: int,
) -> tuple[int, list[AiJobRecordListItem]]:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)
    base_stmt = select(AiJobRecord).where(AiJobRecord.tenant_id == user.tenant_id, AiJobRecord.project_id == project_id)
    total = int((await db.execute(select(func.count()).select_from(base_stmt.subquery()))).scalar_one() or 0)
    rows = (
        await db.execute(base_stmt.order_by(desc(AiJobRecord.created_at)).offset((page - 1) * page_size).limit(page_size))
    ).scalars()
    items = [
        AiJobRecordListItem(
            id=str(row.id),
            projectId=str(row.project_id),
            jobType=row.job_type,
            status=row.status,
            triggerSource=row.trigger_source,
            summary=row.summary,
            createdBy=str(row.created_by) if row.created_by else None,
            createdAt=int(row.created_at.timestamp()),
        )
        for row in rows.all()
    ]
    return total, items


async def list_audit_logs(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    page: int,
    page_size: int,
) -> tuple[int, list[AuditLogListItem]]:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)
    base_stmt = select(AuditLog).where(AuditLog.tenant_id == user.tenant_id, AuditLog.project_id == project_id)
    total = int((await db.execute(select(func.count()).select_from(base_stmt.subquery()))).scalar_one() or 0)
    rows = (
        await db.execute(base_stmt.order_by(desc(AuditLog.created_at)).offset((page - 1) * page_size).limit(page_size))
    ).scalars()
    items = [
        AuditLogListItem(
            id=str(row.id),
            projectId=str(row.project_id) if row.project_id else None,
            module=row.module,
            action=row.action,
            resourceType=row.resource_type,
            resourceId=row.resource_id,
            summary=row.summary,
            detail=dict(row.detail_json or {}),
            userId=str(row.user_id) if row.user_id else None,
            createdAt=int(row.created_at.timestamp()),
        )
        for row in rows.all()
    ]
    return total, items


def _to_trial_operation_import_record(row: AuditLog) -> TrialOperationImportRecordItem:
    detail = dict(row.detail_json or {})
    return TrialOperationImportRecordItem(
        id=str(row.id),
        projectId=str(row.project_id) if row.project_id else None,
        importType=str(detail.get("importType") or "testcases"),
        fileName=str(detail.get("fileName") or row.resource_id),
        status=str(detail.get("status") or "SUCCESS"),
        totalRows=int(detail.get("totalRows") or 0),
        successRows=int(detail.get("successRows") or 0),
        failedRows=int(detail.get("failedRows") or 0),
        summary=row.summary,
        detail=dict(detail.get("detail") or {}),
        createdBy=str(row.user_id) if row.user_id else None,
        createdAt=int(row.created_at.timestamp()),
    )


async def record_trial_operation_import(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    payload: TrialOperationImportRecordCreateRequest,
) -> TrialOperationImportRecordItem:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)
    row = await create_audit_log(
        db,
        user=user,
        project_id=project_id,
        module="trial-operation-import",
        action="IMPORT_BATCH",
        resource_type="trial_operation_import",
        resource_id=payload.fileName,
        summary=payload.summary,
        detail={
            "importType": payload.importType,
            "fileName": payload.fileName,
            "status": payload.status,
            "totalRows": payload.totalRows,
            "successRows": payload.successRows,
            "failedRows": payload.failedRows,
            "detail": payload.detail,
        },
    )
    return _to_trial_operation_import_record(row)


async def list_trial_operation_import_records(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    page: int,
    page_size: int,
) -> tuple[int, list[TrialOperationImportRecordItem]]:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)
    base_stmt = select(AuditLog).where(
        AuditLog.tenant_id == user.tenant_id,
        AuditLog.project_id == project_id,
        AuditLog.module == "trial-operation-import",
        AuditLog.action == "IMPORT_BATCH",
    )
    total = int((await db.execute(select(func.count()).select_from(base_stmt.subquery()))).scalar_one() or 0)
    rows = (
        await db.execute(base_stmt.order_by(desc(AuditLog.created_at)).offset((page - 1) * page_size).limit(page_size))
    ).scalars().all()
    return total, [_to_trial_operation_import_record(row) for row in rows]
