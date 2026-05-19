from __future__ import annotations

import re
import uuid
from collections import Counter
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, to_unix_ts
from app.models.defect import Defect, DefectEvent
from app.models.enums import ProjectRole
from app.models.project import Project, ProjectMember
from app.services.platform_record import create_audit_log
from app.schemas.defect import (
    DefectClusterItem,
    DefectCreateRequest,
    DefectDetail,
    DefectImportErrorItem,
    DefectImportRequest,
    DefectImportResult,
    DefectListItem,
    DefectRiskHint,
    DefectTransitionRequest,
)

_ALLOWED_STATUSES: set[str] = {"OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"}
_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "OPEN": {"IN_PROGRESS", "CLOSED"},
    "IN_PROGRESS": {"RESOLVED"},
    "RESOLVED": {"CLOSED"},
    "CLOSED": set(),
}
_ALLOWED_SEVERITIES: set[str] = {"P0", "P1", "P2", "P3"}
_CLUSTER_TOKEN_PATTERN = re.compile(r"[^0-9a-z\u4e00-\u9fff]+")
_CLUSTER_STOP_WORDS: set[str] = {
    "a",
    "an",
    "and",
    "are",
    "at",
    "be",
    "bug",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "when",
    "with",
}
_SEVERITY_RISK_WEIGHT: dict[str, float] = {"P0": 5.0, "P1": 3.8, "P2": 2.4, "P3": 1.2}
_STATUS_RISK_WEIGHT: dict[str, float] = {"OPEN": 1.4, "IN_PROGRESS": 1.8}


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


def _normalize_severity(value: str | None) -> str:
    normalized = str(value or "P2").strip().upper()
    if normalized not in _ALLOWED_SEVERITIES:
        raise HTTPException(status_code=400, detail="invalid_severity")
    return normalized


def _normalize_status(value: str) -> str:
    normalized = str(value or "").strip().upper()
    if normalized not in _ALLOWED_STATUSES:
        raise HTTPException(status_code=400, detail="invalid_status")
    return normalized


def _to_defect_detail(row: Defect) -> DefectDetail:
    return DefectDetail(
        id=str(row.id),
        projectId=str(row.project_id),
        title=row.title,
        description=row.description,
        status=row.status,
        severity=row.severity,
        assigneeId=str(row.assignee_id) if row.assignee_id else None,
        reporterId=str(row.reporter_id),
        createdBy=str(row.created_by),
        createdAt=to_unix_ts(row.created_at),
        updatedAt=to_unix_ts(row.updated_at),
    )


async def _get_defect_or_404(db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID, defect_id: uuid.UUID) -> Defect:
    row = await db.scalar(
        select(Defect).where(
            Defect.id == defect_id,
            Defect.project_id == project_id,
            Defect.tenant_id == user.tenant_id,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Defect not found")
    return row


async def _append_defect_event(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    defect: Defect,
    event_type: str,
    from_status: str | None = None,
    to_status: str | None = None,
    from_assignee_id: uuid.UUID | None = None,
    to_assignee_id: uuid.UUID | None = None,
    note: str | None = None,
    detail_json: dict | None = None,
) -> None:
    db.add(
        DefectEvent(
            tenant_id=user.tenant_id,
            project_id=project_id,
            defect_id=defect.id,
            event_type=event_type,
            from_status=from_status,
            to_status=to_status,
            from_assignee_id=from_assignee_id,
            to_assignee_id=to_assignee_id,
            note=note,
            detail_json=detail_json or {},
            created_by=user.id,
        )
    )
    await db.flush()


def _parse_optional_uuid_ref(value: str | None, *, field_name: str) -> str | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return str(uuid.UUID(raw))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"invalid_{field_name}") from exc


def _normalize_cluster_tokens(title: str, description: str | None) -> list[str]:
    merged = f"{title or ''} {description or ''}".lower()
    normalized = _CLUSTER_TOKEN_PATTERN.sub(" ", merged)
    tokens: list[str] = []
    seen: set[str] = set()
    for token in normalized.split():
        if token in _CLUSTER_STOP_WORDS:
            continue
        if token.isascii() and len(token) <= 1:
            continue
        if token in seen:
            continue
        seen.add(token)
        tokens.append(token)
    return tokens[:8]


def _build_cluster_key(tokens: list[str]) -> str:
    if not tokens:
        return "misc"
    return "-".join(tokens[:3])[:128]


def _guess_root_cause_hint(tokens: list[str]) -> str:
    merged = " ".join(tokens)
    if any(keyword in merged for keyword in ("timeout", "network", "dns", "socket", "超时", "网络")):
        return "可能是网络或依赖服务不稳定"
    if any(keyword in merged for keyword in ("auth", "permission", "token", "鉴权", "权限")):
        return "可能是权限或鉴权配置问题"
    if any(keyword in merged for keyword in ("null", "none", "npe", "空指针")):
        return "可能是空值处理缺失"
    if any(keyword in merged for keyword in ("assert", "expect", "校验", "断言")):
        return "可能是断言或业务规则变更引起"
    return "疑似同类缺陷，建议结合最近改动排查"


def _estimate_cluster_confidence(*, count: int, token_count: int) -> float:
    score = 0.35 + min(0.4, 0.12 * max(count - 1, 0))
    if token_count >= 3:
        score += 0.2
    elif token_count == 2:
        score += 0.12
    elif token_count == 1:
        score += 0.06
    return round(min(score, 0.98), 2)


def _recency_weight(updated_at: datetime, *, now: datetime) -> float:
    age_days = max((now - updated_at).total_seconds() / 86400, 0)
    if age_days <= 1:
        return 2.6
    if age_days <= 3:
        return 1.8
    if age_days <= 7:
        return 1.0
    if age_days <= 14:
        return 0.5
    return 0.2


def _risk_hint_text(*, severity: str, status: str, updated_at: datetime, now: datetime) -> str:
    if severity == "P0":
        return "P0 缺陷处于未关闭状态，建议优先回归"
    if status == "IN_PROGRESS":
        return "缺陷处理中且尚未收敛，建议回归关键链路"
    if (now - updated_at).total_seconds() <= 3 * 86400:
        return "近期活跃缺陷，建议纳入本轮回归"
    return "持续未关闭缺陷，建议保持回归覆盖"


async def create_defect(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    payload: DefectCreateRequest,
) -> DefectDetail:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)
    row = Defect(
        tenant_id=user.tenant_id,
        project_id=project_id,
        title=payload.title.strip(),
        description=payload.description,
        status="OPEN",
        severity=_normalize_severity(payload.severity),
        assignee_id=None,
        reporter_id=user.id,
        created_by=user.id,
    )
    db.add(row)
    await db.flush()
    await create_audit_log(
        db, user=user, project_id=project_id,
        module="defect", action="CREATE_DEFECT",
        resource_type="defect", resource_id=str(row.id),
        summary=row.title,
        detail={"severity": row.severity, "status": row.status},
    )
    return _to_defect_detail(row)


async def import_defects(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    payload: DefectImportRequest,
) -> DefectImportResult:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)
    total = len(payload.items)
    success = 0
    errors: list[DefectImportErrorItem] = []
    for index, item in enumerate(payload.items):
        try:
            title = item.title.strip()
            if not title:
                raise HTTPException(status_code=400, detail="invalid_title")
            severity = _normalize_severity(item.severity)
            description = item.description.strip() if item.description else None
            if description == "":
                description = None
            row = Defect(
                tenant_id=user.tenant_id,
                project_id=project_id,
                title=title,
                description=description,
                status="OPEN",
                severity=severity,
                assignee_id=None,
                reporter_id=user.id,
                created_by=user.id,
            )
            db.add(row)
            await db.flush()
            detail_json: dict[str, str] = {}
            run_id = _parse_optional_uuid_ref(item.runId, field_name="run_id")
            case_run_id = _parse_optional_uuid_ref(item.caseRunId, field_name="case_run_id")
            testcase_id = _parse_optional_uuid_ref(item.testcaseId, field_name="testcase_id")
            if run_id:
                detail_json["runId"] = run_id
            if case_run_id:
                detail_json["caseRunId"] = case_run_id
            if testcase_id:
                detail_json["testcaseId"] = testcase_id
            source = item.source.strip() if item.source else ""
            if source:
                detail_json["source"] = source
            await _append_defect_event(
                db,
                user=user,
                project_id=project_id,
                defect=row,
                event_type="IMPORTED",
                note="Imported from structured JSON",
                detail_json=detail_json,
            )
            success += 1
        except HTTPException as exc:
            errors.append(DefectImportErrorItem(index=index, title=item.title, error=str(exc.detail)))
    return DefectImportResult(total=total, success=success, failed=total - success, errors=errors)


async def list_defects(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    page: int,
    page_size: int,
    status: str | None = None,
    q: str | None = None,
) -> tuple[int, list[DefectListItem]]:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)
    base_stmt = select(Defect).where(Defect.tenant_id == user.tenant_id, Defect.project_id == project_id)
    if status:
        normalized_status = _normalize_status(status)
        base_stmt = base_stmt.where(Defect.status == normalized_status)
    keyword = str(q or "").strip()
    if keyword:
        pattern = f"%{keyword}%"
        base_stmt = base_stmt.where((Defect.title.ilike(pattern)) | (Defect.description.ilike(pattern)))
    total = int((await db.execute(select(func.count()).select_from(base_stmt.subquery()))).scalar_one() or 0)
    rows = (
        await db.execute(
            base_stmt.order_by(desc(Defect.updated_at), desc(Defect.id)).offset((page - 1) * page_size).limit(page_size)
        )
    ).scalars().all()
    return total, [_to_defect_detail(row) for row in rows]


async def get_defect(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    defect_id: uuid.UUID,
) -> DefectDetail:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)
    row = await _get_defect_or_404(db, user=user, project_id=project_id, defect_id=defect_id)
    return _to_defect_detail(row)


async def assign_defect(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    defect_id: uuid.UUID,
    assignee_id: uuid.UUID,
    note: str | None = None,
) -> DefectDetail:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)
    row = await _get_defect_or_404(db, user=user, project_id=project_id, defect_id=defect_id)
    previous_assignee_id = row.assignee_id
    row.assignee_id = assignee_id
    await db.flush()
    await _append_defect_event(
        db,
        user=user,
        project_id=project_id,
        defect=row,
        event_type="ASSIGNED",
        from_assignee_id=previous_assignee_id,
        to_assignee_id=assignee_id,
        note=note,
    )
    await create_audit_log(
        db, user=user, project_id=project_id,
        module="defect", action="ASSIGN_DEFECT",
        resource_type="defect", resource_id=str(row.id),
        summary=row.title,
        detail={"from_assignee": str(previous_assignee_id) if previous_assignee_id else None, "to_assignee": str(assignee_id)},
    )
    return _to_defect_detail(row)


async def transition_defect(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    defect_id: uuid.UUID,
    payload: DefectTransitionRequest,
) -> DefectDetail:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)
    row = await _get_defect_or_404(db, user=user, project_id=project_id, defect_id=defect_id)
    current_status = _normalize_status(row.status)
    target_status = _normalize_status(payload.toStatus)
    if target_status not in _ALLOWED_TRANSITIONS.get(current_status, set()):
        raise HTTPException(status_code=400, detail="invalid_status_transition")
    row.status = target_status
    await db.flush()
    await _append_defect_event(
        db,
        user=user,
        project_id=project_id,
        defect=row,
        event_type="STATUS_TRANSITION",
        from_status=current_status,
        to_status=target_status,
        note=payload.note,
    )
    await create_audit_log(
        db, user=user, project_id=project_id,
        module="defect", action="TRANSITION_DEFECT",
        resource_type="defect", resource_id=str(row.id),
        summary=row.title,
        detail={"from_status": current_status, "to_status": target_status},
    )
    return _to_defect_detail(row)


async def list_defect_clusters(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
) -> list[DefectClusterItem]:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)
    rows = (
        await db.execute(
            select(Defect.title, Defect.description).where(
                Defect.tenant_id == user.tenant_id,
                Defect.project_id == project_id,
            )
        )
    ).all()
    clusters: dict[str, dict[str, object]] = {}
    for title, description in rows:
        tokens = _normalize_cluster_tokens(title, description)
        cluster_key = _build_cluster_key(tokens)
        bucket = clusters.setdefault(
            cluster_key,
            {"count": 0, "sample_titles": [], "token_counter": Counter()},
        )
        bucket["count"] = int(bucket["count"]) + 1
        sample_titles = bucket["sample_titles"]
        if isinstance(sample_titles, list) and len(sample_titles) < 3 and title not in sample_titles:
            sample_titles.append(title)
        token_counter = bucket["token_counter"]
        if isinstance(token_counter, Counter):
            token_counter.update(tokens[:6])
    results: list[DefectClusterItem] = []
    for cluster_key, bucket in clusters.items():
        token_counter = bucket["token_counter"]
        top_tokens = [token for token, _ in token_counter.most_common(3)] if isinstance(token_counter, Counter) else []
        results.append(
            DefectClusterItem(
                clusterKey=cluster_key,
                count=int(bucket["count"]),
                sampleTitles=list(bucket["sample_titles"]) if isinstance(bucket["sample_titles"], list) else [],
                rootCauseHint=_guess_root_cause_hint(top_tokens),
                confidence=_estimate_cluster_confidence(count=int(bucket["count"]), token_count=len(top_tokens)),
            )
        )
    results.sort(key=lambda item: (-item.count, item.clusterKey))
    return results


async def list_defect_risk_hints(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
) -> list[DefectRiskHint]:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)
    rows = (
        await db.execute(
            select(Defect).where(
                Defect.tenant_id == user.tenant_id,
                Defect.project_id == project_id,
                Defect.status.in_(("OPEN", "IN_PROGRESS")),
            )
        )
    ).scalars().all()
    now = datetime.now(timezone.utc)
    hints: list[DefectRiskHint] = []
    for row in rows:
        severity = str(row.severity or "P3").strip().upper()
        status = str(row.status or "").strip().upper()
        severity_weight = _SEVERITY_RISK_WEIGHT.get(severity, 1.0)
        status_weight = _STATUS_RISK_WEIGHT.get(status, 0.0)
        updated_at = row.updated_at
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)
        score = round(severity_weight + status_weight + _recency_weight(updated_at, now=now), 2)
        if score < 4.0:
            continue
        hints.append(
            DefectRiskHint(
                defectId=str(row.id),
                title=row.title,
                status=status,
                severity=severity,
                updatedAt=to_unix_ts(row.updated_at),
                riskScore=score,
                hint=_risk_hint_text(severity=severity, status=status, updated_at=updated_at, now=now),
            )
        )
    hints.sort(key=lambda item: (-item.riskScore, -item.updatedAt))
    return hints
