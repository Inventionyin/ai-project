from __future__ import annotations

from pydantic import Field

from app.models.enums import ArtifactType
from app.schemas.common import BaseSchema
from app.schemas.types import IdStr, UrlStr


class ArtifactGetData(BaseSchema):
    id: IdStr
    type: ArtifactType
    signedUrl: UrlStr
    meta: dict[str, object] = Field(default_factory=dict)

