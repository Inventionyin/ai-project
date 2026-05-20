from __future__ import annotations

from pydantic import Field

from app.schemas.common import BaseSchema
from app.schemas.types import IdStr, UnixTs


class RetrospectiveRecordCreateRequest(BaseSchema):
    title: str = Field(min_length=1, max_length=255)
    sourceType: str = Field(default="OTHER", min_length=1, max_length=32)
    status: str = Field(default="DRAFT", min_length=1, max_length=32)
    problemSummary: str | None = Field(default=None, max_length=5000)
    rootCause: str | None = Field(default=None, max_length=5000)
    decision: str | None = Field(default=None, max_length=5000)
    actionItems: str | None = Field(default=None, max_length=5000)


class RetrospectiveRecordUpdateRequest(BaseSchema):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    sourceType: str | None = Field(default=None, min_length=1, max_length=32)
    status: str | None = Field(default=None, min_length=1, max_length=32)
    problemSummary: str | None = Field(default=None, max_length=5000)
    rootCause: str | None = Field(default=None, max_length=5000)
    decision: str | None = Field(default=None, max_length=5000)
    actionItems: str | None = Field(default=None, max_length=5000)


class RetrospectiveRecordListItem(BaseSchema):
    id: IdStr
    projectId: IdStr
    title: str
    sourceType: str
    status: str
    problemSummary: str | None = None
    rootCause: str | None = None
    decision: str | None = None
    actionItems: str | None = None
    createdBy: IdStr
    updatedBy: IdStr | None = None
    createdAt: UnixTs
    updatedAt: UnixTs


class RetrospectiveRecordDetail(RetrospectiveRecordListItem):
    pass


class KnowledgeTemplateCreateRequest(BaseSchema):
    name: str = Field(min_length=1, max_length=255)
    category: str = Field(default="GENERAL", min_length=1, max_length=64)
    contentJson: dict[str, object] = Field(default_factory=dict)
    status: str = Field(default="ACTIVE", min_length=1, max_length=32)


class KnowledgeTemplateUpdateRequest(BaseSchema):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    category: str | None = Field(default=None, min_length=1, max_length=64)
    contentJson: dict[str, object] | None = None
    status: str | None = Field(default=None, min_length=1, max_length=32)


class KnowledgeTemplateListItem(BaseSchema):
    id: IdStr
    projectId: IdStr
    name: str
    category: str
    contentJson: dict[str, object] = Field(default_factory=dict)
    status: str
    createdBy: IdStr
    updatedBy: IdStr | None = None
    createdAt: UnixTs
    updatedAt: UnixTs


class KnowledgeTemplateDetail(KnowledgeTemplateListItem):
    pass


class RecommendationEvaluateRequest(BaseSchema):
    targetType: str = Field(min_length=1, max_length=64)
    targetId: str = Field(min_length=1, max_length=64)
    topK: int = Field(default=10, ge=1, le=100)


class KnowledgeRecommendationItem(BaseSchema):
    id: IdStr
    content: str
    score: float | None = None
    type: str
    status: str


class KnowledgeRecommendationStatusUpdateRequest(BaseSchema):
    status: str = Field(min_length=1, max_length=32)


class RecommendationEvaluateResponse(BaseSchema):
    targetType: str
    targetId: str
    recommendations: list[KnowledgeRecommendationItem] = Field(default_factory=list)


class RunDraftRequest(BaseSchema):
    runId: IdStr


class RunDraftResponse(RetrospectiveRecordDetail):
    pass
