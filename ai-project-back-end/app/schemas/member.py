from __future__ import annotations

import uuid
from pydantic import BaseModel


class MemberListItem(BaseModel):
    id: str
    userId: str
    userName: str
    userEmail: str
    role: str
    createdAt: int | None = None


class MemberCreateRequest(BaseModel):
    userId: str
    role: str = "VIEWER"


class MemberUpdateRequest(BaseModel):
    role: str


class MemberListData(BaseModel):
    items: list[MemberListItem]
    total: int
