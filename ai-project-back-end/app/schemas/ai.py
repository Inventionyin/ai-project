from __future__ import annotations

from typing import Annotated

from pydantic import Field

from app.models.enums import Priority
from app.schemas.common import BaseSchema, PageData
from app.schemas.types import IdStr, TitleStr

TagStr = Annotated[str, Field(min_length=1, max_length=64)]


class AIGenerateInput(BaseSchema):
    apiCollectionId: IdStr
    apiRequestId: IdStr | None = None


class AIGenerateOptions(BaseSchema):
    count: int = Field(default=5, ge=1, le=50)
    includeBoundary: bool = Field(default=True)
    includeAbnormal: bool = Field(default=True)


class AIGenerateTestcasesRequest(BaseSchema):
    projectId: IdStr
    input: AIGenerateInput
    options: AIGenerateOptions = Field(default_factory=AIGenerateOptions)


class AITestcaseDraft(BaseSchema):
    title: TitleStr
    contentMd: str = Field(min_length=1)
    tags: list[TagStr] = Field(default_factory=list, max_length=50)
    priority: Priority


class AIGenerateTestcasesData(BaseSchema):
    recordId: IdStr
    drafts: list[AITestcaseDraft] = Field(min_length=1, max_length=200)


class AIAnalyzeRunData(BaseSchema):
    taskId: IdStr


class AIRecordListQuery(BaseSchema):
    entityType: str = Field(min_length=1, max_length=64)
    entityId: IdStr
    page: int = Field(default=1, ge=1)
    pageSize: int = Field(default=20, ge=1, le=200)


class AIRecordListItem(BaseSchema):
    id: IdStr
    entityType: str = Field(min_length=1, max_length=64)
    entityId: IdStr
    model: str | None = Field(default=None, max_length=64)
    createdAt: int = Field(ge=0)


class AIRecordListData(PageData[AIRecordListItem]):
    pass

