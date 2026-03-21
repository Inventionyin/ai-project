from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime

from fastapi import Depends, Header, HTTPException
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.environment import Environment
from app.models.enums import CaseRunStatus, JobStatus, RunStatus, WorkerStatus
from app.models.run import Artifact, CaseRun, Job, Run
from app.models.testcase import TestCase
from app.models.worker import Worker
from app.schemas.worker import (
    JobArtifactSpec,
    JobEnv,
    JobExecution,
    JobItem,
    JobPayload,
    JobSuiteConfig,
    WorkerPollData,
    WorkerRegisterRequest,
)
from app.services.environment import get_secret_keys

_WORKER_CAPABILITIES = {"API", "UI", "PERF"}
_TERMINAL_CASE_STATUS = {CaseRunStatus.PASSED, CaseRunStatus.FAILED, CaseRunStatus.SKIPPED}
_RUNNER_TYPE_DEFAULT = "DEFAULT"
_RUNNER_TYPE_PYTEST_ALLURE = "PYTEST_ALLURE"
_RUNNER_TYPES = {_RUNNER_TYPE_DEFAULT, _RUNNER_TYPE_PYTEST_ALLURE}
_RUN_LEVEL_ARTIFACT_KINDS = {"EXECUTION_LOG", "ALLURE_RESULTS", "ALLURE_REPORT"}
_RUN_LEVEL_ARTIFACT_KEY = "__run__"


@dataclass(frozen=True, slots=True)
class CurrentWorker:
    id: uuid.UUID
    tenant_id: uuid.UUID
    capabilities: frozenset[str]


def _normalize_capabilities(capabilities: list[str]) -> set[str]:
    return {c.strip().upper() for c in capabilities if isinstance(c, str) and c.strip().upper() in _WORKER_CAPABILITIES}


def _token_hash(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _new_worker_token() -> str:
    return f"wk_{secrets.token_urlsafe(32)}"


def _require_worker_payload_identity(payload_worker_id: str, worker: CurrentWorker) -> None:
    try:
        worker_id = uuid.UUID(payload_worker_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid workerId") from exc
    if worker_id != worker.id:
        raise HTTPException(status_code=403, detail="workerId does not match token")


def _required_caps_for_job(job: Job) -> set[str]:
    meta = dict(job.meta_json or {})
    items = meta.get("items")
    if not isinstance(items, list):
        return set()
    required: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        raw_type = str(item.get("type") or "").strip().upper()
        if raw_type == "MIX":
            return set(_WORKER_CAPABILITIES)
        if raw_type in _WORKER_CAPABILITIES:
            required.add(raw_type)
    return required


def _resolve_runner_type(meta: dict[str, object]) -> str:
    runner_type = str(meta.get("runnerType") or "").strip().upper()
    if runner_type in _RUNNER_TYPES:
        return runner_type
    return _RUNNER_TYPE_DEFAULT


def _build_execution_spec(meta: dict[str, object]) -> JobExecution:
    runner_type = _resolve_runner_type(meta)
    if runner_type != _RUNNER_TYPE_PYTEST_ALLURE:
        return JobExecution(runnerType=_RUNNER_TYPE_DEFAULT, artifactSpec=[])
    return JobExecution(
        runnerType=_RUNNER_TYPE_PYTEST_ALLURE,
        artifactSpec=[
            JobArtifactSpec(key="allureResults", fileName="allure-results.zip", required=True),
            JobArtifactSpec(key="executionLog", fileName="execution.log", required=True),
            JobArtifactSpec(key="failureScreenshot", fileName="failure-screenshot.png", optional=True),
            JobArtifactSpec(key="requestResponseSnapshot", fileName="request-response.json", optional=True),
        ],
    )


async def get_current_worker(
    db: AsyncSession = Depends(get_db),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> CurrentWorker:
    if not authorization:
        raise HTTPException(status_code=401, detail="Worker token required")
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        raise HTTPException(status_code=401, detail="Invalid Authorization header")
    token = parts[1].strip()
    worker = await db.scalar(select(Worker).where(Worker.token_hash == _token_hash(token)))
    if worker is None:
        raise HTTPException(status_code=401, detail="Invalid worker token")
    return CurrentWorker(
        id=worker.id,
        tenant_id=worker.tenant_id,
        capabilities=frozenset(_normalize_capabilities(list(worker.capabilities_json or []))),
    )


async def register_worker(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    payload: WorkerRegisterRequest,
) -> tuple[uuid.UUID, str]:
    token = _new_worker_token()
    worker = Worker(
        tenant_id=tenant_id,
        name=payload.name,
        token_hash=_token_hash(token),
        capabilities_json=sorted(_normalize_capabilities(payload.capabilities)),
        slots=payload.slots,
        status=WorkerStatus.ONLINE,
        last_seen_at=datetime.utcnow(),
        version=payload.version,
    )
    db.add(worker)
    await db.flush()
    return worker.id, token


async def heartbeat_worker(
    db: AsyncSession,
    *,
    worker: CurrentWorker,
    worker_id: str,
) -> None:
    _require_worker_payload_identity(worker_id, worker)
    db_worker = await db.scalar(select(Worker).where(Worker.id == worker.id, Worker.tenant_id == worker.tenant_id))
    if db_worker is None:
        raise HTTPException(status_code=401, detail="Worker not found")
    db_worker.last_seen_at = datetime.utcnow()
    db_worker.status = WorkerStatus.ONLINE
    await db.flush()


async def poll_job(
    db: AsyncSession,
    *,
    worker: CurrentWorker,
    worker_id: str,
    capabilities: list[str],
) -> WorkerPollData:
    _require_worker_payload_identity(worker_id, worker)
    now = datetime.utcnow()
    worker_caps = _normalize_capabilities(capabilities)

    db_worker = await db.scalar(select(Worker).where(Worker.id == worker.id, Worker.tenant_id == worker.tenant_id))
    if db_worker is None:
        raise HTTPException(status_code=401, detail="Worker not found")
    db_worker.last_seen_at = now
    db_worker.status = WorkerStatus.ONLINE
    if worker_caps:
        db_worker.capabilities_json = sorted(worker_caps)
    if not worker_caps:
        await db.flush()
        return WorkerPollData(job=None, sleepMs=2000)

    candidates = (
        await db.execute(
            select(Job)
            .where(
                Job.tenant_id == worker.tenant_id,
                Job.status == JobStatus.QUEUED,
                Job.worker_id.is_(None),
            )
            .order_by(Job.created_at.asc())
            .limit(50)
        )
    ).scalars()
    queued_jobs = list(candidates.all())
    selected_job: Job | None = None
    for job in queued_jobs:
        required_caps = _required_caps_for_job(job)
        if required_caps.issubset(worker_caps):
            selected_job = job
            break

    if selected_job is None:
        await db.flush()
        return WorkerPollData(job=None, sleepMs=2000)

    selected_job.worker_id = worker.id
    selected_job.status = JobStatus.RUNNING
    selected_job.start_at = selected_job.start_at or now

    run = await db.scalar(select(Run).where(Run.id == selected_job.run_id, Run.tenant_id == worker.tenant_id))
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.status == RunStatus.QUEUED:
        run.status = RunStatus.RUNNING
        run.start_at = run.start_at or now

    meta = dict(selected_job.meta_json or {})
    items_raw = meta.get("items")
    if not isinstance(items_raw, list) or not items_raw:
        raise HTTPException(status_code=500, detail="Job items missing")

    case_run_ids = []
    testcase_ids = []
    for row in items_raw:
        if not isinstance(row, dict):
            continue
        case_run_id = row.get("caseRunId")
        testcase_id = row.get("testcaseId")
        if isinstance(case_run_id, str):
            case_run_ids.append(uuid.UUID(case_run_id))
        if isinstance(testcase_id, str):
            testcase_ids.append(uuid.UUID(testcase_id))

    if case_run_ids:
        await db.execute(
            update(CaseRun)
            .where(
                CaseRun.tenant_id == worker.tenant_id,
                CaseRun.run_id == run.id,
                CaseRun.id.in_(case_run_ids),
                CaseRun.status == CaseRunStatus.QUEUED,
            )
            .values(status=CaseRunStatus.RUNNING, start_at=now)
        )

    testcase_rows = (
        await db.execute(
            select(TestCase.id, TestCase.content_md).where(
                TestCase.tenant_id == worker.tenant_id,
                TestCase.id.in_(set(testcase_ids)),
            )
        )
    ).all()
    testcase_content_map: dict[uuid.UUID, str] = {row[0]: row[1] for row in testcase_rows}

    env_id = run.env_id
    if isinstance(meta.get("envId"), str):
        try:
            env_id = uuid.UUID(str(meta.get("envId")))
        except ValueError:
            env_id = run.env_id
    env: Environment | None = None
    if env_id is not None:
        env = await db.scalar(select(Environment).where(Environment.id == env_id, Environment.tenant_id == worker.tenant_id))
        if env is None:
            raise HTTPException(status_code=404, detail="Environment not found")
    env_secrets = {k: "" for k in get_secret_keys(env)} if env is not None else {}

    suite_cfg = dict(meta.get("suiteConfig") or {})
    suite_config = JobSuiteConfig(
        timeoutSec=int(suite_cfg.get("timeoutSec") or 600),
        retryCount=int(suite_cfg.get("retryCount") or 1),
        failFast=bool(suite_cfg.get("failFast") or False),
    )

    payload_items: list[JobItem] = []
    for row in items_raw:
        if not isinstance(row, dict):
            continue
        testcase_id = uuid.UUID(str(row["testcaseId"]))
        payload_items.append(
            JobItem(
                caseRunId=str(row["caseRunId"]),
                testcaseId=str(testcase_id),
                type=row["type"],
                contentMd=testcase_content_map.get(testcase_id) or " ",
                apiMethod=str(row.get("apiMethod") or "").strip().upper() or None,
                apiUrl=str(row.get("apiUrl") or "").strip() or None,
                params=dict(row.get("params") or {}),
                headers={str(k): str(v) for k, v in dict(row.get("headers") or {}).items()},
                expectedResult=str(row.get("expectedResult") or "").strip() or None,
                expectedStatusCode=row.get("expectedStatusCode") if isinstance(row.get("expectedStatusCode"), int) else None,
                preconditions=str(row.get("preconditions") or "").strip() or None,
                postconditions=str(row.get("postconditions") or "").strip() or None,
            )
        )

    await db.flush()
    return WorkerPollData(
        job=JobPayload(
            jobId=str(selected_job.id),
            runId=str(run.id),
            env=JobEnv(
                baseUrl=env.base_url if env is not None else "http://localhost",
                variables={str(k): str(v) for k, v in dict(env.variables_json or {}).items()} if env is not None else {},
                secrets=env_secrets,
            ),
            suiteConfig=suite_config,
            execution=_build_execution_spec(meta),
            items=payload_items,
        ),
        sleepMs=2000,
    )


async def report_job_result(
    db: AsyncSession,
    *,
    worker: CurrentWorker,
    worker_id: str,
    run_id: uuid.UUID,
    job_id: uuid.UUID,
    results,
    job_status: JobStatus,
) -> None:
    _require_worker_payload_identity(worker_id, worker)
    now = datetime.utcnow()

    db_worker = await db.scalar(select(Worker).where(Worker.id == worker.id, Worker.tenant_id == worker.tenant_id))
    if db_worker is None:
        raise HTTPException(status_code=401, detail="Worker not found")
    db_worker.last_seen_at = now
    db_worker.status = WorkerStatus.ONLINE

    job = await db.scalar(select(Job).where(Job.id == job_id, Job.run_id == run_id, Job.tenant_id == worker.tenant_id))
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.worker_id is not None and job.worker_id != worker.id:
        raise HTTPException(status_code=403, detail="Job does not belong to current worker")
    if job.worker_id is None:
        job.worker_id = worker.id

    meta_json = dict(job.meta_json or {})
    items = meta_json.get("items")
    if not isinstance(items, list):
        raise HTTPException(status_code=500, detail="Job items missing")
    allowed_case_run_ids = {
        str(item.get("caseRunId"))
        for item in items
        if isinstance(item, dict) and isinstance(item.get("caseRunId"), str)
    }

    requested_case_ids = {result.caseRunId for result in results}
    if not requested_case_ids.issubset(allowed_case_run_ids):
        raise HTTPException(status_code=400, detail="report contains caseRunId outside the job scope")

    try:
        case_run_uuid_map = {cid: uuid.UUID(cid) for cid in requested_case_ids}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid caseRunId") from exc
    db_case_runs = (
        await db.execute(
            select(CaseRun).where(
                CaseRun.tenant_id == worker.tenant_id,
                CaseRun.run_id == run_id,
                CaseRun.id.in_(set(case_run_uuid_map.values())),
            )
        )
    ).scalars()
    case_run_map = {str(row.id): row for row in db_case_runs.all()}
    if len(case_run_map) != len(case_run_uuid_map):
        raise HTTPException(status_code=404, detail="CaseRun not found")

    existing_rows = (
        await db.execute(
            select(Artifact.case_run_id, Artifact.type, Artifact.storage_url).where(
                Artifact.tenant_id == worker.tenant_id,
                Artifact.run_id == run_id,
                or_(
                    Artifact.case_run_id.is_(None),
                    Artifact.case_run_id.in_(set(case_run_uuid_map.values())),
                ),
            )
        )
    ).all()
    existing_artifact_keys: dict[str, set[tuple[str, str]]] = {}
    for case_run_id, artifact_type, storage_url in existing_rows:
        key = _RUN_LEVEL_ARTIFACT_KEY if case_run_id is None else str(case_run_id)
        if key not in existing_artifact_keys:
            existing_artifact_keys[key] = set()
        existing_artifact_keys[key].add((artifact_type.value, storage_url))

    reported_case_runs = {
        str(x)
        for x in (meta_json.get("reportedCaseRuns") or [])
        if isinstance(x, str)
    }

    for result in results:
        case_run = case_run_map[result.caseRunId]
        if result.caseRunId in reported_case_runs:
            continue
        if case_run.status in _TERMINAL_CASE_STATUS:
            reported_case_runs.add(result.caseRunId)
            continue

        case_run.status = result.status
        case_run.start_at = datetime.utcfromtimestamp(result.startAt)
        case_run.end_at = datetime.utcfromtimestamp(result.endAt) if result.endAt else None
        case_run.error_type = result.errorType
        case_run.error_message = result.errorMessage

        metrics_json = dict(result.metrics.model_dump() if result.metrics else {})
        if result.logs:
            metrics_json["logs"] = list(result.logs)
        case_run.metrics_json = metrics_json

        existing_key_set = existing_artifact_keys.setdefault(result.caseRunId, set())
        for artifact in result.artifacts:
            kind = ""
            if isinstance(artifact.meta, dict):
                kind = str(artifact.meta.get("kind") or "").upper()
            is_run_level = kind in _RUN_LEVEL_ARTIFACT_KINDS
            artifact_scope_key = _RUN_LEVEL_ARTIFACT_KEY if is_run_level else result.caseRunId
            existing_key_set = existing_artifact_keys.setdefault(artifact_scope_key, set())
            artifact_key = (artifact.type.value, artifact.storageKey)
            if artifact_key in existing_key_set:
                continue
            existing_key_set.add(artifact_key)
            artifact_size = artifact.meta.get("size")
            size = int(artifact_size) if isinstance(artifact_size, int | float) else None
            db.add(
                Artifact(
                    tenant_id=worker.tenant_id,
                    run_id=run_id,
                    case_run_id=None if is_run_level else case_run.id,
                    type=artifact.type,
                    storage_url=artifact.storageKey,
                    size=size,
                    meta_json=dict(artifact.meta or {}),
                )
            )
        reported_case_runs.add(result.caseRunId)

    meta_json["reportedCaseRuns"] = sorted(reported_case_runs)
    job.meta_json = meta_json
    job.status = job_status
    if job.status in (JobStatus.DONE, JobStatus.FAILED, JobStatus.CANCELED):
        job.end_at = now

    run = await db.scalar(select(Run).where(Run.id == run_id, Run.tenant_id == worker.tenant_id))
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    if job_status == JobStatus.RUNNING:
        run.status = RunStatus.RUNNING
    elif job_status == JobStatus.CANCELED:
        run.status = RunStatus.CANCELED
        run.end_at = now
    elif job_status == JobStatus.FAILED:
        run.status = RunStatus.FAILED
        run.end_at = now
    elif job_status == JobStatus.DONE:
        failed_count = int(
            (
                await db.execute(
                    select(func.count(CaseRun.id)).where(
                        CaseRun.tenant_id == worker.tenant_id,
                        CaseRun.run_id == run_id,
                        CaseRun.status == CaseRunStatus.FAILED,
                    )
                )
            ).scalar_one()
            or 0
        )
        run.status = RunStatus.FAILED if failed_count > 0 else RunStatus.PASSED
        run.end_at = now

    await db.flush()
