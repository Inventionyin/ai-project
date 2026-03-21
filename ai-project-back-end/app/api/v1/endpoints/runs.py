from __future__ import annotations

import asyncio
import mimetypes
import uuid
import zipfile
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_request_id, to_unix_ts
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.enums import ArtifactType, CaseRunStatus, RunStatus
from app.models.run import Artifact, Job, Run
from app.schemas.common import ApiResponse, PageData
from app.schemas.run import (
    CaseRunListItem,
    RunAllureReportGenerateData,
    RunAllureReportDeleteData,
    RunAllureReportListItem,
    RunCancelResponseData,
    RunCreateRequest,
    RunDetailData,
    RunFromTestcasesHttpRequest,
    RunFromTestcasesRequest,
    RunProgress,
    RunRetryRequest,
)
from app.services.run import (
    cancel_run,
    create_run,
    create_run_from_testcases,
    create_run_from_testcases_http,
    delete_run_allure_report,
    get_run,
    list_case_runs,
    list_runs,
    retry_run,
)
from app.services.runner_pytest_allure import generate_allure_report_for_run, resolve_run_allure_paths

router = APIRouter(prefix="/runs")


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


def _to_run_detail(run, done: int, total: int) -> RunDetailData:
    if run.suite_id is None:
        raise HTTPException(status_code=500, detail="Run data invalid")
    start_at = run.start_at or run.created_at
    return RunDetailData(
        id=str(run.id),
        status=run.status,
        progress=RunProgress(done=done, total=total),
        suiteId=str(run.suite_id),
        envId=str(run.env_id) if run.env_id else None,
        startAt=to_unix_ts(start_at),
    )


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

    run, done, total = await get_run(db, user=user, run_id=run.id)
    return ApiResponse(data=_to_run_detail(run, done, total), requestId=request_id)


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
    items = [_to_run_detail(run, done, total_) for run, done, total_ in rows]
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

    count_stmt = select(func.count()).select_from(
        select(Artifact.id)
        .join(Run, Run.id == Artifact.run_id)
        .where(where_clause)
        .subquery()
    )
    total = int((await db.execute(count_stmt)).scalar_one() or 0)

    stmt = (
        select(Artifact)
        .join(Run, Run.id == Artifact.run_id)
        .where(where_clause)
        .order_by(Artifact.created_at.desc())
        .offset((page - 1) * pageSize)
        .limit(pageSize)
    )
    artifact_rows = (await db.execute(stmt)).scalars().all()
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
    return ApiResponse(data=PageData(page=page, pageSize=pageSize, total=total, items=items), requestId=request_id)


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
    run, done, total = await get_run(db, user=user, run_id=run.id)
    return ApiResponse(data=_to_run_detail(run, done, total), requestId=request_id)


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
    run, done, total = await get_run(db, user=user, run_id=run.id)
    return ApiResponse(data=_to_run_detail(run, done, total), requestId=request_id)


@router.get("/{runId}", response_model=ApiResponse[RunDetailData])
async def get_(
    runId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[RunDetailData]:
    run, done, total = await get_run(db, user=user, run_id=runId)
    return ApiResponse(data=_to_run_detail(run, done, total), requestId=request_id)


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
    elif x_user_id and x_tenant_id:
        user = CurrentUser(
            id=uuid.UUID(x_user_id),
            tenant_id=uuid.UUID(x_tenant_id),
            roles=frozenset(r.strip() for r in str(x_roles or "").split(",") if r.strip()),
        )
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    resolved_user = user
    run, _, _ = await get_run(db, user=resolved_user, run_id=runId)
    artifact_rows = (
        await db.execute(
            select(Artifact)
            .where(
                Artifact.tenant_id == resolved_user.tenant_id,
                Artifact.run_id == run.id,
                Artifact.type == ArtifactType.LOG_BUNDLE,
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
    run, _, _ = await get_run(db, user=user, run_id=runId)
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

    run, done, total = await get_run(db, user=user, run_id=new_run.id)
    return ApiResponse(data=_to_run_detail(run, done, total), requestId=request_id)
