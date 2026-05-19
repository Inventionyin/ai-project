from __future__ import annotations

from app.schemas.common import BaseSchema


class PerformanceTestCreateRequest(BaseSchema):
    name: str
    description: str = ""
    testType: str = "LOAD"
    targetUrl: str = ""
    config: dict | None = None
    scriptContent: str = ""
    tags: list[str] | None = None


class PerformanceTestUpdateRequest(BaseSchema):
    name: str | None = None
    description: str | None = None
    testType: str | None = None
    targetUrl: str | None = None
    config: dict | None = None
    scriptContent: str | None = None
    tags: list[str] | None = None


class PerformanceTestDetail(BaseSchema):
    id: str
    projectId: str
    name: str
    description: str
    testType: str
    targetUrl: str
    config: dict
    scriptContent: str
    status: str
    tags: list[str]
    createdBy: str | None = None
    createdAt: int
    updatedAt: int


class PerformanceTestRunDetail(BaseSchema):
    id: str
    testId: str
    status: str
    startedAt: str | None = None
    finishedAt: str | None = None
    durationMs: int | None = None
    metrics: dict
    thresholds: dict
    reportPath: str | None = None
    errorMessage: str | None = None
    createdAt: int
    updatedAt: int


class K6ScriptGenerateRequest(BaseSchema):
    testType: str = "LOAD"
    targetUrl: str
    config: dict | None = None  # {vus, duration, stages, thresholds}


class TrendDataPoint(BaseSchema):
    runId: str
    createdAt: int
    reqPerSec: float | None = None
    avgLatency: float | None = None
    p95: float | None = None
    p99: float | None = None
    errorRate: float | None = None
    durationMs: int | None = None
