from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.schemas.common import BaseSchema
from app.schemas.types import IdStr, UnixTs


class DashboardSummaryData(BaseSchema):
    date: str = Field(min_length=10, max_length=10)
    totalRuns: int = Field(ge=0)
    passedRuns: int = Field(ge=0)
    failedRuns: int = Field(ge=0)
    runningRuns: int = Field(ge=0)
    canceledRuns: int = Field(ge=0)
    passRate: float = Field(ge=0)


class DashboardFailureTopTestcaseItem(BaseSchema):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1, max_length=100)
    failCount: int = Field(ge=0)
    totalRuns: int = Field(ge=0)
    flake: bool
    suiteNames: list[str] = Field(default_factory=list)


class DashboardFailureTopSuiteItem(BaseSchema):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1, max_length=255)
    failCount: int = Field(ge=0)
    totalRuns: int = Field(ge=0)
    lastRunAt: str | None = None


class DashboardFailureTopData(BaseSchema):
    dimension: Literal["testcase", "suite"]
    items: list[DashboardFailureTopTestcaseItem | DashboardFailureTopSuiteItem] = Field(default_factory=list)


class DashboardQualityGateItem(BaseSchema):
    name: str = Field(min_length=1, max_length=100)
    threshold: str = Field(min_length=1, max_length=50)
    current: str = Field(min_length=1, max_length=50)
    passed: bool


class DashboardQualityGateData(BaseSchema):
    overall: Literal["PASSED", "PARTIAL_FAIL", "FAILED", "UNKNOWN"]
    lastCheckedAt: UnixTs | None = None
    linkedRunId: IdStr | None = None
    gates: list[DashboardQualityGateItem] = Field(default_factory=list)


class DashboardTrendItem(BaseSchema):
    date: str = Field(min_length=5, max_length=5)
    passRate: float = Field(ge=0, le=100)
    failCount: int = Field(ge=0)
    totalRuns: int = Field(ge=0)


class DashboardTrendData(BaseSchema):
    days: Literal[7, 14, 30]
    items: list[DashboardTrendItem] = Field(default_factory=list)


class DashboardTrialOperationClusterItem(BaseSchema):
    clusterKey: str = Field(min_length=1, max_length=128)
    count: int = Field(ge=0)
    sampleTitles: list[str] = Field(default_factory=list)
    rootCauseHint: str = Field(min_length=1, max_length=255)
    confidence: float = Field(ge=0, le=1)


class DashboardTrialOperationRiskHint(BaseSchema):
    defectId: IdStr
    title: str = Field(min_length=1, max_length=255)
    status: str = Field(min_length=1, max_length=32)
    severity: str = Field(min_length=1, max_length=16)
    updatedAt: UnixTs
    riskScore: float = Field(ge=0)
    hint: str = Field(min_length=1, max_length=255)


class DashboardTrialOperationAcceptanceSummary(BaseSchema):
    conclusion: str = Field(min_length=1, max_length=64)
    score: int = Field(ge=0, le=100)
    level: Literal["PASS", "WARNING", "BLOCKED", "INSUFFICIENT"]
    highlights: list[str] = Field(default_factory=list, max_length=5)
    risks: list[str] = Field(default_factory=list, max_length=4)
    nextActions: list[str] = Field(default_factory=list, max_length=4)


class DashboardTrialOperationData(BaseSchema):
    metrics: dict[str, int] = Field(default_factory=dict)
    testcasePriorityDistribution: dict[str, int] = Field(default_factory=dict)
    testcaseStatusDistribution: dict[str, int] = Field(default_factory=dict)
    testcaseTypeDistribution: dict[str, int] = Field(default_factory=dict)
    testcaseFeatureDistribution: dict[str, int] = Field(default_factory=dict)
    defectSeverityDistribution: dict[str, int] = Field(default_factory=dict)
    defectStatusDistribution: dict[str, int] = Field(default_factory=dict)
    topDefectClusters: list[DashboardTrialOperationClusterItem] = Field(default_factory=list)
    topRiskHints: list[DashboardTrialOperationRiskHint] = Field(default_factory=list)
    sampleTestcases: list[str] = Field(default_factory=list)
    acceptanceSummary: DashboardTrialOperationAcceptanceSummary


class DashboardTrialOperationReportData(BaseSchema):
    title: str = Field(min_length=1, max_length=128)
    generatedAt: UnixTs
    markdown: str = Field(min_length=1)
    summary: DashboardTrialOperationAcceptanceSummary


class DashboardTrialOperationReportSnapshotCreateRequest(DashboardTrialOperationReportData):
    pass


class DashboardTrialOperationReportSnapshotData(DashboardTrialOperationReportData):
    id: IdStr
    projectId: IdStr | None = None
    score: int | None = Field(default=None, ge=0, le=100)
    level: Literal["PASS", "WARNING", "BLOCKED", "INSUFFICIENT"] | None = None
    acceptanceScore: int | None = Field(default=None, ge=0, le=100)
    acceptanceLevel: Literal["PASS", "WARNING", "BLOCKED", "INSUFFICIENT"] | None = None
    createdBy: IdStr | None = None
    createdAt: UnixTs


class DashboardCaseGovernanceDuplicateTitleItem(BaseSchema):
    title: str = Field(min_length=1, max_length=100)
    count: int = Field(ge=2)
    modules: list[str] = Field(default_factory=list, max_length=8)


class DashboardCaseGovernanceLowValueItem(BaseSchema):
    id: IdStr
    testCaseId: str | None = Field(default=None, max_length=64)
    title: str = Field(min_length=1, max_length=100)
    feature: str | None = Field(default=None, max_length=128)
    priority: str = Field(min_length=1, max_length=16)
    type: str = Field(min_length=1, max_length=16)
    reasons: list[str] = Field(default_factory=list, min_length=1, max_length=6)


class DashboardCaseGovernanceModuleP0DensityItem(BaseSchema):
    feature: str = Field(min_length=1, max_length=128)
    total: int = Field(ge=0)
    p0: int = Field(ge=0)
    p0Density: float = Field(ge=0, le=100)


class DashboardCaseGovernanceData(BaseSchema):
    totalCases: int = Field(ge=0)
    uniqueCaseIds: int = Field(ge=0)
    sourceCaseIds: int = Field(default=0, ge=0)
    formalCases: int = Field(default=0, ge=0)
    testPointCases: int = Field(default=0, ge=0)
    generatedImportIds: int = Field(default=0, ge=0)
    emptyCaseIds: int = Field(ge=0)
    emptyTitles: int = Field(ge=0)
    p0Cases: int = Field(ge=0)
    p0Density: float = Field(ge=0, le=100)
    typeDistribution: dict[str, int] = Field(default_factory=dict)
    priorityDistribution: dict[str, int] = Field(default_factory=dict)
    moduleDistribution: dict[str, int] = Field(default_factory=dict)
    duplicateTitleCandidates: list[DashboardCaseGovernanceDuplicateTitleItem] = Field(default_factory=list)
    lowValueCandidates: list[DashboardCaseGovernanceLowValueItem] = Field(default_factory=list)
    moduleP0Density: list[DashboardCaseGovernanceModuleP0DensityItem] = Field(default_factory=list)


class DashboardTrialOperationGovernanceSuggestionItem(BaseSchema):
    id: str = Field(min_length=1, max_length=128)
    category: Literal["DUPLICATE_TITLE", "LOW_VALUE", "PROMOTE_TEST_POINT", "P0_COVERAGE_GAP"]
    title: str = Field(min_length=1, max_length=128)
    severity: Literal["LOW", "MEDIUM", "HIGH"]
    targetIds: list[IdStr] = Field(default_factory=list)
    targetCount: int = Field(ge=0)
    reason: str = Field(min_length=1, max_length=255)
    recommendation: str = Field(min_length=1, max_length=255)
    action: Literal["TAG_DUPLICATE", "MARK_LOW_VALUE", "PROMOTE_TO_FORMAL", "ADD_P0_REVIEW_TAG"]
    confidence: float = Field(ge=0, le=1)
    canApply: bool = True


class DashboardTrialOperationGovernanceSuggestionBatch(BaseSchema):
    batchId: str = Field(min_length=1, max_length=128)
    generatedAt: UnixTs
    source: Literal["RULE", "AI", "HYBRID"]
    summary: dict[str, int] = Field(default_factory=dict)
    items: list[DashboardTrialOperationGovernanceSuggestionItem] = Field(default_factory=list)


class DashboardTrialOperationGovernanceApplyRequest(BaseSchema):
    batchId: str = Field(min_length=1, max_length=128)
    suggestionIds: list[str] = Field(default_factory=list)


class DashboardTrialOperationGovernanceApplyData(BaseSchema):
    batchId: str = Field(min_length=1, max_length=128)
    appliedSuggestionIds: list[str] = Field(default_factory=list)
    skippedSuggestionIds: list[str] = Field(default_factory=list)
    updatedCases: int = Field(ge=0)
    summary: str = Field(min_length=1, max_length=255)


class DashboardTrialOperationGovernanceHistoryItem(BaseSchema):
    batchId: str = Field(min_length=1, max_length=128)
    generatedAt: UnixTs
    source: Literal["RULE", "AI", "HYBRID"]
    totalSuggestions: int = Field(ge=0)
    appliedSuggestions: int = Field(ge=0)
    updatedCases: int = Field(ge=0)
    status: Literal["GENERATED", "PARTIAL_APPLIED", "APPLIED"]
    summary: str = Field(min_length=1, max_length=255)


class DashboardTrialOperationGovernanceHistoryData(BaseSchema):
    generatedBatches: int = Field(ge=0)
    appliedBatches: int = Field(ge=0)
    appliedSuggestions: int = Field(ge=0)
    updatedCases: int = Field(ge=0)
    latestBatchId: str | None = Field(default=None, max_length=128)
    items: list[DashboardTrialOperationGovernanceHistoryItem] = Field(default_factory=list)


class DashboardTrialOperationExecutionImportRequest(BaseSchema):
    totalLimit: int = Field(default=30, ge=1, le=500)
    failedCaseIds: list[IdStr] = Field(default_factory=list)
    skippedCaseIds: list[IdStr] = Field(default_factory=list)
    note: str | None = Field(default=None, max_length=255)


class DashboardTrialOperationExecutionImportData(BaseSchema):
    runId: IdStr
    total: int = Field(ge=0)
    passed: int = Field(ge=0)
    failed: int = Field(ge=0)
    skipped: int = Field(ge=0)
    summary: str = Field(min_length=1, max_length=255)
