"""Invite service — manages join codes and invite links per competition.

Each competition has at most:
  - one ACTIVE join code  (InviteType.CODE)
  - one ACTIVE invite link (InviteType.LINK)

Admin can regenerate either, which disables the previous active one.
"""

import secrets
import string
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import InviteStatus, InviteType
from app.modules.competitions.models import CompetitionInvite


def _generate_code(length: int = 6) -> str:
    """Generate a short, human-friendly join code (uppercase alphanumeric)."""
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _generate_token(length: int = 24) -> str:
    """Generate a URL-safe invite link token."""
    return secrets.token_urlsafe(length)


async def get_active_invite(
    session: AsyncSession,
    competition_id: uuid.UUID,
    invite_type: InviteType,
) -> CompetitionInvite | None:
    """Get the single active invite of a given type for a competition."""
    result = await session.execute(
        select(CompetitionInvite).where(
            CompetitionInvite.competition_id == competition_id,
            CompetitionInvite.invite_type == invite_type,
            CompetitionInvite.status == InviteStatus.ACTIVE,
        ).limit(1)
    )
    return result.scalars().first()


async def resolve_competition_by_code(
    session: AsyncSession,
    code: str,
) -> CompetitionInvite | None:
    """Find the active invite matching a join code (case-insensitive)."""
    result = await session.execute(
        select(CompetitionInvite).where(
            CompetitionInvite.code == code.strip().upper(),
            CompetitionInvite.invite_type == InviteType.CODE,
            CompetitionInvite.status == InviteStatus.ACTIVE,
        ).limit(1)
    )
    return result.scalars().first()


async def resolve_competition_by_token(
    session: AsyncSession,
    token: str,
) -> CompetitionInvite | None:
    """Find the active invite matching an invite link token."""
    result = await session.execute(
        select(CompetitionInvite).where(
            CompetitionInvite.code == token.strip(),
            CompetitionInvite.invite_type == InviteType.LINK,
            CompetitionInvite.status == InviteStatus.ACTIVE,
        ).limit(1)
    )
    return result.scalars().first()


async def create_invite(
    session: AsyncSession,
    competition_id: uuid.UUID,
    invite_type: InviteType,
    *,
    created_by: uuid.UUID | None = None,
    code_override: str | None = None,
) -> CompetitionInvite:
    """Create a new active invite, disabling any existing active one of the same type."""
    # Disable existing active invite of the same type
    await _disable_active(session, competition_id, invite_type)

    code = code_override
    if code is None:
        code = _generate_code() if invite_type == InviteType.CODE else _generate_token()

    invite = CompetitionInvite(
        competition_id=competition_id,
        invite_type=invite_type,
        code=code,
        status=InviteStatus.ACTIVE,
        created_by=created_by,
    )
    session.add(invite)
    await session.flush()
    return invite


async def regenerate_invite(
    session: AsyncSession,
    competition_id: uuid.UUID,
    invite_type: InviteType,
    *,
    created_by: uuid.UUID | None = None,
) -> CompetitionInvite:
    """Regenerate the active invite — disables old, creates new."""
    return await create_invite(
        session, competition_id, invite_type, created_by=created_by
    )


async def get_invite_state(
    session: AsyncSession,
    competition_id: uuid.UUID,
) -> dict:
    """Get the full invite state for a competition (both code + link)."""
    active_code = await get_active_invite(session, competition_id, InviteType.CODE)
    active_link = await get_active_invite(session, competition_id, InviteType.LINK)

    return {
        "code": _invite_to_dict(active_code) if active_code else None,
        "link": _invite_to_dict(active_link) if active_link else None,
    }


def _invite_to_dict(invite: CompetitionInvite) -> dict:
    return {
        "id": str(invite.id),
        "code": invite.code,
        "invite_type": invite.invite_type.value if hasattr(invite.invite_type, 'value') else str(invite.invite_type),
        "status": invite.status.value if hasattr(invite.status, 'value') else str(invite.status),
        "use_count": invite.use_count,
        "max_uses": invite.max_uses,
        "created_at": invite.created_at.isoformat() if invite.created_at else None,
    }


async def _disable_active(
    session: AsyncSession,
    competition_id: uuid.UUID,
    invite_type: InviteType,
) -> None:
    """Disable all currently active invites of a given type for a competition."""
    result = await session.execute(
        select(CompetitionInvite).where(
            CompetitionInvite.competition_id == competition_id,
            CompetitionInvite.invite_type == invite_type,
            CompetitionInvite.status == InviteStatus.ACTIVE,
        )
    )
    for invite in result.scalars().all():
        invite.status = InviteStatus.DISABLED
