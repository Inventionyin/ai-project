from __future__ import annotations

from pydantic import Field

from app.models.enums import ArtifactType, CaseRunStatus, JobStatus, RunStatus, TriggerType
from app.schemas.common import BaseSchema, PageData
from app.schemas.types import IdStr, UnixTs


class RunCreateRequest(BaseSchema):
    projectId: IdStr
    suiteId: IdStr
    envId: IdStr
    triggerType: TriggerType
    meta: dict[str, object] = Field(default_factory=dict)
    notifyRuleId: IdStr | None = None


class RunFromTestcasesItem(BaseSchema):
    testcaseId: IdStr
    bindingId: IdStr
    overrideParams: dict[str, object] = Field(default_factory=dict)


class RunFromTestcasesRequest(BaseSchema):
    projectId: IdStr
    envId: IdStr
    triggerType: TriggerType
    meta: dict[str, object] = Field(default_factory=dict)
    concurrency: int = Field(default=10, ge=1, le=100)
    stopOnFailure: bool = False
    items: list[RunFromTestcasesItem] = Field(min_length=1, max_length=10_000)
    notifyRuleId: IdStr | None = None


class RunFromTestcasesHttpItem(BaseSchema):
    testcaseId: IdStr
    overrideParams: dict[str, object] = Field(default_factory=dict)


class RunFromTestcasesHttpRequest(BaseSchema):
    projectId: IdStr
    envId: IdStr | None = None
    triggerType: TriggerType
    meta: dict[str, object] = Field(default_factory=dict)
    concurrency: int = Field(default=10, ge=1, le=100)
    stopOnFailure: bool = False
    items: list[RunFromTestcasesHttpItem] = Field(min_length=1, max_length=10_000)
    notifyRuleId: IdStr | None = None


class ProjectCiTokenManageRequest(BaseSchema):
    projectId: IdStr


class ProjectCiTokenPolicyData(BaseSchema):
    allowedRunnerTypes: list[str] = Field(default_factory=list, max_length=20)
    allowedTestCaseIds: list[IdStr] = Field(default_factory=list, max_length=10_000)
    maxTestCaseCount: int | None = Field(default=None, ge=1, le=10_000)


class ProjectCiTokenRotateRequest(ProjectCiTokenManageRequest):
    policy: ProjectCiTokenPolicyData | None = None


class ProjectCiTokenPolicyUpdateRequest(ProjectCiTokenManageRequest):
    policy: ProjectCiTokenPolicyData


class ProjectCiTokenRotateData(BaseSchema):
    projectId: IdStr
    token: str
    hint: str
    rotatedAt: UnixTs
    policy: ProjectCiTokenPolicyData = Field(default_factory=ProjectCiTokenPolicyData)


class ProjectCiTokenStatusData(BaseSchema):
    projectId: IdStr
    enabled: bool
    hint: str | None = None
    rotatedAt: UnixTs | None = None
    lastUsedAt: UnixTs | None = None
    rotatedBy: IdStr | None = None
    policy: ProjectCiTokenPolicyData = Field(default_factory=ProjectCiTokenPolicyData)


class RunCiTriggerRequest(BaseSchema):
    projectId: IdStr
    envId: IdStr | None = None
    meta: dict[str, object] = Field(default_factory=dict)
    concurrency: int = Field(default=10, ge=1, le=100)
    stopOnFailure: bool = False
    items: list[RunFromTestcasesHttpItem] = Field(min_length=1, max_length=10_000)
    notifyRuleId: IdStr | None = None


class RunProgress(BaseSchema):
    done: int = Field(ge=0)
    total: int = Field(ge=0)


class RunMetrics(BaseSchema):
    total: int = Field(ge=0)
    done: int = Field(ge=0)
    passed: int = Field(ge=0)
    failed: int = Field(ge=0)
    skipped: int = Field(ge=0)


class RunDetailData(BaseSchema):
    id: IdStr
    status: RunStatus
    progress: RunProgress
    triggerType: TriggerType | None = None
    executionSource: str | None = None
    metrics: RunMetrics | None = None
    suiteId: IdStr
    envId: IdStr | None = None
    startAt: UnixTs


class RunListQuery(BaseSchema):
    projectId: IdStr
    status: RunStatus | None = None
    fromTs: UnixTs | None = Field(default=None, alias="from")
    toTs: UnixTs | None = Field(default=None, alias="to")
    page: int = Field(default=1, ge=1)
    pageSize: int = Field(default=20, ge=1, le=200)


class CaseRunListQuery(BaseSchema):
    status: CaseRunStatus | None = None
    page: int = Field(default=1, ge=1)
    pageSize: int = Field(default=50, ge=1, le=200)


class ArtifactIndex(BaseSchema):
    type: ArtifactType
    storageKey: str = Field(min_length=1, max_length=1024)
    meta: dict[str, object] = Field(default_factory=dict)


class CaseRunMetrics(BaseSchema):
    durationMs: int = Field(ge=0)


class CaseRunResult(BaseSchema):
    caseRunId: IdStr
    status: CaseRunStatus
    startAt: UnixTs
    endAt: UnixTs | None = None
    errorType: str | None = Field(default=None, max_length=64)
    errorMessage: str | None = Field(default=None, max_length=2000)
    logs: list[str] = Field(default_factory=list, max_length=10_000)
    artifacts: list[ArtifactIndex] = Field(default_factory=list, max_length=2000)
    metrics: CaseRunMetrics | None = None


class CaseRunListItem(BaseSchema):
    caseRunId: IdStr
    testcaseId: IdStr
    status: CaseRunStatus
    startAt: UnixTs | None = None
    endAt: UnixTs | None = None
    errorType: str | None = Field(default=None, max_length=64)
    errorMessage: str | None = Field(default=None, max_length=2000)
    bindingSnapshot: dict[str, object] | None = None


class CaseRunListData(PageData[CaseRunListItem]):
    pass


class RunCancelResponseData(BaseSchema):
    runId: IdStr
    status: RunStatus


class RunRetryRequest(BaseSchema):
    failedOnly: bool = Field(default=True)


class RunAllureReportGenerateData(BaseSchema):
    runId: IdStr
    reportStatus: str
    reportUrl: str | None = None
    reportPath: str | None = None
    resultsPath: str | None = None
    errorCode: str | None = None
    errorMessage: str | None = None


class RunAllureReportListItem(BaseSchema):
    runId: IdStr
    createdAt: UnixTs
    name: str | None = None
    size: int | None = Field(default=None, ge=0)
    reportUrl: str


class RunAllureReportDeleteData(BaseSchema):
    runId: IdStr
    deletedArtifacts: int = Field(ge=0)
    deletedFiles: int = Field(ge=0)
    deletedDirs: int = Field(ge=0)


class RunDebugRequest(BaseSchema):
    projectId: IdStr
    testcaseId: IdStr
    envId: IdStr
    params: dict[str, object] = Field(default_factory=dict)


class JobReportSummary(BaseSchema):
    jobStatus: JobStatus
