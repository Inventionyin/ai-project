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
