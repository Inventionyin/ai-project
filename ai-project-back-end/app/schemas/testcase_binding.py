from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.schemas.common import BaseSchema
from app.schemas.types import IdStr, NameStr, UnixTs

TestcaseBindingLinkType = Literal["API_TARGET", "REQUEST", "COLLECTION"]
TestcaseBindingSourceType = Literal["MANUAL", "AI", "IMPORT"]


class TestcaseBindingListItem(BaseSchema):
    id: IdStr
    projectId: IdStr
    testcaseId: IdStr
    name: NameStr
    linkType: TestcaseBindingLinkType = "API_TARGET"
    datasetId: IdStr | None = None
    apiTargetId: IdStr | None = None
    requestId: IdStr | None = None
    collectionId: IdStr | None = None
    sourceType: TestcaseBindingSourceType = "MANUAL"
    assertSummary: str = Field(default="", max_length=255)
    lastRunStatus: str | None = None
    lastRunAt: UnixTs | None = None
    params: dict[str, object] = Field(default_factory=dict)
    priority: int = Field(ge=1, le=1_000_000)
    enabled: bool
    version: int = Field(ge=1)
    updatedAt: UnixTs


class TestcaseBindingDetail(TestcaseBindingListItem):
    createdAt: UnixTs


class TestcaseBindingCreateRequest(BaseSchema):
    name: NameStr
    datasetId: IdStr | None = None
    apiTargetId: IdStr | None = None
    requestId: IdStr | None = None
    collectionId: IdStr | None = None
    linkType: TestcaseBindingLinkType | None = None
    sourceType: TestcaseBindingSourceType = "MANUAL"
    assertSummary: str = Field(default="", max_length=255)
    params: dict[str, object] = Field(default_factory=dict)
    priority: int = Field(default=100, ge=1, le=1_000_000)
    enabled: bool = True


class TestcaseBindingUpdateRequest(BaseSchema):
    name: NameStr
    datasetId: IdStr | None = None
    apiTargetId: IdStr | None = None
    requestId: IdStr | None = None
    collectionId: IdStr | None = None
    linkType: TestcaseBindingLinkType | None = None
    sourceType: TestcaseBindingSourceType = "MANUAL"
    assertSummary: str = Field(default="", max_length=255)
    params: dict[str, object] = Field(default_factory=dict)
    priority: int = Field(ge=1, le=1_000_000)
    enabled: bool
    version: int = Field(ge=1)
