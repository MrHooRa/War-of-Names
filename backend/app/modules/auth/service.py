"""Account registration and authentication service."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import hash_password, verify_password
from app.core.enums import AccountStatus, AuditActorType
from app.core.utils import now_riyadh_naive
from app.modules.audit.service import write_audit
from app.modules.auth.models import Account


async def register_account(
    session: AsyncSession,
    username: str,
    real_name: str,
    password: str,
    consent_accepted: bool,
    ip_address: str | None = None,
    client_context: dict | None = None,
) -> Account:
    """Create a new account. Raises ValueError if username taken or consent is missing."""
    existing = await session.execute(
        select(Account).where(Account.username == username)
    )
    if existing.scalars().first():
        raise ValueError("اسم المستخدم مستخدم بالفعل")
    if consent_accepted is not True:
        raise ValueError("يجب الموافقة على شروط الاستخدام وسياسة الخصوصية للمتابعة")

    account = Account(
        id=uuid.uuid4(),
        username=username,
        real_name=real_name,
        password_hash=hash_password(password),
        status=AccountStatus.ACTIVE,
        consent_at=now_riyadh_naive(),
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
        after_state={
            "username": username,
            "real_name": real_name,
            "client_context": client_context,
        },
        ip_address=ip_address,
    )

    await session.commit()
    await session.refresh(account)
    return account


async def authenticate(
    session: AsyncSession,
    username: str,
    password: str,
) -> Account | None:
    """Verify credentials for active accounts only.

    Returns the Account on success, or None for unknown credentials and any
    non-active account state so login does not leak account status.
    """
    result = await session.execute(
        select(Account).where(Account.username == username)
    )
    account = result.scalars().first()
    if not account:
        return None
    if account.status != AccountStatus.ACTIVE:
        return None
    if not verify_password(password, account.password_hash):
        return None
    return account
