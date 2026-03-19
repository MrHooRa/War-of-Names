"""Competition and membership Pydantic models."""

from pydantic import BaseModel, field_validator


class JoinRequest(BaseModel):
    invite_code: str
    alias: str

    @field_validator("alias")
    @classmethod
    def alias_clean(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2 or len(v) > 50:
            raise ValueError("اللقب يجب أن يكون بين 2-50 حرف")
        return v
