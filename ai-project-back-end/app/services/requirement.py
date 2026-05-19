from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, to_unix_ts
from app.models.enums import ProjectRole
from app.models.project import Project, ProjectMember
from app.models.enums import Priority, TestCaseStatus, TestCaseType
from app.models.requirement import GeneratedCaseDraft, RequirementAnalysis, RequirementAnalysisRevision, RequirementCaseLink, RequirementDoc, RequirementDocVersion, RequirementTestPoint
from app.models.testcase import TestCase, TestCaseVersion
from app.schemas.requirement_change import RequirementAnalysisRevisionDetail
from app.schemas.requirement import (
    BulkApproveCaseDraftsRequest,
    BulkApproveCaseDraftsResult,
    GenerateCaseDraftsRequest,
    GeneratedCaseDraftDetail,
    RequirementCaseLinkDetail,
    RequirementAnalysisDetail,
    RequirementAnalysisUpdateRequest,
    RequirementDocCreateRequest,
    RequirementDocDetail,
    RequirementDocUpdateRequest,
    RequirementDocVersionDetail,
    RequirementTestPointDetail,
    RequirementTestPointUpdateRequest,
    normalize_scenario_type,
    empty_analysis_payload,
    normalize_analysis_status,
    normalize_doc_source_type,
    normalize_doc_status,
    normalize_risk_level,
    normalize_test_point_status,
)
from app.services.doc_ingest.parse_with_docling import parse_document
from app.services.llm.provider import get_provider
from app.services.platform_record import create_ai_job_record, create_audit_log


def _is_admin(user: CurrentUser) -> bool:
    return "Admin" in user.roles or "ADMIN" in user.roles


async def _get_project(db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID) -> Project:
    project = (await db.execute(select(Project).where(Project.id == project_id, Project.tenant_id == user.tenant_id))).scalar_one_or_none()
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


async def _create_requirement_audit(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    action: str,
    resource_type: str,
    resource_id: str,
    summary: str,
    detail: dict | None = None,
) -> None:
    await create_audit_log(
        db,
        user=user,
        project_id=project_id,
        module="REQUIREMENT",
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        summary=summary,
        detail=detail or {},
    )


def _to_doc_detail(doc: RequirementDoc) -> RequirementDocDetail:
    return RequirementDocDetail(
        id=str(doc.id),
        projectId=str(doc.project_id),
        title=doc.title,
        sourceType=doc.source_type,
        ownerId=str(doc.owner_id) if doc.owner_id else None,
        status=doc.status,
        tags=list(doc.tags_json or []),
        currentVersionId=str(doc.current_version_id) if doc.current_version_id else None,
        createdBy=str(doc.created_by),
        createdAt=to_unix_ts(doc.created_at),
        updatedAt=to_unix_ts(doc.updated_at),
    )


def _to_version_detail(version: RequirementDocVersion) -> RequirementDocVersionDetail:
    return RequirementDocVersionDetail(
        id=str(version.id),
        docId=str(version.doc_id),
        projectId=str(version.project_id),
        version=version.version,
        fileName=version.file_name,
        fileType=version.file_type,
        storageUrl=version.storage_url,
        contentHash=version.content_hash,
        parsedTextUrl=version.parsed_text_url,
        parsedTextPreview=version.parsed_text_preview,
        changeSummary=version.change_summary,
        effectiveScope=version.effective_scope,
        publishedAt=to_unix_ts(version.published_at) if version.published_at else None,
        createdBy=str(version.created_by),
        createdAt=to_unix_ts(version.created_at),
        updatedAt=to_unix_ts(version.updated_at),
    )


def _to_analysis_detail(row: RequirementAnalysis) -> RequirementAnalysisDetail:
    return RequirementAnalysisDetail(
        id=str(row.id),
        projectId=str(row.project_id),
        docId=str(row.doc_id),
        docVersionId=str(row.doc_version_id),
        status=row.status,
        summary=row.summary,
        riskLevel=row.risk_level,
        coverageScore=float(row.coverage_score) if row.coverage_score is not None else None,
        analysis=dict(row.analysis_json or empty_analysis_payload()),
        aiTaskId=str(row.ai_task_id) if row.ai_task_id else None,
        createdBy=str(row.created_by),
        updatedBy=str(row.updated_by) if row.updated_by else None,
        createdAt=to_unix_ts(row.created_at),
        updatedAt=to_unix_ts(row.updated_at),
    )


def _to_analysis_revision_detail(row: RequirementAnalysisRevision) -> RequirementAnalysisRevisionDetail:
    return RequirementAnalysisRevisionDetail(
        id=str(row.id),
        projectId=str(row.project_id),
        analysisId=str(row.analysis_id),
        docId=str(row.doc_id),
        docVersionId=str(row.doc_version_id),
        revisionNo=row.revision_no,
        changeReason=row.change_reason,
        summary=row.summary,
        riskLevel=row.risk_level,
        coverageScore=float(row.coverage_score) if row.coverage_score is not None else None,
        analysis=dict(row.analysis_json or empty_analysis_payload()),
        createdBy=str(row.created_by),
        createdAt=to_unix_ts(row.created_at),
    )


def _strip_code_fences(text: str) -> str:
    t = (text or "").strip()
    if not t.startswith("```"):
        return t
    t = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", t)
    t = re.sub(r"\s*```$", "", t)
    return t.strip()


def _coerce_list(raw: object) -> list:
    if isinstance(raw, list):
        return raw[:200]
    return []


def _normalize_analysis_payload(raw: object) -> dict:
    if isinstance(raw, str):
        try:
            raw = json.loads(_strip_code_fences(raw))
        except Exception:
            raw = {}
    if not isinstance(raw, dict):
        raw = {}
    base = empty_analysis_payload()
    for key in base:
        base[key] = _coerce_list(raw.get(key))
    return base


def _extract_doc_text(version: RequirementDocVersion) -> str:
    if version.parsed_text_url:
        path = Path(version.parsed_text_url)
        if path.exists():
            return path.read_text(encoding="utf-8", errors="ignore")[:20000]
    path = Path(version.storage_url)
    if path.exists():
        try:
            parsed = parse_document(path.read_bytes(), version.file_name, job_id=str(version.id))
            return (parsed.raw.textDigest or "")[:20000]
        except Exception:
            return path.read_text(encoding="utf-8", errors="ignore")[:20000]
    return ""


def _sentence_chunks(text: str, limit: int = 8) -> list[str]:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    if not cleaned:
        return []
    chunks = re.split(r"[。；;.!?\n]+", cleaned)
    out: list[str] = []
    for item in chunks:
        s = item.strip()
        if len(s) < 6:
            continue
        out.append(s[:160])
        if len(out) >= limit:
            break
    return out


def _heuristic_analysis(doc: RequirementDoc, version: RequirementDocVersion, text: str, instruction: str | None) -> tuple[dict, str, str, float]:
    chunks = _sentence_chunks(text, limit=10)
    if not chunks:
        chunks = [f"{doc.title} 文档尚未解析出足够文本，建议先补充或重新上传清晰版本。"]
    feature_points = [{"title": c[:40], "description": c, "source": f"v{version.version}"} for c in chunks[:4]]
    business_rules = [{"title": c[:40], "description": c, "source": f"v{version.version}"} for c in chunks[4:7]]
    test_points = []
    for i, c in enumerate(chunks[:6], start=1):
        test_points.append(
            {
                "title": f"验证{c[:28]}",
                "description": c,
                "scenarioType": "POSITIVE" if i % 2 else "NEGATIVE",
                "priority": "P1" if i <= 3 else "P2",
                "source": f"v{version.version}",
            }
        )
    lower_text = text.lower()
    risky = any(k in lower_text for k in ["权限", "支付", "金额", "安全", "登录", "密码", "token", "并发", "审批"])
    risk_level = "HIGH" if risky else "MEDIUM"
    risk_points = [
        {"title": "权限与数据越权风险", "riskLevel": "HIGH", "description": "需覆盖未授权、越权和跨项目访问。"},
        {"title": "异常输入与边界风险", "riskLevel": "MEDIUM", "description": "需覆盖空值、超长、重复提交和状态冲突。"},
    ]
    payload = {
        "featurePoints": feature_points,
        "businessRules": business_rules,
        "testPoints": test_points,
        "riskPoints": risk_points,
        "boundaryCases": [
            {"title": "空输入/缺失字段", "description": "验证必填字段缺失时的提示和状态不变。"},
            {"title": "重复提交", "description": "验证幂等、去重或重复创建策略。"},
        ],
        "coverageSuggestions": [
            {"title": "补齐异常流", "description": instruction or "优先补充权限、异常输入和状态流转覆盖。"},
            {"title": "建立回归集", "description": "将高风险测试点纳入每次发布前回归。"},
        ],
    }
    summary = f"已从《{doc.title}》v{version.version} 提取 {len(feature_points)} 个功能点、{len(test_points)} 个测试点和 {len(risk_points)} 个风险点。"
    coverage_score = min(0.9, 0.45 + len(test_points) * 0.06 + len(business_rules) * 0.03)
    return payload, summary, risk_level, round(coverage_score, 2)


def _llm_analysis(text: str, instruction: str | None) -> dict | None:
    provider = get_provider()
    if not provider.is_configured:
        return None
    system = (
        "你是资深测试架构师。只输出 JSON 对象，不要 Markdown。字段必须包含 "
        "featurePoints,businessRules,testPoints,riskPoints,boundaryCases,coverageSuggestions。"
    )
    prompt = json.dumps(
        {
            "instruction": instruction or "",
            "docText": text[:16000],
            "schema": empty_analysis_payload(),
        },
        ensure_ascii=False,
    )
    try:
        result = provider.chat(prompt=prompt, system=system, temperature=0.1, max_tokens=4096)
        content = str((result or {}).get("content") or "")
        payload = _normalize_analysis_payload(content)
        if any(payload.values()):
            return payload
    except Exception:
        return None
    return None


async def list_requirement_docs(db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID, page: int, page_size: int, status: str | None, q: str | None) -> tuple[int, list[RequirementDocDetail]]:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)
    page = max(1, int(page or 1))
    page_size = max(1, min(200, int(page_size or 20)))
    filters = [RequirementDoc.tenant_id == user.tenant_id, RequirementDoc.project_id == project_id]
    if status:
        filters.append(RequirementDoc.status == normalize_doc_status(status))
    if q:
        keyword = f"%{q.strip()}%"
        filters.append(or_(RequirementDoc.title.ilike(keyword), RequirementDoc.source_type.ilike(keyword)))

    total = int((await db.execute(select(func.count(RequirementDoc.id)).where(*filters))).scalar_one() or 0)
    rows = (
        await db.execute(
            select(RequirementDoc)
            .where(*filters)
            .order_by(RequirementDoc.updated_at.desc(), RequirementDoc.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars()
    return total, [_to_doc_detail(x) for x in rows.all()]


async def create_requirement_doc(db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID, payload: RequirementDocCreateRequest) -> RequirementDocDetail:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)
    owner_id = uuid.UUID(payload.ownerId) if payload.ownerId else None
    doc = RequirementDoc(
        tenant_id=user.tenant_id,
        project_id=project_id,
        title=payload.title,
        source_type=normalize_doc_source_type(payload.sourceType),
        owner_id=owner_id,
        status=normalize_doc_status(payload.status),
        tags_json=payload.tags or [],
        created_by=user.id,
    )
    db.add(doc)
    await db.flush()
    await _create_requirement_audit(
        db,
        user=user,
        project_id=project_id,
        action="CREATE_DOC",
        resource_type="requirement_doc",
        resource_id=str(doc.id),
        summary=f"创建需求文档：{doc.title}",
        detail={
            "title": doc.title,
            "sourceType": doc.source_type,
            "status": doc.status,
            "tags": list(doc.tags_json or []),
            "ownerId": str(doc.owner_id) if doc.owner_id else None,
        },
    )
    return _to_doc_detail(doc)


async def get_requirement_doc(db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID, doc_id: uuid.UUID) -> RequirementDocDetail:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)
    doc = await db.scalar(select(RequirementDoc).where(RequirementDoc.id == doc_id, RequirementDoc.project_id == project_id, RequirementDoc.tenant_id == user.tenant_id))
    if doc is None:
        raise HTTPException(status_code=404, detail="Requirement doc not found")
    return _to_doc_detail(doc)


async def update_requirement_doc(db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID, doc_id: uuid.UUID, payload: RequirementDocUpdateRequest) -> RequirementDocDetail:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)
    doc = await db.scalar(select(RequirementDoc).where(RequirementDoc.id == doc_id, RequirementDoc.project_id == project_id, RequirementDoc.tenant_id == user.tenant_id))
    if doc is None:
        raise HTTPException(status_code=404, detail="Requirement doc not found")
    changed_fields: list[str] = []
    if payload.title is not None:
        doc.title = payload.title
        changed_fields.append("title")
    if payload.sourceType is not None:
        doc.source_type = normalize_doc_source_type(payload.sourceType)
        changed_fields.append("sourceType")
    if payload.status is not None:
        doc.status = normalize_doc_status(payload.status)
        changed_fields.append("status")
    if payload.tags is not None:
        doc.tags_json = payload.tags
        changed_fields.append("tags")
    if payload.ownerId is not None:
        doc.owner_id = uuid.UUID(payload.ownerId)
        changed_fields.append("ownerId")
    await db.flush()
    await _create_requirement_audit(
        db,
        user=user,
        project_id=project_id,
        action="UPDATE_DOC",
        resource_type="requirement_doc",
        resource_id=str(doc.id),
        summary=f"更新需求文档：{doc.title}",
        detail={"changedFields": changed_fields, "status": doc.status},
    )
    return _to_doc_detail(doc)


async def delete_requirement_doc(db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID, doc_id: uuid.UUID) -> None:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)
    doc = await db.scalar(select(RequirementDoc).where(RequirementDoc.id == doc_id, RequirementDoc.project_id == project_id, RequirementDoc.tenant_id == user.tenant_id))
    if doc is None:
        raise HTTPException(status_code=404, detail="Requirement doc not found")
    await _create_requirement_audit(
        db,
        user=user,
        project_id=project_id,
        action="DELETE_DOC",
        resource_type="requirement_doc",
        resource_id=str(doc.id),
        summary=f"删除需求文档：{doc.title}",
        detail={"title": doc.title, "status": doc.status},
    )
    await db.delete(doc)
    await db.flush()


async def list_requirement_doc_versions(db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID, doc_id: uuid.UUID) -> list[RequirementDocVersionDetail]:
    await get_requirement_doc(db, user=user, project_id=project_id, doc_id=doc_id)
    rows = (
        await db.execute(
            select(RequirementDocVersion)
            .where(
                RequirementDocVersion.tenant_id == user.tenant_id,
                RequirementDocVersion.project_id == project_id,
                RequirementDocVersion.doc_id == doc_id,
            )
            .order_by(RequirementDocVersion.version.desc())
        )
    ).scalars()
    return [_to_version_detail(x) for x in rows.all()]


def _detect_file_type(name: str) -> str:
    ext = os.path.splitext(name or "")[1].lower().lstrip(".")
    if not ext:
        return "OTHER"
    return ext.upper()


async def create_requirement_doc_version(db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID, doc_id: uuid.UUID, upload_file: UploadFile, change_summary: str | None, effective_scope: str | None) -> RequirementDocVersionDetail:
    await get_requirement_doc(db, user=user, project_id=project_id, doc_id=doc_id)
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)
    current_max = (
        await db.execute(select(func.max(RequirementDocVersion.version)).where(RequirementDocVersion.doc_id == doc_id, RequirementDocVersion.tenant_id == user.tenant_id))
    ).scalar_one_or_none()
    next_version = int(current_max or 0) + 1
    version_id = uuid.uuid4()
    file_name = Path(upload_file.filename or "unknown.bin").name or "unknown.bin"
    file_bytes = await upload_file.read()
    content_hash = hashlib.sha256(file_bytes).hexdigest()
    base_dir = Path("var") / "requirements" / str(project_id) / str(doc_id) / str(version_id)
    base_dir.mkdir(parents=True, exist_ok=True)
    source_path = base_dir / file_name
    source_path.write_bytes(file_bytes)
    row = RequirementDocVersion(
        id=version_id,
        tenant_id=user.tenant_id,
        project_id=project_id,
        doc_id=doc_id,
        version=next_version,
        file_name=file_name,
        file_type=_detect_file_type(file_name),
        storage_url=str(source_path).replace("\\", "/"),
        content_hash=content_hash,
        parsed_text_url=None,
        parsed_text_preview=None,
        change_summary=change_summary,
        effective_scope=effective_scope,
        created_by=user.id,
    )
    db.add(row)
    await db.flush()
    await _create_requirement_audit(
        db,
        user=user,
        project_id=project_id,
        action="UPLOAD_VERSION",
        resource_type="requirement_doc_version",
        resource_id=str(row.id),
        summary=f"上传需求文档版本：{file_name}",
        detail={
            "docId": str(doc_id),
            "version": row.version,
            "fileName": row.file_name,
            "fileType": row.file_type,
            "contentHash": row.content_hash,
        },
    )
    return _to_version_detail(row)


async def create_requirement_doc_version_from_bytes(
    db: AsyncSession,
    *,
    user: CurrentUser,
    doc_id: uuid.UUID,
    content: bytes,
    filename: str,
    change_summary: str = "",
    effective_scope: str = "",
) -> RequirementDocVersion:
    """Create a doc version from raw bytes (used by URL import)."""
    version_row = await db.scalar(
        select(RequirementDocVersion).where(
            RequirementDocVersion.doc_id == doc_id,
            RequirementDocVersion.tenant_id == user.tenant_id,
        )
        .order_by(RequirementDocVersion.version.desc())
        .limit(1)
    )
    if version_row is None:
        # Verify doc exists
        doc = await db.scalar(
            select(RequirementDoc).where(
                RequirementDoc.id == doc_id,
                RequirementDoc.tenant_id == user.tenant_id,
            )
        )
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        project_id = doc.project_id
        next_version = 1
    else:
        project_id = version_row.project_id
        next_version = version_row.version + 1

    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)

    version_id = uuid.uuid4()
    file_name = Path(filename).name or "imported-doc"
    content_hash = hashlib.sha256(content).hexdigest()
    base_dir = Path("var") / "requirements" / str(project_id) / str(doc_id) / str(version_id)
    base_dir.mkdir(parents=True, exist_ok=True)
    source_path = base_dir / file_name
    source_path.write_bytes(content)

    row = RequirementDocVersion(
        id=version_id,
        tenant_id=user.tenant_id,
        project_id=project_id,
        doc_id=doc_id,
        version=next_version,
        file_name=file_name,
        file_type=_detect_file_type(file_name),
        storage_url=str(source_path).replace("\\", "/"),
        content_hash=content_hash,
        parsed_text_url=None,
        parsed_text_preview=None,
        change_summary=change_summary,
        effective_scope=effective_scope,
        created_by=user.id,
    )
    db.add(row)
    await db.flush()
    await _create_requirement_audit(
        db,
        user=user,
        project_id=project_id,
        action="IMPORT_URL_VERSION",
        resource_type="requirement_doc_version",
        resource_id=str(row.id),
        summary=f"通过URL导入需求文档版本：{file_name}",
        detail={
            "docId": str(doc_id),
            "version": row.version,
            "fileName": row.file_name,
            "fileType": row.file_type,
            "contentHash": row.content_hash,
        },
    )
    return row


async def parse_requirement_doc_version(db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID, doc_id: uuid.UUID, version_id: uuid.UUID) -> dict[str, str]:
    await get_requirement_doc(db, user=user, project_id=project_id, doc_id=doc_id)
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)
    version = await db.scalar(select(RequirementDocVersion).where(RequirementDocVersion.id == version_id, RequirementDocVersion.project_id == project_id, RequirementDocVersion.doc_id == doc_id, RequirementDocVersion.tenant_id == user.tenant_id))
    if version is None:
        raise HTTPException(status_code=404, detail="Requirement doc version not found")
    source_path = Path(version.storage_url)
    if not source_path.exists():
        raise HTTPException(status_code=404, detail="Source file not found")
    file_bytes = source_path.read_bytes()
    parsed = parse_document(file_bytes, version.file_name, job_id=str(version.id))
    text = parsed.raw.textDigest or ""
    txt_path = source_path.with_suffix(source_path.suffix + ".txt")
    txt_path.write_text(text, encoding="utf-8")
    version.parsed_text_url = str(txt_path).replace("\\", "/")
    version.parsed_text_preview = text[:1000]
    await db.flush()
    await _create_requirement_audit(
        db,
        user=user,
        project_id=project_id,
        action="PARSE_VERSION",
        resource_type="requirement_doc_version",
        resource_id=str(version.id),
        summary=f"解析需求文档版本：{version.file_name}",
        detail={"docId": str(doc_id), "version": version.version, "textLength": len(text)},
    )
    return {"status": "ok"}


async def get_requirement_doc_version_parsed_text(db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID, doc_id: uuid.UUID, version_id: uuid.UUID) -> dict[str, str]:
    await get_requirement_doc(db, user=user, project_id=project_id, doc_id=doc_id)
    version = await db.scalar(select(RequirementDocVersion).where(RequirementDocVersion.id == version_id, RequirementDocVersion.project_id == project_id, RequirementDocVersion.doc_id == doc_id, RequirementDocVersion.tenant_id == user.tenant_id))
    if version is None:
        raise HTTPException(status_code=404, detail="Requirement doc version not found")
    if not version.parsed_text_url:
        return {"text": ""}
    txt_path = Path(version.parsed_text_url)
    if not txt_path.exists():
        return {"text": ""}
    return {"text": txt_path.read_text(encoding="utf-8")}


async def _create_analysis_revision(
    db: AsyncSession,
    *,
    user: CurrentUser,
    analysis: RequirementAnalysis,
    change_reason: str,
) -> RequirementAnalysisRevision:
    current_max = (
        await db.execute(
            select(func.max(RequirementAnalysisRevision.revision_no)).where(
                RequirementAnalysisRevision.analysis_id == analysis.id,
                RequirementAnalysisRevision.project_id == analysis.project_id,
                RequirementAnalysisRevision.tenant_id == analysis.tenant_id,
            )
        )
    ).scalar_one_or_none()
    revision = RequirementAnalysisRevision(
        tenant_id=analysis.tenant_id,
        project_id=analysis.project_id,
        analysis_id=analysis.id,
        doc_id=analysis.doc_id,
        doc_version_id=analysis.doc_version_id,
        revision_no=int(current_max or 0) + 1,
        change_reason=change_reason,
        analysis_json=dict(analysis.analysis_json or {}),
        summary=analysis.summary,
        risk_level=analysis.risk_level,
        coverage_score=analysis.coverage_score,
        created_by=user.id,
    )
    db.add(revision)
    await db.flush()
    return revision


async def _get_requirement_doc_version(db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID, doc_id: uuid.UUID, version_id: uuid.UUID) -> tuple[RequirementDoc, RequirementDocVersion]:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)
    doc = await db.scalar(select(RequirementDoc).where(RequirementDoc.id == doc_id, RequirementDoc.project_id == project_id, RequirementDoc.tenant_id == user.tenant_id))
    if doc is None:
        raise HTTPException(status_code=404, detail="Requirement doc not found")
    version = await db.scalar(
        select(RequirementDocVersion).where(
            RequirementDocVersion.id == version_id,
            RequirementDocVersion.project_id == project_id,
            RequirementDocVersion.doc_id == doc_id,
            RequirementDocVersion.tenant_id == user.tenant_id,
        )
    )
    if version is None:
        raise HTTPException(status_code=404, detail="Requirement doc version not found")
    return doc, version


async def generate_requirement_analysis(db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID, doc_id: uuid.UUID, version_id: uuid.UUID, instruction: str | None) -> RequirementAnalysisDetail:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)
    doc, version = await _get_requirement_doc_version(db, user=user, project_id=project_id, doc_id=doc_id, version_id=version_id)
    text = _extract_doc_text(version)
    analysis = _llm_analysis(text, instruction)
    if analysis is None:
        analysis, summary, risk_level, coverage_score = _heuristic_analysis(doc, version, text, instruction)
    else:
        summary = f"AI 已从《{doc.title}》v{version.version} 生成结构化需求分析。"
        risk_level = "MEDIUM"
        coverage_score = 0.72
    ai_job = await create_ai_job_record(
        db,
        user=user,
        project_id=project_id,
        job_type="REQUIREMENT_ANALYSIS",
        status="SUCCEEDED",
        trigger_source="REQUIREMENTS",
        summary=summary,
        detail={"docId": str(doc_id), "docVersionId": str(version_id)},
    )
    row = RequirementAnalysis(
        tenant_id=user.tenant_id,
        project_id=project_id,
        doc_id=doc_id,
        doc_version_id=version_id,
        status="GENERATED",
        analysis_json=_normalize_analysis_payload(analysis),
        summary=summary,
        risk_level=risk_level,
        coverage_score=coverage_score,
        ai_task_id=ai_job.id,
        created_by=user.id,
        updated_by=None,
    )
    db.add(row)
    await db.flush()
    await _create_analysis_revision(db, user=user, analysis=row, change_reason="generated")
    await _create_requirement_audit(
        db,
        user=user,
        project_id=project_id,
        action="GENERATE_ANALYSIS",
        resource_type="requirement_analysis",
        resource_id=str(row.id),
        summary=f"生成需求分析：{doc.title} v{version.version}",
        detail={"docId": str(doc_id), "docVersionId": str(version_id), "aiTaskId": str(ai_job.id)},
    )
    return _to_analysis_detail(row)


async def list_requirement_analyses(db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID, doc_id: uuid.UUID | None, version_id: uuid.UUID | None) -> list[RequirementAnalysisDetail]:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)
    filters = [RequirementAnalysis.tenant_id == user.tenant_id, RequirementAnalysis.project_id == project_id]
    if doc_id is not None:
        filters.append(RequirementAnalysis.doc_id == doc_id)
    if version_id is not None:
        filters.append(RequirementAnalysis.doc_version_id == version_id)
    rows = (
        await db.execute(
            select(RequirementAnalysis)
            .where(*filters)
            .order_by(RequirementAnalysis.updated_at.desc(), RequirementAnalysis.id.desc())
        )
    ).scalars()
    return [_to_analysis_detail(row) for row in rows.all()]


async def get_requirement_analysis(db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID, analysis_id: uuid.UUID) -> RequirementAnalysisDetail:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)
    row = await db.scalar(
        select(RequirementAnalysis).where(
            RequirementAnalysis.id == analysis_id,
            RequirementAnalysis.project_id == project_id,
            RequirementAnalysis.tenant_id == user.tenant_id,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Requirement analysis not found")
    return _to_analysis_detail(row)


async def update_requirement_analysis(db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID, analysis_id: uuid.UUID, payload: RequirementAnalysisUpdateRequest) -> RequirementAnalysisDetail:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)
    row = await db.scalar(
        select(RequirementAnalysis).where(
            RequirementAnalysis.id == analysis_id,
            RequirementAnalysis.project_id == project_id,
            RequirementAnalysis.tenant_id == user.tenant_id,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Requirement analysis not found")
    if payload.status is not None:
        row.status = normalize_analysis_status(payload.status)
    if payload.summary is not None:
        row.summary = payload.summary
    if payload.riskLevel is not None:
        row.risk_level = normalize_risk_level(payload.riskLevel)
    if payload.coverageScore is not None:
        row.coverage_score = payload.coverageScore
    if payload.analysis is not None:
        row.analysis_json = _normalize_analysis_payload(payload.analysis)
    row.updated_by = user.id
    await db.flush()
    await _create_analysis_revision(db, user=user, analysis=row, change_reason="manual_update")
    await _create_requirement_audit(
        db,
        user=user,
        project_id=project_id,
        action="UPDATE_ANALYSIS",
        resource_type="requirement_analysis",
        resource_id=str(row.id),
        summary="人工更新需求分析",
        detail={"status": row.status, "riskLevel": row.risk_level, "coverageScore": float(row.coverage_score) if row.coverage_score is not None else None},
    )
    return _to_analysis_detail(row)


async def list_requirement_analysis_revisions(db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID, analysis_id: uuid.UUID) -> list[RequirementAnalysisRevisionDetail]:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)
    exists = await db.scalar(
        select(RequirementAnalysis.id).where(
            RequirementAnalysis.id == analysis_id,
            RequirementAnalysis.project_id == project_id,
            RequirementAnalysis.tenant_id == user.tenant_id,
        )
    )
    if exists is None:
        raise HTTPException(status_code=404, detail="Requirement analysis not found")
    rows = (
        await db.execute(
            select(RequirementAnalysisRevision)
            .where(
                RequirementAnalysisRevision.analysis_id == analysis_id,
                RequirementAnalysisRevision.project_id == project_id,
                RequirementAnalysisRevision.tenant_id == user.tenant_id,
            )
            .order_by(RequirementAnalysisRevision.revision_no.desc(), RequirementAnalysisRevision.id.desc())
        )
    ).scalars().all()
    return [_to_analysis_revision_detail(row) for row in rows]


async def rollback_requirement_analysis_revision(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    analysis_id: uuid.UUID,
    revision_id: uuid.UUID,
) -> RequirementAnalysisDetail:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)
    analysis = await db.scalar(
        select(RequirementAnalysis).where(
            RequirementAnalysis.id == analysis_id,
            RequirementAnalysis.project_id == project_id,
            RequirementAnalysis.tenant_id == user.tenant_id,
        )
    )
    if analysis is None:
        raise HTTPException(status_code=404, detail="Requirement analysis not found")
    revision = await db.scalar(
        select(RequirementAnalysisRevision).where(
            RequirementAnalysisRevision.id == revision_id,
            RequirementAnalysisRevision.analysis_id == analysis_id,
            RequirementAnalysisRevision.project_id == project_id,
            RequirementAnalysisRevision.tenant_id == user.tenant_id,
        )
    )
    if revision is None:
        raise HTTPException(status_code=404, detail="Requirement analysis revision not found")
    analysis.summary = revision.summary
    analysis.risk_level = revision.risk_level
    analysis.coverage_score = revision.coverage_score
    analysis.analysis_json = _normalize_analysis_payload(revision.analysis_json)
    analysis.updated_by = user.id
    await db.flush()
    await _create_analysis_revision(
        db,
        user=user,
        analysis=analysis,
        change_reason=f"rollback_to_{revision.revision_no}",
    )
    await _create_requirement_audit(
        db,
        user=user,
        project_id=project_id,
        action="ROLLBACK_ANALYSIS",
        resource_type="requirement_analysis",
        resource_id=str(analysis.id),
        summary=f"回滚需求分析到修订 {revision.revision_no}",
        detail={"revisionId": str(revision.id), "revisionNo": revision.revision_no},
    )
    return _to_analysis_detail(analysis)


async def rollback_requirement_doc_version(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    doc_id: uuid.UUID,
    version_id: uuid.UUID,
) -> RequirementDoc:
    """Rollback a requirement doc to point to a previous version as current."""
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)
    doc = await db.scalar(
        select(RequirementDoc).where(
            RequirementDoc.id == doc_id,
            RequirementDoc.project_id == project_id,
            RequirementDoc.tenant_id == user.tenant_id,
        )
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    version = await db.scalar(
        select(RequirementDocVersion).where(
            RequirementDocVersion.id == version_id,
            RequirementDocVersion.doc_id == doc_id,
            RequirementDocVersion.project_id == project_id,
            RequirementDocVersion.tenant_id == user.tenant_id,
        )
    )
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    old_version_id = doc.current_version_id
    doc.current_version_id = version.id
    await db.flush()
    await _create_requirement_audit(
        db,
        user=user,
        project_id=project_id,
        action="ROLLBACK_DOC_VERSION",
        resource_type="requirement_doc",
        resource_id=str(doc.id),
        summary=f"回滚文档「{doc.title}」到版本 v{version.version}",
        detail={
            "docId": str(doc_id),
            "fromVersionId": str(old_version_id) if old_version_id else None,
            "toVersionId": str(version_id),
            "toVersion": version.version,
        },
    )
    return doc


def normalize_analysis_test_points_payload(payload: object) -> list[dict]:
    raw = payload if isinstance(payload, dict) else {}
    test_points = raw.get("testPoints") if isinstance(raw, dict) else None
    if not isinstance(test_points, list):
        return []
    out: list[dict] = []
    for idx, item in enumerate(test_points):
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        if not title:
            continue
        out.append(
            {
                "title": title[:255],
                "description": str(item.get("description") or "").strip() or None,
                "scenarioType": normalize_scenario_type(str(item.get("scenarioType") or "POSITIVE")),
                "priority": str(item.get("priority") or "P2").strip().upper() or "P2",
                "riskLevel": normalize_risk_level(str(item.get("riskLevel") or "MEDIUM")),
                "sourcePath": str(item.get("sourcePath") or f"analysis.testPoints[{idx}]").strip(),
                "aiMeta": item.get("aiMeta") if isinstance(item.get("aiMeta"), dict) else {},
            }
        )
    return out


def _to_test_point_detail(row: RequirementTestPoint) -> RequirementTestPointDetail:
    return RequirementTestPointDetail(
        id=str(row.id),
        projectId=str(row.project_id),
        analysisId=str(row.analysis_id),
        title=row.title,
        description=row.description,
        scenarioType=row.scenario_type,
        priority=row.priority,
        riskLevel=row.risk_level,
        sourcePath=row.source_path,
        status=row.status,
        aiMeta=dict(row.ai_meta_json or {}),
        createdBy=str(row.created_by),
        updatedBy=str(row.updated_by) if row.updated_by else None,
        createdAt=to_unix_ts(row.created_at),
        updatedAt=to_unix_ts(row.updated_at),
    )


def _to_case_draft_detail(row: GeneratedCaseDraft) -> GeneratedCaseDraftDetail:
    return GeneratedCaseDraftDetail(
        id=str(row.id),
        projectId=str(row.project_id),
        analysisId=str(row.analysis_id),
        testPointId=str(row.test_point_id) if row.test_point_id else None,
        title=row.title,
        type=row.type,
        priority=row.priority,
        preconditions=row.preconditions,
        steps=list(row.steps_json or []),
        expectedResults=list(row.expected_results_json or []),
        testData=dict(row.test_data_json or {}),
        status=row.status,
        confidence=float(row.confidence) if row.confidence is not None else None,
        aiMeta=dict(row.ai_meta_json or {}),
        createdBy=str(row.created_by),
        reviewedBy=str(row.reviewed_by) if row.reviewed_by else None,
        createdAt=to_unix_ts(row.created_at),
        updatedAt=to_unix_ts(row.updated_at),
    )


def _to_case_link_detail(row: RequirementCaseLink, testcase_title: str | None = None) -> RequirementCaseLinkDetail:
    return RequirementCaseLinkDetail(
        id=str(row.id),
        projectId=str(row.project_id),
        docId=str(row.doc_id),
        docVersionId=str(row.doc_version_id),
        analysisId=str(row.analysis_id),
        testPointId=str(row.test_point_id) if row.test_point_id else None,
        caseDraftId=str(row.case_draft_id),
        testcaseId=str(row.testcase_id),
        testcaseTitle=testcase_title,
        linkType=row.link_type,
        confidence=float(row.confidence) if row.confidence is not None else None,
        createdBy=str(row.created_by),
        createdAt=to_unix_ts(row.created_at),
    )


def _should_create_case_draft(test_point_id: uuid.UUID | None, existing_test_point_ids: set[uuid.UUID]) -> bool:
    return test_point_id is None or test_point_id not in existing_test_point_ids


def _is_committable_case_draft_status(status: str) -> bool:
    return str(status or "").strip().upper() == "PENDING"


async def sync_requirement_test_points(db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID, analysis_id: uuid.UUID) -> list[RequirementTestPointDetail]:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)
    analysis = await db.scalar(select(RequirementAnalysis).where(RequirementAnalysis.id == analysis_id, RequirementAnalysis.project_id == project_id, RequirementAnalysis.tenant_id == user.tenant_id))
    if analysis is None:
        raise HTTPException(status_code=404, detail="Requirement analysis not found")
    points = normalize_analysis_test_points_payload(analysis.analysis_json)
    await db.execute(delete(RequirementTestPoint).where(RequirementTestPoint.analysis_id == analysis_id, RequirementTestPoint.project_id == project_id, RequirementTestPoint.tenant_id == user.tenant_id))
    for item in points:
        db.add(
            RequirementTestPoint(
                tenant_id=user.tenant_id,
                project_id=project_id,
                analysis_id=analysis_id,
                title=item["title"],
                description=item["description"],
                scenario_type=item["scenarioType"],
                priority=item["priority"],
                risk_level=item["riskLevel"],
                source_path=item["sourcePath"],
                status="DRAFT",
                ai_meta_json=item["aiMeta"],
                created_by=user.id,
                updated_by=None,
            )
        )
    await db.flush()
    rows = (await db.execute(select(RequirementTestPoint).where(RequirementTestPoint.analysis_id == analysis_id, RequirementTestPoint.project_id == project_id, RequirementTestPoint.tenant_id == user.tenant_id).order_by(RequirementTestPoint.created_at.asc()))).scalars().all()
    details = [_to_test_point_detail(x) for x in rows]
    await _create_requirement_audit(
        db,
        user=user,
        project_id=project_id,
        action="SYNC_TEST_POINTS",
        resource_type="requirement_analysis",
        resource_id=str(analysis_id),
        summary=f"同步需求测试点：{len(details)} 条",
        detail={"testPointCount": len(details)},
    )
    return details


async def list_requirement_test_points(db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID, analysis_id: uuid.UUID) -> list[RequirementTestPointDetail]:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)
    rows = (await db.execute(select(RequirementTestPoint).where(RequirementTestPoint.analysis_id == analysis_id, RequirementTestPoint.project_id == project_id, RequirementTestPoint.tenant_id == user.tenant_id).order_by(RequirementTestPoint.created_at.asc()))).scalars().all()
    return [_to_test_point_detail(x) for x in rows]


async def update_requirement_test_point(db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID, test_point_id: uuid.UUID, payload: RequirementTestPointUpdateRequest) -> RequirementTestPointDetail:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)
    row = await db.scalar(select(RequirementTestPoint).where(RequirementTestPoint.id == test_point_id, RequirementTestPoint.project_id == project_id, RequirementTestPoint.tenant_id == user.tenant_id))
    if row is None:
        raise HTTPException(status_code=404, detail="Requirement test point not found")
    if payload.title is not None:
        row.title = payload.title.strip()
    if payload.description is not None:
        row.description = payload.description
    if payload.scenarioType is not None:
        row.scenario_type = normalize_scenario_type(payload.scenarioType)
    if payload.priority is not None:
        row.priority = payload.priority.strip().upper()
    if payload.riskLevel is not None:
        row.risk_level = normalize_risk_level(payload.riskLevel)
    if payload.status is not None:
        row.status = normalize_test_point_status(payload.status)
    if payload.aiMeta is not None:
        row.ai_meta_json = payload.aiMeta
    row.updated_by = user.id
    await db.flush()
    await _create_requirement_audit(
        db,
        user=user,
        project_id=project_id,
        action="UPDATE_TEST_POINT",
        resource_type="requirement_test_point",
        resource_id=str(row.id),
        summary=f"更新需求测试点：{row.title}",
        detail={"analysisId": str(row.analysis_id), "status": row.status, "priority": row.priority, "riskLevel": row.risk_level},
    )
    return _to_test_point_detail(row)


async def generate_case_drafts_from_analysis(db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID, analysis_id: uuid.UUID, payload: GenerateCaseDraftsRequest) -> list[GeneratedCaseDraftDetail]:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)
    stmt = select(RequirementTestPoint).where(RequirementTestPoint.analysis_id == analysis_id, RequirementTestPoint.project_id == project_id, RequirementTestPoint.tenant_id == user.tenant_id)
    mode = str(payload.mode or "ACCEPTED_ONLY").strip().upper()
    if payload.testPointIds:
        ids = [uuid.UUID(x) for x in payload.testPointIds]
        stmt = stmt.where(RequirementTestPoint.id.in_(ids))
    elif mode == "ACCEPTED_ONLY":
        stmt = stmt.where(RequirementTestPoint.status == "ACCEPTED")
    points = (await db.execute(stmt.order_by(RequirementTestPoint.created_at.asc()))).scalars().all()
    if payload.forceRegenerate:
        await db.execute(delete(GeneratedCaseDraft).where(GeneratedCaseDraft.analysis_id == analysis_id, GeneratedCaseDraft.project_id == project_id, GeneratedCaseDraft.tenant_id == user.tenant_id))
        existing_test_point_ids: set[uuid.UUID] = set()
    else:
        existing_rows = (
            await db.execute(
                select(GeneratedCaseDraft.test_point_id).where(
                    GeneratedCaseDraft.analysis_id == analysis_id,
                    GeneratedCaseDraft.project_id == project_id,
                    GeneratedCaseDraft.tenant_id == user.tenant_id,
                    GeneratedCaseDraft.test_point_id.is_not(None),
                )
            )
        ).scalars().all()
        existing_test_point_ids = {x for x in existing_rows if x is not None}
    for p in points:
        if not _should_create_case_draft(p.id, existing_test_point_ids):
            continue
        db.add(
            GeneratedCaseDraft(
                tenant_id=user.tenant_id,
                project_id=project_id,
                analysis_id=analysis_id,
                test_point_id=p.id,
                title=f"验证{p.title}",
                type="API",
                priority=p.priority if p.priority in {"P0", "P1", "P2", "P3"} else "P2",
                preconditions="准备测试数据与权限",
                steps_json=[{"step": f"执行：{p.description or p.title}"}],
                expected_results_json=[f"满足测试点：{p.title}"],
                test_data_json={},
                status="PENDING",
                confidence=0.8,
                ai_meta_json={"source": {"analysisId": str(analysis_id), "testPointId": str(p.id)}},
                created_by=user.id,
                reviewed_by=None,
            )
        )
    await db.flush()
    rows = (await db.execute(select(GeneratedCaseDraft).where(GeneratedCaseDraft.analysis_id == analysis_id, GeneratedCaseDraft.project_id == project_id, GeneratedCaseDraft.tenant_id == user.tenant_id).order_by(GeneratedCaseDraft.created_at.asc()))).scalars().all()
    details = [_to_case_draft_detail(x) for x in rows]
    await _create_requirement_audit(
        db,
        user=user,
        project_id=project_id,
        action="GENERATE_CASE_DRAFTS",
        resource_type="requirement_analysis",
        resource_id=str(analysis_id),
        summary=f"生成用例草稿：{len(details)} 条",
        detail={"caseDraftCount": len(details), "mode": mode, "forceRegenerate": payload.forceRegenerate},
    )
    return details


async def list_generated_case_drafts(db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID, analysis_id: uuid.UUID) -> list[GeneratedCaseDraftDetail]:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)
    rows = (await db.execute(select(GeneratedCaseDraft).where(GeneratedCaseDraft.analysis_id == analysis_id, GeneratedCaseDraft.project_id == project_id, GeneratedCaseDraft.tenant_id == user.tenant_id).order_by(GeneratedCaseDraft.created_at.asc()))).scalars().all()
    return [_to_case_draft_detail(x) for x in rows]


async def list_requirement_case_links(db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID, analysis_id: uuid.UUID) -> list[RequirementCaseLinkDetail]:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)
    rows = (
        await db.execute(
            select(RequirementCaseLink, TestCase.title)
            .outerjoin(
                TestCase,
                (TestCase.id == RequirementCaseLink.testcase_id)
                & (TestCase.tenant_id == RequirementCaseLink.tenant_id)
                & (TestCase.project_id == RequirementCaseLink.project_id),
            )
            .where(
                RequirementCaseLink.tenant_id == user.tenant_id,
                RequirementCaseLink.project_id == project_id,
                RequirementCaseLink.analysis_id == analysis_id,
            )
            .order_by(RequirementCaseLink.created_at.desc(), RequirementCaseLink.id.desc())
        )
    ).all()
    return [_to_case_link_detail(link, testcase_title=title) for link, title in rows]


async def bulk_approve_case_drafts(db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID, payload: BulkApproveCaseDraftsRequest) -> BulkApproveCaseDraftsResult:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)
    ids = [uuid.UUID(x) for x in payload.draftIds]
    drafts = (await db.execute(select(GeneratedCaseDraft).where(GeneratedCaseDraft.id.in_(ids), GeneratedCaseDraft.project_id == project_id, GeneratedCaseDraft.tenant_id == user.tenant_id))).scalars().all()
    analysis_ids = {d.analysis_id for d in drafts}
    analyses = (
        await db.execute(
            select(RequirementAnalysis).where(
                RequirementAnalysis.id.in_(analysis_ids),
                RequirementAnalysis.project_id == project_id,
                RequirementAnalysis.tenant_id == user.tenant_id,
            )
        )
    ).scalars().all()
    analysis_map = {a.id: a for a in analyses}
    created_ids: list[str] = []
    approved_count = 0
    for d in drafts:
        if not _is_committable_case_draft_status(d.status):
            continue
        analysis = analysis_map.get(d.analysis_id)
        if analysis is None:
            continue
        tc = TestCase(
            tenant_id=user.tenant_id,
            project_id=project_id,
            title=d.title[:100],
            type=TestCaseType.API if d.type == "API" else TestCaseType.MIX,
            priority=Priority[d.priority] if d.priority in {"P0", "P1", "P2", "P3"} else Priority.P2,
            status=TestCaseStatus.DRAFT,
            content_md="\n".join([str(x.get("step") or "") for x in (d.steps_json or [])]).strip(),
            tags_json=["requirement-draft"],
            feature="RequirementAnalysis",
            story=None,
            api_url=None,
            api_method=None,
            ai_meta_json={
                "source": {
                    "kind": "requirement_case_draft",
                    "analysisId": str(d.analysis_id),
                    "testPointId": str(d.test_point_id) if d.test_point_id else None,
                    "draftId": str(d.id),
                },
                "expectedResults": list(d.expected_results_json or []),
                "testData": dict(d.test_data_json or {}),
            },
            generated_by_ai=True,
            owner_id=None,
            created_by=user.id,
            version=0,
        )
        db.add(tc)
        await db.flush()
        db.add(
            TestCaseVersion(
                tenant_id=user.tenant_id,
                testcase_id=tc.id,
                version=0,
                content_md=tc.content_md,
                created_by=user.id,
            )
        )
        db.add(
            RequirementCaseLink(
                tenant_id=user.tenant_id,
                project_id=project_id,
                doc_id=analysis.doc_id,
                doc_version_id=analysis.doc_version_id,
                analysis_id=d.analysis_id,
                test_point_id=d.test_point_id,
                case_draft_id=d.id,
                testcase_id=tc.id,
                link_type="GENERATED_FROM",
                confidence=d.confidence,
                created_by=user.id,
            )
        )
        d.status = "COMMITTED"
        d.reviewed_by = user.id
        approved_count += 1
        created_ids.append(str(tc.id))
    await db.flush()
    if approved_count > 0:
        await _create_requirement_audit(
            db,
            user=user,
            project_id=project_id,
            action="BULK_APPROVE_CASE_DRAFTS",
            resource_type="generated_case_draft",
            resource_id=",".join(payload.draftIds),
            summary=f"批量审核用例草稿：入库 {approved_count} 条",
            detail={
                "draftIds": list(payload.draftIds),
                "approvedDraftCount": approved_count,
                "createdTestCaseCount": len(created_ids),
                "testCaseIds": created_ids,
            },
        )
    return BulkApproveCaseDraftsResult(
        approvedDraftCount=approved_count,
        createdTestCaseCount=len(created_ids),
        testCaseIds=created_ids,
    )
