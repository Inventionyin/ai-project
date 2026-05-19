from __future__ import annotations

from pydantic import Field

from app.schemas.common import BaseSchema, PageData
from app.schemas.types import IdStr, NameStr, UnixTs


class OrganizationCreateRequest(BaseSchema):
    name: NameStr
    description: str | None = Field(default=None, max_length=512)
    settings: dict | None = None


class OrganizationUpdateRequest(BaseSchema):
    name: NameStr | None = None
    description: str | None = Field(default=None, max_length=512)
    settings: dict | None = None


class OrganizationListQuery(BaseSchema):
    page: int = Field(default=1, ge=1)
    pageSize: int = Field(default=20, ge=1, le=200)
    keyword: str | None = Field(default=None, max_length=255)


class OrganizationListItem(BaseSchema):
    id: IdStr
    name: NameStr
    description: str | None = None
    projectCount: int = Field(ge=0)
    createdAt: UnixTs


class OrganizationListData(PageData[OrganizationListItem]):
    pass


class OrganizationDetailData(BaseSchema):
    id: IdStr
    name: NameStr
    description: str | None = None
    settings: dict | None = None
    projectCount: int = Field(ge=0)
    createdAt: UnixTs
    updatedAt: UnixTs
