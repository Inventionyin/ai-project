from __future__ import annotations

from pydantic import Field

from app.schemas.common import BaseSchema
from app.schemas.types import IdStr, NameStr, UnixTs, UrlStr


class ApiTargetListItem(BaseSchema):
    id: IdStr
    projectId: IdStr
    name: NameStr
    baseUrl: UrlStr
    defaultMethod: str | None = Field(default=None, min_length=1, max_length=16)
    defaultPath: str | None = Field(default=None, max_length=1024)
    headers: dict[str, object] = Field(default_factory=dict)
    authRef: dict[str, object] = Field(default_factory=dict)
    timeoutMs: int = Field(ge=1, le=600000)
    enabled: bool
    version: int = Field(ge=1)
    updatedAt: UnixTs


class ApiTargetDetail(ApiTargetListItem):
    createdAt: UnixTs


class ApiTargetCreateRequest(BaseSchema):
    projectId: IdStr
    name: NameStr
    baseUrl: UrlStr
    defaultMethod: str | None = Field(default=None, min_length=1, max_length=16)
    defaultPath: str | None = Field(default=None, max_length=1024)
    headers: dict[str, object] = Field(default_factory=dict)
    authRef: dict[str, object] = Field(default_factory=dict)
    timeoutMs: int = Field(default=10000, ge=1, le=600000)
    enabled: bool = True


class ApiTargetUpdateRequest(BaseSchema):
    name: NameStr
    baseUrl: UrlStr
    defaultMethod: str | None = Field(default=None, min_length=1, max_length=16)
    defaultPath: str | None = Field(default=None, max_length=1024)
    headers: dict[str, object] = Field(default_factory=dict)
    authRef: dict[str, object] = Field(default_factory=dict)
    timeoutMs: int = Field(ge=1, le=600000)
    enabled: bool
    version: int = Field(ge=1)
