from __future__ import annotations

from typing import Annotated
from typing import Literal

from pydantic import Field

from app.schemas.common import BaseSchema, PageData
from app.schemas.types import IdStr, TitleStr, UnixTs, UrlStr

LabelStr = Annotated[str, Field(min_length=1, max_length=64)]
NotificationChannel = Literal["WEBHOOK", "EMAIL", "IM"]
NotificationDiagnosticsStatus = Literal["BLOCKED", "WARN", "READY"]
NotificationDiagnosticsCheckLevel = Literal["BLOCKER", "WARNING", "READY"]


class IssueCreateRequest(BaseSchema):
    projectId: IdStr
    runId: IdStr
    caseRunId: IdStr | None = None
    title: TitleStr
    description: str | None = Field(default=None, max_length=10_000)
    labels: list[LabelStr] = Field(default_factory=list, max_length=50)


class IssueCreateData(BaseSchema):
    issueId: IdStr
    url: UrlStr | None = None


class NotificationConfigCreateRequest(BaseSchema):
    channel: NotificationChannel
    target: Annotated[str, Field(min_length=1, max_length=2048)]
    rule: dict[str, object] = Field(default_factory=dict)
    enabled: bool = True


class NotificationConfigUpdateRequest(BaseSchema):
    channel: NotificationChannel
    target: Annotated[str, Field(min_length=1, max_length=2048)]
    rule: dict[str, object] = Field(default_factory=dict)
    enabled: bool = True


class NotificationConfigDetail(BaseSchema):
    id: IdStr
    projectId: IdStr
    channel: NotificationChannel
    target: str
    rule: dict[str, object] = Field(default_factory=dict)
    enabled: bool
    createdAt: UnixTs | None = None


class IntegrationIssueCreateRequest(BaseSchema):
    provider: Annotated[str, Field(min_length=1, max_length=64)]
    runId: IdStr
    caseRunId: IdStr | None = None
    title: TitleStr
    description: str | None = Field(default=None, max_length=10_000)
    url: UrlStr | None = None


class IntegrationIssueDetail(BaseSchema):
    id: IdStr
    runId: IdStr
    caseRunId: IdStr | None = None
    provider: str
    issueKey: IdStr
    url: UrlStr
    createdAt: UnixTs | None = None


class NotificationDeliveryListItem(BaseSchema):
    id: IdStr
    projectId: IdStr
    runId: IdStr
    notificationId: IdStr
    channel: str
    target: str
    provider: str
    status: str
    attempts: int = Field(ge=0)
    maxRetries: int = Field(ge=0)
    nextRetryAt: UnixTs | None = None
    lastError: str | None = None
    lastStatusCode: int | None = None
    lastDurationMs: int | None = None
    createdAt: UnixTs | None = None
    updatedAt: UnixTs | None = None


class NotificationDeliveryListData(PageData[NotificationDeliveryListItem]):
    pass


class NotificationDeliveryRetryResult(BaseSchema):
    id: IdStr
    status: str
    attempts: int = Field(ge=0)


class NotificationDiagnosticsSummary(BaseSchema):
    status: NotificationDiagnosticsStatus
    total: int = Field(ge=0)
    blocking: int = Field(ge=0)
    warnings: int = Field(ge=0)
    ready: int = Field(ge=0)
    failedDeliveries: int = Field(ge=0)


class NotificationDiagnosticsCheck(BaseSchema):
    id: str
    level: NotificationDiagnosticsCheckLevel
    scope: str
    title: str
    detail: str
    recommendation: str
    notificationId: IdStr | None = None


class NotificationDiagnosticsFailure(BaseSchema):
    id: IdStr
    notificationId: IdStr
    channel: str
    target: str
    provider: str
    status: str
    attempts: int = Field(ge=0)
    lastStatusCode: int | None = None
    lastError: str | None = None
    updatedAt: UnixTs | None = None


class NotificationDiagnosticsProviderReadiness(BaseSchema):
    provider: str
    ready: bool
    reason: str
    notificationCount: int = Field(ge=0)
    configured: bool = False
    missingFields: list[str] = Field(default_factory=list)
    diagnostics: dict[str, object] = Field(default_factory=dict)


class NotificationDiagnosticsData(BaseSchema):
    summary: NotificationDiagnosticsSummary
    checks: list[NotificationDiagnosticsCheck] = Field(default_factory=list)
    recentFailures: list[NotificationDiagnosticsFailure] = Field(default_factory=list)
    providerReadiness: list[NotificationDiagnosticsProviderReadiness] = Field(default_factory=list)


class NotificationStrategyCenterDeliveryStats(BaseSchema):
    sent: int = Field(ge=0)
    failed: int = Field(ge=0)
    queued: int = Field(ge=0)
    lastDeliveryAt: UnixTs | None = None
    lastStatus: str | None = None


class NotificationStrategyCenterFilterReasonStats(BaseSchema):
    scopeReason: int = Field(ge=0)
    eventFiltered: int = Field(ge=0)
    unsupportedProvider: int = Field(ge=0)
    templateNotFound: int = Field(ge=0)


class NotificationStrategyCenterSimulationScopeReasonItem(BaseSchema):
    reason: str
    count: int = Field(ge=0)


class NotificationStrategyCenterSimulationStats(BaseSchema):
    sampleCount: int = Field(ge=0)
    matchedCount: int = Field(ge=0)
    scopeReasonTop: list[NotificationStrategyCenterSimulationScopeReasonItem] = Field(default_factory=list, max_length=3)


class NotificationStrategyCenterItem(BaseSchema):
    id: IdStr
    channel: str
    target: str
    enabled: bool
    events: list[str] = Field(default_factory=list)
    templateStrategySummary: dict[str, object] = Field(default_factory=dict)
    rolloutScopeSummary: dict[str, object] = Field(default_factory=dict)
    autoRollbackSummary: dict[str, object] = Field(default_factory=dict)
    deliveryStats: NotificationStrategyCenterDeliveryStats
    filterReasonStats: NotificationStrategyCenterFilterReasonStats
    simulationStats: NotificationStrategyCenterSimulationStats | None = None


class NotificationStrategySimulateRunContext(BaseSchema):
    envId: IdStr | None = None
    triggerType: str | None = None
    metaTags: list[str] = Field(default_factory=list)
    layerValue: str | None = None
    weekday: int | None = Field(default=None, ge=1, le=7)
    hour: int | None = Field(default=None, ge=0, le=23)
    timezoneOffsetMinutes: int | None = Field(default=None, ge=-720, le=840)
    seed: str | int | None = None


class NotificationStrategySimulateRequest(BaseSchema):
    notificationId: IdStr
    runContext: NotificationStrategySimulateRunContext | None = None


class NotificationStrategySimulateBatchRequest(BaseSchema):
    notificationId: IdStr
    runContexts: list[NotificationStrategySimulateRunContext] = Field(min_length=1, max_length=200)


class NotificationStrategySimulationConflictCandidate(BaseSchema):
    id: str | None = None
    priority: int | None = None
    weight: int | None = None


class NotificationStrategySimulationResult(BaseSchema):
    matched: bool
    scopeReason: str
    scopeDecision: dict[str, object] = Field(default_factory=dict)
    resolvedBatchPercent: int | None = None
    resolvedPriority: int | None = None
    resolvedLayer: dict[str, object] = Field(default_factory=dict)
    resolvedTimeWindow: dict[str, object] = Field(default_factory=dict)
    explanations: list[str] = Field(default_factory=list)
    conflictCandidates: list[NotificationStrategySimulationConflictCandidate] = Field(default_factory=list)


class NotificationStrategySimulationBatchItem(BaseSchema):
    runContext: NotificationStrategySimulateRunContext
    result: NotificationStrategySimulationResult


class NotificationStrategySimulationBatchResult(BaseSchema):
    items: list[NotificationStrategySimulationBatchItem] = Field(default_factory=list)

