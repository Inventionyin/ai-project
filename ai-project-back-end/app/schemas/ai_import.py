from __future__ import annotations

from pydantic import Field, model_validator

from app.models.enums import AiImportJobStatus, AiImportSourceType, Priority, TestCaseType
from app.schemas.common import BaseSchema
from app.schemas.types import IdStr, UnixTs, UrlStr


class AiImportSourceRef(BaseSchema):
    figmaUrl: UrlStr | None = None
    prdUrl: UrlStr | None = None
    htmlUrl: UrlStr | None = None
    fileName: str | None = Field(default=None, min_length=1, max_length=255)


class AiImportGenerateConfig(BaseSchema):
    language: str = Field(default="zh-CN", min_length=2, max_length=32)
    maxCases: int = Field(default=80, ge=1, le=500)
    dedupeStrategy: str = Field(default="TITLE_STORY_URL", min_length=1, max_length=64)
    defaultPriority: Priority = Field(default=Priority.P1)
    defaultType: TestCaseType = Field(default=TestCaseType.API)
    autoExtractApi: bool = Field(default=True)


class AiImportSkillConfig(BaseSchema):
    enableFeature: bool = Field(default=True)
    enableEpic: bool = Field(default=True)
    enableStory: bool = Field(default=True)
    enableTask: bool = Field(default=True)
    enableDescription: bool = Field(default=True)
    enableTitle: bool = Field(default=True)
    enableStep: bool = Field(default=True)


class AiImportCreateJobRequest(BaseSchema):
    projectId: IdStr
    sourceType: AiImportSourceType
    source: AiImportSourceRef = Field(default_factory=AiImportSourceRef)
    generateConfig: AiImportGenerateConfig = Field(default_factory=AiImportGenerateConfig)
    skillConfig: AiImportSkillConfig = Field(default_factory=AiImportSkillConfig)

    @model_validator(mode="after")
    def validate_source(self) -> "AiImportCreateJobRequest":
        if self.sourceType == AiImportSourceType.FIGMA_LINK and not self.source.figmaUrl:
            raise ValueError("figmaUrl is required when sourceType is FIGMA_LINK")
        return self


class AiImportCreateJobData(BaseSchema):
    jobId: IdStr
    projectId: IdStr
    sourceType: AiImportSourceType
    status: AiImportJobStatus
    createdAt: UnixTs


class AiImportUploadJobFileData(BaseSchema):
    jobId: IdStr
    projectId: IdStr
    sourceType: AiImportSourceType
    status: AiImportJobStatus
    fileName: str = Field(min_length=1, max_length=255)
    fileSize: int = Field(ge=1)
    uploadedAt: UnixTs


class AiImportPreviewItem(BaseSchema):
    id: IdStr
    title: str = Field(min_length=1, max_length=100)
    type: str = Field(min_length=1, max_length=16)
    priority: str = Field(min_length=1, max_length=8)
    status: str = Field(min_length=1, max_length=16)
    feature: str | None = Field(default=None, max_length=128)
    epic: str | None = Field(default=None, max_length=128)
    story: str | None = Field(default=None, max_length=128)
    task: str | None = Field(default=None, max_length=128)
    description: str | None = None
    steps: list[dict] = Field(default_factory=list)
    apiUrl: str | None = Field(default=None, max_length=1024)
    apiMethod: str | None = Field(default=None, max_length=16)
    tags: list[str] = Field(default_factory=list)
    confidence: float | None = None
    selected: bool


class AiImportGetJobData(BaseSchema):
    jobId: IdStr
    projectId: IdStr
    sourceType: AiImportSourceType
    status: AiImportJobStatus
    summary: dict = Field(default_factory=dict)
    previewItems: list[AiImportPreviewItem] = Field(default_factory=list)
    createdAt: UnixTs
    updatedAt: UnixTs


# API Collection Import Specific Schemas
class ApiImportCreateJobRequest(BaseSchema):
    projectId: IdStr


class ApiImportCreateJobData(BaseSchema):
    jobId: IdStr
    projectId: IdStr
    status: AiImportJobStatus
    createdAt: UnixTs


class ApiImportPreviewRequest(BaseSchema):
    method: str = Field(min_length=1, max_length=16)
    url: str = Field(min_length=1, max_length=1024)
    name: str = Field(min_length=1, max_length=128)
    headers: dict = Field(default_factory=dict)
    body: dict = Field(default_factory=dict)
    diffStatus: str = Field(min_length=1, max_length=16) # 'new', 'updated', 'unchanged'


class ApiImportPreviewGroup(BaseSchema):
    name: str = Field(min_length=1, max_length=128)
    requests: list[ApiImportPreviewRequest] = Field(default_factory=list)


class ApiImportPreviewResult(BaseSchema):
    collectionName: str = Field(min_length=1, max_length=128)
    groups: list[ApiImportPreviewGroup] = Field(default_factory=list)


class ApiImportJobDetail(BaseSchema):
    jobId: IdStr
    projectId: IdStr
    status: AiImportJobStatus
    warnings: list[dict] = Field(default_factory=list)
    previewData: ApiImportPreviewResult | None = None
    createdAt: UnixTs
    updatedAt: UnixTs


class ApiImportCommitRequest(BaseSchema):
    selectedRequests: list[ApiImportPreviewRequest] = Field(default_factory=list)
    overrideExisting: bool = Field(default=True)
