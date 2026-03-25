from __future__ import annotations

from typing import Any

from pydantic import Field

from app.schemas.common import BaseSchema


class UiTestGenerateRunRequest(BaseSchema):
    projectId: str = Field(min_length=1, max_length=64)
    pageId: str = Field(min_length=1, max_length=128)
    figmaUrl: str | None = Field(default=None, max_length=2048)
    assertLevel: str = Field(default="P0", min_length=2, max_length=2)
    headed: bool = False
    baseUrl: str | None = Field(default=None, max_length=2048)
    updateManifest: bool = True
    triggerBy: str = Field(default="AI_ASSISTANT", min_length=2, max_length=32)
    meta: dict[str, Any] = Field(default_factory=dict)


class UiTestSummary(BaseSchema):
    total: int = Field(ge=0)
    passed: int = Field(ge=0)
    failed: int = Field(ge=0)
    skipped: int = Field(ge=0)
    durationMs: int = Field(ge=0)


class UiTestGenerateRunData(BaseSchema):
    runId: str = Field(min_length=1, max_length=64)
    status: str = Field(min_length=4, max_length=16)
    result: str = Field(min_length=4, max_length=16)
    pageId: str = Field(min_length=1, max_length=128)
    assertLevel: str = Field(min_length=2, max_length=2)
    specPath: str = Field(min_length=1, max_length=2048)
    reportDir: str = Field(min_length=1, max_length=2048)
    reportIndexUrl: str = Field(min_length=1, max_length=2048)
    summary: UiTestSummary
    startedAt: int = Field(ge=0)
    finishedAt: int = Field(ge=0)
    stdout: str = ""
    stderr: str = ""


class UiTestReportListItem(BaseSchema):
    runId: str = Field(min_length=1, max_length=64)
    projectId: str = Field(min_length=1, max_length=64)
    pageId: str = Field(min_length=1, max_length=128)
    status: str = Field(min_length=4, max_length=16)
    result: str = Field(min_length=4, max_length=16)
    assertLevel: str = Field(min_length=2, max_length=2)
    total: int = Field(ge=0)
    passed: int = Field(ge=0)
    failed: int = Field(ge=0)
    skipped: int = Field(ge=0)
    durationMs: int = Field(ge=0)
    reportDir: str = Field(min_length=1, max_length=2048)
    reportIndexUrl: str = Field(min_length=1, max_length=2048)
    createdAt: int = Field(ge=0)
    finishedAt: int = Field(ge=0)


class UiTestFailedCase(BaseSchema):
    title: str = Field(min_length=1, max_length=2048)
    error: str = Field(min_length=1, max_length=20000)
    screenshot: str | None = Field(default=None, max_length=2048)
    trace: str | None = Field(default=None, max_length=2048)


class UiTestReportDetailData(BaseSchema):
    runId: str = Field(min_length=1, max_length=64)
    projectId: str = Field(min_length=1, max_length=64)
    pageId: str = Field(min_length=1, max_length=128)
    status: str = Field(min_length=4, max_length=16)
    result: str = Field(min_length=4, max_length=16)
    assertLevel: str = Field(min_length=2, max_length=2)
    specPath: str = Field(min_length=1, max_length=2048)
    reportDir: str = Field(min_length=1, max_length=2048)
    reportIndexUrl: str = Field(min_length=1, max_length=2048)
    summary: UiTestSummary
    failedCases: list[UiTestFailedCase] = Field(default_factory=list)
    startedAt: int = Field(ge=0)
    finishedAt: int = Field(ge=0)
