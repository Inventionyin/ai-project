from __future__ import annotations

import uuid
from typing import Sequence

from fastapi import HTTPException
from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.models.environment import Environment
from app.models.enums import ProjectRole
from app.models.project import Project, ProjectMember
from app.models.suite import Suite, SuiteItem
from app.models.testcase import TestCase


def _is_admin(user: CurrentUser) -> bool:
    return "Admin" in user.roles or "ADMIN" in user.roles


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
    raise HTTPException(status_code=403, detail="No access to this project")


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
    raise HTTPException(status_code=403, detail="Only Owner/Editor can modify this project")


async def _get_test_env_id(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
) -> str | None:
    env = await db.scalar(
        select(Environment.id)
        .where(
            Environment.tenant_id == user.tenant_id,
            Environment.project_id == project_id,
            func.lower(Environment.name) == "test",
        )
        .order_by(Environment.updated_at.desc())
    )
    return str(env) if env else None


async def create_suite(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    name: str,
    config: dict,
    default_env_id: str | None,
) -> Suite:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)

    config_json = dict(config or {})
    resolved_default_env_id = default_env_id
    if resolved_default_env_id is None:
        resolved_default_env_id = await _get_test_env_id(db, user=user, project_id=project.id)
    if resolved_default_env_id is not None:
        config_json["defaultEnvId"] = resolved_default_env_id

    suite = Suite(
        tenant_id=user.tenant_id,
        project_id=project.id,
        name=name,
        config_json=config_json,
        created_by=user.id,
    )
    db.add(suite)
    await db.flush()
    return suite


async def list_suites(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID | None,
    page: int,
    page_size: int,
) -> tuple[int, Sequence[Suite]]:
    if project_id is not None:
        project = await _get_project(db, user=user, project_id=project_id)
        await _require_project_read(db, user=user, project=project)
        base_stmt = select(Suite).where(
            Suite.tenant_id == user.tenant_id,
            Suite.project_id == project.id,
        )
    else:
        base_stmt = (
            select(Suite)
            .join(Project, Suite.project_id == Project.id)
            .outerjoin(
                ProjectMember,
                and_(
                    ProjectMember.project_id == Project.id,
                    ProjectMember.user_id == user.id,
                    ProjectMember.tenant_id == user.tenant_id,
                ),
            )
            .where(Suite.tenant_id == user.tenant_id)
        )
        if not _is_admin(user):
            base_stmt = base_stmt.where(
                or_(
                    Project.owner_id == user.id,
                    ProjectMember.role.in_(
                        (ProjectRole.ADMIN, ProjectRole.OWNER, ProjectRole.EDITOR, ProjectRole.VIEWER)
                    ),
                )
            )

    total = int((await db.execute(select(func.count()).select_from(base_stmt.subquery()))).scalar_one() or 0)

    rows = (
        await db.execute(
            base_stmt.order_by(Suite.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
        )
    ).scalars()
    return total, list(rows.all())


async def get_suite(
    db: AsyncSession,
    *,
    user: CurrentUser,
    suite_id: uuid.UUID,
) -> Suite:
    suite = await db.scalar(select(Suite).where(Suite.id == suite_id, Suite.tenant_id == user.tenant_id))
    if suite is None:
        raise HTTPException(status_code=404, detail="Suite not found")
    project = await _get_project(db, user=user, project_id=suite.project_id)
    await _require_project_read(db, user=user, project=project)
    return suite


async def update_suite(
    db: AsyncSession,
    *,
    user: CurrentUser,
    suite_id: uuid.UUID,
    project_id: uuid.UUID,
    name: str,
    config: dict,
    default_env_id: str | None,
) -> Suite:
    suite = await get_suite(db, user=user, suite_id=suite_id)
    if suite.project_id != project_id:
        raise HTTPException(status_code=400, detail="projectId mismatch")

    project = await _get_project(db, user=user, project_id=suite.project_id)
    await _require_project_write(db, user=user, project=project)

    config_json = dict(config or {})
    if default_env_id is not None:
        config_json["defaultEnvId"] = default_env_id

    suite.name = name
    suite.config_json = config_json
    await db.flush()
    return suite


async def delete_suite(
    db: AsyncSession,
    *,
    user: CurrentUser,
    suite_id: uuid.UUID,
) -> None:
    suite = await get_suite(db, user=user, suite_id=suite_id)
    project = await _get_project(db, user=user, project_id=suite.project_id)
    await _require_project_write(db, user=user, project=project)
    await db.delete(suite)
    await db.flush()


async def upsert_suite_items(
    db: AsyncSession,
    *,
    user: CurrentUser,
    suite_id: uuid.UUID,
    items: list[dict],
) -> None:
    suite = await get_suite(db, user=user, suite_id=suite_id)
    project = await _get_project(db, user=user, project_id=suite.project_id)
    await _require_project_write(db, user=user, project=project)

    order_nos = [int(i["orderNo"]) for i in items]
    if len(order_nos) != len(set(order_nos)):
        raise HTTPException(status_code=400, detail="orderNo duplicated")

    testcase_ids = [uuid.UUID(str(i["testcaseId"])) for i in items]
    if testcase_ids:
        testcases = (
            await db.execute(
                select(TestCase.id, TestCase.project_id)
                .where(TestCase.tenant_id == user.tenant_id, TestCase.id.in_(testcase_ids))
            )
        ).all()
        if len(testcases) != len(set(testcase_ids)):
            raise HTTPException(status_code=404, detail="TestCase not found")
        for _, tc_project_id in testcases:
            if tc_project_id != suite.project_id:
                raise HTTPException(status_code=400, detail="TestCase not in this project")

    await db.execute(
        delete(SuiteItem).where(SuiteItem.suite_id == suite.id, SuiteItem.tenant_id == user.tenant_id)
    )

    for item in items:
        db.add(
            SuiteItem(
                tenant_id=user.tenant_id,
                suite_id=suite.id,
                testcase_id=uuid.UUID(str(item["testcaseId"])),
                order_no=int(item["orderNo"]),
                params_json=dict(item.get("params") or {}),
            )
        )

    await db.flush()


async def list_suite_items(
    db: AsyncSession,
    *,
    user: CurrentUser,
    suite_id: uuid.UUID,
) -> list[tuple[SuiteItem, TestCase]]:
    suite = await get_suite(db, user=user, suite_id=suite_id)
    rows = (
        await db.execute(
            select(SuiteItem, TestCase)
            .join(TestCase, SuiteItem.testcase_id == TestCase.id)
            .where(
                SuiteItem.tenant_id == user.tenant_id,
                SuiteItem.suite_id == suite.id,
                TestCase.tenant_id == user.tenant_id,
            )
            .order_by(SuiteItem.order_no.asc())
        )
    ).all()
    return [(r[0], r[1]) for r in rows]
