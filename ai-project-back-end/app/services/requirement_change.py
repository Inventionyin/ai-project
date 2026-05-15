from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, to_unix_ts
from app.models.enums import ProjectRole
from app.models.project import Project, ProjectMember
from app.models.requirement import (
    RequirementCaseLink,
    RequirementChangeItem,
    RequirementChangeSet,
    RequirementDoc,
    RequirementDocVersion,
    RequirementRegressionCase,
    RequirementRegressionSet,
)
from app.models.testcase import TestCase
from app.schemas.requirement_change import (
    RequirementChangeItemDetail,
    RequirementChangeSetCreateRequest,
    RequirementChangeSetDetail,
    RequirementRegressionCaseDetail,
    RequirementRegressionSetDetail,
)
from app.services.platform_record import create_ai_job_record


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


def _text_chunks(version: RequirementDocVersion) -> list[str]:
    raw = "\n".join(
        part
        for part in [
            version.change_summary or "",
            version.effective_scope or "",
            version.parsed_text_preview or "",
            version.file_name or "",
        ]
        if part
    )
    chunks = []
    seen: set[str] = set()
    for line in raw.replace("\r\n", "\n").split("\n"):
        value = " ".join(line.strip().split())
        if len(value) < 4:
            continue
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        chunks.append(value[:240])
    return chunks


def _build_change_item_payloads(baseline: RequirementDocVersion, target: RequirementDocVersion) -> list[dict[str, str]]:
    baseline_chunks = set(_text_chunks(baseline))
    target_chunks = set(_text_chunks(target))
    added = sorted(target_chunks - baseline_chunks)
    removed = sorted(baseline_chunks - target_chunks)
    payloads: list[dict[str, str]] = []
    for idx, text in enumerate(added[:20], start=1):
        payloads.append(
            {
                "change_type": "ADDED",
                "title": f"新增需求点 {idx}",
                "description": text,
                "impact_level": "MEDIUM",
                "source_path": f"target:v{target.version}:{idx}",
            }
        )
    for idx, text in enumerate(removed[:20], start=1):
        payloads.append(
            {
                "change_type": "REMOVED",
                "title": f"移除需求点 {idx}",
                "description": text,
                "impact_level": "HIGH",
                "source_path": f"baseline:v{baseline.version}:{idx}",
            }
        )
    return payloads


def _to_change_item_detail(row: RequirementChangeItem) -> RequirementChangeItemDetail:
    return RequirementChangeItemDetail(
        id=str(row.id),
        changeType=row.change_type,
        title=row.title,
        description=row.description,
        impactLevel=row.impact_level,
        sourcePath=row.source_path,
    )


def _to_change_set_detail(row: RequirementChangeSet, items: list[RequirementChangeItem]) -> RequirementChangeSetDetail:
    return RequirementChangeSetDetail(
        id=str(row.id),
        projectId=str(row.project_id),
        docId=str(row.doc_id),
        baselineVersionId=str(row.baseline_version_id),
        targetVersionId=str(row.target_version_id),
        summary=row.summary,
        status=row.status,
        items=[_to_change_item_detail(item) for item in items],
        createdBy=str(row.created_by),
        createdAt=to_unix_ts(row.created_at),
        updatedAt=to_unix_ts(row.updated_at),
    )


def _to_regression_case_detail(row: RequirementRegressionCase, testcase_title: str | None) -> RequirementRegressionCaseDetail:
    return RequirementRegressionCaseDetail(
        id=str(row.id),
        testcaseId=str(row.testcase_id),
        testcaseTitle=testcase_title,
        priority=row.priority,
        reason=row.reason,
        sourcePaths=list(row.source_paths_json or []),
    )


def _to_regression_set_detail(
    row: RequirementRegressionSet,
    cases: list[tuple[RequirementRegressionCase, str | None]],
) -> RequirementRegressionSetDetail:
    return RequirementRegressionSetDetail(
        id=str(row.id),
        projectId=str(row.project_id),
        changeSetId=str(row.change_set_id),
        summary=row.summary,
        status=row.status,
        cases=[_to_regression_case_detail(case, title) for case, title in cases],
        createdBy=str(row.created_by),
        createdAt=to_unix_ts(row.created_at),
        updatedAt=to_unix_ts(row.updated_at),
    )


async def _get_doc(db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID, doc_id: uuid.UUID) -> RequirementDoc:
    doc = await db.scalar(
        select(RequirementDoc).where(
            RequirementDoc.id == doc_id,
            RequirementDoc.project_id == project_id,
            RequirementDoc.tenant_id == user.tenant_id,
        )
    )
    if doc is None:
        raise HTTPException(status_code=404, detail="Requirement doc not found")
    return doc


async def _get_version(db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID, doc_id: uuid.UUID, version_id: uuid.UUID) -> RequirementDocVersion:
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
    return version


async def create_requirement_change_set(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    doc_id: uuid.UUID,
    payload: RequirementChangeSetCreateRequest,
) -> RequirementChangeSetDetail:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)
    await _get_doc(db, user=user, project_id=project_id, doc_id=doc_id)
    baseline = await _get_version(db, user=user, project_id=project_id, doc_id=doc_id, version_id=uuid.UUID(payload.baselineVersionId))
    target = await _get_version(db, user=user, project_id=project_id, doc_id=doc_id, version_id=uuid.UUID(payload.targetVersionId))
    if baseline.id == target.id:
        raise HTTPException(status_code=400, detail="baseline_and_target_must_differ")
    item_payloads = _build_change_item_payloads(baseline, target)
    row = RequirementChangeSet(
        tenant_id=user.tenant_id,
        project_id=project_id,
        doc_id=doc_id,
        baseline_version_id=baseline.id,
        target_version_id=target.id,
        summary=f"检测到 {len(item_payloads)} 个需求变更点",
        status="GENERATED",
        created_by=user.id,
    )
    db.add(row)
    await db.flush()
    items = [
        RequirementChangeItem(
            tenant_id=user.tenant_id,
            project_id=project_id,
            change_set_id=row.id,
            change_type=item["change_type"],
            title=item["title"],
            description=item["description"],
            impact_level=item["impact_level"],
            source_path=item["source_path"],
            created_by=user.id,
        )
        for item in item_payloads
    ]
    for item in items:
        db.add(item)
    await db.flush()
    await create_ai_job_record(
        db,
        user=user,
        project_id=project_id,
        job_type="REQUIREMENT_CHANGE_ANALYSIS",
        status="SUCCEEDED",
        trigger_source="REQUIREMENTS",
        summary=row.summary,
        detail={"docId": str(doc_id), "changeSetId": str(row.id)},
    )
    return _to_change_set_detail(row, items)


async def list_requirement_change_sets(db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID, doc_id: uuid.UUID) -> list[RequirementChangeSetDetail]:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)
    await _get_doc(db, user=user, project_id=project_id, doc_id=doc_id)
    rows = (
        await db.execute(
            select(RequirementChangeSet)
            .where(
                RequirementChangeSet.tenant_id == user.tenant_id,
                RequirementChangeSet.project_id == project_id,
                RequirementChangeSet.doc_id == doc_id,
            )
            .order_by(RequirementChangeSet.created_at.desc(), RequirementChangeSet.id.desc())
        )
    ).scalars().all()
    result = []
    for row in rows:
        items = (
            await db.execute(
                select(RequirementChangeItem)
                .where(RequirementChangeItem.change_set_id == row.id, RequirementChangeItem.tenant_id == user.tenant_id)
                .order_by(RequirementChangeItem.created_at.asc(), RequirementChangeItem.id.asc())
            )
        ).scalars().all()
        result.append(_to_change_set_detail(row, items))
    return result


async def get_requirement_change_set(db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID, change_set_id: uuid.UUID) -> RequirementChangeSetDetail:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)
    row = await db.scalar(
        select(RequirementChangeSet).where(
            RequirementChangeSet.id == change_set_id,
            RequirementChangeSet.project_id == project_id,
            RequirementChangeSet.tenant_id == user.tenant_id,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Requirement change set not found")
    items = (
        await db.execute(
            select(RequirementChangeItem)
            .where(RequirementChangeItem.change_set_id == row.id, RequirementChangeItem.tenant_id == user.tenant_id)
            .order_by(RequirementChangeItem.created_at.asc(), RequirementChangeItem.id.asc())
        )
    ).scalars().all()
    return _to_change_set_detail(row, items)


async def create_requirement_regression_set(db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID, change_set_id: uuid.UUID) -> RequirementRegressionSetDetail:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)
    change_set = await db.scalar(
        select(RequirementChangeSet).where(
            RequirementChangeSet.id == change_set_id,
            RequirementChangeSet.project_id == project_id,
            RequirementChangeSet.tenant_id == user.tenant_id,
        )
    )
    if change_set is None:
        raise HTTPException(status_code=404, detail="Requirement change set not found")
    existing_set = await db.scalar(
        select(RequirementRegressionSet).where(
            RequirementRegressionSet.change_set_id == change_set.id,
            RequirementRegressionSet.project_id == project_id,
            RequirementRegressionSet.tenant_id == user.tenant_id,
        )
    )
    if existing_set is not None:
        cases = (
            await db.execute(
                select(RequirementRegressionCase, TestCase.title)
                .outerjoin(
                    TestCase,
                    (TestCase.id == RequirementRegressionCase.testcase_id)
                    & (TestCase.tenant_id == RequirementRegressionCase.tenant_id)
                    & (TestCase.project_id == RequirementRegressionCase.project_id),
                )
                .where(
                    RequirementRegressionCase.regression_set_id == existing_set.id,
                    RequirementRegressionCase.tenant_id == user.tenant_id,
                )
                .order_by(RequirementRegressionCase.created_at.asc(), RequirementRegressionCase.id.asc())
            )
        ).all()
        return _to_regression_set_detail(existing_set, cases)
    change_items = (
        await db.execute(
            select(RequirementChangeItem)
            .where(RequirementChangeItem.change_set_id == change_set.id, RequirementChangeItem.tenant_id == user.tenant_id)
            .order_by(RequirementChangeItem.created_at.asc(), RequirementChangeItem.id.asc())
        )
    ).scalars().all()
    linked = (
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
                RequirementCaseLink.doc_id == change_set.doc_id,
                RequirementCaseLink.doc_version_id == change_set.target_version_id,
            )
            .order_by(RequirementCaseLink.created_at.desc(), RequirementCaseLink.id.desc())
        )
    ).all()
    regression_set = RequirementRegressionSet(
        tenant_id=user.tenant_id,
        project_id=project_id,
        change_set_id=change_set.id,
        summary=f"共需回归 {len({link.testcase_id for link, _ in linked})} 条用例",
        status="GENERATED",
        created_by=user.id,
    )
    db.add(regression_set)
    await db.flush()
    source_paths = [item.source_path for item in change_items if item.source_path]
    seen: set[uuid.UUID] = set()
    cases: list[tuple[RequirementRegressionCase, str | None]] = []
    for link, title in linked:
        if link.testcase_id in seen:
            continue
        seen.add(link.testcase_id)
        row = RequirementRegressionCase(
            tenant_id=user.tenant_id,
            project_id=project_id,
            regression_set_id=regression_set.id,
            testcase_id=link.testcase_id,
            priority="P1" if any(item.impact_level == "HIGH" for item in change_items) else "P2",
            reason="需求版本变更关联的追溯用例",
            source_paths_json=source_paths,
            created_by=user.id,
        )
        db.add(row)
        cases.append((row, title))
    await db.flush()
    return _to_regression_set_detail(regression_set, cases)


async def get_requirement_regression_set(db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID, regression_set_id: uuid.UUID) -> RequirementRegressionSetDetail:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)
    row = await db.scalar(
        select(RequirementRegressionSet).where(
            RequirementRegressionSet.id == regression_set_id,
            RequirementRegressionSet.project_id == project_id,
            RequirementRegressionSet.tenant_id == user.tenant_id,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Requirement regression set not found")
    cases = (
        await db.execute(
            select(RequirementRegressionCase, TestCase.title)
            .outerjoin(
                TestCase,
                (TestCase.id == RequirementRegressionCase.testcase_id)
                & (TestCase.tenant_id == RequirementRegressionCase.tenant_id)
                & (TestCase.project_id == RequirementRegressionCase.project_id),
            )
            .where(
                RequirementRegressionCase.regression_set_id == row.id,
                RequirementRegressionCase.tenant_id == user.tenant_id,
            )
            .order_by(RequirementRegressionCase.created_at.asc(), RequirementRegressionCase.id.asc())
        )
    ).all()
    return _to_regression_set_detail(row, cases)
