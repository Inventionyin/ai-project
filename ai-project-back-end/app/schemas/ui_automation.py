from __future__ import annotations

from typing import Any

from pydantic import Field

from app.schemas.common import BaseSchema


class UiTestScriptCreateRequest(BaseSchema):
    name: str = Field(min_length=1, max_length=255)
    description: str = ""
    projectId: str = Field(min_length=1, max_length=64)
    scriptType: str = Field(default="PLAYWRIGHT", max_length=32)
    browser: str = Field(default="chromium", max_length=32)
    viewportWidth: int = Field(default=1280, ge=320, le=3840)
    viewportHeight: int = Field(default=720, ge=240, le=2160)
    baseUrl: str = Field(default="", max_length=512)
    tags: list[str] = Field(default_factory=list)


class UiTestScriptUpdateRequest(BaseSchema):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    scriptType: str | None = Field(default=None, max_length=32)
    browser: str | None = Field(default=None, max_length=32)
    viewportWidth: int | None = Field(default=None, ge=320, le=3840)
    viewportHeight: int | None = Field(default=None, ge=240, le=2160)
    baseUrl: str | None = Field(default=None, max_length=512)
    tags: list[str] | None = None


class UiTestScriptDetail(BaseSchema):
    id: str
    projectId: str
    name: str
    description: str = ""
    scriptType: str = "PLAYWRIGHT"
    scriptContent: str = ""
    recordingJson: dict[str, Any] = Field(default_factory=dict)
    status: str = "DRAFT"
    browser: str = "chromium"
    viewportWidth: int = 1280
    viewportHeight: int = 720
    baseUrl: str = ""
    tags: list[str] = Field(default_factory=list)
    createdBy: str | None = None
    createdAt: int = 0
    updatedAt: int = 0


class UiTestRunDetail(BaseSchema):
    id: str
    scriptId: str
    status: str = "QUEUED"
    startedAt: str | None = None
    finishedAt: str | None = None
    durationMs: int | None = None
    stepsTotal: int = 0
    stepsPassed: int = 0
    stepsFailed: int = 0
    screenshotPaths: list[str] = Field(default_factory=list)
    errorMessage: str | None = None
    tracePath: str | None = None
    reportPath: str | None = None
    createdAt: int = 0
    updatedAt: int = 0


class UiTestRecordRequest(BaseSchema):
    actions: list[dict[str, Any]] = Field(min_length=1)


class UiTestGenerateRequest(BaseSchema):
    pass


class UiTestRunRequest(BaseSchema):
    pass
