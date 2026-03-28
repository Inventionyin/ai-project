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


<<<<<<< HEAD
class UiTestGeneratePytestPoRequest(BaseSchema):
    projectId: str = Field(min_length=1, max_length=64)
    pageUrl: str = Field(min_length=8, max_length=2048)
    pageId: str | None = Field(default=None, min_length=1, max_length=128)
    suiteType: str = Field(default="smoke", min_length=5, max_length=16)
    assertLevel: str = Field(default="P0", min_length=2, max_length=2)
    headed: bool = False
    forceRecapture: bool = False
    triggerBy: str = Field(default="AI_ASSISTANT", min_length=2, max_length=32)
    meta: dict[str, Any] = Field(default_factory=dict)


class UiTestGeneratePytestPoData(BaseSchema):
    pageId: str = Field(min_length=1, max_length=128)
    suiteType: str = Field(min_length=5, max_length=16)
    assertLevel: str = Field(min_length=2, max_length=2)
    captureDir: str = Field(min_length=1, max_length=2048)
    elementsPath: str = Field(min_length=1, max_length=2048)
    screenshotPath: str = Field(min_length=1, max_length=2048)
    testPath: str = Field(min_length=1, max_length=2048)
    pagePath: str = Field(min_length=1, max_length=2048)
    locatorsPath: str = Field(min_length=1, max_length=2048)
    commandHint: str = Field(min_length=1, max_length=2048)
    elementCount: int = Field(ge=0)
    reusedCapture: bool = False


=======
>>>>>>> 0f64092fd6c7abac3f72736aa6652163d25e1b0b
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
<<<<<<< HEAD


class UiBaselineRenderViewport(BaseSchema):
    width: int = Field(ge=200, le=10000)
    height: int = Field(ge=200, le=10000)


class UiBaselineRenderConfig(BaseSchema):
    viewport: UiBaselineRenderViewport
    deviceScaleFactor: int = Field(default=1, ge=1, le=4)


class UiBaselineInitRequest(BaseSchema):
    action: str | None = Field(default=None, max_length=64)
    projectId: str = Field(min_length=1, max_length=64)
    pageId: str = Field(min_length=1, max_length=128)
    envUrl: str = Field(min_length=8, max_length=2048)
    routePath: str = Field(min_length=1, max_length=1024)
    baselineVersion: str = Field(default="v1", min_length=1, max_length=64)
    figmaUrl: str = Field(min_length=8, max_length=2048)
    render: UiBaselineRenderConfig | None = None


class UiBaselineInitData(BaseSchema):
    pageId: str = Field(min_length=1, max_length=128)
    manifestPath: str = Field(min_length=1, max_length=2048)
    pageDoc: str = Field(min_length=1, max_length=2048)
    baselineDir: str = Field(min_length=1, max_length=2048)


class UiBaselineImageItem(BaseSchema):
    name: str = Field(min_length=1, max_length=128)
    type: str = Field(min_length=1, max_length=32)
    baselinePath: str = Field(min_length=1, max_length=2048)


class UiBaselineBindImagesRequest(BaseSchema):
    action: str | None = Field(default=None, max_length=64)
    pageId: str = Field(min_length=1, max_length=128)
    baselineVersion: str = Field(default="v1", min_length=1, max_length=64)
    images: list[UiBaselineImageItem] = Field(default_factory=list, max_length=200)


class UiBaselineBindImagesData(BaseSchema):
    pageId: str = Field(min_length=1, max_length=128)
    baselineVersion: str = Field(min_length=1, max_length=64)
    pageDoc: str = Field(min_length=1, max_length=2048)
    updatedCount: int = Field(ge=0)


class UiBaselineSelectorRule(BaseSchema):
    prefer: str = Field(default="testid", min_length=1, max_length=16)
    testid: str | None = Field(default=None, max_length=256)
    fallbackCss: str | None = Field(default=None, max_length=512)


class UiBaselineSelectorsConfig(BaseSchema):
    loginForm: UiBaselineSelectorRule | None = None
    masks: list[str] = Field(default_factory=list, max_length=200)


class UiBaselineThresholdItem(BaseSchema):
    maxDiffPixelRatio: float = Field(default=0.01, ge=0.0, le=1.0)


class UiBaselineThresholdsConfig(BaseSchema):
    loginForm: UiBaselineThresholdItem | None = None
    fullPage: UiBaselineThresholdItem | None = None


class UiBaselineSelectorsRequest(BaseSchema):
    action: str | None = Field(default=None, max_length=64)
    pageId: str = Field(min_length=1, max_length=128)
    selectors: UiBaselineSelectorsConfig
    thresholds: UiBaselineThresholdsConfig | None = None


class UiBaselineSelectorsData(BaseSchema):
    pageId: str = Field(min_length=1, max_length=128)
    updatedAt: str = Field(min_length=1, max_length=64)
=======
>>>>>>> 0f64092fd6c7abac3f72736aa6652163d25e1b0b
