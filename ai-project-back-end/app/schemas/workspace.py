from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.schemas.common import BaseSchema
from app.schemas.types import UnixTs


class WorkspaceAssetSummary(BaseSchema):
    requirementDocs: int = Field(ge=0)
    testcases: int = Field(ge=0)
    formalCases: int = Field(ge=0)
    testPoints: int = Field(ge=0)
    apiCollections: int = Field(ge=0)
    apiRequests: int = Field(ge=0)
    suites: int = Field(ge=0)


class WorkspaceAutomationSummary(BaseSchema):
    runs: int = Field(ge=0)
    executedCaseRuns: int = Field(ge=0)
    passRate: float = Field(ge=0, le=100)
    latestRunAt: UnixTs | None = None


class WorkspaceRiskSummary(BaseSchema):
    defects: int = Field(ge=0)
    p0Open: int = Field(ge=0)
    riskHints: int = Field(ge=0)


class WorkspaceCapabilitySummary(BaseSchema):
    role: Literal["admin", "owner", "editor", "viewer"]
    assets: bool
    ai: bool
    automation: bool
    settings: bool
    ops: bool


class WorkspaceSummaryData(BaseSchema):
    assets: WorkspaceAssetSummary
    automation: WorkspaceAutomationSummary
    risks: WorkspaceRiskSummary
    capabilities: WorkspaceCapabilitySummary
