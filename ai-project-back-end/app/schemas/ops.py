from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from app.schemas.common import BaseSchema

OpsHealthStatus = Literal["READY", "WARN", "BLOCKED"]


class OpsHealthCheck(BaseSchema):
    key: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=128)
    status: OpsHealthStatus
    detail: str = Field(min_length=1, max_length=512)
    metric: dict[str, Any] = Field(default_factory=dict)
    recommendation: str = Field(min_length=1, max_length=512)


class OpsHealthSummaryData(BaseSchema):
    overallStatus: OpsHealthStatus
    generatedAt: datetime
    checks: list[OpsHealthCheck]
