from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.models.ai_import import AiImportItem, AiImportJob
from app.models.enums import AiImportJobStatus, AiImportSourceType, ProjectRole
from app.models.project import Project, ProjectMember
from app.schemas.ai_import import AiImportCreateJobRequest
from app.services.collection import get_collection_by_name, create_collection, create_group, create_request

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


import asyncio

async def parse_api_collection_async(job_id: uuid.UUID, storage_key: str | None = None, filename: str | None = None):
    import logging
    import asyncio
    from app.core.database import get_sessionmaker
    from app.services.doc_ingest.parse_with_docling import parse_document
    from app.services.doc_ingest.llm_enhancer import apply_llm_enhancement

    logger = logging.getLogger(__name__)
    
    # Wait a short moment to ensure the main transaction that triggered this task has committed
    await asyncio.sleep(0.5)
    
    sm = get_sessionmaker()
    
    async with sm() as db:
        try:
            job = await db.get(AiImportJob, job_id)
            if not job:
                logger.error(f"Job {job_id} not found in async task")
                return
                
            source_ref = job.source_ref_json or {}
            # Use provided values or fallback to DB values
            storage_key = storage_key or source_ref.get("storageKey")
            filename = filename or source_ref.get("fileName", "unknown")
            
            if not storage_key:
                logger.error(f"Storage key missing for job {job_id}")
                job.status = AiImportJobStatus.FAILED.value
                job.summary_json = {"error": "Storage key missing"}
                await db.commit()
                return
                
            # Path resolution
            if "/" in storage_key:
                # Extracts tenant_id/job_id/filename structure
                file_path = _UPLOAD_DIR / storage_key
            else:
                file_path = _UPLOAD_DIR / storage_key
                
            if not file_path.exists():
                logger.error(f"File not found: {file_path} (storage_key: {storage_key})")
                job.status = AiImportJobStatus.FAILED.value
                job.summary_json = {"error": f"File not found: {file_path.name}"}
                await db.commit()
                return
                
            file_content = file_path.read_bytes()
            
            # Step 1: Parse Document
            logger.info(f"Starting docling parse for {filename}...")
            # This calls docling (if installed) or fallback parsers
            parse_result = parse_document(file_content, filename, job_id=str(job_id))
            logger.info(f"Docling parse done. Found {len(parse_result.apiCandidates or [])} raw candidates.")
            
            # Step 2: LLM Enhancement
            skill_config = job.skill_config_json or {}
            # We use AUTO mode by default to replace the mock and actually invoke LLM
            llm_mode = skill_config.get("llmMode", "AUTO")
            logger.info(f"Starting LLM enhancement with mode: {llm_mode}")
            parse_result = apply_llm_enhancement(parse_result, llm_mode)
            
            # Step 3: Map to preview_data_json format
            candidates = parse_result.apiCandidates or []
            logger.info(f"Final candidates count: {len(candidates)}")
            
            groups_dict = {}
            for cand in candidates:
                group_name = cand.feature or "Default Group"
                if group_name not in groups_dict:
                    groups_dict[group_name] = []
                    
                groups_dict[group_name].append({
                    "method": cand.method or "GET",
                    "url": cand.url or "",
                    "name": cand.name or f"{cand.method} {cand.url}",
                    "headers": cand.headers or {},
                    "body": cand.params or {},
                    "diffStatus": "new"
                })
                
            groups = [
                {"name": g_name, "requests": reqs}
                for g_name, reqs in groups_dict.items()
            ]
            
            job.status = AiImportJobStatus.PARSED_PREVIEW.value
            job.preview_data_json = {
                "collectionName": filename,
                "groups": groups
            }
            await db.commit()
            logger.info(f"Job {job_id} parse completed successfully.")
            
        except Exception as e:
            logger.exception(f"Error parsing api collection for job {job_id}: {e}")
            job.status = AiImportJobStatus.FAILED.value
            job.summary_json = {"error": str(e)}
            await db.commit()


async def create_api_import_job(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
) -> AiImportJob:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)

    job = AiImportJob(
        tenant_id=user.tenant_id,
        project_id=project_id,
        source_type=AiImportSourceType.API_COLLECTION_DOC.value,
        status=AiImportJobStatus.PENDING.value,
        source_ref_json={},
        generate_config_json={},
        skill_config_json={},
        summary_json={},
        created_by=user.id,
    )
    db.add(job)
    await db.flush()
    return job


async def upload_api_import_file(
    db: AsyncSession,
    *,
    user: CurrentUser,
    job_id: uuid.UUID,
    file: UploadFile,
) -> AiImportJob:
    job = await _get_job(db, user=user, job_id=job_id)
    project = await _get_project(db, user=user, project_id=job.project_id)
    await _require_project_write(db, user=user, project=project)

    if job.source_type != AiImportSourceType.API_COLLECTION_DOC.value:
        raise HTTPException(status_code=400, detail="Job is not an API collection import job")
    if job.status != AiImportJobStatus.PENDING.value:
        raise HTTPException(status_code=400, detail="Job status is not PENDING")

    file_content = await file.read()
    if not file_content:
        raise HTTPException(status_code=400, detail="file is empty")
    if len(file_content) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="file size exceeds 10MB")

    normalized_filename = _normalize_filename(file.filename or "unknown")
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
    job.status = AiImportJobStatus.PARSING.value
    await db.flush()

    # Trigger background parsing task
    # Pass storageKey and fileName directly to avoid race conditions with DB commit
    asyncio.create_task(parse_api_collection_async(
        job.id, 
        storage_key=source_ref_json.get("storageKey"),
        filename=normalized_filename
    ))
    
    return job


async def get_api_import_job(
    db: AsyncSession,
    *,
    user: CurrentUser,
    job_id: uuid.UUID,
) -> AiImportJob:
    job = await _get_job(db, user=user, job_id=job_id)
    project = await _get_project(db, user=user, project_id=job.project_id)
    await _require_project_read(db, user=user, project=project)

    if job.source_type != AiImportSourceType.API_COLLECTION_DOC.value:
        raise HTTPException(status_code=400, detail="Job is not an API collection import job")
    
    return job


async def commit_api_import_job(
    db: AsyncSession,
    *,
    user: CurrentUser,
    job_id: uuid.UUID,
    selected_requests: list[dict[str, object]],
    override_existing: bool,
) -> None:
    job = await _get_job(db, user=user, job_id=job_id)
    project = await _get_project(db, user=user, project_id=job.project_id)
    await _require_project_write(db, user=user, project=project)

    if job.source_type != AiImportSourceType.API_COLLECTION_DOC.value:
        raise HTTPException(status_code=400, detail="Job is not an API collection import job")
    
    if job.status != AiImportJobStatus.PARSED_PREVIEW.value:
        raise HTTPException(status_code=400, detail="Job must be in PARSED_PREVIEW status to commit")
        
    preview_data = job.preview_data_json
    if not preview_data:
        raise HTTPException(status_code=400, detail="No preview data found")
        
    collection_name = str(preview_data.get("collectionName", "Imported Collection"))
    
    # Try to find existing collection or create new one
    collection = await get_collection_by_name(db, user=user, project_id=project.id, name=collection_name)
    if not collection:
        collection = await create_collection(
            db, 
            user=user, 
            project_id=project.id, 
            name=collection_name, 
            variables={}
        )
    
    # Filter selected requests
    selected_set = {(str(req.get("method")), str(req.get("url"))) for req in selected_requests}
    
    groups = preview_data.get("groups")
    if not isinstance(groups, list):
        groups = []

    for group_data in groups:
        if not isinstance(group_data, dict):
            continue
        group_name = str(group_data.get("name", "Default Group"))
        
        group_requests = group_data.get("requests")
        if not isinstance(group_requests, list):
            group_requests = []

        requests_to_import = [
            req for req in group_requests
            if isinstance(req, dict) and (str(req.get("method")), str(req.get("url"))) in selected_set
        ]
        
        if not requests_to_import:
            continue
            
        group = await create_group(db, user=user, collection_id=collection.id, name=group_name)
        
        for req_data in requests_to_import:
            # Here we just insert new requests. If override_existing is True, we would normally
            # check and update existing ones. For simplicity in this step, we just create.
            await create_request(
                db,
                user=user,
                collection_id=collection.id,
                group_id=group.id,
                name=str(req_data.get("name", "Untitled")),
                method=str(req_data.get("method", "GET")),
                url=str(req_data.get("url", "")),
                headers=req_data.get("headers", {}),
                body=req_data.get("body", {}),
            )
            
    job.status = AiImportJobStatus.COMMITTED.value
    await db.flush()
