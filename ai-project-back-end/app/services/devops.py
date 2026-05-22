from __future__ import annotations

import hashlib
import hmac
import logging
import re
import uuid
from urllib.parse import quote

import requests as http_requests
from fastapi import HTTPException
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.models.devops_pipeline import DevOpsPipeline, DevOpsRun
from app.models.enums import DevOpsPipelineStatus, DevOpsRunStatus, ProjectRole
from app.models.project import Project, ProjectMember
from app.schemas.devops import DevOpsPipelineDetail, DevOpsRunDetail, DevOpsTriggerConfigDiagnostics
from app.services.platform_record import create_audit_log
from app.services.security_policy import mask_sensitive_fields

logger = logging.getLogger(__name__)

_DEVOPS_CALLBACK_EXTERNAL_ID_PARAM = "WEITESTING_EXTERNAL_RUN_ID"
_SENSITIVE_VALUE_KEYS = (
    "token",
    "secret",
    "password",
    "authorization",
    "api_key",
    "apikey",
    "github_token",
    "githubToken",
    "jenkins_api_token",
    "jenkinsApiToken",
    "api_token",
    "apiToken",
    "trigger_token",
    "triggerToken",
)


def _is_admin(user: CurrentUser) -> bool:
    return "Admin" in user.roles or "ADMIN" in user.roles


async def _get_project(db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID) -> Project:
    project = await db.scalar(select(Project).where(Project.id == project_id, Project.tenant_id == user.tenant_id))
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


async def _require_project_write(db: AsyncSession, *, user: CurrentUser, project: Project) -> None:
    if _is_admin(user) or project.owner_id == user.id:
        return
    role = (await db.execute(
        select(ProjectMember.role).where(
            ProjectMember.project_id == project.id,
            ProjectMember.user_id == user.id,
            ProjectMember.tenant_id == user.tenant_id,
        )
    )).scalar_one_or_none()
    if role in (ProjectRole.ADMIN, ProjectRole.OWNER, ProjectRole.EDITOR):
        return
    raise HTTPException(status_code=403, detail="No write access to this project")


async def _require_project_read(db: AsyncSession, *, user: CurrentUser, project: Project) -> None:
    if _is_admin(user) or project.owner_id == user.id:
        return
    role = (await db.execute(
        select(ProjectMember.role).where(
            ProjectMember.project_id == project.id,
            ProjectMember.user_id == user.id,
            ProjectMember.tenant_id == user.tenant_id,
        )
    )).scalar_one_or_none()
    if role in (ProjectRole.ADMIN, ProjectRole.OWNER, ProjectRole.EDITOR, ProjectRole.VIEWER):
        return
    raise HTTPException(status_code=403, detail="No access to this project")


def _to_pipeline_detail(row: DevOpsPipeline) -> DevOpsPipelineDetail:
    config = dict(row.config_json) if row.config_json else None
    return DevOpsPipelineDetail(
        id=str(row.id),
        projectId=str(row.project_id),
        name=row.name,
        provider=row.provider,
        repoFullName=row.repo_full_name,
        workflowFile=row.workflow_file,
        config=mask_sensitive_fields(config) if config else None,
        enabled=row.enabled,
        status=row.status,
        createdBy=str(row.created_by) if row.created_by else None,
        createdAt=int(row.created_at.timestamp()),
        updatedAt=int(row.updated_at.timestamp()),
    )


def _to_run_detail(row: DevOpsRun) -> DevOpsRunDetail:
    return DevOpsRunDetail(
        id=str(row.id),
        projectId=str(row.project_id),
        pipelineId=str(row.pipeline_id),
        externalRunId=row.external_run_id,
        status=row.status,
        triggerType=row.trigger_type,
        commitSha=row.commit_sha,
        branch=row.branch,
        errorMessage=row.error_message,
        logUrl=row.log_url,
        meta=dict(row.meta_json) if row.meta_json else None,
        createdBy=str(row.created_by) if row.created_by else None,
        createdAt=int(row.created_at.timestamp()),
        updatedAt=int(row.updated_at.timestamp()),
    )


def _jenkins_job_path(job_name: str) -> str:
    parts = [part.strip("/") for part in job_name.split("/") if part.strip("/")]
    if not parts:
        raise HTTPException(status_code=400, detail="Jenkins job name is required")
    return "/".join(f"job/{quote(part)}" for part in parts)


def _first_config_value(config: dict, *keys: str) -> object | None:
    for key in keys:
        value = config.get(key)
        if value is not None and str(value).strip():
            return value
    return None


def _request_auth_from_config(config: dict) -> tuple[str, str] | None:
    username = str(config.get("username") or "").strip()
    api_token = str(_first_config_value(config, "api_token", "apiToken", "jenkins_api_token", "jenkinsApiToken") or "").strip()
    if username and api_token:
        return username, api_token
    return None


def _sanitize_error_message(message: str, pipeline: DevOpsPipeline) -> str:
    sanitized = message
    config = pipeline.config_json or {}
    secret_values: list[str] = []
    for key in _SENSITIVE_VALUE_KEYS:
        value = config.get(key)
        if value:
            secret_values.append(str(value))
    for value in secret_values:
        if value:
            sanitized = sanitized.replace(value, "***REDACTED***")
    sanitized = re.sub(
        r"(?i)\b(?:token|secret|password|api[_-]?key|api[_-]?token|authorization)\s*[:=]\s*([^\s,;]+)",
        lambda m: m.group(0).replace(m.group(1), "***REDACTED***"),
        sanitized,
    )
    return sanitized[:500]


def validate_pipeline_trigger_config(pipeline: DevOpsPipeline) -> DevOpsTriggerConfigDiagnostics:
    provider = pipeline.provider or ""
    config = pipeline.config_json or {}
    missing: list[str] = []
    if provider == "github_actions":
        if not str(pipeline.repo_full_name or "").strip():
            missing.append("repoFullName")
        if not str(pipeline.workflow_file or "").strip():
            missing.append("workflowFile")
        if not str(_first_config_value(config, "github_token", "githubToken") or "").strip():
            missing.append("config.github_token")
    elif provider == "jenkins":
        base_url = str(_first_config_value(config, "jenkins_url", "jenkinsUrl", "base_url", "baseUrl") or "").strip()
        job_name = str(_first_config_value(config, "job_name", "jobName") or pipeline.workflow_file or "").strip()
        if not base_url:
            missing.append("config.base_url")
        if not job_name:
            missing.append("config.job_name|workflowFile")
    return DevOpsTriggerConfigDiagnostics(ok=not missing, provider=provider, missing=missing)


def _trigger_github_actions(
    *,
    pipeline: DevOpsPipeline,
    branch: str | None,
    params: dict | None,
    external_run_id: str,
) -> tuple[bool, str | None, str | None]:
    config = pipeline.config_json or {}
    gh_token = str(_first_config_value(config, "github_token", "githubToken") or "").strip()
    if not gh_token:
        return False, "GitHub token is required", None
    default_branch = str(_first_config_value(config, "default_branch", "defaultBranch") or "main").strip()
    inputs = dict(params or {})
    inputs.setdefault("weitestingExternalRunId", external_run_id)
    resp = http_requests.post(
        f"https://api.github.com/repos/{pipeline.repo_full_name}/actions/workflows/{pipeline.workflow_file}/dispatches",
        headers={"Authorization": f"Bearer {gh_token}", "Accept": "application/vnd.github+json"},
        json={"ref": branch or default_branch or "main", "inputs": inputs},
        timeout=10,
    )
    if resp.status_code in (200, 201, 204):
        return True, None, None
    return False, _sanitize_error_message(f"GitHub API error: {resp.status_code} {resp.text}", pipeline), None


def _trigger_jenkins(
    *,
    pipeline: DevOpsPipeline,
    params: dict | None,
    external_run_id: str,
) -> tuple[bool, str | None, str | None]:
    config = pipeline.config_json or {}
    base_url = str(_first_config_value(config, "jenkins_url", "jenkinsUrl", "base_url", "baseUrl") or "").strip().rstrip("/")
    job_name = str(_first_config_value(config, "job_name", "jobName") or pipeline.workflow_file or pipeline.repo_full_name or "").strip()
    if not base_url:
        return False, "Jenkins base URL is required", None
    job_path = _jenkins_job_path(job_name)
    request_params = dict(params or {})
    request_params.setdefault(_DEVOPS_CALLBACK_EXTERNAL_ID_PARAM, external_run_id)
    trigger_token = str(_first_config_value(config, "trigger_token", "triggerToken") or "").strip()
    if trigger_token:
        request_params.setdefault("token", trigger_token)
    crumb = str(config.get("crumb") or "").strip()
    headers = {"Jenkins-Crumb": crumb} if crumb else None
    auth = _request_auth_from_config(config)
    endpoint = "buildWithParameters" if request_params else "build"
    resp = http_requests.post(
        f"{base_url}/{job_path}/{endpoint}",
        params=request_params,
        headers=headers,
        auth=auth,
        timeout=10,
    )
    if resp.status_code in (200, 201, 202, 204):
        return True, None, resp.headers.get("Location")
    return False, _sanitize_error_message(f"Jenkins API error: {resp.status_code} {resp.text}", pipeline), None


async def create_pipeline(
    db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID,
    name: str, provider: str = "github_actions",
    repo_full_name: str | None = None, workflow_file: str | None = None,
    config: dict | None = None, webhook_secret: str | None = None,
) -> DevOpsPipelineDetail:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)
    row = DevOpsPipeline(
        tenant_id=user.tenant_id, project_id=project_id, name=name,
        provider=provider, repo_full_name=repo_full_name, workflow_file=workflow_file,
        config_json=config, webhook_secret=webhook_secret, created_by=user.id,
    )
    db.add(row)
    await db.flush()
    await create_audit_log(
        db, user=user, project_id=project_id,
        action="CREATE_DEVOPS_PIPELINE", resource_type="devops_pipeline",
        resource_id=str(row.id), summary=f"创建 DevOps 流水线: {name}",
    )
    return _to_pipeline_detail(row)


async def list_pipelines(
    db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID,
    page: int, page_size: int,
) -> tuple[int, list[DevOpsPipelineDetail]]:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)
    base = select(DevOpsPipeline).where(
        DevOpsPipeline.tenant_id == user.tenant_id,
        DevOpsPipeline.project_id == project_id,
    )
    total = int((await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one() or 0)
    rows = (await db.execute(base.order_by(desc(DevOpsPipeline.created_at)).offset((page - 1) * page_size).limit(page_size))).scalars().all()
    return total, [_to_pipeline_detail(r) for r in rows]


async def get_pipeline(
    db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID, pipeline_id: uuid.UUID,
) -> DevOpsPipelineDetail:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)
    row = await db.scalar(select(DevOpsPipeline).where(
        DevOpsPipeline.id == pipeline_id,
        DevOpsPipeline.project_id == project_id,
        DevOpsPipeline.tenant_id == user.tenant_id,
    ))
    if row is None:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return _to_pipeline_detail(row)


async def update_pipeline(
    db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID, pipeline_id: uuid.UUID,
    **kwargs,
) -> DevOpsPipelineDetail:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)
    row = await db.scalar(select(DevOpsPipeline).where(
        DevOpsPipeline.id == pipeline_id,
        DevOpsPipeline.project_id == project_id,
        DevOpsPipeline.tenant_id == user.tenant_id,
    ))
    if row is None:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    for key, value in kwargs.items():
        if value is not None:
            if key == "repo_full_name":
                row.repo_full_name = value
            elif key == "workflow_file":
                row.workflow_file = value
            elif key == "config":
                row.config_json = value
            elif key == "webhook_secret":
                row.webhook_secret = value
            elif key == "enabled":
                row.enabled = value
            elif key == "name":
                row.name = value
    await db.flush()
    return _to_pipeline_detail(row)


async def delete_pipeline(
    db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID, pipeline_id: uuid.UUID,
) -> None:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)
    row = await db.scalar(select(DevOpsPipeline).where(
        DevOpsPipeline.id == pipeline_id,
        DevOpsPipeline.project_id == project_id,
        DevOpsPipeline.tenant_id == user.tenant_id,
    ))
    if row is None:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    await db.delete(row)
    await db.flush()


async def trigger_pipeline(
    db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID, pipeline_id: uuid.UUID,
    branch: str | None = None, commit_sha: str | None = None, params: dict | None = None,
) -> DevOpsRunDetail:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)
    pipeline = await db.scalar(select(DevOpsPipeline).where(
        DevOpsPipeline.id == pipeline_id,
        DevOpsPipeline.project_id == project_id,
        DevOpsPipeline.tenant_id == user.tenant_id,
    ))
    if pipeline is None:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    if not pipeline.enabled:
        raise HTTPException(status_code=400, detail="Pipeline is disabled")
    diagnostics = validate_pipeline_trigger_config(pipeline)
    if not diagnostics.ok:
        raise HTTPException(
            status_code=400,
            detail=f"Pipeline trigger configuration invalid: missing {', '.join(diagnostics.missing)}",
        )
    external_run_id = str(uuid.uuid4())
    run = DevOpsRun(
        tenant_id=user.tenant_id, project_id=project_id,
        pipeline_id=pipeline_id, status=DevOpsRunStatus.PENDING.value,
        external_run_id=external_run_id,
        trigger_type="manual", branch=branch, commit_sha=commit_sha,
        meta_json=params, created_by=user.id,
    )
    db.add(run)
    pipeline.status = DevOpsPipelineStatus.RUNNING.value
    await db.flush()
    if pipeline.provider == "github_actions":
        try:
            ok, error_message, log_url = _trigger_github_actions(
                pipeline=pipeline,
                branch=branch,
                params=params,
                external_run_id=external_run_id,
            )
            run.status = DevOpsRunStatus.RUNNING.value if ok else DevOpsRunStatus.FAILED.value
            run.error_message = error_message
            run.log_url = log_url
        except Exception as exc:
            run.status = DevOpsRunStatus.FAILED.value
            run.error_message = _sanitize_error_message(str(exc), pipeline)
    elif pipeline.provider == "jenkins":
        try:
            ok, error_message, log_url = _trigger_jenkins(
                pipeline=pipeline,
                params=params,
                external_run_id=external_run_id,
            )
            run.status = DevOpsRunStatus.RUNNING.value if ok else DevOpsRunStatus.FAILED.value
            run.error_message = error_message
            run.log_url = log_url
        except Exception as exc:
            run.status = DevOpsRunStatus.FAILED.value
            run.error_message = _sanitize_error_message(str(exc), pipeline)
    await db.flush()
    await create_audit_log(
        db, user=user, project_id=project_id,
        action="TRIGGER_DEVOPS_PIPELINE", resource_type="devops_run",
        resource_id=str(run.id), summary=f"触发 DevOps 流水线: {pipeline.name}",
    )
    return _to_run_detail(run)


async def list_runs(
    db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID,
    pipeline_id: uuid.UUID | None = None, page: int = 1, page_size: int = 20,
) -> tuple[int, list[DevOpsRunDetail]]:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)
    base = select(DevOpsRun).where(
        DevOpsRun.tenant_id == user.tenant_id,
        DevOpsRun.project_id == project_id,
    )
    if pipeline_id:
        base = base.where(DevOpsRun.pipeline_id == pipeline_id)
    total = int((await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one() or 0)
    rows = (await db.execute(base.order_by(desc(DevOpsRun.created_at)).offset((page - 1) * page_size).limit(page_size))).scalars().all()
    return total, [_to_run_detail(r) for r in rows]


async def handle_callback(
    db: AsyncSession, *,
    project_id: uuid.UUID,
    external_run_id: str, status: str,
    webhook_secret: str | None = None,
    signature: str | None = None,
    raw_body: bytes | None = None,
    commit_sha: str | None = None, branch: str | None = None,
    error_message: str | None = None, log_url: str | None = None,
    meta: dict | None = None,
) -> DevOpsRunDetail:
    run = await db.scalar(select(DevOpsRun).where(
        DevOpsRun.external_run_id == external_run_id,
        DevOpsRun.project_id == project_id,
    ))
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    pipeline = await db.scalar(select(DevOpsPipeline).where(DevOpsPipeline.id == run.pipeline_id))
    if pipeline is None:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    if pipeline.webhook_secret:
        secret_ok = webhook_secret and hmac.compare_digest(webhook_secret, pipeline.webhook_secret)
        signature_ok = False
        if signature and raw_body:
            expected = "sha256=" + hmac.new(
                pipeline.webhook_secret.encode("utf-8"),
                raw_body,
                hashlib.sha256,
            ).hexdigest()
            signature_ok = hmac.compare_digest(signature, expected)
        if not secret_ok and not signature_ok:
            raise HTTPException(status_code=403, detail="Invalid webhook secret")
    run.status = status
    if commit_sha:
        run.commit_sha = commit_sha
    if branch:
        run.branch = branch
    if error_message:
        run.error_message = error_message
    if log_url:
        run.log_url = log_url
    if meta:
        run.meta_json = meta
    if pipeline and status in (DevOpsRunStatus.SUCCESS.value, DevOpsRunStatus.FAILED.value):
        pipeline.status = DevOpsPipelineStatus.IDLE.value if status == DevOpsRunStatus.SUCCESS.value else DevOpsPipelineStatus.FAILED.value
    await db.flush()
    return _to_run_detail(run)
