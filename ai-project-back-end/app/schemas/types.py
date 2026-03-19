from __future__ import annotations

from typing import Annotated

from pydantic import Field

IdStr = Annotated[str, Field(min_length=1, max_length=64)]
UnixTs = Annotated[int, Field(ge=0)]

NameStr = Annotated[str, Field(min_length=1, max_length=255)]
TitleStr = Annotated[str, Field(min_length=1, max_length=100)]

UrlStr = Annotated[str, Field(min_length=1, max_length=2048)]
VersionStr = Annotated[str, Field(min_length=1, max_length=32)]

EmailStr = Annotated[
    str,
    Field(
        min_length=3,
        max_length=255,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    ),
]

