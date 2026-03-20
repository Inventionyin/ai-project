from __future__ import annotations

import uuid
from typing import Sequence

from fastapi import HTTPException
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.models.enums import ProjectRole, TestCaseStatus, TestCaseType
from app.models.project import Project, ProjectMember
from app.models.run import CaseRun
from app.models.testcase import TestCase, TestCaseVersion
from app.models.user import User
from app.schemas.testcase import TestCaseCreateRequest, TestCasePutRequest


def _is_admin(user: CurrentUser) -> bool:
    return "Admin" in user.roles or "ADMIN" in user.roles


def _parse_version_minor(version: str) -> int:
    v = version.strip()
    if v.startswith("v") or v.startswith("V"):
        v = v[1:]
    parts = v.split(".", 1)
    major = parts[0]
    if major != "1":
        raise HTTPException(status_code=400, detail="Invalid version")
    if len(parts) == 1:
        return 0
    try:
        minor = int(parts[1])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid version") from exc
    if minor < 0:
        raise HTTPException(status_code=400, detail="Invalid version")
    return minor


def _format_version(minor: int) -> str:
    return f"v1.{minor}"


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _merge_api_params(meta_json: dict | None, api_params: dict | None) -> dict:
    base = meta_json.copy() if isinstance(meta_json, dict) else {}
    if api_params is not None:
        base["apiParams"] = api_params
    return base


async def _check_project_permission(
    db: AsyncSession,
    user: CurrentUser,
    project_id: uuid.UUID,
    required_roles: list[ProjectRole] | None = None,
) -> None:
    if _is_admin(user):
        return

    # Check if user is project owner
    project = await db.scalar(select(Project).where(Project.id == project_id, Project.tenant_id == user.tenant_id))
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.owner_id == user.id:
        return

    # Check member role
    member = await db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user.id,
            ProjectMember.tenant_id == user.tenant_id,
        )
    )
    
    if not member:
        raise HTTPException(status_code=403, detail="Not a member of this project")

    if required_roles and member.role not in required_roles:
        raise HTTPException(status_code=403, detail="Insufficient permissions")


async def create_testcase(
    db: AsyncSession,
    *,
    user: CurrentUser,
    payload: TestCaseCreateRequest,
) -> TestCase:
    project_id = uuid.UUID(payload.projectId)
    await _check_project_permission(db, user, project_id, [ProjectRole.OWNER, ProjectRole.ADMIN, ProjectRole.EDITOR])

    owner_id = user.id
    if payload.ownerId:
        owner_id = uuid.UUID(payload.ownerId)
        owner_user = await db.scalar(
            select(User).where(User.id == owner_id, User.tenant_id == user.tenant_id)
        )
        if not owner_user:
            raise HTTPException(status_code=400, detail="Owner not found")

    testcase = TestCase(
        tenant_id=user.tenant_id,
        project_id=project_id,
        title=payload.title,
        type=payload.type,
        priority=payload.priority,
        status=payload.status,
        tags_json=payload.tags,
        content_md=payload.contentMd,
        feature=_normalize_optional_text(payload.feature),
        api_url=_normalize_optional_text(payload.apiUrl),
        api_method=_normalize_optional_text(payload.apiMethod.upper() if payload.apiMethod else None),
        ai_meta_json=_merge_api_params({}, payload.apiParams),
        created_by=user.id,
        owner_id=owner_id,
        version=0,
    )
    db.add(testcase)
    await db.flush() # to get ID
    
    # Create initial version
    version = TestCaseVersion(
        tenant_id=user.tenant_id,
        testcase_id=testcase.id,
        version=0,
        content_md=payload.contentMd,
        created_by=user.id,
    )
    db.add(version)
    
    return testcase


async def list_testcase_owner_options(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
) -> list[tuple[uuid.UUID, str]]:
    await _check_project_permission(
        db,
        user,
        project_id,
        [ProjectRole.OWNER, ProjectRole.ADMIN, ProjectRole.EDITOR, ProjectRole.VIEWER],
    )
    project = await db.scalar(select(Project).where(Project.id == project_id, Project.tenant_id == user.tenant_id))
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    users = (
        await db.execute(
            select(User)
            .where(
                User.tenant_id == user.tenant_id,
                (User.id == project.owner_id)
                | (
                    User.id.in_(
                        select(ProjectMember.user_id).where(
                            ProjectMember.project_id == project_id,
                            ProjectMember.tenant_id == user.tenant_id,
                        )
                    )
                ),
            )
            .order_by(User.username.asc().nullslast(), User.name.asc())
        )
    ).scalars().all()
    options: list[tuple[uuid.UUID, str]] = []
    for item in users:
        display_name = (item.username or "").strip() or item.name.strip()
        options.append((item.id, display_name))
    return options


async def get_owner_name(
    db: AsyncSession,
    *,
    user: CurrentUser,
    owner_id: uuid.UUID | None,
) -> str | None:
    if not owner_id:
        return None
    owner = await db.scalar(select(User).where(User.id == owner_id, User.tenant_id == user.tenant_id))
    if not owner:
        return None
    return (owner.username or "").strip() or owner.name.strip()


async def get_testcase(
    db: AsyncSession,
    *,
    user: CurrentUser,
    testcase_id: uuid.UUID,
) -> TestCase:
    stmt = select(TestCase).where(TestCase.id == testcase_id, TestCase.tenant_id == user.tenant_id)
    testcase = await db.scalar(stmt)
    if not testcase:
        raise HTTPException(status_code=404, detail="TestCase not found")
        
    # Check read permission (Viewer or above)
    await _check_project_permission(db, user, testcase.project_id, [ProjectRole.OWNER, ProjectRole.ADMIN, ProjectRole.EDITOR, ProjectRole.VIEWER])
    
    return testcase


async def update_testcase(
    db: AsyncSession,
    *,
    user: CurrentUser,
    testcase_id: uuid.UUID,
    payload: TestCasePutRequest,
) -> TestCase:
    testcase = await get_testcase(db, user=user, testcase_id=testcase_id)
    
    # Check write permission
    await _check_project_permission(db, user, testcase.project_id, [ProjectRole.OWNER, ProjectRole.ADMIN, ProjectRole.EDITOR])

    if uuid.UUID(payload.projectId) != testcase.project_id:
        raise HTTPException(status_code=400, detail="projectId mismatch")

    testcase.title = payload.title
    testcase.type = payload.type
    testcase.priority = payload.priority
    testcase.status = payload.status
    testcase.tags_json = payload.tags
    testcase.content_md = payload.contentMd
    if payload.feature is not None:
        testcase.feature = _normalize_optional_text(payload.feature)
    if payload.apiUrl is not None:
        testcase.api_url = _normalize_optional_text(payload.apiUrl)
    if payload.apiMethod is not None:
        testcase.api_method = _normalize_optional_text(payload.apiMethod.upper())
    if payload.apiParams is not None:
        testcase.ai_meta_json = _merge_api_params(testcase.ai_meta_json, payload.apiParams)
    if payload.ownerId is not None:
        testcase.owner_id = uuid.UUID(payload.ownerId)

    testcase.version += 1
    version = TestCaseVersion(
        tenant_id=user.tenant_id,
        testcase_id=testcase.id,
        version=testcase.version,
        content_md=testcase.content_md,
        created_by=user.id,
    )
    db.add(version)
    
    return testcase


async def delete_testcase(
    db: AsyncSession,
    *,
    user: CurrentUser,
    testcase_id: uuid.UUID,
) -> None:
    testcase = await get_testcase(db, user=user, testcase_id=testcase_id)
    await _check_project_permission(db, user, testcase.project_id, [ProjectRole.OWNER, ProjectRole.ADMIN, ProjectRole.EDITOR])
    
    await db.delete(testcase)


async def list_testcases(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    title: str | None = None,
    page: int,
    page_size: int,
    type_: TestCaseType | None = None,
    status: TestCaseStatus | None = None,
    tag: str | None = None,
    owner_id: uuid.UUID | None = None,
) -> tuple[int, Sequence[TestCase]]:
    # Check read permission
    await _check_project_permission(db, user, project_id, [ProjectRole.OWNER, ProjectRole.ADMIN, ProjectRole.EDITOR, ProjectRole.VIEWER])

    stmt = select(TestCase).where(TestCase.project_id == project_id, TestCase.tenant_id == user.tenant_id)
    
    if title and title.strip():
        stmt = stmt.where(TestCase.title.ilike(f"%{title.strip()}%"))
    if type_:
        stmt = stmt.where(TestCase.type == type_)
    if status:
        stmt = stmt.where(TestCase.status == status)
    if tag:
        stmt = stmt.where(TestCase.tags_json.contains([tag]))
    if owner_id:
        stmt = stmt.where(TestCase.owner_id == owner_id)

    total_stmt = select(func.count()).select_from(stmt.subquery())
    total = await db.scalar(total_stmt) or 0

    stmt = stmt.order_by(desc(TestCase.updated_at)).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    return total, result.scalars().all()


async def get_latest_case_runs(
    db: AsyncSession,
    *,
    user: CurrentUser,
    testcase_ids: Sequence[uuid.UUID],
) -> dict[uuid.UUID, CaseRun]:
    if not testcase_ids:
        return {}
    latest_at = func.coalesce(CaseRun.end_at, CaseRun.start_at, CaseRun.updated_at, CaseRun.created_at)
    ranked_subquery = (
        select(
            CaseRun.id.label("id"),
            CaseRun.testcase_id.label("testcase_id"),
            func.row_number()
            .over(
                partition_by=CaseRun.testcase_id,
                order_by=(desc(latest_at), desc(CaseRun.created_at), desc(CaseRun.id)),
            )
            .label("row_num"),
        )
        .where(
            CaseRun.tenant_id == user.tenant_id,
            CaseRun.testcase_id.in_(testcase_ids),
        )
        .subquery()
    )
    latest_stmt = select(CaseRun).join(
        ranked_subquery,
        and_(CaseRun.id == ranked_subquery.c.id, ranked_subquery.c.row_num == 1),
    )
    result = await db.execute(latest_stmt)
    latest_runs = result.scalars().all()
    return {item.testcase_id: item for item in latest_runs}


async def get_testcase_versions(
    db: AsyncSession,
    *,
    user: CurrentUser,
    testcase_id: uuid.UUID,
) -> Sequence[TestCaseVersion]:
    testcase = await get_testcase(db, user=user, testcase_id=testcase_id)
    # Permission already checked in get_testcase
    
    stmt = select(TestCaseVersion).where(TestCaseVersion.testcase_id == testcase_id).order_by(desc(TestCaseVersion.version))
    result = await db.execute(stmt)
    return result.scalars().all()


async def restore_testcase_version(
    db: AsyncSession,
    *,
    user: CurrentUser,
    testcase_id: uuid.UUID,
    version_num: str,
) -> TestCase:
    testcase = await get_testcase(db, user=user, testcase_id=testcase_id)
    await _check_project_permission(db, user, testcase.project_id, [ProjectRole.OWNER, ProjectRole.ADMIN, ProjectRole.EDITOR])

    minor = _parse_version_minor(version_num)
    target_version = await db.scalar(
        select(TestCaseVersion).where(
            TestCaseVersion.testcase_id == testcase_id,
            TestCaseVersion.version == minor
        )
    )
    
    if not target_version:
        raise HTTPException(status_code=404, detail="Version not found")
        
    # Create new version with content from old version
    testcase.content_md = target_version.content_md
    testcase.version += 1
    
    new_version = TestCaseVersion(
        tenant_id=user.tenant_id,
        testcase_id=testcase.id,
        version=testcase.version,
        content_md=target_version.content_md,
        created_by=user.id,
    )
    db.add(new_version)
    
    return testcase
