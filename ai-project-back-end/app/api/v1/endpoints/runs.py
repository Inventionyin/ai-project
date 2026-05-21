from __future__ import annotations

import asyncio
import mimetypes
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_request_id, to_unix_ts
from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.enums import ArtifactType, CaseRunStatus, RunStatus
from app.models.run import Artifact, CaseRun, Job, Run
from app.schemas.common import ApiResponse, PageData
from app.schemas.run import (
    CaseRunListItem,
    ProjectCiTokenListData,
    ProjectCiTokenManageRequest,
    ProjectCiTokenNamedManageRequest,
    ProjectCiTokenNamedPolicyUpdateRequest,
    ProjectCiTokenNamedRotateData,
    ProjectCiTokenNamedRotateRequest,
    ProjectCiTokenRotateData,
    ProjectCiTokenPolicyData,
    ProjectCiTokenPolicyUpdateRequest,
    ProjectCiTokenRecordData,
    ProjectCiTokenStatusData,
    ProjectCiTokenRotateRequest,
    RunAllureReportGenerateData,
    RunAllureReportDeleteData,
    RunAllureReportListItem,
    RunCancelResponseData,
    RunCiTriggerRequest,
    RunCreateRequest,
    RunDetailData,
    RunFromTestcasesHttpRequest,
    RunFromTestcasesRequest,
    RunMetrics,
    RunProgress,
    RunRetryRequest,
)
from app.services.run import (
    CiTokenPolicyDenied,
    cancel_run,
    create_run_via_ci_token,
    create_run,
    create_run_from_testcases,
    create_run_from_testcases_http,
    delete_run_allure_report,
    get_project_ci_token_status,
    get_project_ci_token_policy,
    get_project_ci_token_record_policy,
    get_run,
    list_project_ci_token_records,
    list_case_runs,
    list_runs,
    report_project_ci_token_leak,
    report_project_ci_token_record_leak,
    resolve_ci_token_state,
    resolve_project_ci_token_record_state,
    revoke_project_ci_token,
    revoke_project_ci_token_record,
    rotate_project_ci_token,
    rotate_project_ci_token_record,
    update_project_ci_token_policy,
    update_project_ci_token_record_policy,
    retry_run,
)
from app.services.runner_pytest_allure import generate_allure_report_for_run, resolve_run_allure_paths

router = APIRouter(prefix="/runs")
_LEGACY_ALLURE_RUNS_ROOT = Path("D:/ai-project/allure-data/runs")


def _resolve_user_with_optional_token(user: CurrentUser, access_token: str | None) -> CurrentUser:
    token = str(access_token or "").strip()
    if not token:
        return user
    payload = decode_access_token(token)
    return CurrentUser(id=payload.user_id, tenant_id=payload.tenant_id, roles=payload.roles)


def _find_allure_report_dir(*, artifact_path: Path | None, workspace_path: Path | None) -> Path | None:
    report_dir: Path | None = None
    if artifact_path is not None:
        if artifact_path.is_dir():
            report_dir = artifact_path
        elif artifact_path.suffix.lower() == ".zip" and artifact_path.exists():
            extract_root = artifact_path.parent
            target = extract_root / "allure-report"
            if not target.exists():
                with zipfile.ZipFile(artifact_path, mode="r") as archive:
                    archive.extractall(path=extract_root)
            report_dir = target
    if (report_dir is None or not report_dir.exists()) and workspace_path is not None:
        candidate = workspace_path / "allure-report"
        if candidate.exists():
            report_dir = candidate
    if report_dir is None or not report_dir.exists():
        return None
    return report_dir.resolve()


def _zip_allure_report_dir(report_dir: Path) -> Path:
    zip_path = report_dir.parent / "allure-report.zip"
    with zipfile.ZipFile(zip_path, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for child in report_dir.rglob("*"):
            if child.is_file():
                archive.write(child, child.relative_to(report_dir.parent))
    return zip_path


def _safe_resolve_report_file(report_dir: Path, asset_path: str) -> Path:
    normalized = str(asset_path or "").strip("/")
    target = (report_dir / normalized).resolve() if normalized else (report_dir / "index.html").resolve()
    target.relative_to(report_dir)
    return target


def _resolve_token(access_token: str | None, referer: str | None) -> str:
    token = str(access_token or "").strip()
    if token:
        return token
    ref = str(referer or "").strip()
    if not ref:
        return ""
    parsed = urlparse(ref)
    token_values = parse_qs(parsed.query).get("access_token") or []
    if not token_values:
        return ""
    return str(token_values[0] or "").strip()


def _to_run_detail(run, done: int, total: int, passed: int, failed: int, skipped: int) -> RunDetailData:
    if run.suite_id is None:
        raise HTTPException(status_code=500, detail="Run data invalid")
    start_at = run.start_at or run.created_at
    execution_source = None
    try:
        raw = (run.summary_json or {}).get("executionSource")
        if isinstance(raw, str) and raw.strip():
            execution_source = raw.strip()
    except Exception:
        execution_source = None
    return RunDetailData(
        id=str(run.id),
        status=run.status,
        progress=RunProgress(done=done, total=total),
        triggerType=run.trigger_type,
        executionSource=execution_source,
        metrics=RunMetrics(total=total, done=done, passed=passed, failed=failed, skipped=skipped),
        suiteId=str(run.suite_id),
        envId=str(run.env_id) if run.env_id else None,
        startAt=to_unix_ts(start_at),
    )


def _to_utc_unix_ts(dt) -> int:
    if dt.tzinfo is not None:
        return int(dt.astimezone(timezone.utc).timestamp())
    return int(dt.replace(tzinfo=timezone.utc).timestamp())


def _redact_person_id(value) -> str | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    if len(raw) <= 8:
        return raw
    return f"{raw[:8]}...{raw[-4:]}"


async def _load_run_case_metrics(db: AsyncSession, *, run: Run) -> tuple[int, int, int, int, int]:
    total = int(
        (
            await db.execute(
                select(func.count(CaseRun.id)).where(CaseRun.run_id == run.id, CaseRun.tenant_id == run.tenant_id)
            )
        ).scalar_one()
        or 0
    )
    grouped = (
        await db.execute(
            select(CaseRun.status, func.count(CaseRun.id))
            .where(CaseRun.run_id == run.id, CaseRun.tenant_id == run.tenant_id)
            .group_by(CaseRun.status)
        )
    ).all()
    counts = {status: int(cnt or 0) for status, cnt in grouped}
    passed = int(counts.get(CaseRunStatus.PASSED, 0))
    failed = int(counts.get(CaseRunStatus.FAILED, 0))
    skipped = int(counts.get(CaseRunStatus.SKIPPED, 0))
    done = passed + failed + skipped
    return done, total, passed, failed, skipped


def _to_ci_token_status(project) -> ProjectCiTokenStatusData:
    state = resolve_ci_token_state(project)
    return ProjectCiTokenStatusData(
        projectId=str(project.id),
        enabled=state == "active",
        state=state,
        hint=getattr(project, "ci_token_hint", None),
        rotatedAt=_to_utc_unix_ts(project.ci_token_rotated_at) if getattr(project, "ci_token_rotated_at", None) else None,
        lastUsedAt=_to_utc_unix_ts(project.ci_token_last_used_at) if getattr(project, "ci_token_last_used_at", None) else None,
        rotatedBy=_redact_person_id(getattr(project, "ci_token_rotated_by", None)),
        expiresAt=_to_utc_unix_ts(project.ci_token_expires_at) if getattr(project, "ci_token_expires_at", None) else None,
        revokedAt=_to_utc_unix_ts(project.ci_token_revoked_at) if getattr(project, "ci_token_revoked_at", None) else None,
        revokedBy=_redact_person_id(getattr(project, "ci_token_revoked_by", None)),
        revokedReason=getattr(project, "ci_token_revoked_reason", None),
        leakReportedAt=_to_utc_unix_ts(project.ci_token_leak_reported_at) if getattr(project, "ci_token_leak_reported_at", None) else None,
        leakReportedBy=_redact_person_id(getattr(project, "ci_token_leak_reported_by", None)),
        leakReportReason=getattr(project, "ci_token_leak_report_reason", None),
        policy=_to_ci_token_policy(project),
    )


def _to_ci_token_policy(project) -> ProjectCiTokenPolicyData:
    policy = get_project_ci_token_policy(project)
    return ProjectCiTokenPolicyData(
        allowedRunnerTypes=list(policy["allowedRunnerTypes"]),
        allowedTestCaseIds=list(policy["allowedTestCaseIds"]),
        maxTestCaseCount=policy["maxTestCaseCount"],
    )


def _to_ci_token_record_policy(token) -> ProjectCiTokenPolicyData:
    policy = get_project_ci_token_record_policy(token)
    return ProjectCiTokenPolicyData(
        allowedRunnerTypes=list(policy["allowedRunnerTypes"]),
        allowedTestCaseIds=list(policy["allowedTestCaseIds"]),
        maxTestCaseCount=policy["maxTestCaseCount"],
    )


def _to_ci_token_record(token) -> ProjectCiTokenRecordData:
    state = resolve_project_ci_token_record_state(token)
    return ProjectCiTokenRecordData(
        id=str(token.id),
        projectId=str(token.project_id),
        name=str(token.name),
        primary=bool(token.is_primary),
        enabled=state == "active",
        state=state,
        hint=getattr(token, "token_hint", None),
        rotatedAt=_to_utc_unix_ts(token.rotated_at) if getattr(token, "rotated_at", None) else None,
        lastUsedAt=_to_utc_unix_ts(token.last_used_at) if getattr(token, "last_used_at", None) else None,
        rotatedBy=_redact_person_id(getattr(token, "rotated_by", None)),
        expiresAt=_to_utc_unix_ts(token.expires_at) if getattr(token, "expires_at", None) else None,
        revokedAt=_to_utc_unix_ts(token.revoked_at) if getattr(token, "revoked_at", None) else None,
        revokedBy=_redact_person_id(getattr(token, "revoked_by", None)),
        revokedReason=getattr(token, "revoked_reason", None),
        leakReportedAt=_to_utc_unix_ts(token.leak_reported_at) if getattr(token, "leak_reported_at", None) else None,
        leakReportedBy=_redact_person_id(getattr(token, "leak_reported_by", None)),
        leakReportReason=getattr(token, "leak_report_reason", None),
        policy=_to_ci_token_record_policy(token),
    )


@router.post("/ci-token/rotate", response_model=ApiResponse[ProjectCiTokenRotateData])
async def rotate_ci_token_(
    payload: ProjectCiTokenRotateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[ProjectCiTokenRotateData]:
    try:
        expires_at = datetime.utcfromtimestamp(payload.expiresAt) if payload.expiresAt is not None else None
        project, token = await rotate_project_ci_token(
            db,
            user=user,
            project_id=uuid.UUID(payload.projectId),
            policy=payload.policy.model_dump(mode="json") if payload.policy else None,
            expires_at=expires_at,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(
        data=ProjectCiTokenRotateData(
            projectId=str(project.id),
            enabled=resolve_ci_token_state(project) == "active",
            state=resolve_ci_token_state(project),
            token=token,
            hint=str(project.ci_token_hint or ""),
            rotatedAt=_to_utc_unix_ts(project.ci_token_rotated_at),
            expiresAt=_to_utc_unix_ts(project.ci_token_expires_at) if getattr(project, "ci_token_expires_at", None) else None,
            lastUsedAt=_to_utc_unix_ts(project.ci_token_last_used_at) if getattr(project, "ci_token_last_used_at", None) else None,
            rotatedBy=_redact_person_id(getattr(project, "ci_token_rotated_by", None)),
            revokedAt=_to_utc_unix_ts(project.ci_token_revoked_at) if getattr(project, "ci_token_revoked_at", None) else None,
            revokedBy=_redact_person_id(getattr(project, "ci_token_revoked_by", None)),
            revokedReason=getattr(project, "ci_token_revoked_reason", None),
            leakReportedAt=_to_utc_unix_ts(project.ci_token_leak_reported_at) if getattr(project, "ci_token_leak_reported_at", None) else None,
            leakReportedBy=_redact_person_id(getattr(project, "ci_token_leak_reported_by", None)),
            leakReportReason=getattr(project, "ci_token_leak_report_reason", None),
            policy=_to_ci_token_policy(project),
        ),
        requestId=request_id,
    )


@router.get("/ci-tokens", response_model=ApiResponse[ProjectCiTokenListData])
async def list_ci_tokens_(
    projectId: str = Query(...),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[ProjectCiTokenListData]:
    project, tokens = await list_project_ci_token_records(db, user=user, project_id=uuid.UUID(projectId))
    return ApiResponse(
        data=ProjectCiTokenListData(projectId=str(project.id), tokens=[_to_ci_token_record(token) for token in tokens]),
        requestId=request_id,
    )


@router.post("/ci-tokens/rotate", response_model=ApiResponse[ProjectCiTokenNamedRotateData])
async def rotate_named_ci_token_(
    payload: ProjectCiTokenNamedRotateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[ProjectCiTokenNamedRotateData]:
    try:
        expires_at = datetime.utcfromtimestamp(payload.expiresAt) if payload.expiresAt is not None else None
        record, token = await rotate_project_ci_token_record(
            db,
            user=user,
            project_id=uuid.UUID(payload.projectId),
            name=payload.name,
            primary=payload.primary,
            policy=payload.policy.model_dump(mode="json") if payload.policy else None,
            expires_at=expires_at,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    data = _to_ci_token_record(record).model_dump()
    return ApiResponse(data=ProjectCiTokenNamedRotateData(**data, token=token), requestId=request_id)


@router.put("/ci-tokens/policy", response_model=ApiResponse[ProjectCiTokenRecordData])
async def update_named_ci_token_policy_(
    payload: ProjectCiTokenNamedPolicyUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[ProjectCiTokenRecordData]:
    try:
        record = await update_project_ci_token_record_policy(
            db,
            user=user,
            project_id=uuid.UUID(payload.projectId),
            token_id=uuid.UUID(payload.tokenId) if payload.tokenId else None,
            name=payload.name,
            policy=payload.policy.model_dump(mode="json"),
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=_to_ci_token_record(record), requestId=request_id)


@router.delete("/ci-tokens", response_model=ApiResponse[ProjectCiTokenRecordData])
async def revoke_named_ci_token_(
    payload: ProjectCiTokenNamedManageRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[ProjectCiTokenRecordData]:
    try:
        record = await revoke_project_ci_token_record(
            db,
            user=user,
            project_id=uuid.UUID(payload.projectId),
            token_id=uuid.UUID(payload.tokenId) if payload.tokenId else None,
            name=payload.name,
            reason=payload.reason,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=_to_ci_token_record(record), requestId=request_id)


@router.post("/ci-tokens/report-leak", response_model=ApiResponse[ProjectCiTokenRecordData])
async def report_named_ci_token_leak_(
    payload: ProjectCiTokenNamedManageRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[ProjectCiTokenRecordData]:
    try:
        record = await report_project_ci_token_record_leak(
            db,
            user=user,
            project_id=uuid.UUID(payload.projectId),
            token_id=uuid.UUID(payload.tokenId) if payload.tokenId else None,
            name=payload.name,
            reason=payload.reason,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=_to_ci_token_record(record), requestId=request_id)


@router.get("/ci-token/status", response_model=ApiResponse[ProjectCiTokenStatusData])
async def get_ci_token_status_(
    projectId: str = Query(...),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[ProjectCiTokenStatusData]:
    project = await get_project_ci_token_status(db, user=user, project_id=uuid.UUID(projectId))
    return ApiResponse(data=_to_ci_token_status(project), requestId=request_id)


@router.put("/ci-token/policy", response_model=ApiResponse[ProjectCiTokenStatusData])
async def update_ci_token_policy_(
    payload: ProjectCiTokenPolicyUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[ProjectCiTokenStatusData]:
    try:
        project = await update_project_ci_token_policy(
            db,
            user=user,
            project_id=uuid.UUID(payload.projectId),
            policy=payload.policy.model_dump(mode="json"),
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=_to_ci_token_status(project), requestId=request_id)


@router.delete("/ci-token", response_model=ApiResponse[ProjectCiTokenStatusData])
async def revoke_ci_token_(
    payload: ProjectCiTokenManageRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[ProjectCiTokenStatusData]:
    try:
        project = await revoke_project_ci_token(db, user=user, project_id=uuid.UUID(payload.projectId), reason=payload.reason)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=_to_ci_token_status(project), requestId=request_id)


@router.post("/ci-token/report-leak", response_model=ApiResponse[ProjectCiTokenStatusData])
async def report_ci_token_leak_(
    payload: ProjectCiTokenManageRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[ProjectCiTokenStatusData]:
    try:
        project = await report_project_ci_token_leak(db, user=user, project_id=uuid.UUID(payload.projectId), reason=payload.reason)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=_to_ci_token_status(project), requestId=request_id)


@router.post("/ci-trigger", response_model=ApiResponse[RunDetailData])
async def ci_trigger_(
    payload: RunCiTriggerRequest,
    ci_token: str | None = Header(default=None, alias="X-CI-Token"),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[RunDetailData]:
    token = str(ci_token or "").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Invalid CI token")
    idem = (idempotency_key or "").strip() or None
    if idem is not None:
        idem = idem[:128]
    env_uuid: uuid.UUID | None = None
    if payload.envId:
        env_uuid = uuid.UUID(payload.envId)
    try:
        run = await create_run_via_ci_token(
            db,
            project_id=uuid.UUID(payload.projectId),
            ci_token=token,
            env_id=env_uuid,
            meta=dict(payload.meta or {}),
            concurrency=payload.concurrency,
            stop_on_failure=payload.stopOnFailure,
            items=[item.model_dump() for item in payload.items],
            notify_rule_id=payload.notifyRuleId,
            idempotency_key=idem,
        )
        await db.commit()
    except CiTokenPolicyDenied:
        try:
            await db.commit()
        except Exception:
            await db.rollback()
            raise
        raise
    except Exception:
        await db.rollback()
        raise
    done, total, passed, failed, skipped = await _load_run_case_metrics(db, run=run)
    return ApiResponse(data=_to_run_detail(run, done, total, passed, failed, skipped), requestId=request_id)


@router.post("", response_model=ApiResponse[RunDetailData])
async def create_(
    payload: RunCreateRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[RunDetailData]:
    idem = (idempotency_key or "").strip() or None
    if idem is not None:
        idem = idem[:128]
    try:
        run = await create_run(
            db,
            user=user,
            project_id=uuid.UUID(payload.projectId),
            suite_id=uuid.UUID(payload.suiteId),
            env_id=uuid.UUID(payload.envId),
            trigger_type=payload.triggerType,
            meta=dict(payload.meta or {}),
            notify_rule_id=payload.notifyRuleId,
            idempotency_key=idem,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    run, done, total, passed, failed, skipped = await get_run(db, user=user, run_id=run.id)
    return ApiResponse(data=_to_run_detail(run, done, total, passed, failed, skipped), requestId=request_id)


@router.get("", response_model=ApiResponse[PageData[RunDetailData]])
async def list_(
    projectId: str | None = Query(default=None),
    status: RunStatus | None = None,
    fromTs: int | None = Query(default=None, alias="from"),
    toTs: int | None = Query(default=None, alias="to"),
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[PageData[RunDetailData]]:
    project_uuid: uuid.UUID | None = None
    if projectId:
        try:
            project_uuid = uuid.UUID(projectId)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid projectId") from exc

    total, rows = await list_runs(
        db,
        user=user,
        project_id=project_uuid,
        status=status,
        from_ts=fromTs,
        to_ts=toTs,
        page=page,
        page_size=pageSize,
    )
    items = [_to_run_detail(run, done, total_, passed, failed, skipped) for run, done, total_, passed, failed, skipped in rows]
    return ApiResponse(data=PageData(page=page, pageSize=pageSize, total=total, items=items), requestId=request_id)


@router.get("/allure-reports", response_model=ApiResponse[PageData[RunAllureReportListItem]])
async def list_allure_reports_(
    projectId: str | None = Query(default=None),
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[PageData[RunAllureReportListItem]]:
    pid = str(projectId or "").strip()
    if not pid:
        raise HTTPException(status_code=400, detail="projectId_required")
    try:
        project_uuid = uuid.UUID(pid)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid projectId") from exc

    where_clause = (
        (Artifact.tenant_id == user.tenant_id)
        & (Run.tenant_id == user.tenant_id)
        & (Run.project_id == project_uuid)
        & (Artifact.type == ArtifactType.LOG_BUNDLE)
        & (Artifact.case_run_id.is_(None))
        & (func.upper(Artifact.meta_json["kind"].astext) == "ALLURE_REPORT")
    )

    ranked = (
        select(
            Artifact.id.label("artifact_id"),
            Artifact.run_id.label("run_id"),
            Artifact.created_at.label("created_at"),
            func.row_number()
            .over(
                partition_by=Artifact.run_id,
                order_by=(Artifact.created_at.desc(), Artifact.id.desc()),
            )
            .label("rn"),
        )
        .join(Run, Run.id == Artifact.run_id)
        .where(where_clause)
        .subquery()
    )

    total = int((await db.execute(select(func.count()).select_from(ranked).where(ranked.c.rn == 1))).scalar_one() or 0)

    stmt = (
        select(Artifact)
        .join(ranked, Artifact.id == ranked.c.artifact_id)
        .where(ranked.c.rn == 1)
        .order_by(ranked.c.created_at.desc())
        .offset((page - 1) * pageSize)
        .limit(pageSize)
    )
    artifact_rows = (await db.execute(stmt)).scalars().all()
    artifact_run_ids = {
        x
        for x in (
            (
                await db.execute(
                    select(Artifact.run_id)
                    .join(Run, Run.id == Artifact.run_id)
                    .where(where_clause)
                    .distinct()
                )
            )
            .scalars()
            .all()
        )
    }
    items = [
        RunAllureReportListItem(
            runId=str(row.run_id),
            createdAt=to_unix_ts(row.created_at),
            name=(row.meta_json.get("name") if isinstance(row.meta_json, dict) else None),
            size=(row.size if row.size is not None else None),
            reportUrl=f"/api/runs/{row.run_id}/allure-report/",
        )
        for row in artifact_rows
    ]

    scan_limit = min(int(pageSize) * 3, 600)
    run_rows = (
        (
            await db.execute(
                select(Run.id, Run.start_at, Run.end_at)
                .where(Run.tenant_id == user.tenant_id, Run.project_id == project_uuid)
                .order_by(Run.start_at.desc().nullslast(), Run.id.desc())
                .offset((page - 1) * pageSize)
                .limit(scan_limit)
            )
        )
        .all()
        or []
    )
    legacy_enabled = _LEGACY_ALLURE_RUNS_ROOT.exists()
    fallback_count = 0
    for run_id, start_at, end_at in run_rows:
        if run_id in artifact_run_ids:
            continue
        _, report_dir = resolve_run_allure_paths(str(run_id))
        report_zip = report_dir.parent / "allure-report.zip"
        found_dir: Path | None = report_dir if report_dir.exists() else None
        found_zip: Path | None = report_zip if report_zip.exists() and report_zip.is_file() else None
        if found_dir is None and found_zip is None and legacy_enabled:
            legacy_run_root = _LEGACY_ALLURE_RUNS_ROOT / str(run_id)
            legacy_report_dir = legacy_run_root / "allure-report"
            legacy_report_zip = legacy_run_root / "allure-report.zip"
            if legacy_report_dir.exists():
                found_dir = legacy_report_dir
            if legacy_report_zip.exists() and legacy_report_zip.is_file():
                found_zip = legacy_report_zip
        if found_dir is None and found_zip is None:
            continue
        created_at = start_at or end_at
        items.append(
            RunAllureReportListItem(
                runId=str(run_id),
                createdAt=to_unix_ts(created_at) if created_at else 0,
                name="allure-report.zip" if found_zip is not None else "allure-report",
                size=(found_zip.stat().st_size if found_zip is not None else None),
                reportUrl=f"/api/runs/{run_id}/allure-report/",
            )
        )
        fallback_count += 1

    items.sort(key=lambda x: int(x.createdAt or 0), reverse=True)
    return ApiResponse(
        data=PageData(page=page, pageSize=pageSize, total=total + fallback_count, items=items[:pageSize]),
        requestId=request_id,
    )


@router.delete("/{runId}/allure-report", response_model=ApiResponse[RunAllureReportDeleteData])
async def delete_allure_report_(
    runId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[RunAllureReportDeleteData]:
    try:
        deleted_artifacts, deleted_files, deleted_dirs = await delete_run_allure_report(db, user=user, run_id=runId)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(
        data=RunAllureReportDeleteData(
            runId=str(runId),
            deletedArtifacts=int(deleted_artifacts),
            deletedFiles=int(deleted_files),
            deletedDirs=int(deleted_dirs),
        ),
        requestId=request_id,
    )


@router.post("/{runId}/allure-report/delete", response_model=ApiResponse[RunAllureReportDeleteData])
async def delete_allure_report_via_post_(
    runId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[RunAllureReportDeleteData]:
    try:
        deleted_artifacts, deleted_files, deleted_dirs = await delete_run_allure_report(db, user=user, run_id=runId)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(
        data=RunAllureReportDeleteData(
            runId=str(runId),
            deletedArtifacts=int(deleted_artifacts),
            deletedFiles=int(deleted_files),
            deletedDirs=int(deleted_dirs),
        ),
        requestId=request_id,
    )


@router.post("/from-testcases", response_model=ApiResponse[RunDetailData])
async def create_from_testcases_(
    payload: RunFromTestcasesRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[RunDetailData]:
    idem = (idempotency_key or "").strip() or None
    if idem is not None:
        idem = idem[:128]
    try:
        run = await create_run_from_testcases(
            db,
            user=user,
            project_id=uuid.UUID(payload.projectId),
            env_id=uuid.UUID(payload.envId),
            trigger_type=payload.triggerType,
            meta=dict(payload.meta or {}),
            concurrency=payload.concurrency,
            stop_on_failure=payload.stopOnFailure,
            items=[item.model_dump() for item in payload.items],
            notify_rule_id=payload.notifyRuleId,
            idempotency_key=idem,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    run, done, total, passed, failed, skipped = await get_run(db, user=user, run_id=run.id)
    return ApiResponse(data=_to_run_detail(run, done, total, passed, failed, skipped), requestId=request_id)


@router.post("/from-testcases-http", response_model=ApiResponse[RunDetailData])
async def create_from_testcases_http_(
    payload: RunFromTestcasesHttpRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[RunDetailData]:
    idem = (idempotency_key or "").strip() or None
    if idem is not None:
        idem = idem[:128]
    env_uuid: uuid.UUID | None = None
    if payload.envId:
        env_uuid = uuid.UUID(payload.envId)
    try:
        run = await create_run_from_testcases_http(
            db,
            user=user,
            project_id=uuid.UUID(payload.projectId),
            env_id=env_uuid,
            trigger_type=payload.triggerType,
            meta=dict(payload.meta or {}),
            concurrency=payload.concurrency,
            stop_on_failure=payload.stopOnFailure,
            items=[item.model_dump() for item in payload.items],
            notify_rule_id=payload.notifyRuleId,
            idempotency_key=idem,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    run, done, total, passed, failed, skipped = await get_run(db, user=user, run_id=run.id)
    return ApiResponse(data=_to_run_detail(run, done, total, passed, failed, skipped), requestId=request_id)


@router.get("/{runId}", response_model=ApiResponse[RunDetailData])
async def get_(
    runId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[RunDetailData]:
    run, done, total, passed, failed, skipped = await get_run(db, user=user, run_id=runId)
    return ApiResponse(data=_to_run_detail(run, done, total, passed, failed, skipped), requestId=request_id)


@router.get("/{runId}/allure-report", include_in_schema=False)
async def redirect_allure_report_(
    runId: uuid.UUID,
) -> RedirectResponse:
    return RedirectResponse(url=f"/api/runs/{runId}/allure-report/")


@router.get("/{runId}/allure-report/", include_in_schema=False)
@router.get("/{runId}/allure-report/{asset_path:path}", include_in_schema=False)
async def get_allure_report_(
    runId: uuid.UUID,
    asset_path: str = "",
    access_token: str | None = Query(default=None, alias="access_token"),
    referer: str | None = Header(default=None, alias="Referer"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
    x_roles: str | None = Header(default=None, alias="X-Roles"),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    user: CurrentUser | None = None
    token = _resolve_token(access_token, referer)
    if token:
        payload = decode_access_token(token)
        user = CurrentUser(id=payload.user_id, tenant_id=payload.tenant_id, roles=payload.roles)
    elif authorization:
        parts = authorization.split(" ", 1)
        if len(parts) == 2 and parts[0].lower() == "bearer" and parts[1].strip():
            payload = decode_access_token(parts[1].strip())
            user = CurrentUser(id=payload.user_id, tenant_id=payload.tenant_id, roles=payload.roles)
    elif x_user_id and x_tenant_id and get_settings().auth_header_impersonation_enabled:
        user = CurrentUser(
            id=uuid.UUID(x_user_id),
            tenant_id=uuid.UUID(x_tenant_id),
            roles=frozenset(r.strip() for r in str(x_roles or "").split(",") if r.strip()),
        )
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    resolved_user = user
    run, _, _, _, _, _ = await get_run(db, user=resolved_user, run_id=runId)
    artifact_rows = (
        await db.execute(
            select(Artifact)
            .where(
                Artifact.tenant_id == resolved_user.tenant_id,
                Artifact.run_id == run.id,
                Artifact.type == ArtifactType.LOG_BUNDLE,
                Artifact.case_run_id.is_(None),
            )
            .order_by(Artifact.created_at.desc())
        )
    ).scalars()
    allure_artifact = next(
        (
            row
            for row in artifact_rows
            if isinstance(row.meta_json, dict) and str(row.meta_json.get("kind") or "").upper() == "ALLURE_REPORT"
        ),
        None,
    )
    artifact_path = Path(str(allure_artifact.storage_url)).expanduser() if allure_artifact is not None else None
    workspace_row = await db.scalar(
        select(Job)
        .where(Job.tenant_id == resolved_user.tenant_id, Job.run_id == run.id)
        .order_by(Job.created_at.desc())
    )
    workspace_value = None
    if workspace_row is not None and isinstance(workspace_row.meta_json, dict):
        workspace_value = workspace_row.meta_json.get("workspace")
    workspace_path = Path(str(workspace_value)).expanduser() if workspace_value else None
    report_dir = _find_allure_report_dir(artifact_path=artifact_path, workspace_path=workspace_path)
    if report_dir is None:
        _, run_report_dir = resolve_run_allure_paths(str(run.id))
        if run_report_dir.exists():
            report_dir = run_report_dir.resolve()
    if report_dir is None and _LEGACY_ALLURE_RUNS_ROOT.exists():
        legacy_dir = (_LEGACY_ALLURE_RUNS_ROOT / str(run.id) / "allure-report").resolve()
        if legacy_dir.exists():
            report_dir = legacy_dir
    if report_dir is None:
        raise HTTPException(status_code=404, detail="Allure report not found")
    try:
        target = _safe_resolve_report_file(report_dir, asset_path)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Allure report file not found") from exc
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="Allure report file not found")
    media_type = mimetypes.guess_type(str(target))[0]
    return FileResponse(path=target, media_type=media_type)


@router.post("/{runId}/allure-report/generate", response_model=ApiResponse[RunAllureReportGenerateData])
async def generate_allure_report_(
    runId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[RunAllureReportGenerateData]:
    run, _, _, _, _, _ = await get_run(db, user=user, run_id=runId)
    job = await db.scalar(
        select(Job)
        .where(Job.tenant_id == user.tenant_id, Job.run_id == run.id)
        .order_by(Job.created_at.desc())
        .limit(1)
    )
    timeout_sec = 600
    if job is not None and isinstance(job.meta_json, dict):
        suite_cfg = dict(job.meta_json.get("suiteConfig") or {})
        timeout_value = suite_cfg.get("timeoutSec")
        if isinstance(timeout_value, int | float):
            timeout_sec = int(timeout_value)
    output = await asyncio.to_thread(generate_allure_report_for_run, str(run.id), timeout_sec=max(timeout_sec, 1))
    results_path, report_path = resolve_run_allure_paths(str(run.id))
    run_summary = dict(run.summary_json or {})
    execution_result = dict(run_summary.get("executionResult") or {})
    if output.error_code:
        execution_result["reportStatus"] = "FAILED"
        execution_result["reportErrorCode"] = output.error_code
        execution_result["reportMessage"] = (output.stderr or output.stdout or "").strip()[:2000] or output.error_code
        run_summary["executionResult"] = execution_result
        run.summary_json = run_summary
        await db.flush()
        await db.commit()
        return ApiResponse(
            data=RunAllureReportGenerateData(
                runId=str(run.id),
                reportStatus="FAILED",
                resultsPath=str(results_path),
                reportPath=str(report_path),
                errorCode=output.error_code,
                errorMessage=(output.stderr or output.stdout or "").strip()[:2000] or output.error_code,
            ),
            requestId=request_id,
        )
    if output.report_dir is None or not output.report_dir.exists():
        raise HTTPException(status_code=404, detail="Allure report not found")
    zip_path = _zip_allure_report_dir(output.report_dir)
    report_meta = {"name": "allure-report.zip", "kind": "ALLURE_REPORT", "size": zip_path.stat().st_size}
    existing_report_artifact = await db.scalar(
        select(Artifact)
        .where(
            Artifact.tenant_id == user.tenant_id,
            Artifact.run_id == run.id,
            Artifact.type == ArtifactType.LOG_BUNDLE,
            Artifact.case_run_id.is_(None),
        )
        .order_by(Artifact.created_at.desc())
    )
    if existing_report_artifact is not None and isinstance(existing_report_artifact.meta_json, dict):
        kind = str(existing_report_artifact.meta_json.get("kind") or "").upper()
        if kind == "ALLURE_REPORT":
            existing_report_artifact.storage_url = str(zip_path)
            existing_report_artifact.size = zip_path.stat().st_size
            existing_report_artifact.meta_json = report_meta
        else:
            existing_report_artifact = None
    if existing_report_artifact is None:
        db.add(
            Artifact(
                tenant_id=user.tenant_id,
                run_id=run.id,
                case_run_id=None,
                type=ArtifactType.LOG_BUNDLE,
                storage_url=str(zip_path),
                size=zip_path.stat().st_size,
                meta_json=report_meta,
            )
        )
    execution_result["reportStatus"] = "READY"
    execution_result["reportErrorCode"] = None
    execution_result["reportMessage"] = None
    execution_result["reportPath"] = str(output.report_dir)
    run_summary["executionResult"] = execution_result
    run.summary_json = run_summary
    await db.flush()
    await db.commit()
    return ApiResponse(
        data=RunAllureReportGenerateData(
            runId=str(run.id),
            reportStatus="READY",
            reportUrl=f"/api/runs/{run.id}/allure-report/",
            resultsPath=str(results_path),
            reportPath=str(report_path),
        ),
        requestId=request_id,
    )


@router.get("/{runId}/case-runs", response_model=ApiResponse[PageData[CaseRunListItem]])
async def list_case_runs_(
    runId: uuid.UUID,
    status: CaseRunStatus | None = None,
    page: int = Query(1, ge=1),
    pageSize: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[PageData[CaseRunListItem]]:
    run, total, rows = await list_case_runs(db, user=user, run_id=runId, status=status, page=page, page_size=pageSize)
    binding_snapshots = ((run.summary_json or {}).get("bindingSnapshots") or {}) if isinstance(run.summary_json, dict) else {}
    items = [
        CaseRunListItem(
            caseRunId=str(cr.id),
            testcaseId=str(cr.testcase_id),
            status=cr.status,
            startAt=to_unix_ts(cr.start_at) if cr.start_at else None,
            endAt=to_unix_ts(cr.end_at) if cr.end_at else None,
            errorType=cr.error_type,
            errorMessage=cr.error_message,
            bindingSnapshot=binding_snapshots.get(str(cr.id)),
        )
        for cr in rows
    ]
    return ApiResponse(data=PageData(page=page, pageSize=pageSize, total=total, items=items), requestId=request_id)


@router.post("/{runId}/cancel", response_model=ApiResponse[RunCancelResponseData])
async def cancel_(
    runId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[RunCancelResponseData]:
    try:
        run = await cancel_run(db, user=user, run_id=runId)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=RunCancelResponseData(runId=str(run.id), status=run.status), requestId=request_id)


@router.post("/{runId}/retry", response_model=ApiResponse[RunDetailData])
async def retry_(
    runId: uuid.UUID,
    payload: RunRetryRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[RunDetailData]:
    idem = (idempotency_key or "").strip() or None
    if idem is not None:
        idem = idem[:128]
    try:
        new_run = await retry_run(
            db,
            user=user,
            run_id=runId,
            failed_only=bool(payload.failedOnly),
            idempotency_key=idem,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    run, done, total, passed, failed, skipped = await get_run(db, user=user, run_id=new_run.id)
    return ApiResponse(data=_to_run_detail(run, done, total, passed, failed, skipped), requestId=request_id)
