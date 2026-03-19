from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.models.environment import Environment
from app.models.enums import CaseRunStatus, JobStatus, ProjectRole, RunStatus, TriggerType
from app.models.project import Project, ProjectMember
from app.models.run import CaseRun, Job, Run
from app.models.suite import Suite, SuiteItem
from app.models.testcase import TestCase
from app.models.testcase_binding import TestcaseBinding


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
    raise HTTPException(status_code=403, detail="Only Owner/Editor can run this project")


def _stable_payload_sig(payload: dict[str, object]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


async def _get_or_create_direct_suite(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project: Project,
) -> Suite:
    suite = await db.scalar(
        select(Suite)
        .where(
            Suite.tenant_id == user.tenant_id,
            Suite.project_id == project.id,
            Suite.name == "__TESTCASE_DIRECT__",
        )
        .order_by(Suite.created_at.asc())
    )
    if suite is not None:
        return suite
    suite = Suite(
        tenant_id=user.tenant_id,
        project_id=project.id,
        name="__TESTCASE_DIRECT__",
        config_json={"source": "TESTCASE_DIRECT"},
        created_by=user.id,
    )
    db.add(suite)
    await db.flush()
    return suite


async def _get_existing_idempotent_run(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    idempotency_key: str,
    payload_sig: str,
) -> Run | None:
    run = await db.scalar(
        select(Run).where(
            Run.tenant_id == user.tenant_id,
            Run.project_id == project_id,
            Run.idempotency_key == idempotency_key,
        )
    )
    if run is None:
        return None
    existing_sig = ((run.summary_json or {}).get("idempotency") or {}).get("sig")
    if existing_sig and existing_sig != payload_sig:
        raise HTTPException(status_code=409, detail="Idempotency-Key reused with different payload")
    return run


async def create_run(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    suite_id: uuid.UUID,
    env_id: uuid.UUID,
    trigger_type: TriggerType,
    meta: dict[str, object],
    notify_rule_id: str | None,
    idempotency_key: str | None,
) -> Run:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)

    suite = await db.scalar(select(Suite).where(Suite.id == suite_id, Suite.tenant_id == user.tenant_id))
    if suite is None:
        raise HTTPException(status_code=404, detail="Suite not found")
    if suite.project_id != project.id:
        raise HTTPException(status_code=400, detail="Suite not in this project")

    env = await db.scalar(select(Environment).where(Environment.id == env_id, Environment.tenant_id == user.tenant_id))
    if env is None:
        raise HTTPException(status_code=404, detail="Environment not found")
    if env.project_id != project.id:
        raise HTTPException(status_code=400, detail="Environment not in this project")

    suite_items = (
        await db.execute(
            select(SuiteItem).where(SuiteItem.tenant_id == user.tenant_id, SuiteItem.suite_id == suite.id).order_by(
                SuiteItem.order_no.asc()
            )
        )
    ).scalars()
    suite_items_list = list(suite_items.all())
    if not suite_items_list:
        raise HTTPException(status_code=400, detail="Suite has no items")

    payload_for_sig: dict[str, object] = {
        "projectId": str(project_id),
        "suiteId": str(suite_id),
        "envId": str(env_id),
        "triggerType": trigger_type.value,
        "meta": meta or {},
        "notifyRuleId": notify_rule_id,
    }
    payload_sig = _stable_payload_sig(payload_for_sig)
    if idempotency_key:
        existing = await _get_existing_idempotent_run(
            db,
            user=user,
            project_id=project_id,
            idempotency_key=idempotency_key,
            payload_sig=payload_sig,
        )
        if existing is not None:
            return existing

    suite_snapshot_items = [
        {"orderNo": int(i.order_no), "testcaseId": str(i.testcase_id), "params": dict(i.params_json or {})}
        for i in suite_items_list
    ]

    run_summary = {
        "meta": dict(meta or {}),
        "notifyRuleId": notify_rule_id,
        "suiteSnapshot": {
            "suiteId": str(suite.id),
            "name": suite.name,
            "config": dict(suite.config_json or {}),
            "items": suite_snapshot_items,
        },
    }
    if idempotency_key:
        run_summary["idempotency"] = {"key": idempotency_key, "sig": payload_sig}

    run = Run(
        tenant_id=user.tenant_id,
        project_id=project.id,
        suite_id=suite.id,
        env_id=env.id,
        trigger_type=trigger_type,
        status=RunStatus.QUEUED,
        start_at=datetime.utcnow(),
        summary_json=run_summary,
        idempotency_key=idempotency_key,
        created_by=user.id,
    )
    db.add(run)
    try:
        await db.flush()
    except IntegrityError:
        if not idempotency_key:
            raise
        await db.rollback()
        existing = await _get_existing_idempotent_run(
            db,
            user=user,
            project_id=project_id,
            idempotency_key=idempotency_key,
            payload_sig=payload_sig,
        )
        if existing is None:
            raise
        return existing

    case_runs: list[CaseRun] = []
    for item in suite_items_list:
        case_run = CaseRun(
            tenant_id=user.tenant_id,
            run_id=run.id,
            testcase_id=item.testcase_id,
            status=CaseRunStatus.QUEUED,
        )
        db.add(case_run)
        case_runs.append(case_run)

    await db.flush()

    testcase_ids = [cr.testcase_id for cr in case_runs]
    testcase_types = {
        r[0]: r[1]
        for r in (
            await db.execute(
                select(TestCase.id, TestCase.type).where(TestCase.tenant_id == user.tenant_id, TestCase.id.in_(testcase_ids))
            )
        ).all()
    }

    items_for_job = []
    for suite_item, case_run in zip(suite_items_list, case_runs, strict=True):
        items_for_job.append(
            {
                "caseRunId": str(case_run.id),
                "testcaseId": str(case_run.testcase_id),
                "type": testcase_types.get(case_run.testcase_id).value if testcase_types.get(case_run.testcase_id) else None,
                "params": dict(suite_item.params_json or {}),
                "orderNo": int(suite_item.order_no),
            }
        )

    job = Job(
        tenant_id=user.tenant_id,
        run_id=run.id,
        status=JobStatus.QUEUED,
        meta_json={
            "projectId": str(project.id),
            "suiteId": str(suite.id),
            "envId": str(env.id),
            "triggerType": trigger_type.value,
            "meta": dict(meta or {}),
            "notifyRuleId": notify_rule_id,
            "suiteConfig": dict(suite.config_json or {}),
            "items": items_for_job,
        },
    )
    db.add(job)
    await db.flush()
    return run


async def create_run_from_testcases(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    env_id: uuid.UUID,
    trigger_type: TriggerType,
    meta: dict[str, object],
    concurrency: int,
    stop_on_failure: bool,
    items: list[dict[str, object]],
    notify_rule_id: str | None,
    idempotency_key: str | None,
) -> Run:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)
    env = await db.scalar(select(Environment).where(Environment.id == env_id, Environment.tenant_id == user.tenant_id))
    if env is None:
        raise HTTPException(status_code=404, detail="Environment not found")
    if env.project_id != project.id:
        raise HTTPException(status_code=400, detail="Environment not in this project")
    if not items:
        raise HTTPException(status_code=400, detail="items_required")

    dedupe_pairs: set[tuple[str, str]] = set()
    testcase_ids: list[uuid.UUID] = []
    binding_ids: list[uuid.UUID] = []
    normalized_items: list[dict[str, object]] = []
    for row in items:
        testcase_id = uuid.UUID(str(row["testcaseId"]))
        binding_id = uuid.UUID(str(row["bindingId"]))
        pair = (str(testcase_id), str(binding_id))
        if pair in dedupe_pairs:
            raise HTTPException(status_code=400, detail="duplicate_items_in_request")
        dedupe_pairs.add(pair)
        testcase_ids.append(testcase_id)
        binding_ids.append(binding_id)
        normalized_items.append(
            {
                "testcaseId": testcase_id,
                "bindingId": binding_id,
                "overrideParams": dict(row.get("overrideParams") or {}),
            }
        )

    testcase_rows = (
        await db.execute(
            select(TestCase.id, TestCase.project_id, TestCase.type).where(
                TestCase.tenant_id == user.tenant_id, TestCase.id.in_(set(testcase_ids))
            )
        )
    ).all()
    testcase_map = {r[0]: {"project_id": r[1], "type": r[2]} for r in testcase_rows}
    if len(testcase_map) != len(set(testcase_ids)):
        raise HTTPException(status_code=404, detail="TestCase not found")
    if any(v["project_id"] != project.id for v in testcase_map.values()):
        raise HTTPException(status_code=400, detail="testcase_not_in_project")

    binding_rows = (
        await db.execute(
            select(TestcaseBinding).where(
                TestcaseBinding.tenant_id == user.tenant_id,
                TestcaseBinding.id.in_(set(binding_ids)),
            )
        )
    ).scalars()
    binding_map = {b.id: b for b in binding_rows.all()}
    if len(binding_map) != len(set(binding_ids)):
        raise HTTPException(status_code=404, detail="binding_not_found")

    for row in normalized_items:
        testcase_id = row["testcaseId"]
        binding = binding_map[row["bindingId"]]
        if binding.project_id != project.id:
            raise HTTPException(status_code=400, detail="binding_not_in_project")
        if binding.testcase_id != testcase_id:
            raise HTTPException(status_code=400, detail="binding_testcase_mismatch")
        if not binding.enabled:
            raise HTTPException(status_code=400, detail="binding_disabled")

    payload_for_sig: dict[str, object] = {
        "projectId": str(project_id),
        "envId": str(env_id),
        "triggerType": trigger_type.value,
        "meta": meta or {},
        "concurrency": concurrency,
        "stopOnFailure": stop_on_failure,
        "items": [
            {
                "testcaseId": str(item["testcaseId"]),
                "bindingId": str(item["bindingId"]),
                "overrideParams": dict(item["overrideParams"] or {}),
            }
            for item in normalized_items
        ],
        "notifyRuleId": notify_rule_id,
    }
    payload_sig = _stable_payload_sig(payload_for_sig)
    if idempotency_key:
        existing = await _get_existing_idempotent_run(
            db,
            user=user,
            project_id=project.id,
            idempotency_key=idempotency_key,
            payload_sig=payload_sig,
        )
        if existing is not None:
            return existing

    suite = await _get_or_create_direct_suite(db, user=user, project=project)
    suite_snapshot_items: list[dict[str, object]] = []
    for order_no, row in enumerate(normalized_items, start=1):
        binding = binding_map[row["bindingId"]]
        override_params = dict(row["overrideParams"] or {})
        merged_params = dict(binding.params_json or {})
        merged_params.update(override_params)
        suite_snapshot_items.append(
            {
                "orderNo": order_no,
                "testcaseId": str(row["testcaseId"]),
                "bindingId": str(binding.id),
                "params": merged_params,
            }
        )

    run_summary = {
        "meta": dict(meta or {}),
        "notifyRuleId": notify_rule_id,
        "executionSource": "TESTCASE_DIRECT",
        "stopOnFailure": stop_on_failure,
        "concurrency": concurrency,
        "suiteSnapshot": {
            "suiteId": str(suite.id),
            "name": suite.name,
            "config": dict(suite.config_json or {}),
            "items": suite_snapshot_items,
        },
    }
    if idempotency_key:
        run_summary["idempotency"] = {"key": idempotency_key, "sig": payload_sig}

    run = Run(
        tenant_id=user.tenant_id,
        project_id=project.id,
        suite_id=suite.id,
        env_id=env.id,
        trigger_type=trigger_type,
        status=RunStatus.QUEUED,
        start_at=datetime.utcnow(),
        summary_json=run_summary,
        idempotency_key=idempotency_key,
        created_by=user.id,
    )
    db.add(run)
    try:
        await db.flush()
    except IntegrityError:
        if not idempotency_key:
            raise
        await db.rollback()
        existing = await _get_existing_idempotent_run(
            db,
            user=user,
            project_id=project.id,
            idempotency_key=idempotency_key,
            payload_sig=payload_sig,
        )
        if existing is None:
            raise
        return existing

    case_runs: list[CaseRun] = []
    for row in normalized_items:
        case_run = CaseRun(
            tenant_id=user.tenant_id,
            run_id=run.id,
            testcase_id=row["testcaseId"],
            status=CaseRunStatus.QUEUED,
        )
        db.add(case_run)
        case_runs.append(case_run)
    await db.flush()

    binding_snapshot_map: dict[str, dict[str, object]] = {}
    items_for_job: list[dict[str, object]] = []
    for order_no, row in enumerate(normalized_items, start=1):
        testcase_id = row["testcaseId"]
        binding = binding_map[row["bindingId"]]
        override_params = dict(row["overrideParams"] or {})
        merged_params = dict(binding.params_json or {})
        merged_params.update(override_params)
        case_run = case_runs[order_no - 1]
        binding_snapshot = {
            "bindingId": str(binding.id),
            "name": binding.name,
            "datasetId": str(binding.dataset_id) if binding.dataset_id else None,
            "apiTargetId": str(binding.api_target_id) if binding.api_target_id else None,
            "params": dict(binding.params_json or {}),
            "priority": binding.priority,
            "enabled": binding.enabled,
            "version": binding.version,
        }
        binding_snapshot_map[str(case_run.id)] = binding_snapshot
        items_for_job.append(
            {
                "caseRunId": str(case_run.id),
                "testcaseId": str(testcase_id),
                "bindingId": str(binding.id),
                "type": testcase_map[testcase_id]["type"].value if testcase_map[testcase_id]["type"] else None,
                "params": merged_params,
                "orderNo": order_no,
            }
        )

    run.summary_json = {**dict(run.summary_json or {}), "bindingSnapshots": binding_snapshot_map}

    job = Job(
        tenant_id=user.tenant_id,
        run_id=run.id,
        status=JobStatus.QUEUED,
        meta_json={
            "projectId": str(project.id),
            "suiteId": str(suite.id),
            "envId": str(env.id),
            "triggerType": trigger_type.value,
            "meta": dict(meta or {}),
            "notifyRuleId": notify_rule_id,
            "executionSource": "TESTCASE_DIRECT",
            "stopOnFailure": stop_on_failure,
            "concurrency": concurrency,
            "suiteConfig": dict(suite.config_json or {}),
            "items": items_for_job,
        },
    )
    db.add(job)
    await db.flush()
    return run


async def list_runs(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID | None,
    status: RunStatus | None,
    from_ts: int | None,
    to_ts: int | None,
    page: int,
    page_size: int,
) -> tuple[int, list[tuple[Run, int, int]]]:
    if project_id is not None:
        project = await _get_project(db, user=user, project_id=project_id)
        await _require_project_read(db, user=user, project=project)

    done_subq = (
        select(func.count(CaseRun.id))
        .where(
            CaseRun.run_id == Run.id,
            CaseRun.status.in_((CaseRunStatus.PASSED, CaseRunStatus.FAILED, CaseRunStatus.SKIPPED)),
        )
        .correlate(Run)
        .scalar_subquery()
    )
    total_subq = (
        select(func.count(CaseRun.id))
        .where(CaseRun.run_id == Run.id)
        .correlate(Run)
        .scalar_subquery()
    )

    stmt = (
        select(Run, done_subq.label("done"), total_subq.label("total"))
        .join(Project, Run.project_id == Project.id)
        .outerjoin(
            ProjectMember,
            and_(
                ProjectMember.project_id == Project.id,
                ProjectMember.user_id == user.id,
                ProjectMember.tenant_id == user.tenant_id,
            ),
        )
        .where(Run.tenant_id == user.tenant_id)
    )
    if not _is_admin(user):
        stmt = stmt.where(
            or_(
                Project.owner_id == user.id,
                ProjectMember.role.in_((ProjectRole.ADMIN, ProjectRole.OWNER, ProjectRole.EDITOR, ProjectRole.VIEWER)),
            )
        )
    if project_id is not None:
        stmt = stmt.where(Run.project_id == project_id)
    if status is not None:
        stmt = stmt.where(Run.status == status)
    if from_ts is not None:
        stmt = stmt.where(Run.start_at >= datetime.utcfromtimestamp(from_ts))
    if to_ts is not None:
        stmt = stmt.where(Run.start_at <= datetime.utcfromtimestamp(to_ts))

    total = int((await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one() or 0)

    rows = (
        await db.execute(
            stmt.order_by(Run.start_at.desc().nullslast(), Run.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    items: list[tuple[Run, int, int]] = [(r[0], int(r[1] or 0), int(r[2] or 0)) for r in rows]
    return total, items


async def get_run(
    db: AsyncSession,
    *,
    user: CurrentUser,
    run_id: uuid.UUID,
) -> tuple[Run, int, int]:
    run = await db.scalar(select(Run).where(Run.id == run_id, Run.tenant_id == user.tenant_id))
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    project = await _get_project(db, user=user, project_id=run.project_id)
    await _require_project_read(db, user=user, project=project)

    total = int(
        (
            await db.execute(select(func.count(CaseRun.id)).where(CaseRun.run_id == run.id, CaseRun.tenant_id == user.tenant_id))
        ).scalar_one()
        or 0
    )
    done = int(
        (
            await db.execute(
                select(func.count(CaseRun.id)).where(
                    CaseRun.run_id == run.id,
                    CaseRun.tenant_id == user.tenant_id,
                    CaseRun.status.in_((CaseRunStatus.PASSED, CaseRunStatus.FAILED, CaseRunStatus.SKIPPED)),
                )
            )
        ).scalar_one()
        or 0
    )
    return run, done, total


async def list_case_runs(
    db: AsyncSession,
    *,
    user: CurrentUser,
    run_id: uuid.UUID,
    status: CaseRunStatus | None,
    page: int,
    page_size: int,
) -> tuple[Run, int, list[CaseRun]]:
    run = await db.scalar(select(Run).where(Run.id == run_id, Run.tenant_id == user.tenant_id))
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    project = await _get_project(db, user=user, project_id=run.project_id)
    await _require_project_read(db, user=user, project=project)

    stmt = select(CaseRun).where(CaseRun.tenant_id == user.tenant_id, CaseRun.run_id == run.id)
    if status is not None:
        stmt = stmt.where(CaseRun.status == status)

    total = int((await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one() or 0)
    rows = (
        await db.execute(
            stmt.order_by(CaseRun.created_at.asc()).offset((page - 1) * page_size).limit(page_size)
        )
    ).scalars()
    return run, total, list(rows.all())


async def cancel_run(
    db: AsyncSession,
    *,
    user: CurrentUser,
    run_id: uuid.UUID,
) -> Run:
    run = await db.scalar(select(Run).where(Run.id == run_id, Run.tenant_id == user.tenant_id))
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    project = await _get_project(db, user=user, project_id=run.project_id)
    await _require_project_write(db, user=user, project=project)

    if run.status not in (RunStatus.QUEUED, RunStatus.RUNNING):
        raise HTTPException(status_code=400, detail="Run cannot be canceled")

    run.status = RunStatus.CANCELED
    run.end_at = datetime.utcnow()

    await db.execute(
        update(Job)
        .where(Job.tenant_id == user.tenant_id, Job.run_id == run.id, Job.status.in_((JobStatus.QUEUED, JobStatus.RUNNING)))
        .values(status=JobStatus.CANCELED, end_at=datetime.utcnow())
    )
    await db.execute(
        update(CaseRun)
        .where(
            CaseRun.tenant_id == user.tenant_id,
            CaseRun.run_id == run.id,
            CaseRun.status.in_((CaseRunStatus.QUEUED, CaseRunStatus.RUNNING)),
        )
        .values(status=CaseRunStatus.SKIPPED, end_at=datetime.utcnow())
    )
    await db.flush()
    return run


async def retry_run(
    db: AsyncSession,
    *,
    user: CurrentUser,
    run_id: uuid.UUID,
    failed_only: bool,
    idempotency_key: str | None,
) -> Run:
    run = await db.scalar(select(Run).where(Run.id == run_id, Run.tenant_id == user.tenant_id))
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    project = await _get_project(db, user=user, project_id=run.project_id)
    await _require_project_write(db, user=user, project=project)

    suite_id = run.suite_id
    env_id = run.env_id
    if suite_id is None or env_id is None:
        raise HTTPException(status_code=400, detail="Run cannot be retried")

    suite_items = ((run.summary_json or {}).get("suiteSnapshot") or {}).get("items") or []
    if not suite_items:
        suite_items_rows = (
            await db.execute(
                select(SuiteItem).where(SuiteItem.tenant_id == user.tenant_id, SuiteItem.suite_id == suite_id).order_by(
                    SuiteItem.order_no.asc()
                )
            )
        ).scalars()
        suite_items = [
            {"orderNo": int(i.order_no), "testcaseId": str(i.testcase_id), "params": dict(i.params_json or {})}
            for i in suite_items_rows.all()
        ]

    if failed_only:
        failed_ids = (
            await db.execute(
                select(CaseRun.testcase_id).where(
                    CaseRun.tenant_id == user.tenant_id, CaseRun.run_id == run.id, CaseRun.status == CaseRunStatus.FAILED
                )
            )
        ).scalars()
        failed_set = {str(tid) for tid in failed_ids.all()}
        suite_items = [i for i in suite_items if str(i.get("testcaseId")) in failed_set]

    if not suite_items:
        raise HTTPException(status_code=400, detail="No cases to retry")

    suite = await db.scalar(select(Suite).where(Suite.id == suite_id, Suite.tenant_id == user.tenant_id))
    env = await db.scalar(select(Environment).where(Environment.id == env_id, Environment.tenant_id == user.tenant_id))
    if suite is None or env is None:
        raise HTTPException(status_code=404, detail="Suite or Environment not found")

    payload_for_sig: dict[str, object] = {
        "projectId": str(run.project_id),
        "suiteId": str(suite_id),
        "envId": str(env_id),
        "triggerType": TriggerType.MANUAL.value,
        "meta": {"retryOf": str(run.id), "failedOnly": failed_only},
        "notifyRuleId": (run.summary_json or {}).get("notifyRuleId"),
    }
    payload_sig = _stable_payload_sig(payload_for_sig)
    if idempotency_key:
        existing = await _get_existing_idempotent_run(
            db,
            user=user,
            project_id=run.project_id,
            idempotency_key=idempotency_key,
            payload_sig=payload_sig,
        )
        if existing is not None:
            return existing

    retry_summary = {
        "meta": {"retryOf": str(run.id), "failedOnly": failed_only},
        "notifyRuleId": (run.summary_json or {}).get("notifyRuleId"),
        "suiteSnapshot": {
            "suiteId": str(suite.id),
            "name": suite.name,
            "config": dict(suite.config_json or {}),
            "items": suite_items,
        },
    }
    if idempotency_key:
        retry_summary["idempotency"] = {"key": idempotency_key, "sig": payload_sig}

    retry_run_obj = Run(
        tenant_id=user.tenant_id,
        project_id=run.project_id,
        suite_id=suite.id,
        env_id=env.id,
        trigger_type=TriggerType.MANUAL,
        status=RunStatus.QUEUED,
        start_at=datetime.utcnow(),
        summary_json=retry_summary,
        idempotency_key=idempotency_key,
        created_by=user.id,
    )
    db.add(retry_run_obj)
    try:
        await db.flush()
    except IntegrityError:
        if not idempotency_key:
            raise
        await db.rollback()
        existing = await _get_existing_idempotent_run(
            db,
            user=user,
            project_id=run.project_id,
            idempotency_key=idempotency_key,
            payload_sig=payload_sig,
        )
        if existing is None:
            raise
        return existing

    testcase_ids = [uuid.UUID(str(i["testcaseId"])) for i in suite_items]

    testcase_types = {
        r[0]: r[1]
        for r in (
            await db.execute(
                select(TestCase.id, TestCase.type).where(TestCase.tenant_id == user.tenant_id, TestCase.id.in_(testcase_ids))
            )
        ).all()
    }

    retry_case_runs: list[CaseRun] = []
    retry_suite_items: list[dict] = []
    for item in suite_items:
        testcase_id = uuid.UUID(str(item["testcaseId"]))
        case_run = CaseRun(
            tenant_id=user.tenant_id,
            run_id=retry_run_obj.id,
            testcase_id=testcase_id,
            status=CaseRunStatus.QUEUED,
        )
        db.add(case_run)
        retry_case_runs.append(case_run)
        retry_suite_items.append(dict(item))

    await db.flush()

    items_for_job = []
    for item, case_run in zip(retry_suite_items, retry_case_runs, strict=True):
        testcase_id = uuid.UUID(str(item["testcaseId"]))
        items_for_job.append(
            {
                "caseRunId": str(case_run.id),
                "testcaseId": str(testcase_id),
                "type": testcase_types.get(testcase_id).value if testcase_types.get(testcase_id) else None,
                "params": dict(item.get("params") or {}),
                "orderNo": int(item.get("orderNo") or 0),
            }
        )

    job = Job(
        tenant_id=user.tenant_id,
        run_id=retry_run_obj.id,
        status=JobStatus.QUEUED,
        meta_json={
            "projectId": str(run.project_id),
            "suiteId": str(suite.id),
            "envId": str(env.id),
            "triggerType": TriggerType.MANUAL.value,
            "meta": {"retryOf": str(run.id), "failedOnly": failed_only},
            "notifyRuleId": (run.summary_json or {}).get("notifyRuleId"),
            "suiteConfig": dict(suite.config_json or {}),
            "items": items_for_job,
        },
    )
    db.add(job)
    await db.flush()
    return retry_run_obj
