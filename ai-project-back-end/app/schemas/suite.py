from __future__ import annotations

from pydantic import Field

from app.models.enums import Priority, TestCaseStatus, TestCaseType
from app.schemas.common import BaseSchema, PageData
from app.schemas.types import IdStr, NameStr, TitleStr, UnixTs


class SuiteConfig(BaseSchema):
    timeoutSec: int = Field(default=600, ge=1, le=86_400)
    concurrency: int = Field(default=4, ge=1, le=256)
    retryCount: int = Field(default=1, ge=0, le=20)
    retryOnlyOn: list[str] = Field(default_factory=lambda: ["NETWORK", "TIMEOUT", "FLAKE"], max_length=32)
    failFast: bool = Field(default=False)
    variables: dict[str, str] = Field(default_factory=dict)


class SuiteCreateRequest(BaseSchema):
    projectId: IdStr
    name: NameStr
    defaultEnvId: IdStr | None = None
    config: SuiteConfig


class SuitePutRequest(BaseSchema):
    projectId: IdStr
    name: NameStr
    defaultEnvId: IdStr | None = None
    config: SuiteConfig


class SuiteItemInput(BaseSchema):
    testcaseId: IdStr
    orderNo: int = Field(ge=1)
    params: dict[str, object] = Field(default_factory=dict)


class SuiteItemsUpsertRequest(BaseSchema):
    items: list[SuiteItemInput] = Field(min_length=1, max_length=10_000)


class SuitePublic(BaseSchema):
    id: IdStr
    projectId: IdStr
    name: NameStr
    defaultEnvId: IdStr | None = None
    config: SuiteConfig
    createdAt: UnixTs
    updatedAt: UnixTs


class SuiteListItem(SuitePublic):
    pass


class SuiteListData(PageData[SuiteListItem]):
    pass


class SuiteItemPublic(BaseSchema):
    id: IdStr
    suiteId: IdStr
    testcaseId: IdStr
    orderNo: int = Field(ge=1)
    params: dict[str, object] = Field(default_factory=dict)
    testcaseTitle: TitleStr
    testcaseType: TestCaseType
    testcasePriority: Priority
    testcaseStatus: TestCaseStatus

