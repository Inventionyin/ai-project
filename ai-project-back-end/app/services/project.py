from __future__ import annotations

import uuid
from datetime import datetime, time, timedelta

from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.models.ai_import import AiImportItem, AiImportJob
from app.models.api import ApiCollection, ApiCollectionGroup, ApiRequest
from app.models.api_target import ApiTarget
from app.models.environment import Environment
from app.models.integration import AiRecord, IssueLink, Notification
from app.models.enums import ProjectRole, RunStatus
from app.models.project import Project, ProjectMember
from app.models.run import Artifact, CaseRun, Job, Run
from app.models.suite import Suite, SuiteItem
from app.models.test_data_set import TestDataSet
from app.models.testcase import TestCase, TestCaseVersion
from app.models.testcase_binding import TestcaseBinding


def _is_admin(user: CurrentUser) -> bool:
    return "Admin" in user.roles or "ADMIN" in user.roles


def _calculate_pass_rate(*, passed_runs: int, failed_runs: int) -> float | None:
    finished_runs = passed_runs + failed_runs
    if finished_runs <= 0:
        return None
    return round((passed_runs / finished_runs) * 100, 1)


async def create_project(
    db: AsyncSession,
    *,
    user: CurrentUser,
    name: str,
    description: str | None,
    owner_id: uuid.UUID,
) -> Project:
    if not (_is_admin(user) or owner_id == user.id):
        raise HTTPException(status_code=403, detail="Only Owner/Admin can create projects for others")

    project = Project(tenant_id=user.tenant_id, name=name, description=description, owner_id=owner_id)
    db.add(project)
    await db.flush()
    return project


async def list_projects(
    db: AsyncSession,
    *,
    user: CurrentUser,
    page: int,
    page_size: int,
    keyword: str | None,
) -> tuple[int, list[tuple[Project, int, int, float | None]]]:
    base_stmt = select(Project).where(Project.tenant_id == user.tenant_id)
    if keyword:
        base_stmt = base_stmt.where(Project.name.ilike(f"%{keyword}%"))

    total_stmt = select(func.count()).select_from(base_stmt.subquery())
    total = int((await db.execute(total_stmt)).scalar_one())

    member_count_subq = (
        select(func.count(ProjectMember.id))
        .where(ProjectMember.project_id == Project.id, ProjectMember.tenant_id == user.tenant_id)
        .correlate(Project)
        .scalar_subquery()
    )
    case_count_subq = (
        select(func.count(TestCase.id))
        .where(TestCase.project_id == Project.id, TestCase.tenant_id == user.tenant_id)
        .correlate(Project)
        .scalar_subquery()
    )
    passed_runs_subq = (
        select(func.count(Run.id))
        .where(
            Run.project_id == Project.id,
            Run.tenant_id == user.tenant_id,
            Run.status == RunStatus.PASSED,
        )
        .correlate(Project)
        .scalar_subquery()
    )
    failed_runs_subq = (
        select(func.count(Run.id))
        .where(
            Run.project_id == Project.id,
            Run.tenant_id == user.tenant_id,
            Run.status == RunStatus.FAILED,
        )
        .correlate(Project)
        .scalar_subquery()
    )

    stmt = (
        select(
            Project,
            member_count_subq.label("member_count"),
            case_count_subq.label("case_count"),
            passed_runs_subq.label("passed_runs"),
            failed_runs_subq.label("failed_runs"),
        )
        .where(Project.tenant_id == user.tenant_id)
        .order_by(Project.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    if keyword:
        stmt = stmt.where(Project.name.ilike(f"%{keyword}%"))

    rows = (await db.execute(stmt)).all()
    items: list[tuple[Project, int, int, float | None]] = []
    for row in rows:
        project = row[0]
        member_count = int(row[1] or 0)
        case_count = int(row[2] or 0)
        passed_runs = int(row[3] or 0)
        failed_runs = int(row[4] or 0)
        pass_rate = _calculate_pass_rate(passed_runs=passed_runs, failed_runs=failed_runs)
        items.append((project, member_count, case_count, pass_rate))
    return total, items


async def get_project_metrics(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
) -> tuple[int, float | None]:
    case_count = int(
        (
            await db.execute(
                select(func.count(TestCase.id)).where(
                    TestCase.project_id == project_id,
                    TestCase.tenant_id == user.tenant_id,
                )
            )
        ).scalar_one()
    )
    passed_runs = int(
        (
            await db.execute(
                select(func.count(Run.id)).where(
                    Run.project_id == project_id,
                    Run.tenant_id == user.tenant_id,
                    Run.status == RunStatus.PASSED,
                )
            )
        ).scalar_one()
    )
    failed_runs = int(
        (
            await db.execute(
                select(func.count(Run.id)).where(
                    Run.project_id == project_id,
                    Run.tenant_id == user.tenant_id,
                    Run.status == RunStatus.FAILED,
                )
            )
        ).scalar_one()
    )
    return case_count, _calculate_pass_rate(passed_runs=passed_runs, failed_runs=failed_runs)


async def get_project(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
) -> tuple[Project, int]:
    project = (
        await db.execute(select(Project).where(Project.id == project_id, Project.tenant_id == user.tenant_id))
    ).scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    member_count = int(
        (
            await db.execute(
                select(func.count(ProjectMember.id)).where(ProjectMember.project_id == project.id)
            )
        ).scalar_one()
    )
    return project, member_count


async def get_home_stats(
    db: AsyncSession,
    *,
    user: CurrentUser,
) -> tuple[int, int, int, float]:
    project_total = int(
        (
            await db.execute(
                select(func.count(Project.id)).where(Project.tenant_id == user.tenant_id)
            )
        ).scalar_one()
    )
    testcase_total = int(
        (
            await db.execute(
                select(func.count(TestCase.id)).where(TestCase.tenant_id == user.tenant_id)
            )
        ).scalar_one()
    )

    target_date = datetime.utcnow().date()
    day_start = datetime.combine(target_date, time.min)
    day_end = day_start + timedelta(days=1)
    run_rows = (
        await db.execute(
            select(Run.status, func.count(Run.id))
            .where(
                Run.tenant_id == user.tenant_id,
                Run.start_at >= day_start,
                Run.start_at < day_end,
            )
            .group_by(Run.status)
        )
    ).all()

    counters = {status: int(count or 0) for status, count in run_rows}
    passed_runs = counters.get(RunStatus.PASSED, 0)
    failed_runs = counters.get(RunStatus.FAILED, 0)
    running_runs = counters.get(RunStatus.RUNNING, 0) + counters.get(RunStatus.QUEUED, 0)
    canceled_runs = counters.get(RunStatus.CANCELED, 0)
    today_run_total = passed_runs + failed_runs + running_runs + canceled_runs
    finished_runs = passed_runs + failed_runs
    today_pass_rate = round((passed_runs / finished_runs) * 100, 1) if finished_runs > 0 else 0.0

    return project_total, testcase_total, today_run_total, today_pass_rate


async def _require_project_write(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project: Project,
) -> None:
    if _is_admin(user):
        return
    if project.owner_id == user.id:
        return

    role = (
        await db.execute(
            select(ProjectMember.role).where(
                ProjectMember.project_id == project.id,
                ProjectMember.user_id == user.id,
                ProjectMember.tenant_id == user.tenant_id,
            )
        )
    ).scalar_one_or_none()
    if role in (ProjectRole.ADMIN, ProjectRole.OWNER):
        return
    raise HTTPException(status_code=403, detail="Only Owner/Admin can modify this project")


async def update_project(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    name: str | None,
    description: str | None,
    owner_id: uuid.UUID | None,
) -> tuple[Project, int]:
    project, member_count = await get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)

    if name is not None:
        project.name = name
    if description is not None:
        project.description = description
    if owner_id is not None:
        if not _is_admin(user):
            raise HTTPException(status_code=403, detail="Only Admin can transfer project ownership")
        project.owner_id = owner_id

    await db.flush()
    return project, member_count


async def delete_project(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
) -> None:
    project, _ = await get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)

    run_ids = list(
        (
            await db.scalars(
                select(Run.id).where(
                    Run.tenant_id == user.tenant_id,
                    Run.project_id == project.id,
                )
            )
        ).all()
    )
    testcase_ids = list(
        (
            await db.scalars(
                select(TestCase.id).where(
                    TestCase.tenant_id == user.tenant_id,
                    TestCase.project_id == project.id,
                )
            )
        ).all()
    )
    collection_ids = list(
        (
            await db.scalars(
                select(ApiCollection.id).where(
                    ApiCollection.tenant_id == user.tenant_id,
                    ApiCollection.project_id == project.id,
                )
            )
        ).all()
    )
    suite_ids = list(
        (
            await db.scalars(
                select(Suite.id).where(
                    Suite.tenant_id == user.tenant_id,
                    Suite.project_id == project.id,
                )
            )
        ).all()
    )

    if run_ids:
        await db.execute(
            delete(IssueLink).where(
                IssueLink.tenant_id == user.tenant_id,
                IssueLink.run_id.in_(run_ids),
            )
        )
        await db.execute(
            delete(Artifact).where(
                Artifact.tenant_id == user.tenant_id,
                Artifact.run_id.in_(run_ids),
            )
        )
        await db.execute(
            delete(CaseRun).where(
                CaseRun.tenant_id == user.tenant_id,
                CaseRun.run_id.in_(run_ids),
            )
        )
        await db.execute(
            delete(Job).where(
                Job.tenant_id == user.tenant_id,
                Job.run_id.in_(run_ids),
            )
        )

    if testcase_ids:
        await db.execute(
            delete(SuiteItem).where(
                SuiteItem.tenant_id == user.tenant_id,
                SuiteItem.testcase_id.in_(testcase_ids),
            )
        )
        await db.execute(
            delete(TestCaseVersion).where(
                TestCaseVersion.tenant_id == user.tenant_id,
                TestCaseVersion.testcase_id.in_(testcase_ids),
            )
        )
        await db.execute(
            delete(TestcaseBinding).where(
                TestcaseBinding.tenant_id == user.tenant_id,
                TestcaseBinding.testcase_id.in_(testcase_ids),
            )
        )
        await db.execute(
            delete(CaseRun).where(
                CaseRun.tenant_id == user.tenant_id,
                CaseRun.testcase_id.in_(testcase_ids),
            )
        )

    if suite_ids:
        await db.execute(
            delete(SuiteItem).where(
                SuiteItem.tenant_id == user.tenant_id,
                SuiteItem.suite_id.in_(suite_ids),
            )
        )

    if collection_ids:
        await db.execute(
            delete(ApiRequest).where(
                ApiRequest.tenant_id == user.tenant_id,
                ApiRequest.collection_id.in_(collection_ids),
            )
        )
        await db.execute(
            delete(ApiCollectionGroup).where(
                ApiCollectionGroup.tenant_id == user.tenant_id,
                ApiCollectionGroup.collection_id.in_(collection_ids),
            )
        )

    await db.execute(
        delete(TestcaseBinding).where(
            TestcaseBinding.tenant_id == user.tenant_id,
            TestcaseBinding.project_id == project.id,
        )
    )
    await db.execute(
        delete(AiImportItem).where(
            AiImportItem.tenant_id == user.tenant_id,
            AiImportItem.project_id == project.id,
        )
    )
    await db.execute(
        delete(AiImportJob).where(
            AiImportJob.tenant_id == user.tenant_id,
            AiImportJob.project_id == project.id,
        )
    )
    await db.execute(
        delete(ApiTarget).where(
            ApiTarget.tenant_id == user.tenant_id,
            ApiTarget.project_id == project.id,
        )
    )
    await db.execute(
        delete(ApiCollection).where(
            ApiCollection.tenant_id == user.tenant_id,
            ApiCollection.project_id == project.id,
        )
    )
    await db.execute(
        delete(Run).where(
            Run.tenant_id == user.tenant_id,
            Run.project_id == project.id,
        )
    )
    await db.execute(
        delete(TestCase).where(
            TestCase.tenant_id == user.tenant_id,
            TestCase.project_id == project.id,
        )
    )
    await db.execute(
        delete(Suite).where(
            Suite.tenant_id == user.tenant_id,
            Suite.project_id == project.id,
        )
    )
    await db.execute(
        delete(TestDataSet).where(
            TestDataSet.tenant_id == user.tenant_id,
            TestDataSet.project_id == project.id,
        )
    )
    await db.execute(
        delete(Environment).where(
            Environment.tenant_id == user.tenant_id,
            Environment.project_id == project.id,
        )
    )
    await db.execute(
        delete(Notification).where(
            Notification.tenant_id == user.tenant_id,
            Notification.project_id == project.id,
        )
    )
    await db.execute(
        delete(AiRecord).where(
            AiRecord.tenant_id == user.tenant_id,
            AiRecord.project_id == project.id,
        )
    )
    await db.execute(
        delete(ProjectMember).where(
            ProjectMember.tenant_id == user.tenant_id,
            ProjectMember.project_id == project.id,
        )
    )

    await db.delete(project)
    await db.flush()

