from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.models.ai_import import AiImportItem, AiImportJob
from app.models.enums import AiImportJobStatus, AiImportSourceType, ProjectRole
from app.models.project import Project, ProjectMember
from app.schemas.ai_import import AiImportCreateJobRequest

_UPLOAD_DIR = Path(__file__).resolve().parents[2] / "var" / "ai_import_uploads"
_MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def _is_admin(user: CurrentUser) -> bool:
    return "Admin" in user.roles or "ADMIN" in user.roles


def _stable_payload_sig(payload: dict[str, object]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


async def _get_project(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
) -> Project:
    project = await db.scalar(select(Project).where(Project.id == project_id, Project.tenant_id == user.tenant_id))
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


async def _get_member_role(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
) -> ProjectRole | None:
    return (
        await db.execute(
            select(ProjectMember.role).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user.id,
                ProjectMember.tenant_id == user.tenant_id,
            )
        )
    ).scalar_one_or_none()


async def _require_project_write(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project: Project,
) -> None:
    if _is_admin(user) or project.owner_id == user.id:
        return
    role = await _get_member_role(db, user=user, project_id=project.id)
    if role in (ProjectRole.ADMIN, ProjectRole.OWNER, ProjectRole.EDITOR):
        return
    raise HTTPException(status_code=403, detail="Only Owner/Editor can create ai import job")


async def _require_project_read(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project: Project,
) -> None:
    if _is_admin(user) or project.owner_id == user.id:
        return
    role = await _get_member_role(db, user=user, project_id=project.id)
    if role in (ProjectRole.ADMIN, ProjectRole.OWNER, ProjectRole.EDITOR, ProjectRole.VIEWER):
        return
    raise HTTPException(status_code=403, detail="No permission to view ai import job")


async def _get_existing_idempotent_job(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    idempotency_key: str,
    payload_sig: str,
) -> AiImportJob | None:
    job = await db.scalar(
        select(AiImportJob)
        .where(
            AiImportJob.tenant_id == user.tenant_id,
            AiImportJob.project_id == project_id,
            AiImportJob.summary_json["idempotency"]["key"].astext == idempotency_key,
        )
        .order_by(AiImportJob.created_at.desc())
    )
    if job is None:
        return None
    existing_sig = ((job.summary_json or {}).get("idempotency") or {}).get("sig")
    if existing_sig and existing_sig != payload_sig:
        raise HTTPException(status_code=409, detail="idempotency_key_payload_mismatch")
    return job


async def _get_job(
    db: AsyncSession,
    *,
    user: CurrentUser,
    job_id: uuid.UUID,
) -> AiImportJob:
    job = await db.scalar(
        select(AiImportJob).where(
            AiImportJob.id == job_id,
            AiImportJob.tenant_id == user.tenant_id,
        )
    )
    if job is None:
        raise HTTPException(status_code=404, detail="Ai import job not found")
    return job


def _normalize_filename(filename: str) -> str:
    normalized = re.sub(r"\s+", " ", Path(filename).name).strip()
    if not normalized:
        raise HTTPException(status_code=400, detail="filename is required")
    if len(normalized) > 255:
        raise HTTPException(status_code=400, detail="filename length must be <= 255")
    return normalized


def _coerce_json_object(raw: object) -> dict[str, object]:
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        if isinstance(parsed, dict):
            return parsed
    return {}


async def create_ai_import_job(
    db: AsyncSession,
    *,
    user: CurrentUser,
    payload: AiImportCreateJobRequest,
    idempotency_key: str | None,
) -> AiImportJob:
    try:
        project_id = uuid.UUID(payload.projectId)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid projectId") from exc
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)

    payload_for_sig: dict[str, object] = payload.model_dump(mode="json")
    payload_sig = _stable_payload_sig(payload_for_sig)
    if idempotency_key:
        existing = await _get_existing_idempotent_job(
            db,
            user=user,
            project_id=project_id,
            idempotency_key=idempotency_key,
            payload_sig=payload_sig,
        )
        if existing is not None:
            return existing

    summary_json: dict[str, object] = {
        "previewCount": 0,
        "committedCount": 0,
    }
    if idempotency_key:
        summary_json["idempotency"] = {
            "key": idempotency_key,
            "sig": payload_sig,
        }

    job = AiImportJob(
        tenant_id=user.tenant_id,
        project_id=project_id,
        source_type=payload.sourceType.value,
        status=AiImportJobStatus.PENDING.value,
        source_ref_json=payload.source.model_dump(mode="json", exclude_none=True),
        generate_config_json=payload.generateConfig.model_dump(mode="json"),
        skill_config_json=payload.skillConfig.model_dump(mode="json"),
        summary_json=summary_json,
        created_by=user.id,
    )
    db.add(job)
    try:
        await db.flush()
    except IntegrityError:
        if not idempotency_key:
            raise
        await db.rollback()
        existing = await _get_existing_idempotent_job(
            db,
            user=user,
            project_id=project_id,
            idempotency_key=idempotency_key,
            payload_sig=payload_sig,
        )
        if existing is None:
            raise
        return existing
    return job


async def upload_ai_import_job_file(
    db: AsyncSession,
    *,
    user: CurrentUser,
    job_id: uuid.UUID,
    source_type: AiImportSourceType,
    filename: str,
    file_content: bytes,
) -> tuple[AiImportJob, int]:
    if not file_content:
        raise HTTPException(status_code=400, detail="file is empty")
    if len(file_content) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="file size exceeds 10MB")

    job = await _get_job(db, user=user, job_id=job_id)
    project = await _get_project(db, user=user, project_id=job.project_id)
    await _require_project_write(db, user=user, project=project)

    if source_type == AiImportSourceType.FIGMA_LINK:
        raise HTTPException(status_code=400, detail="FIGMA_LINK does not support file upload")
    if job.source_type != source_type.value:
        raise HTTPException(status_code=400, detail="sourceType mismatch with job")
    if job.status not in {AiImportJobStatus.PENDING.value, AiImportJobStatus.UPLOADED.value}:
        raise HTTPException(status_code=400, detail="job status does not allow file upload")

    normalized_filename = _normalize_filename(filename)
    now = datetime.now(UTC)

    target_dir = _UPLOAD_DIR / str(user.tenant_id) / str(job_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(normalized_filename).suffix.lower()
    stored_name = f"{uuid.uuid4().hex}{ext}"
    target_path = target_dir / stored_name
    target_path.write_bytes(file_content)

    source_ref_json = _coerce_json_object(job.source_ref_json)
    source_ref_json.update(
        {
            "fileName": normalized_filename,
            "storageKey": f"{user.tenant_id}/{job_id}/{stored_name}",
            "uploadedAt": now.isoformat(),
            "fileSize": len(file_content),
        }
    )
    job.source_ref_json = source_ref_json
    job.status = AiImportJobStatus.UPLOADED.value
    await db.flush()
    return job, len(file_content)


async def get_ai_import_job(
    db: AsyncSession,
    *,
    user: CurrentUser,
    job_id: uuid.UUID,
) -> tuple[AiImportJob, list[AiImportItem]]:
    job = await _get_job(db, user=user, job_id=job_id)
    project = await _get_project(db, user=user, project_id=job.project_id)
    await _require_project_read(db, user=user, project=project)
    items = (
        await db.execute(
            select(AiImportItem)
            .where(
                AiImportItem.tenant_id == user.tenant_id,
                AiImportItem.job_id == job_id,
            )
            .order_by(AiImportItem.created_at.asc(), AiImportItem.id.asc())
        )
    ).scalars().all()
    return job, items
