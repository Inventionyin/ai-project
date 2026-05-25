from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from app.schemas.common import BaseSchema
from app.schemas.types import IdStr

ExternalIntegrationDiagnosticStatus = Literal["READY", "WARN", "BLOCKED"]
ExternalIntegrationDiagnosticCategory = Literal["notification", "issue", "devops", "ops", "acceptance"]


class ExternalIntegrationDiagnosticsSummary(BaseSchema):
    status: ExternalIntegrationDiagnosticStatus
    totalChecks: int = Field(ge=0)
    blocking: int = Field(ge=0)
    warnings: int = Field(ge=0)
    ready: int = Field(ge=0)


class ExternalIntegrationDiagnosticItem(BaseSchema):
    id: str = Field(min_length=1, max_length=128)
    category: ExternalIntegrationDiagnosticCategory
    provider: str = Field(min_length=1, max_length=64)
    status: ExternalIntegrationDiagnosticStatus
    title: str = Field(min_length=1, max_length=128)
    detail: str = Field(min_length=1, max_length=512)
    recommendation: str = Field(min_length=1, max_length=512)
    configured: bool | None = None
    missingFields: list[str] = Field(default_factory=list)
    lastVerifiedAt: datetime | None = None


class ExternalIntegrationIssueProviderStats(BaseSchema):
    provider: str = Field(min_length=1, max_length=64)
    total: int = Field(ge=0)


class ExternalIntegrationDiagnosticsData(BaseSchema):
    projectId: IdStr | None = None
    projectName: str | None = Field(default=None, max_length=255)
    generatedAt: datetime | None = None
    summary: ExternalIntegrationDiagnosticsSummary
    checks: list[ExternalIntegrationDiagnosticItem] = Field(default_factory=list)
    issueLinks: list[ExternalIntegrationIssueProviderStats] = Field(default_factory=list)
    nextActions: list[str] = Field(default_factory=list)
