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
