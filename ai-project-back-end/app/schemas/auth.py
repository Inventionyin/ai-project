from __future__ import annotations

import re

from pydantic import Field, field_validator, model_validator

from app.schemas.common import BaseSchema
from app.schemas.types import EmailStr, IdStr, NameStr, UnixTs


class RegisterRequest(BaseSchema):
    phone: str = Field(min_length=11, max_length=20, pattern=r"^1[3-9]\d{9}$")
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)
    confirmPassword: str = Field(min_length=8, max_length=128)
    captcha: str = Field(min_length=1, max_length=16)

    @field_validator("password")
    @classmethod
    def _validate_password_complexity(cls, v: str) -> str:
        if not re.search(r"[A-Za-z]", v) or not re.search(r"\d", v):
            raise ValueError("密码复杂度不足：需包含字母和数字")
        return v

    @model_validator(mode="after")
    def _validate_confirm_password(self) -> "RegisterRequest":
        if self.password != self.confirmPassword:
            raise ValueError("confirmPassword must match password")
        return self


class RegisterResponseData(BaseSchema):
    userId: IdStr
    phone: str
    username: str
    createdAt: UnixTs


class LoginRequest(BaseSchema):
    username: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class LoginResponseData(BaseSchema):
    accessToken: str = Field(min_length=1)
    expiresIn: int = Field(ge=1)


class LogoutResponseData(BaseSchema):
    success: bool = True


class MeResponseData(BaseSchema):
    userId: IdStr
    email: EmailStr | None = None
    phone: str | None = None
    username: str | None = None
    name: NameStr
    roles: list[str] = Field(min_length=0)
    tenantId: IdStr
