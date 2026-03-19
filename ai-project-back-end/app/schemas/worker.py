from __future__ import annotations

from typing import Literal

from pydantic import Field, field_serializer

from app.models.enums import JobStatus, TestCaseType
from app.schemas.common import BaseSchema
from app.schemas.run import CaseRunResult
from app.schemas.types import IdStr, NameStr, UrlStr, VersionStr

WorkerCapability = Literal["API", "UI", "PERF"]


class WorkerRegisterRequest(BaseSchema):
    name: NameStr
    capabilities: list[WorkerCapability] = Field(min_length=1, max_length=16)
    slots: int = Field(ge=1, le=256)
    version: VersionStr


class WorkerRegisterData(BaseSchema):
    workerId: IdStr
    token: str = Field(min_length=1, max_length=256)


class WorkerHeartbeatRequest(BaseSchema):
    workerId: IdStr
    slotsFree: int = Field(ge=0, le=256)
    runningJobIds: list[IdStr] = Field(default_factory=list, max_length=256)
    meta: dict[str, float] = Field(default_factory=dict)


class WorkerPollRequest(BaseSchema):
    workerId: IdStr
    capabilities: list[WorkerCapability] = Field(min_length=1, max_length=16)


class JobEnv(BaseSchema):
    baseUrl: UrlStr
    variables: dict[str, str] = Field(default_factory=dict)
    secrets: dict[str, str] = Field(default_factory=dict)

    @field_serializer("secrets")
    def _mask_secrets(self, value: dict[str, str]) -> dict[str, str]:
        return {k: "******" for k in value.keys()}


class JobSuiteConfig(BaseSchema):
    timeoutSec: int = Field(default=600, ge=1, le=86_400)
    retryCount: int = Field(default=1, ge=0, le=20)
    failFast: bool = Field(default=False)


class JobItem(BaseSchema):
    caseRunId: IdStr
    testcaseId: IdStr
    type: TestCaseType
    contentMd: str = Field(min_length=1)
    params: dict[str, object] = Field(default_factory=dict)


class JobPayload(BaseSchema):
    jobId: IdStr
    runId: IdStr
    env: JobEnv
    suiteConfig: JobSuiteConfig
    items: list[JobItem] = Field(min_length=1, max_length=10_000)


class WorkerPollData(BaseSchema):
    job: JobPayload | None = None
    sleepMs: int = Field(default=2000, ge=200, le=60_000)


class WorkerReportRequest(BaseSchema):
    workerId: IdStr
    jobId: IdStr
    runId: IdStr
    results: list[CaseRunResult] = Field(min_length=1, max_length=10_000)
    jobStatus: JobStatus

