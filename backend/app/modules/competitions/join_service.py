"""Join service — handles membership creation via invite code or link.

Centralizes all join validation and membership creation logic so that
both the code-based and link-based join endpoints share the same flow.
"""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import (
    CompetitionStatus,
    CycleStatus,
    InviteStatus,
    LedgerDirection,
    LedgerEntryType,
    MembershipStatus,
    SeasonStatus,
)
from app.modules.competitions.models import (
    AliasRecord,
    Competition,
    CompetitionInvite,
    Cycle,
    Membership,
    Season,
)
from app.modules.scoring.models import LedgerEntry
from app.modules.settings.service import get_setting

_FALLBACK_INITIAL_BALANCE = 1000


class JoinError(Exception):
    """Structured join error with machine-readable error_code."""

    def __init__(self, error_code: str, message: str, status_code: int = 400):
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


async def validate_join(
    session: AsyncSession,
    competition: Competition,
    invite: CompetitionInvite,
    account_id: uuid.UUID,
    alias: str,
) -> None:
    """Validate all join preconditions. Raises JoinError on failure."""
    # Competition state
    if competition.status not in (CompetitionStatus.ACTIVE, CompetitionStatus.REGISTRATION_OPEN):
        raise JoinError("competition_inactive", "المنافسة غير مفتوحة للتسجيل حالياً")

    if not competition.registration_open:
        raise JoinError("registration_closed", "التسجيل مغلق في هذه المنافسة")

    # Invite state
    if invite.status != InviteStatus.ACTIVE:
        raise JoinError("invite_invalid", "رمز الدعوة غير صالح")

    if invite.expires_at and invite.expires_at <= datetime.utcnow():
        raise JoinError("invite_expired", "رمز الدعوة منتهي الصلاحية")

    if invite.max_uses and invite.use_count >= invite.max_uses:
        raise JoinError("invite_exhausted", "رمز الدعوة وصل للحد الأقصى من الاستخدامات")

    # Duplicate membership
    existing = await session.execute(
        select(Membership).where(
            Membership.account_id == account_id,
            Membership.competition_id == competition.id,
        )
    )
    if existing.scalars().first():
        raise JoinError("already_joined", "أنت مسجل بالفعل في هذه المنافسة")

    # Alias uniqueness
    alias_conflict = await session.execute(
        select(Membership).where(
            Membership.competition_id == competition.id,
            Membership.current_alias == alias,
        )
    )
    if alias_conflict.scalars().first():
        raise JoinError("alias_taken", "هذا اللقب مستخدم بالفعل في المنافسة")

    # Lifecycle readiness (season + cycle should exist)
    season = await _get_active_season(session, competition.id)
    if not season:
        raise JoinError("lifecycle_not_ready", "لا يوجد موسم نشط في المنافسة — لا يمكن الانضمام حالياً")


async def execute_join(
    session: AsyncSession,
    competition: Competition,
    invite: CompetitionInvite,
    account_id: uuid.UUID,
    alias: str,
) -> dict:
    """Create membership + ledger + alias record. Returns join summary.

    Caller must have already validated via validate_join().
    """
    # Initial balance from settings
    initial_balance = await get_setting(
        session, "score_initial_balance", competition_id=competition.id
    )
    if initial_balance is None:
        initial_balance = _FALLBACK_INITIAL_BALANCE
    initial_balance = int(initial_balance)

    # Create membership
    membership = Membership(
        account_id=account_id,
        competition_id=competition.id,
        status=MembershipStatus.ACTIVE,
        current_alias=alias,
        current_balance=initial_balance,
    )
    session.add(membership)
    await session.flush()

    # Get active season/cycle
    season = await _get_active_season(session, competition.id)
    cycle = None
    if season:
        cycle = await _get_active_cycle(session, season.id)

    # Grant initial balance via ledger
    ledger_entry = LedgerEntry(
        membership_id=membership.id,
        competition_id=competition.id,
        season_id=season.id if season else None,
        cycle_id=cycle.id if cycle else None,
        entry_type=LedgerEntryType.INITIAL_BALANCE,
        amount=initial_balance,
        direction=LedgerDirection.CREDIT,
        balance_before=0,
        balance_after=initial_balance,
        reason="رصيد ابتدائي عند الانضمام",
    )
    session.add(ledger_entry)

    # Create alias record
    alias_record = AliasRecord(
        membership_id=membership.id,
        alias_value=alias,
        is_active=True,
        season_id=season.id if season else None,
        cycle_id=cycle.id if cycle else None,
    )
    session.add(alias_record)

    # Increment invite use count
    invite.use_count += 1

    await session.commit()

    return {
        "membership_id": str(membership.id),
        "competition_id": str(competition.id),
        "competition_name": competition.name,
        "alias": membership.current_alias,
        "balance": membership.current_balance,
    }


async def _get_active_season(session: AsyncSession, competition_id: uuid.UUID) -> Season | None:
    result = await session.execute(
        select(Season).where(
            Season.competition_id == competition_id,
            Season.status == SeasonStatus.ACTIVE,
        ).limit(1)
    )
    return result.scalars().first()


async def _get_active_cycle(session: AsyncSession, season_id: uuid.UUID) -> Cycle | None:
    result = await session.execute(
        select(Cycle).where(
            Cycle.season_id == season_id,
            Cycle.status == CycleStatus.ACTIVE,
        ).limit(1)
    )
    return result.scalars().first()
