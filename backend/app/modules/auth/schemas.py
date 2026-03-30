"""Auth request/response Pydantic models."""

import re

from pydantic import BaseModel, field_validator


class RegisterRequest(BaseModel):
    username: str
    real_name: str
    password: str
    consent_accepted: bool

    @field_validator("username")
    @classmethod
    def username_clean(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^[a-zA-Z0-9_]{3,30}$", v):
            raise ValueError(
                "اسم المستخدم يجب أن يكون بين 3-30 حرفاً "
                "(أحرف إنجليزية وأرقام وشرطة سفلية فقط)"
            )
        return v

    @field_validator("real_name")
    @classmethod
    def real_name_clean(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2 or len(v) > 100:
            raise ValueError("الاسم الحقيقي يجب أن يكون بين 2-100 حرف")
        # Strip HTML tags for defense-in-depth
        import re as _re
        if _re.search(r"<[^>]+>", v):
            raise ValueError("الاسم لا يمكن أن يحتوي على رموز HTML")
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("كلمة المرور يجب أن تكون 6 أحرف على الأقل")
        return v

    @field_validator("consent_accepted")
    @classmethod
    def consent_required(cls, v: bool) -> bool:
        if v is not True:
            raise ValueError("يجب الموافقة على شروط الاستخدام وسياسة الخصوصية للمتابعة")
        return v


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    token: str
    account_id: str
    username: str
    real_name: str
    is_admin: bool = False
    is_owner: bool = False


class MeResponse(BaseModel):
    account_id: str
    username: str
    real_name: str
    is_admin: bool = False
    is_owner: bool = False
