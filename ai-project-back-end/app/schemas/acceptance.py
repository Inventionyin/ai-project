from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from app.schemas.common import BaseSchema
from app.schemas.types import IdStr


AcceptanceStatus = Literal["READY", "WARN", "BLOCKED"]


class AcceptanceCheck(BaseSchema):
    key: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=128)
    status: AcceptanceStatus
    detail: str = Field(min_length=1, max_length=512)
    metric: dict[str, Any] = Field(default_factory=dict)
    recommendation: str = Field(min_length=1, max_length=512)


class AcceptanceExternalSystem(BaseSchema):
    provider: str = Field(min_length=1, max_length=64)
    status: AcceptanceStatus
    configured: bool
    lastVerifiedAt: datetime | None = None
    missingFields: list[str] = Field(default_factory=list)
    detail: str = Field(min_length=1, max_length=512)
    recommendation: str = Field(min_length=1, max_length=512)


class AcceptanceSummaryData(BaseSchema):
    overallStatus: AcceptanceStatus
    generatedAt: datetime
    projectId: IdStr
    projectName: str = Field(min_length=1, max_length=255)
    score: int = Field(ge=0, le=100)
    checks: list[AcceptanceCheck] = Field(default_factory=list)
    externalSystems: list[AcceptanceExternalSystem] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    nextActions: list[str] = Field(default_factory=list)


class AcceptanceReportData(BaseSchema):
    title: str = Field(min_length=1, max_length=128)
    generatedAt: datetime
    summary: AcceptanceSummaryData
    markdown: str = Field(min_length=1)
