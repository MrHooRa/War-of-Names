from __future__ import annotations

"""Protection lifecycle helpers.

`ProtectionRecord` is the authoritative source of protection state.
`Membership.protection` is only a cached summary used by read paths.
"""

import uuid
from collections.abc import Iterable
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ProtectionType

if TYPE_CHECKING:
    from app.modules.attacks.models import ProtectionRecord
    from app.modules.competitions.models import Membership

ATTACK_PARTIAL_PROTECTION_SOURCE = "attack_partial_protection"
ADMIN_PROTECTION_SOURCE = "admin_override"


def _now() -> datetime:
    from app.core.utils import now_riyadh_naive

    return now_riyadh_naive()


def active_protection_filters(now: datetime | None = None):
    """Return the shared active-window filter for protection records."""
    from app.modules.attacks.models import ProtectionRecord

    effective_now = now or _now()
    return and_(
        ProtectionRecord.starts_at <= effective_now,
        or_(
            ProtectionRecord.ends_at.is_(None),
            ProtectionRecord.ends_at > effective_now,
        ),
    )


def record_affects_membership_protection(record: ProtectionRecord) -> bool:
    """Return whether a record contributes to the membership-level protection cache."""
    if record.protection_type == ProtectionType.FULL:
        return True
    if record.protection_type != ProtectionType.PARTIAL:
        return False

    return not (
        record.source_type == ATTACK_PARTIAL_PROTECTION_SOURCE
    )


def resolve_membership_protection(records: Iterable[ProtectionRecord]) -> ProtectionType:
    """Resolve membership.protection from active records with correct precedence."""
    effective = ProtectionType.NONE

    for record in records:
        if not record_affects_membership_protection(record):
            continue
        if record.protection_type == ProtectionType.FULL:
            return ProtectionType.FULL
        if record.protection_type == ProtectionType.PARTIAL:
            effective = ProtectionType.PARTIAL

    return effective


async def get_active_protection_records(
    session: AsyncSession,
    membership_id: uuid.UUID,
    *,
    now: datetime | None = None,
) -> list[ProtectionRecord]:
    """Load active protection records for a membership."""
    from app.modules.attacks.models import ProtectionRecord

    result = await session.execute(
        select(ProtectionRecord).where(
            ProtectionRecord.membership_id == membership_id,
            active_protection_filters(now),
        )
    )
    return result.scalars().all()


async def reconcile_membership_protection(
    session: AsyncSession,
    membership: Membership,
    *,
    now: datetime | None = None,
) -> ProtectionType:
    """Sync the cached membership protection with the authoritative records."""
    effective_now = now or _now()
    await session.flush()
    active_records = await get_active_protection_records(session, membership.id, now=effective_now)
    membership.protection = resolve_membership_protection(active_records)
    return membership.protection


async def expire_active_protection_records(
    session: AsyncSession,
    membership_id: uuid.UUID,
    *,
    now: datetime | None = None,
    protection_type: ProtectionType | None = None,
    membership_level_only: bool = False,
) -> list[ProtectionRecord]:
    """Close active protection records and keep their history intact."""
    effective_now = now or _now()
    active_records = await get_active_protection_records(session, membership_id, now=effective_now)

    expired: list[ProtectionRecord] = []
    for record in active_records:
        if protection_type and record.protection_type != protection_type:
            continue
        if membership_level_only and not record_affects_membership_protection(record):
            continue
        record.ends_at = effective_now
        expired.append(record)

    return expired


async def create_protection_record(
    session: AsyncSession,
    membership: Membership,
    *,
    protection_type: ProtectionType,
    source_type: str,
    source_id: uuid.UUID | None = None,
    season_id: uuid.UUID | None = None,
    cycle_id: uuid.UUID | None = None,
    reason: str | None = None,
    starts_at: datetime | None = None,
    ends_at: datetime | None = None,
    reconcile_membership: bool = True,
) -> ProtectionRecord:
    """Create a protection record and optionally refresh the cached membership state."""
    from app.modules.attacks.models import ProtectionRecord

    effective_start = starts_at or _now()
    record = ProtectionRecord(
        membership_id=membership.id,
        protection_type=protection_type,
        source_type=source_type,
        source_id=source_id,
        season_id=season_id,
        cycle_id=cycle_id,
        reason=reason,
        starts_at=effective_start,
        ends_at=ends_at,
    )
    session.add(record)

    if reconcile_membership:
        await reconcile_membership_protection(session, membership, now=effective_start)

    return record
