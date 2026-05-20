from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from sqlalchemy import desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.models.doc_parse_job import DocParseJob
from app.models.enums import DocParseJobStatus
from app.models.project import Project, ProjectMember
from app.models.requirement import RequirementDocVersion
from app.schemas.doc_parse_job import DocParseJobDetail
from app.services.platform_record import create_audit_log

logger = logging.getLogger(__name__)


def _is_admin(user: CurrentUser) -> bool:
    return "Admin" in user.roles or "ADMIN" in user.roles


async def _get_project(db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID) -> Project:
    project = await db.scalar(select(Project).where(Project.id == project_id, Project.tenant_id == user.tenant_id))
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


async def _require_project_write(db: AsyncSession, *, user: CurrentUser, project: Project) -> None:
    if _is_admin(user) or project.owner_id == user.id:
        return
    from app.models.enums import ProjectRole
    role = (await db.execute(
        select(ProjectMember.role).where(
            ProjectMember.project_id == project.id,
            ProjectMember.user_id == user.id,
            ProjectMember.tenant_id == user.tenant_id,
        )
    )).scalar_one_or_none()
    if role in (ProjectRole.ADMIN, ProjectRole.OWNER, ProjectRole.EDITOR):
        return
    raise HTTPException(status_code=403, detail="No write access to this project")


async def _require_project_read(db: AsyncSession, *, user: CurrentUser, project: Project) -> None:
    if _is_admin(user) or project.owner_id == user.id:
        return
    from app.models.enums import ProjectRole
    role = (await db.execute(
        select(ProjectMember.role).where(
            ProjectMember.project_id == project.id,
            ProjectMember.user_id == user.id,
            ProjectMember.tenant_id == user.tenant_id,
        )
    )).scalar_one_or_none()
    if role in (ProjectRole.ADMIN, ProjectRole.OWNER, ProjectRole.EDITOR, ProjectRole.VIEWER):
        return
    raise HTTPException(status_code=403, detail="No access to this project")


def _to_detail(row: DocParseJob) -> DocParseJobDetail:
    return DocParseJobDetail(
        id=str(row.id),
        projectId=str(row.project_id),
        docId=str(row.doc_id),
        docVersionId=str(row.doc_version_id),
        status=row.status,
        attempts=row.attempts,
        maxRetries=row.max_retries,
        errorMessage=row.error_message,
        result=dict(row.result_json) if row.result_json else None,
        createdBy=str(row.created_by) if row.created_by else None,
        createdAt=int(row.created_at.timestamp()),
        updatedAt=int(row.updated_at.timestamp()),
    )


async def create_doc_parse_job(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    doc_id: uuid.UUID,
    doc_version_id: uuid.UUID,
) -> DocParseJobDetail:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)
    version = await db.scalar(select(RequirementDocVersion).where(
        RequirementDocVersion.id == doc_version_id,
        RequirementDocVersion.doc_id == doc_id,
        RequirementDocVersion.project_id == project_id,
        RequirementDocVersion.tenant_id == user.tenant_id,
    ))
    if version is None:
        raise HTTPException(status_code=404, detail="Doc version not found")
    existing = await db.scalar(select(DocParseJob).where(
        DocParseJob.doc_version_id == doc_version_id,
        DocParseJob.status.in_([DocParseJobStatus.PENDING.value, DocParseJobStatus.RUNNING.value]),
        DocParseJob.tenant_id == user.tenant_id,
    ))
    if existing:
        return _to_detail(existing)
    job = DocParseJob(
        tenant_id=user.tenant_id,
        project_id=project_id,
        doc_id=doc_id,
        doc_version_id=doc_version_id,
        status=DocParseJobStatus.PENDING.value,
        created_by=user.id,
    )
    db.add(job)
    await db.flush()
    await create_audit_log(
        db, user=user, project_id=project_id,
        action="CREATE_DOC_PARSE_JOB", resource_type="doc_parse_job",
        resource_id=str(job.id), summary=f"创建文档解析任务: {version.file_name}",
    )
    return _to_detail(job)


async def get_doc_parse_job(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    job_id: uuid.UUID,
) -> DocParseJobDetail:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)
    job = await db.scalar(select(DocParseJob).where(
        DocParseJob.id == job_id,
        DocParseJob.project_id == project_id,
        DocParseJob.tenant_id == user.tenant_id,
    ))
    if job is None:
        raise HTTPException(status_code=404, detail="Doc parse job not found")
    return _to_detail(job)


async def list_doc_parse_jobs(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    page: int,
    page_size: int,
    status: str | None = None,
) -> tuple[int, list[DocParseJobDetail]]:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)
    base = select(DocParseJob).where(
        DocParseJob.tenant_id == user.tenant_id,
        DocParseJob.project_id == project_id,
    )
    if status:
        base = base.where(DocParseJob.status == status)
    total = int((await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one() or 0)
    rows = (await db.execute(base.order_by(desc(DocParseJob.created_at)).offset((page - 1) * page_size).limit(page_size))).scalars().all()
    return total, [_to_detail(r) for r in rows]


async def retry_doc_parse_job(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    job_id: uuid.UUID,
) -> DocParseJobDetail:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)
    job = await db.scalar(select(DocParseJob).where(
        DocParseJob.id == job_id,
        DocParseJob.project_id == project_id,
        DocParseJob.tenant_id == user.tenant_id,
    ))
    if job is None:
        raise HTTPException(status_code=404, detail="Doc parse job not found")
    if job.status not in (DocParseJobStatus.FAILED.value, DocParseJobStatus.SUCCESS.value):
        raise HTTPException(status_code=400, detail="Only failed or completed jobs can be retried")
    job.status = DocParseJobStatus.PENDING.value
    job.attempts = 0
    job.error_message = None
    job.result_json = None
    await db.flush()
    await create_audit_log(
        db, user=user, project_id=project_id,
        action="RETRY_DOC_PARSE_JOB", resource_type="doc_parse_job",
        resource_id=str(job.id), summary="重试文档解析任务",
    )
    return _to_detail(job)


async def process_pending_doc_parse_jobs(
    db: AsyncSession,
    *,
    batch_size: int = 5,
) -> int:
    from app.models.requirement import RequirementDocVersion
    from app.services.doc_ingest.parse_with_docling import parse_document

    rows = (await db.execute(
        select(DocParseJob).where(
            DocParseJob.status == DocParseJobStatus.PENDING.value,
        ).order_by(DocParseJob.created_at).limit(batch_size).with_for_update(skip_locked=True)
    )).scalars().all()
    processed = 0
    for job in rows:
        job.status = DocParseJobStatus.RUNNING.value
        job.attempts += 1
        await db.flush()
        try:
            version = await db.scalar(select(RequirementDocVersion).where(
                RequirementDocVersion.id == job.doc_version_id,
            ))
            if version is None:
                job.status = DocParseJobStatus.FAILED.value
                job.error_message = "Doc version not found"
                await db.flush()
                processed += 1
                continue
            source_path = Path(version.storage_url)
            if not source_path.exists():
                job.status = DocParseJobStatus.FAILED.value
                job.error_message = "Source file not found"
                await db.flush()
                processed += 1
                continue
            file_bytes = source_path.read_bytes()
            parsed = await asyncio.to_thread(parse_document, file_bytes, version.file_name, job_id=str(job.id))
            text = parsed.raw.textDigest or ""
            txt_path = source_path.with_suffix(source_path.suffix + ".txt")
            txt_path.write_text(text, encoding="utf-8")
            version.parsed_text_url = str(txt_path).replace("\\", "/")
            version.parsed_text_preview = text[:1000]
            job.status = DocParseJobStatus.SUCCESS.value
            job.result_json = {"textLength": len(text), "preview": text[:200]}
            await db.flush()
            processed += 1
        except Exception as exc:
            logger.exception("Doc parse job %s failed (attempt %s)", job.id, job.attempts)
            if job.attempts >= job.max_retries:
                job.status = DocParseJobStatus.FAILED.value
                job.error_message = str(exc)[:1000]
            else:
                job.status = DocParseJobStatus.PENDING.value
                job.error_message = str(exc)[:1000]
            await db.flush()
            processed += 1
    return processed


async def run_doc_parse_job_consumer(
    *,
    stop_event: asyncio.Event,
    sessionmaker: Any,
    poll_interval_seconds: float = 2.0,
    batch_size: int = 5,
) -> None:
    while not stop_event.is_set():
        try:
            async with sessionmaker() as db:
                processed = await process_pending_doc_parse_jobs(db, batch_size=batch_size)
                if processed > 0:
                    await db.commit()
        except Exception:
            logger.exception("Doc parse job consumer error")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=max(0.1, float(poll_interval_seconds)))
        except asyncio.TimeoutError:
            continue
