from __future__ import annotations

from pydantic import Field

from app.schemas.common import BaseSchema
from app.schemas.types import IdStr, NameStr, UrlStr, UnixTs


class CollectionListItem(BaseSchema):
    id: IdStr
    projectId: IdStr
    name: NameStr
    requestCount: int = Field(ge=0)
    updatedAt: UnixTs


class CollectionCreateRequest(BaseSchema):
    projectId: IdStr
    name: NameStr
    variables: dict[str, object] = Field(default_factory=dict)


class CollectionUpdateRequest(BaseSchema):
    name: NameStr | None = None
    variables: dict[str, object] | None = None


class ApiRequestPublic(BaseSchema):
    id: IdStr
    collectionId: IdStr
    groupId: IdStr | None = None
    name: NameStr
    method: str = Field(min_length=1, max_length=16)
    url: UrlStr
    headers: dict[str, object] = Field(default_factory=dict)
    auth: dict[str, object] = Field(default_factory=dict)
    body: dict[str, object] = Field(default_factory=dict)
    asserts: dict[str, object] = Field(default_factory=dict)
    updatedAt: UnixTs


class ApiCollectionGroupPublic(BaseSchema):
    id: IdStr
    collectionId: IdStr
    name: NameStr
    order: int = Field(ge=0)


class ApiCollectionGroupWithRequests(ApiCollectionGroupPublic):
    requests: list[ApiRequestPublic] = Field(default_factory=list)


class ApiCollectionDetail(BaseSchema):
    id: IdStr
    projectId: IdStr
    name: NameStr
    variables: dict[str, object] = Field(default_factory=dict)
    groups: list[ApiCollectionGroupWithRequests] = Field(default_factory=list)
    requests: list[ApiRequestPublic] = Field(default_factory=list)
    updatedAt: UnixTs


class GroupCreateRequest(BaseSchema):
    name: NameStr


class GroupUpdateRequest(BaseSchema):
    name: NameStr


class GroupUpdateByIdRequest(BaseSchema):
    groupId: IdStr
    name: NameStr


class GroupOrderItem(BaseSchema):
    id: IdStr
    order: int = Field(ge=0)


class GroupsReorderRequest(BaseSchema):
    items: list[GroupOrderItem] = Field(alias="groups", min_length=1, max_length=10_000)


class ApiRequestCreateRequest(BaseSchema):
    groupId: IdStr | None = None
    name: NameStr
    method: str = Field(min_length=1, max_length=16)
    url: UrlStr
    headers: dict[str, object] = Field(default_factory=dict)
    auth: dict[str, object] = Field(default_factory=dict)
    body: dict[str, object] = Field(default_factory=dict)
    asserts: dict[str, object] = Field(default_factory=dict)


class ImportCollectionRequest(BaseSchema):
    projectId: IdStr
    format: str = Field(min_length=1, max_length=32)
    content: str = Field(min_length=1)


class PostmanCloudListRequest(BaseSchema):
    projectId: IdStr
    apiKey: str | None = Field(default=None, max_length=512)
    workspaceId: str | None = Field(default=None, max_length=128)


class PostmanCloudSyncRequest(PostmanCloudListRequest):
    collectionUid: str = Field(min_length=1, max_length=255)


class PostmanCloudCollectionListItem(BaseSchema):
    id: str | None = None
    uid: str
    name: str
    updatedAt: str | None = None


class PostmanCloudCollectionListData(BaseSchema):
    items: list[PostmanCloudCollectionListItem] = Field(default_factory=list)


class PostmanCloudSyncData(BaseSchema):
    postmanUid: str
    collection: ApiCollectionDetail


class ExportCollectionData(BaseSchema):
    format: str = Field(min_length=1, max_length=32)
    content: str = Field(min_length=1)


class RunCollectionRequest(BaseSchema):
    envId: IdStr | None = None
    concurrency: int = Field(default=1, ge=1, le=100)
    iterations: int = Field(default=1, ge=1, le=1000)


class RunApiRequestRequest(BaseSchema):
    envId: IdStr | None = None
