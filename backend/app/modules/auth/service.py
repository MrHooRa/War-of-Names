"""Account registration and authentication service."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import hash_password, verify_password
from app.core.enums import AccountStatus, AuditActorType
from app.modules.audit.service import write_audit
from app.modules.auth.models import Account


async def register_account(
    session: AsyncSession,
    username: str,
    real_name: str,
    password: str,
) -> Account:
    """Create a new account. Raises ValueError if username taken."""
    existing = await session.execute(
        select(Account).where(Account.username == username)
    )
    if existing.scalars().first():
        raise ValueError("اسم المستخدم مستخدم بالفعل")

    account = Account(
        id=uuid.uuid4(),
        username=username,
        real_name=real_name,
        password_hash=hash_password(password),
        status=AccountStatus.ACTIVE,
    )
    session.add(account)
    await session.flush()  # ensure account.id is available for audit

    # Audit trail for user registration
    await write_audit(
        session,
        actor_id=account.id,
        actor_type=AuditActorType.PARTICIPANT,
        subject_type="account",
        subject_id=account.id,
        event_type="account_registered",
        summary=f"تسجيل حساب جديد: {username}",
        after_state={"username": username, "real_name": real_name},
    )

    await session.commit()
    await session.refresh(account)
    return account


async def authenticate(
    session: AsyncSession,
    username: str,
    password: str,
) -> Account | None:
    """Verify credentials. Returns Account on success, None on failure."""
    result = await session.execute(
        select(Account).where(Account.username == username)
    )
    account = result.scalars().first()
    if not account:
        return None
    if not verify_password(password, account.password_hash):
        return None
    return account
