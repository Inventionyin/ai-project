from __future__ import annotations

from decimal import Decimal
import uuid

from fastapi import HTTPException
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, to_unix_ts
from app.models.enums import ProjectRole
from app.models.knowledge import KnowledgeRecommendation, KnowledgeRule, KnowledgeTemplate, RetrospectiveRecord
from app.models.project import Project, ProjectMember
from app.models.run import CaseRun, Run
from app.schemas.knowledge import (
    KnowledgeTemplateCreateRequest,
    KnowledgeTemplateDetail,
    KnowledgeRecommendationItem,
    KnowledgeTemplateUpdateRequest,
    RecommendationEvaluateRequest,
    RecommendationEvaluateResponse,
    RetrospectiveRecordCreateRequest,
    RetrospectiveRecordDetail,
    RetrospectiveRecordListItem,
    RetrospectiveRecordUpdateRequest,
)
from app.services.platform_record import create_audit_log

_ALLOWED_SOURCE_TYPES: set[str] = {"PRD", "SPEC", "PROTOTYPE", "DEFECT", "RUN", "OTHER"}
_ALLOWED_STATUSES: set[str] = {"DRAFT", "REVIEWING", "PUBLISHED", "ARCHIVED"}
_ALLOWED_TEMPLATE_STATUSES: set[str] = {"ACTIVE", "INACTIVE", "ARCHIVED"}
_ALLOWED_RECOMMENDATION_STATUSES: set[str] = {"PENDING", "ADOPTED", "REJECTED"}


def _is_admin(user: CurrentUser) -> bool:
    return "Admin" in user.roles or "ADMIN" in user.roles


def _normalize_source_type(value: str) -> str:
    normalized = str(value or "").strip().upper()
    if normalized not in _ALLOWED_SOURCE_TYPES:
        raise HTTPException(status_code=400, detail="invalid_source_type")
    return normalized


def _normalize_status(value: str) -> str:
    normalized = str(value or "").strip().upper()
    if normalized not in _ALLOWED_STATUSES:
        raise HTTPException(status_code=400, detail="invalid_status")
    return normalized


def _normalize_title(value: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise HTTPException(status_code=400, detail="invalid_title")
    return normalized


def _normalize_template_name(value: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise HTTPException(status_code=400, detail="invalid_template_name")
    return normalized


def _normalize_template_category(value: str) -> str:
    normalized = str(value or "").strip().upper()
    if not normalized:
        raise HTTPException(status_code=400, detail="invalid_template_category")
    return normalized[:64]


def _normalize_template_status(value: str) -> str:
    normalized = str(value or "").strip().upper()
    if normalized not in _ALLOWED_TEMPLATE_STATUSES:
        raise HTTPException(status_code=400, detail="invalid_template_status")
    return normalized


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


def _to_retrospective_detail(row: RetrospectiveRecord) -> RetrospectiveRecordDetail:
    return RetrospectiveRecordDetail(
        id=str(row.id),
        projectId=str(row.project_id),
        title=row.title,
        sourceType=row.source_type,
        status=row.status,
        problemSummary=row.problem_summary,
        rootCause=row.root_cause,
        decision=row.decision,
        actionItems=row.action_items,
        createdBy=str(row.created_by),
        updatedBy=str(row.updated_by) if row.updated_by else None,
        createdAt=to_unix_ts(row.created_at),
        updatedAt=to_unix_ts(row.updated_at),
    )


def _to_template_detail(row: KnowledgeTemplate) -> KnowledgeTemplateDetail:
    return KnowledgeTemplateDetail(
        id=str(row.id),
        projectId=str(row.project_id),
        name=row.name,
        category=row.category,
        contentJson=dict(row.content_json or {}),
        status=row.status,
        createdBy=str(row.created_by),
        updatedBy=str(row.updated_by) if row.updated_by else None,
        createdAt=to_unix_ts(row.created_at),
        updatedAt=to_unix_ts(row.updated_at),
    )


def _normalize_target_type(value: str) -> str:
    normalized = str(value or "").strip().upper()
    if not normalized:
        raise HTTPException(status_code=400, detail="invalid_target_type")
    return normalized


def _score_to_float(value: Decimal | float | int | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _condition_matches(
    *,
    trigger_type: str,
    condition: dict[str, object],
    target_type: str,
    target_id: str,
) -> bool:
    normalized_trigger_type = str(trigger_type or "").strip().upper()
    if normalized_trigger_type not in {"", "ANY", target_type}:
        return False

    condition_target_type = condition.get("targetType")
    if condition_target_type is not None and str(condition_target_type).strip().upper() != target_type:
        return False

    condition_target_id = condition.get("targetId")
    if condition_target_id is not None and str(condition_target_id).strip() != target_id:
        return False
    return True


def _score_rule(*, rule: KnowledgeRule, target_type: str, target_id: str) -> float:
    score = float(rule.action_json.get("score") or rule.condition_json.get("score") or 0.5)
    condition = dict(rule.condition_json or {})
    if str(condition.get("targetType", "")).strip().upper() == target_type:
        score += 0.2
    if str(condition.get("targetId", "")).strip() == target_id:
        score += 0.3
    return round(min(score, 1.0), 4)


def _to_recommendation_item(row: KnowledgeRecommendation) -> KnowledgeRecommendationItem:
    return KnowledgeRecommendationItem(
        id=str(row.id),
        content=row.content,
        score=_score_to_float(row.score),
        type=row.recommendation_type,
        status=row.status,
    )


def _normalize_recommendation_status(value: str) -> str:
    normalized = str(value or "").strip().upper()
    if normalized not in _ALLOWED_RECOMMENDATION_STATUSES:
        raise HTTPException(status_code=400, detail="invalid_recommendation_status")
    return normalized


async def _get_retrospective_or_404(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    record_id: uuid.UUID,
) -> RetrospectiveRecord:
    row = await db.scalar(
        select(RetrospectiveRecord).where(
            RetrospectiveRecord.id == record_id,
            RetrospectiveRecord.project_id == project_id,
            RetrospectiveRecord.tenant_id == user.tenant_id,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Retrospective record not found")
    return row


async def create_retrospective_record(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    payload: RetrospectiveRecordCreateRequest,
) -> RetrospectiveRecordDetail:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)

    row = RetrospectiveRecord(
        tenant_id=user.tenant_id,
        project_id=project_id,
        title=_normalize_title(payload.title),
        source_type=_normalize_source_type(payload.sourceType),
        status=_normalize_status(payload.status),
        problem_summary=payload.problemSummary,
        root_cause=payload.rootCause,
        decision=payload.decision,
        action_items=payload.actionItems,
        created_by=user.id,
        updated_by=user.id,
    )
    db.add(row)
    await db.flush()
    await create_audit_log(
        db,
        user=user,
        project_id=project.id,
        module="KNOWLEDGE",
        action="CREATE_RETROSPECTIVE",
        resource_type="retrospective_record",
        resource_id=str(row.id),
        summary=f"Create retrospective: {row.title}",
        detail={"sourceType": row.source_type, "status": row.status},
    )
    return _to_retrospective_detail(row)


async def create_retrospective_draft_from_run(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    run_id: uuid.UUID,
) -> RetrospectiveRecordDetail:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)

    run = await db.scalar(
        select(Run).where(
            Run.id == run_id,
            Run.project_id == project_id,
            Run.tenant_id == user.tenant_id,
        )
    )
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    case_status_rows = (
        await db.execute(
            select(CaseRun.status, func.count())
            .where(
                CaseRun.run_id == run.id,
                CaseRun.tenant_id == user.tenant_id,
            )
            .group_by(CaseRun.status)
        )
    ).all()
    counts = {str(status): int(total) for status, total in case_status_rows}
    passed = counts.get("PASSED", 0)
    failed = counts.get("FAILED", 0)
    skipped = counts.get("SKIPPED", 0)
    total = sum(counts.values())

    title = f"Run {run.id} 复盘草稿"
    problem_summary = f"Run 执行统计：total={total}, passed={passed}, failed={failed}, skipped={skipped}"
    root_cause = "待补充"
    decision = "待补充"
    action_items = "待补充"

    row = RetrospectiveRecord(
        tenant_id=user.tenant_id,
        project_id=project_id,
        title=title,
        source_type="RUN",
        status="DRAFT",
        problem_summary=problem_summary,
        root_cause=root_cause,
        decision=decision,
        action_items=action_items,
        created_by=user.id,
        updated_by=user.id,
    )
    db.add(row)
    await db.flush()
    await create_audit_log(
        db,
        user=user,
        project_id=project.id,
        module="KNOWLEDGE",
        action="CREATE_RETROSPECTIVE_FROM_RUN",
        resource_type="retrospective_record",
        resource_id=str(row.id),
        summary=f"Create retrospective draft from run: {run.id}",
        detail={
            "runId": str(run.id),
            "sourceType": row.source_type,
            "status": row.status,
            "stats": {
                "total": total,
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
            },
        },
    )
    return _to_retrospective_detail(row)


async def list_retrospective_records(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    page: int,
    page_size: int,
    source_type: str | None,
    status: str | None,
) -> tuple[int, list[RetrospectiveRecordListItem]]:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)

    normalized_source_type = _normalize_source_type(source_type) if source_type is not None else None
    normalized_status = _normalize_status(status) if status is not None else None

    base_stmt = select(RetrospectiveRecord).where(
        RetrospectiveRecord.tenant_id == user.tenant_id,
        RetrospectiveRecord.project_id == project_id,
    )
    if normalized_source_type:
        base_stmt = base_stmt.where(RetrospectiveRecord.source_type == normalized_source_type)
    if normalized_status:
        base_stmt = base_stmt.where(RetrospectiveRecord.status == normalized_status)

    total = int((await db.execute(select(func.count()).select_from(base_stmt.subquery()))).scalar_one() or 0)
    rows = (
        await db.execute(
            base_stmt.order_by(desc(RetrospectiveRecord.updated_at), desc(RetrospectiveRecord.id))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()
    return total, [_to_retrospective_detail(row) for row in rows]


async def get_retrospective_record(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    record_id: uuid.UUID,
) -> RetrospectiveRecordDetail:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)
    row = await _get_retrospective_or_404(db, user=user, project_id=project_id, record_id=record_id)
    return _to_retrospective_detail(row)


async def update_retrospective_record(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    record_id: uuid.UUID,
    payload: RetrospectiveRecordUpdateRequest,
) -> RetrospectiveRecordDetail:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)
    row = await _get_retrospective_or_404(db, user=user, project_id=project_id, record_id=record_id)

    if payload.title is not None:
        row.title = _normalize_title(payload.title)
    if payload.sourceType is not None:
        row.source_type = _normalize_source_type(payload.sourceType)
    if payload.status is not None:
        row.status = _normalize_status(payload.status)
    if payload.problemSummary is not None:
        row.problem_summary = payload.problemSummary
    if payload.rootCause is not None:
        row.root_cause = payload.rootCause
    if payload.decision is not None:
        row.decision = payload.decision
    if payload.actionItems is not None:
        row.action_items = payload.actionItems
    row.updated_by = user.id

    await db.flush()
    await create_audit_log(
        db,
        user=user,
        project_id=project.id,
        module="KNOWLEDGE",
        action="UPDATE_RETROSPECTIVE",
        resource_type="retrospective_record",
        resource_id=str(row.id),
        summary=f"Update retrospective: {row.title}",
        detail={"sourceType": row.source_type, "status": row.status},
    )
    return _to_retrospective_detail(row)


async def _get_template_or_404(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    template_id: uuid.UUID,
) -> KnowledgeTemplate:
    row = await db.scalar(
        select(KnowledgeTemplate).where(
            KnowledgeTemplate.id == template_id,
            KnowledgeTemplate.project_id == project_id,
            KnowledgeTemplate.tenant_id == user.tenant_id,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Knowledge template not found")
    return row


async def create_knowledge_template(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    payload: KnowledgeTemplateCreateRequest,
) -> KnowledgeTemplateDetail:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)

    row = KnowledgeTemplate(
        tenant_id=user.tenant_id,
        project_id=project.id,
        name=_normalize_template_name(payload.name),
        category=_normalize_template_category(payload.category),
        content_json=dict(payload.contentJson or {}),
        status=_normalize_template_status(payload.status),
        created_by=user.id,
        updated_by=user.id,
    )
    db.add(row)
    await db.flush()
    await create_audit_log(
        db,
        user=user,
        project_id=project.id,
        module="KNOWLEDGE",
        action="CREATE_TEMPLATE",
        resource_type="knowledge_template",
        resource_id=str(row.id),
        summary=f"Create knowledge template: {row.name}",
        detail={"category": row.category, "status": row.status},
    )
    return _to_template_detail(row)


async def list_knowledge_templates(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    page: int,
    page_size: int,
    category: str | None,
    status: str | None,
) -> tuple[int, list[KnowledgeTemplateDetail]]:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)

    normalized_category = _normalize_template_category(category) if category is not None else None
    normalized_status = _normalize_template_status(status) if status is not None else None

    base_stmt = select(KnowledgeTemplate).where(
        KnowledgeTemplate.tenant_id == user.tenant_id,
        KnowledgeTemplate.project_id == project.id,
    )
    if normalized_category:
        base_stmt = base_stmt.where(KnowledgeTemplate.category == normalized_category)
    if normalized_status:
        base_stmt = base_stmt.where(KnowledgeTemplate.status == normalized_status)

    total = int((await db.execute(select(func.count()).select_from(base_stmt.subquery()))).scalar_one() or 0)
    rows = (
        await db.execute(
            base_stmt.order_by(desc(KnowledgeTemplate.updated_at), desc(KnowledgeTemplate.id))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()
    return total, [_to_template_detail(row) for row in rows]


async def get_knowledge_template(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    template_id: uuid.UUID,
) -> KnowledgeTemplateDetail:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)
    row = await _get_template_or_404(db, user=user, project_id=project.id, template_id=template_id)
    return _to_template_detail(row)


async def update_knowledge_template(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    template_id: uuid.UUID,
    payload: KnowledgeTemplateUpdateRequest,
) -> KnowledgeTemplateDetail:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)
    row = await _get_template_or_404(db, user=user, project_id=project.id, template_id=template_id)

    if payload.name is not None:
        row.name = _normalize_template_name(payload.name)
    if payload.category is not None:
        row.category = _normalize_template_category(payload.category)
    if payload.contentJson is not None:
        row.content_json = dict(payload.contentJson)
    if payload.status is not None:
        row.status = _normalize_template_status(payload.status)
    row.updated_by = user.id

    await db.flush()
    await create_audit_log(
        db,
        user=user,
        project_id=project.id,
        module="KNOWLEDGE",
        action="UPDATE_TEMPLATE",
        resource_type="knowledge_template",
        resource_id=str(row.id),
        summary=f"Update knowledge template: {row.name}",
        detail={"category": row.category, "status": row.status},
    )
    return _to_template_detail(row)


async def evaluate_recommendations(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    payload: RecommendationEvaluateRequest,
) -> RecommendationEvaluateResponse:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)

    target_type = _normalize_target_type(payload.targetType)
    target_id = str(payload.targetId).strip()
    top_k = payload.topK

    rules = (
        await db.execute(
            select(KnowledgeRule).where(
                KnowledgeRule.tenant_id == user.tenant_id,
                KnowledgeRule.project_id == project.id,
                KnowledgeRule.enabled.is_(True),
            )
        )
    ).scalars().all()

    target_retrospective_id: uuid.UUID | None = None
    if target_type == "RETROSPECTIVE":
        try:
            target_retrospective_id = uuid.UUID(target_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="invalid_target_id") from exc

    matched_rows: list[KnowledgeRecommendation] = []
    for rule in rules:
        condition = dict(rule.condition_json or {})
        if not _condition_matches(
            trigger_type=rule.trigger_type,
            condition=condition,
            target_type=target_type,
            target_id=target_id,
        ):
            continue

        action_json = dict(rule.action_json or {})
        recommendation_type = str(action_json.get("type") or "GENERAL").strip().upper() or "GENERAL"
        content = str(action_json.get("content") or f"Rule {rule.name} matched for {target_type}:{target_id}").strip()
        status = str(action_json.get("status") or "PENDING").strip().upper() or "PENDING"
        score = _score_rule(rule=rule, target_type=target_type, target_id=target_id)

        existing = await db.scalar(
            select(KnowledgeRecommendation).where(
                KnowledgeRecommendation.tenant_id == user.tenant_id,
                KnowledgeRecommendation.project_id == project.id,
                KnowledgeRecommendation.retrospective_id == target_retrospective_id,
                KnowledgeRecommendation.recommendation_type == recommendation_type,
                KnowledgeRecommendation.content == content,
            )
        )
        if existing is not None:
            matched_rows.append(existing)
            continue

        row = KnowledgeRecommendation(
            tenant_id=user.tenant_id,
            project_id=project.id,
            retrospective_id=target_retrospective_id,
            recommendation_type=recommendation_type,
            content=content,
            status=status,
            score=score,
            created_by=user.id,
            updated_by=user.id,
        )
        db.add(row)
        await db.flush()
        matched_rows.append(row)

    matched_rows.sort(key=lambda x: (_score_to_float(x.score) or 0.0, str(x.id)), reverse=True)
    return RecommendationEvaluateResponse(
        targetType=target_type,
        targetId=target_id,
        recommendations=[_to_recommendation_item(row) for row in matched_rows[:top_k]],
    )


async def update_recommendation_status(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    recommendation_id: uuid.UUID,
    status: str,
) -> KnowledgeRecommendationItem:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)

    normalized_status = _normalize_recommendation_status(status)
    row = await db.scalar(
        select(KnowledgeRecommendation).where(
            KnowledgeRecommendation.id == recommendation_id,
            KnowledgeRecommendation.project_id == project.id,
            KnowledgeRecommendation.tenant_id == user.tenant_id,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Knowledge recommendation not found")

    row.status = normalized_status
    row.updated_by = user.id
    await db.flush()
    await create_audit_log(
        db,
        user=user,
        project_id=project.id,
        module="KNOWLEDGE",
        action="UPDATE_RECOMMENDATION_STATUS",
        resource_type="knowledge_recommendation",
        resource_id=str(row.id),
        summary=f"Update knowledge recommendation status: {row.id}",
        detail={"status": row.status},
    )
    return _to_recommendation_item(row)
