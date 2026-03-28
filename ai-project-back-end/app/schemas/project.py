from __future__ import annotations

from pydantic import AliasChoices, Field

from app.schemas.common import BaseSchema, PageData
from app.schemas.types import IdStr, NameStr, UnixTs


class ProjectCreateRequest(BaseSchema):
    name: NameStr
    description: str | None = Field(
        default=None,
        max_length=2000,
        validation_alias=AliasChoices("description", "Description", "desc", "remark", "projectDescription", "projectDesc"),
    )
    ownerId: IdStr


class ProjectUpdateRequest(BaseSchema):
    name: NameStr | None = None
    description: str | None = Field(
        default=None,
        max_length=2000,
        validation_alias=AliasChoices("description", "Description", "desc", "remark", "projectDescription", "projectDesc"),
    )
    ownerId: IdStr | None = None


class ProjectListQuery(BaseSchema):
    page: int = Field(default=1, ge=1)
    pageSize: int = Field(default=20, ge=1, le=200)
    keyword: str | None = Field(default=None, max_length=255)


class ProjectListItem(BaseSchema):
    id: IdStr
    name: NameStr
    description: str | None = Field(default=None, max_length=2000)
    ownerId: IdStr
    memberCount: int = Field(ge=0)
    caseCount: int = Field(ge=0)
    passRate: float | None = Field(default=None, ge=0, le=100)
    createdAt: UnixTs


class ProjectListData(PageData[ProjectListItem]):
    pass


class ProjectDetailData(BaseSchema):
    id: IdStr
    name: NameStr
    description: str | None = Field(default=None, max_length=2000)
    ownerId: IdStr
    memberCount: int = Field(ge=0)
    createdAt: UnixTs


class ProjectHomeStatsData(BaseSchema):
    projectTotal: int = Field(ge=0)
    testcaseTotal: int = Field(ge=0)
    todayRunTotal: int = Field(ge=0)
    todayPassRate: float = Field(ge=0, le=100)
