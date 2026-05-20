from __future__ import annotations

from app.schemas.common import BaseSchema


class DevOpsPipelineCreateRequest(BaseSchema):
    name: str
    provider: str = "github_actions"
    repoFullName: str | None = None
    workflowFile: str | None = None
    config: dict | None = None
    webhookSecret: str | None = None


class DevOpsPipelineUpdateRequest(BaseSchema):
    name: str | None = None
    repoFullName: str | None = None
    workflowFile: str | None = None
    config: dict | None = None
    webhookSecret: str | None = None
    enabled: bool | None = None


class DevOpsPipelineDetail(BaseSchema):
    id: str
    projectId: str
    name: str
    provider: str
    repoFullName: str | None = None
    workflowFile: str | None = None
    config: dict | None = None
    enabled: bool
    status: str
    createdBy: str | None = None
    createdAt: int
    updatedAt: int


class DevOpsRunDetail(BaseSchema):
    id: str
    projectId: str
    pipelineId: str
    externalRunId: str | None = None
    status: str
    triggerType: str
    commitSha: str | None = None
    branch: str | None = None
    errorMessage: str | None = None
    logUrl: str | None = None
    meta: dict | None = None
    createdBy: str | None = None
    createdAt: int
    updatedAt: int


class DevOpsTriggerRequest(BaseSchema):
    branch: str | None = None
    commitSha: str | None = None
    params: dict | None = None


class DevOpsCallbackRequest(BaseSchema):
    externalRunId: str
    status: str
    commitSha: str | None = None
    branch: str | None = None
    errorMessage: str | None = None
    logUrl: str | None = None
    meta: dict | None = None


class DevOpsTriggerConfigDiagnostics(BaseSchema):
    ok: bool
    provider: str
    missing: list[str] = []
