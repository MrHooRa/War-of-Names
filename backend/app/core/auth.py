"""JWT creation/verification and password hashing utilities."""

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select

from app.config import settings
from app.core.database import async_session
from app.modules.auth.models import Account

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
_bearer = HTTPBearer(auto_error=False)

ALGORITHM = "HS256"


def hash_password(plain: str) -> str:
    return _pwd.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd.verify(plain, hashed)


def create_access_token(account_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    return jwt.encode(
        {"sub": account_id, "exp": expire},
        settings.jwt_secret,
        algorithm=ALGORITHM,
    )


async def get_current_account(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> Account:
    """FastAPI dependency — resolves Bearer token to Account or raises 401."""
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="يرجى تسجيل الدخول أولاً",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not credentials:
        raise exc
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=[ALGORITHM])
        account_id: str | None = payload.get("sub")
        if not account_id:
            raise exc
    except JWTError:
        raise exc

    async with async_session() as session:
        result = await session.execute(select(Account).where(Account.id == account_id))
        account = result.scalars().first()

    if not account or account.status != "active":
        raise exc
    return account


async def get_admin_account(
    account: Annotated[Account, Depends(get_current_account)],
) -> Account:
    """FastAPI dependency — resolves to Account only if user is an admin."""
    if not account.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ليس لديك صلاحيات المشرف",
        )
    return account
