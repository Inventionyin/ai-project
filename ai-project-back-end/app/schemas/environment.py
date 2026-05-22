from __future__ import annotations

from pydantic import Field

from app.schemas.common import BaseSchema
from app.schemas.types import IdStr, NameStr, UnixTs, UrlStr


class HealthCheckConfig(BaseSchema):
    url: UrlStr
    timeoutMs: int = Field(ge=1, le=60_000)
    expectedStatus: int = Field(ge=100, le=599)


class EnvironmentCreateRequest(BaseSchema):
    name: NameStr
    baseUrl: UrlStr
    variables: dict[str, str] = Field(default_factory=dict)
    secrets: dict[str, str] = Field(default_factory=dict)
    healthCheck: HealthCheckConfig | None = None


class EnvironmentUpdateRequest(BaseSchema):
    name: NameStr | None = None
    baseUrl: UrlStr | None = None
    variables: dict[str, str] | None = None
    secrets: dict[str, str] | None = None
    healthCheck: HealthCheckConfig | None = None


class EnvironmentPublic(BaseSchema):
    id: IdStr
    projectId: IdStr
    name: NameStr
    baseUrl: UrlStr
    variables: dict[str, str] = Field(default_factory=dict)
    secretKeys: list[str] = Field(default_factory=list)
    healthCheck: HealthCheckConfig | None = None
    createdAt: UnixTs | None = None
    updatedAt: UnixTs | None = None
