from __future__ import annotations

from pydantic import Field

from app.schemas.common import BaseSchema
from app.schemas.types import IdStr, NameStr, UnixTs


class TestcaseBindingListItem(BaseSchema):
    id: IdStr
    projectId: IdStr
    testcaseId: IdStr
    name: NameStr
    datasetId: IdStr | None = None
    apiTargetId: IdStr | None = None
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
    params: dict[str, object] = Field(default_factory=dict)
    priority: int = Field(default=100, ge=1, le=1_000_000)
    enabled: bool = True


class TestcaseBindingUpdateRequest(BaseSchema):
    name: NameStr
    datasetId: IdStr | None = None
    apiTargetId: IdStr | None = None
    params: dict[str, object] = Field(default_factory=dict)
    priority: int = Field(ge=1, le=1_000_000)
    enabled: bool
    version: int = Field(ge=1)
