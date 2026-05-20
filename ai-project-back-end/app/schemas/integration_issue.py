from __future__ import annotations

from typing import Annotated

from pydantic import Field

from app.schemas.common import BaseSchema
from app.schemas.types import IdStr, TitleStr, UnixTs, UrlStr

ProviderStr = Annotated[str, Field(min_length=1, max_length=64)]


class IntegrationIssueCreateRequest(BaseSchema):
    provider: ProviderStr
    runId: IdStr
    caseRunId: IdStr | None = None
    title: TitleStr
    description: str | None = Field(default=None, max_length=10_000)
    url: UrlStr | None = None
    projectKey: str | None = Field(default=None, min_length=1, max_length=64)
    issueType: str | None = Field(default=None, min_length=1, max_length=64)
    config: dict[str, object] | None = None
    credentials: dict[str, object] | None = None


class IntegrationIssueDetail(BaseSchema):
    id: IdStr
    runId: IdStr
    caseRunId: IdStr | None = None
    provider: str
    issueKey: IdStr
    url: UrlStr
    createdAt: UnixTs | None = None
