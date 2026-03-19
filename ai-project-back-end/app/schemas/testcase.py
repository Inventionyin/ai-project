from __future__ import annotations

from typing import Annotated

from pydantic import Field

from app.models.enums import CaseRunStatus, Priority, TestCaseStatus, TestCaseType
from app.schemas.common import BaseSchema, PageData
from app.schemas.types import IdStr, TitleStr, UnixTs

TestCaseVersionStr = Annotated[str, Field(min_length=1, max_length=32, pattern=r"^(?:v?1(?:\.\d+)?)$")]

TagStr = Annotated[str, Field(min_length=1, max_length=64)]


class TestCaseCreateRequest(BaseSchema):
    projectId: IdStr
    title: TitleStr
    type: TestCaseType
    priority: Priority
    status: TestCaseStatus
    tags: list[TagStr] = Field(default_factory=list, max_length=50)
    contentMd: str = Field(min_length=1)
    ownerId: IdStr | None = None


class TestCaseUpdateRequest(BaseSchema):
    version: TestCaseVersionStr
    title: TitleStr | None = None
    type: TestCaseType | None = None
    priority: Priority | None = None
    status: TestCaseStatus | None = None
    tags: list[TagStr] | None = Field(default=None, max_length=50)
    contentMd: str | None = Field(default=None, min_length=1)
    ownerId: IdStr | None = None


class TestCasePutRequest(BaseSchema):
    projectId: IdStr
    title: TitleStr
    type: TestCaseType
    priority: Priority
    status: TestCaseStatus
    tags: list[TagStr] = Field(default_factory=list, max_length=50)
    contentMd: str = Field(min_length=1)
    ownerId: IdStr | None = None


class TestCaseRestoreRequest(BaseSchema):
    version: TestCaseVersionStr


class TestCaseListQuery(BaseSchema):
    projectId: IdStr
    title: TitleStr | None = None
    type: TestCaseType | None = None
    status: TestCaseStatus | None = None
    tag: TagStr | None = None
    ownerId: IdStr | None = None
    page: int = Field(default=1, ge=1)
    pageSize: int = Field(default=20, ge=1, le=200)


class TestCaseDetail(BaseSchema):
    id: IdStr
    projectId: IdStr
    title: TitleStr
    type: TestCaseType
    priority: Priority
    status: TestCaseStatus
    tags: list[TagStr] = Field(default_factory=list, max_length=50)
    ownerId: IdStr | None = None
    ownerName: str | None = None
    version: TestCaseVersionStr
    contentMd: str = Field(min_length=1)


class TestCaseVersionSchema(BaseSchema):
    id: IdStr
    testcaseId: IdStr
    version: TestCaseVersionStr
    contentMd: str
    createdAt: int
    createdBy: IdStr | None


class TestCaseListItem(BaseSchema):
    id: IdStr
    projectId: IdStr
    title: TitleStr
    type: TestCaseType
    priority: Priority
    status: TestCaseStatus
    tags: list[TagStr] = Field(default_factory=list, max_length=50)
    ownerId: IdStr | None = None
    ownerName: str | None = None
    version: TestCaseVersionStr
    lastRun: CaseRunStatus | None = None
    updatedAt: UnixTs


class TestCaseOwnerOption(BaseSchema):
    id: IdStr
    username: str


class TestCaseListData(PageData[TestCaseListItem]):
    pass
