from __future__ import annotations

import uuid
from typing import Sequence

from fastapi import HTTPException
from sqlalchemy import and_, delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.models.enums import ProjectRole, TestCaseStatus, TestCaseType
from app.models.integration import IssueLink
from app.models.project import Project, ProjectMember
from app.models.run import Artifact, CaseRun
from app.models.suite import SuiteItem
from app.models.testcase import TestCase, TestCaseVersion
from app.models.testcase_binding import TestcaseBinding
from app.models.user import User
from app.schemas.testcase import TestCaseCreateRequest, TestCasePutRequest
from app.services.platform_record import create_audit_log


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


async def _create_testcase_audit(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    action: str,
    testcase: TestCase | None = None,
    resource_id: str | None = None,
    summary: str | None = None,
    detail: dict | None = None,
) -> None:
    await create_audit_log(
        db,
        user=user,
        project_id=project_id,
        module="TESTCASE",
        action=action,
        resource_type="testcase",
        resource_id=resource_id or (str(testcase.id) if testcase is not None else ""),
        summary=summary or (testcase.title if testcase is not None else None),
        detail=detail,
    )


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _normalize_test_case_id(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _normalize_expected_status_code(value: int | None) -> int | None:
    if value is None:
        return None
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        return None
    return normalized


def _normalize_expected_result(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _normalize_api_headers(value: dict[str, str] | None) -> dict[str, str]:
    if value is None:
        return {}
    normalized: dict[str, str] = {}
    for raw_key, raw_value in value.items():
        key = str(raw_key).strip()
        if not key:
            raise HTTPException(status_code=400, detail="apiHeaders key cannot be empty")
        if "\r" in key or "\n" in key:
            raise HTTPException(status_code=400, detail="apiHeaders key contains invalid characters")
        header_value = str(raw_value)
        if "\r" in header_value or "\n" in header_value:
            raise HTTPException(status_code=400, detail="apiHeaders value contains invalid characters")
        normalized[key] = header_value
    return normalized


def _merge_api_meta(
    meta_json: dict | None,
    *,
    api_params: dict | None = None,
    api_headers: dict[str, str] | None = None,
    expected_status_code: int | None = None,
    preconditions: str | None = None,
    postconditions: str | None = None,
    expected_result: str | None = None,
) -> dict:
    base = meta_json.copy() if isinstance(meta_json, dict) else {}
    if api_params is not None:
        base["apiParams"] = api_params
    if api_headers is not None:
        base["apiHeaders"] = _normalize_api_headers(api_headers)
    if expected_status_code is None:
        base.pop("expectedStatusCode", None)
    else:
        base["expectedStatusCode"] = _normalize_expected_status_code(expected_status_code)
    if preconditions is None:
        base.pop("preconditions", None)
    else:
        base["preconditions"] = preconditions.strip()
    if postconditions is None:
        base.pop("postconditions", None)
    else:
        base["postconditions"] = postconditions.strip()
    if expected_result is not None:
        base["expectedResult"] = expected_result.strip()
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
    test_case_id = _normalize_test_case_id(payload.testCaseId)
    if test_case_id is not None:
        existing = await db.scalar(
            select(TestCase.id).where(
                TestCase.tenant_id == user.tenant_id,
                TestCase.project_id == project_id,
                TestCase.test_case_id == test_case_id,
            )
        )
        if existing:
            raise HTTPException(status_code=400, detail="testCaseId already exists")
    feature = _normalize_optional_text(payload.feature)
    api_url = _normalize_optional_text(payload.apiUrl)
    api_method = _normalize_optional_text(payload.apiMethod.upper() if payload.apiMethod else None)
    if feature is None:
        raise HTTPException(status_code=400, detail="Feature is required")
    if api_method is None:
        raise HTTPException(status_code=400, detail="API method is required")
    if api_url is None:
        raise HTTPException(status_code=400, detail="API URL is required")
    expected_result = _normalize_expected_result(payload.expectedResult)
    if expected_result is None:
        raise HTTPException(status_code=400, detail="expectedResult is required")
    preconditions = _normalize_optional_text(payload.preconditions)
    postconditions = _normalize_optional_text(payload.postconditions)

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
        test_case_id=test_case_id,
        title=payload.title,
        type=payload.type,
        priority=payload.priority,
        status=payload.status,
        tags_json=payload.tags,
        content_md=payload.contentMd,
        feature=feature,
        api_url=api_url,
        api_method=api_method,
        ai_meta_json=_merge_api_meta(
            {},
            api_params=payload.apiParams,
            api_headers=payload.apiHeaders,
            expected_status_code=payload.expectedStatusCode,
            preconditions=preconditions,
            postconditions=postconditions,
            expected_result=expected_result,
        ),
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
    await _create_testcase_audit(
        db,
        user=user,
        project_id=project_id,
        action="CREATE_TESTCASE",
        testcase=testcase,
        detail={"title": testcase.title, "type": testcase.type, "priority": testcase.priority},
    )
    
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

    test_case_id = _normalize_test_case_id(payload.testCaseId)
    if test_case_id is not None and test_case_id != testcase.test_case_id:
        existing = await db.scalar(
            select(TestCase.id).where(
                TestCase.tenant_id == user.tenant_id,
                TestCase.project_id == testcase.project_id,
                TestCase.test_case_id == test_case_id,
                TestCase.id != testcase.id,
            )
        )
        if existing:
            raise HTTPException(status_code=400, detail="testCaseId already exists")

    feature = _normalize_optional_text(payload.feature)
    api_method = _normalize_optional_text(payload.apiMethod.upper() if payload.apiMethod else None)
    api_url = _normalize_optional_text(payload.apiUrl)
    expected_result = _normalize_expected_result(payload.expectedResult)
    if feature is None:
        raise HTTPException(status_code=400, detail="Feature is required")
    if api_method is None:
        raise HTTPException(status_code=400, detail="API method is required")
    if api_url is None:
        raise HTTPException(status_code=400, detail="API URL is required")
    if expected_result is None:
        raise HTTPException(status_code=400, detail="expectedResult is required")
    preconditions = _normalize_optional_text(payload.preconditions)
    postconditions = _normalize_optional_text(payload.postconditions)

    testcase.test_case_id = test_case_id
    testcase.title = payload.title
    testcase.type = payload.type
    testcase.priority = payload.priority
    testcase.status = payload.status
    testcase.tags_json = payload.tags
    testcase.content_md = payload.contentMd
    testcase.feature = feature
    testcase.api_url = api_url
    testcase.api_method = api_method
    testcase.ai_meta_json = _merge_api_meta(
        testcase.ai_meta_json,
        api_params=payload.apiParams,
        api_headers=payload.apiHeaders,
        expected_status_code=payload.expectedStatusCode,
        preconditions=preconditions,
        postconditions=postconditions,
        expected_result=expected_result,
    )
    if payload.ownerId:
        owner_id = uuid.UUID(payload.ownerId)
        owner_user = await db.scalar(
            select(User).where(User.id == owner_id, User.tenant_id == user.tenant_id)
        )
        if not owner_user:
            raise HTTPException(status_code=400, detail="Owner not found")
        testcase.owner_id = owner_id
    else:
        testcase.owner_id = None

    testcase.version += 1
    version = TestCaseVersion(
        tenant_id=user.tenant_id,
        testcase_id=testcase.id,
        version=testcase.version,
        content_md=testcase.content_md,
        created_by=user.id,
    )
    db.add(version)
    await _create_testcase_audit(
        db,
        user=user,
        project_id=testcase.project_id,
        action="UPDATE_TESTCASE",
        testcase=testcase,
        detail={"title": testcase.title, "version": _format_version(testcase.version)},
    )
    
    return testcase


async def delete_testcase(
    db: AsyncSession,
    *,
    user: CurrentUser,
    testcase_id: uuid.UUID,
) -> None:
    testcase = await get_testcase(db, user=user, testcase_id=testcase_id)
    await _check_project_permission(db, user, testcase.project_id, [ProjectRole.OWNER, ProjectRole.ADMIN, ProjectRole.EDITOR])
    project_id = testcase.project_id
    title = testcase.title

    case_run_ids = list(
        (
            await db.scalars(
                select(CaseRun.id).where(
                    CaseRun.tenant_id == user.tenant_id,
                    CaseRun.testcase_id == testcase.id,
                )
            )
        ).all()
    )
    if case_run_ids:
        await db.execute(
            delete(IssueLink).where(
                IssueLink.tenant_id == user.tenant_id,
                IssueLink.case_run_id.in_(case_run_ids),
            )
        )
        await db.execute(
            delete(Artifact).where(
                Artifact.tenant_id == user.tenant_id,
                Artifact.case_run_id.in_(case_run_ids),
            )
        )

    await db.execute(
        delete(CaseRun).where(
            CaseRun.tenant_id == user.tenant_id,
            CaseRun.testcase_id == testcase.id,
        )
    )
    await db.execute(
        delete(SuiteItem).where(
            SuiteItem.tenant_id == user.tenant_id,
            SuiteItem.testcase_id == testcase.id,
        )
    )
    await db.execute(
        delete(TestcaseBinding).where(
            TestcaseBinding.tenant_id == user.tenant_id,
            TestcaseBinding.testcase_id == testcase.id,
        )
    )
    await db.execute(
        delete(TestCaseVersion).where(
            TestCaseVersion.tenant_id == user.tenant_id,
            TestCaseVersion.testcase_id == testcase.id,
        )
    )

    await db.delete(testcase)
    await _create_testcase_audit(
        db,
        user=user,
        project_id=project_id,
        action="DELETE_TESTCASE",
        resource_id=str(testcase_id),
        summary=title,
        detail={"title": title},
    )


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
    await _create_testcase_audit(
        db,
        user=user,
        project_id=testcase.project_id,
        action="RESTORE_TESTCASE_VERSION",
        testcase=testcase,
        detail={"restoredVersion": version_num, "newVersion": _format_version(testcase.version)},
    )

    return testcase


async def archive_testcase(
    db: AsyncSession,
    *,
    user: CurrentUser,
    testcase_id: uuid.UUID,
) -> TestCase:
    testcase = await get_testcase(db, user=user, testcase_id=testcase_id)
    await _check_project_permission(db, user, testcase.project_id, [ProjectRole.OWNER, ProjectRole.ADMIN, ProjectRole.EDITOR])

    previous_status = testcase.status
    testcase.status = "ARCHIVED"
    testcase.version += 1
    version = TestCaseVersion(
        tenant_id=user.tenant_id,
        testcase_id=testcase.id,
        version=testcase.version,
        content_md=testcase.content_md,
        created_by=user.id,
    )
    db.add(version)
    await _create_testcase_audit(
        db,
        user=user,
        project_id=testcase.project_id,
        action="ARCHIVE_TESTCASE",
        testcase=testcase,
        detail={"previousStatus": previous_status, "newStatus": "ARCHIVED"},
    )
    return testcase


async def unarchive_testcase(
    db: AsyncSession,
    *,
    user: CurrentUser,
    testcase_id: uuid.UUID,
) -> TestCase:
    testcase = await get_testcase(db, user=user, testcase_id=testcase_id)
    await _check_project_permission(db, user, testcase.project_id, [ProjectRole.OWNER, ProjectRole.ADMIN, ProjectRole.EDITOR])

    if testcase.status != "ARCHIVED":
        raise HTTPException(status_code=400, detail="TestCase is not archived")

    testcase.status = "DRAFT"
    testcase.version += 1
    version = TestCaseVersion(
        tenant_id=user.tenant_id,
        testcase_id=testcase.id,
        version=testcase.version,
        content_md=testcase.content_md,
        created_by=user.id,
    )
    db.add(version)
    await _create_testcase_audit(
        db,
        user=user,
        project_id=testcase.project_id,
        action="UNARCHIVE_TESTCASE",
        testcase=testcase,
        detail={"previousStatus": "ARCHIVED", "newStatus": "DRAFT"},
    )
    return testcase
