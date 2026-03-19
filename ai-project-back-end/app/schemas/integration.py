from __future__ import annotations

from typing import Annotated

from pydantic import Field

from app.schemas.common import BaseSchema
from app.schemas.types import IdStr, TitleStr, UrlStr

LabelStr = Annotated[str, Field(min_length=1, max_length=64)]


class IssueCreateRequest(BaseSchema):
    projectId: IdStr
    runId: IdStr
    caseRunId: IdStr | None = None
    title: TitleStr
    description: str | None = Field(default=None, max_length=10_000)
    labels: list[LabelStr] = Field(default_factory=list, max_length=50)


class IssueCreateData(BaseSchema):
    issueId: IdStr
    url: UrlStr | None = None

