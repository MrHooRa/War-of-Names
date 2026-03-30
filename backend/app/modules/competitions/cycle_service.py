"""
Season & cycle lifecycle service — start, end, advance with real operational events.

Every cycle transition triggers:
  - Protection resets (clear temporary protections at cycle rollover)
  - Bankruptcy recovery (clear is_bankrupt flags)
  - Member notifications (CYCLE_STARTED / CYCLE_ENDED)
  - Status cascading (deactivate previous active cycle in season)

Season transitions trigger:
  - Multi-active prevention (complete other active seasons)
  - Cascade to child cycles (end active cycles when ending a season)
  - Member notifications (GENERAL — no dedicated season enum value)
"""

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import (
    BankruptcyState,
    CycleStatus,
    MembershipStatus,
    NotificationPriority,
    NotificationType,
    SeasonStatus,
)
from app.core.utils import now_riyadh_naive
from app.modules.attacks.models import BankruptcyRecord
from app.modules.attacks.protection_service import (
    expire_active_protection_records,
    reconcile_membership_protection,
)
from app.modules.competitions.models import Cycle, Membership, Season
from app.modules.notifications.service import create_notification


class CycleTransitionResult:
    """Captures what happened during a cycle transition for reporting."""

    def __init__(self):
        self.protections_cleared: int = 0
        self.bankruptcies_cleared: int = 0
        self.members_notified: int = 0

    def to_dict(self) -> dict:
        return {
            "protections_cleared": self.protections_cleared,
            "bankruptcies_cleared": self.bankruptcies_cleared,
            "members_notified": self.members_notified,
        }


async def _get_competition_members(
    session: AsyncSession,
    competition_id: uuid.UUID,
) -> list:
    """Get all active members of a competition."""
    result = await session.execute(
        select(Membership).where(
            Membership.competition_id == competition_id,
            Membership.status == MembershipStatus.ACTIVE,
        )
    )
    return result.scalars().all()


async def _clear_protections(
    session: AsyncSession,
    competition_id: uuid.UUID,
) -> int:
    """Reset all temporary protections for competition members back to NONE."""
    result = await session.execute(
        select(Membership).where(
            Membership.competition_id == competition_id,
            Membership.status == MembershipStatus.ACTIVE,
        )
    )
    members = result.scalars().all()
    now = now_riyadh_naive()
    cleared = 0

    for membership in members:
        expired_records = await expire_active_protection_records(session, membership.id, now=now)
        previous_protection = membership.protection
        new_protection = await reconcile_membership_protection(session, membership, now=now)
        if expired_records or previous_protection != new_protection:
            cleared += 1

    return cleared


async def _clear_bankruptcies(
    session: AsyncSession,
    competition_id: uuid.UUID,
    cycle_id: uuid.UUID | None = None,
) -> int:
    """Clear bankruptcy flags on memberships and mark BankruptcyRecords as CLEARED."""
    # Clear membership flags
    result = await session.execute(
        select(Membership).where(
            Membership.competition_id == competition_id,
            Membership.is_bankrupt == True,
        )
    )
    bankrupt_members = result.scalars().all()
    for m in bankrupt_members:
        m.is_bankrupt = False

    # Mark active BankruptcyRecords as CLEARED
    if cycle_id:
        await session.execute(
            update(BankruptcyRecord)
            .where(
                BankruptcyRecord.cycle_id == cycle_id,
                BankruptcyRecord.status == BankruptcyState.ACTIVE,
            )
            .values(status=BankruptcyState.CLEARED, resolved_at=now_riyadh_naive())
        )

    return len(bankrupt_members)


async def _notify_members(
    session: AsyncSession,
    members: list,
    notification_type: NotificationType,
    title: str,
    message: str,
    priority: NotificationPriority = NotificationPriority.NORMAL,
    reference_type: str | None = None,
    reference_id: uuid.UUID | None = None,
) -> int:
    """Send a notification to all members in the list."""
    for m in members:
        await create_notification(
            session,
            recipient_id=m.account_id,
            notification_type=notification_type,
            title=title,
            message=message,
            membership_id=m.id,
            priority=priority,
            reference_type=reference_type,
            reference_id=reference_id,
        )
    return len(members)


async def start_cycle(
    session: AsyncSession,
    cycle: Cycle,
    season: Season,
) -> CycleTransitionResult:
    """
    Start a cycle — the full lifecycle event:
      1. Deactivate any other active cycle in the same season
      2. Activate this cycle with starts_at = now
      3. Clear protections from previous cycle
      4. Clear bankruptcies from previous cycle
      5. Notify all competition members
    """
    result = CycleTransitionResult()

    # 1. Deactivate other active cycles in the same season
    await session.execute(
        update(Cycle)
        .where(
            Cycle.season_id == season.id,
            Cycle.status == CycleStatus.ACTIVE,
            Cycle.id != cycle.id,
        )
        .values(status=CycleStatus.COMPLETED, ends_at=now_riyadh_naive())
    )

    # 2. Activate this cycle
    cycle.status = CycleStatus.ACTIVE
    cycle.starts_at = now_riyadh_naive()

    # 3. Clear protections
    result.protections_cleared = await _clear_protections(
        session, season.competition_id
    )

    # 4. Clear bankruptcies
    result.bankruptcies_cleared = await _clear_bankruptcies(
        session, season.competition_id
    )

    # 5. Notify all active members
    members = await _get_competition_members(session, season.competition_id)
    result.members_notified = await _notify_members(
        session,
        members,
        notification_type=NotificationType.CYCLE_STARTED,
        title="بداية دورة جديدة",
        message=f"بدأت {cycle.label}! تم إعادة تعيين الحماية وتصفية الإفلاس. حان وقت المعركة!",
        priority=NotificationPriority.HIGH,
        reference_type="cycle",
        reference_id=cycle.id,
    )

    return result


async def end_cycle(
    session: AsyncSession,
    cycle: Cycle,
    season: Season,
) -> CycleTransitionResult:
    """
    End a cycle — the full lifecycle event:
      1. Mark cycle as COMPLETED with ends_at = now
      2. Clear temporary protections
      3. Clear bankruptcies
      4. Notify all competition members
    """
    result = CycleTransitionResult()

    # 1. Complete the cycle
    cycle.status = CycleStatus.COMPLETED
    cycle.ends_at = now_riyadh_naive()

    # 2. Clear protections
    result.protections_cleared = await _clear_protections(
        session, season.competition_id
    )

    # 3. Clear bankruptcies
    result.bankruptcies_cleared = await _clear_bankruptcies(
        session, season.competition_id, cycle_id=cycle.id
    )

    # 4. Notify all active members
    members = await _get_competition_members(session, season.competition_id)
    result.members_notified = await _notify_members(
        session,
        members,
        notification_type=NotificationType.CYCLE_ENDED,
        title="انتهت الدورة",
        message=f"انتهت {cycle.label}. تم إعادة تعيين الحماية والإفلاس.",
        priority=NotificationPriority.NORMAL,
        reference_type="cycle",
        reference_id=cycle.id,
    )

    return result


async def maybe_auto_start_next_cycle(
    session: AsyncSession,
    season: Season,
    ended_cycle: Cycle,
) -> dict | None:
    """Start the next cycle automatically when the season setting enables it."""
    if season.status != SeasonStatus.ACTIVE:
        return None

    from app.modules.settings.service import get_setting

    auto_advance = await get_setting(
        session,
        "season_auto_advance_cycles",
        competition_id=season.competition_id,
        season_id=season.id,
        cycle_id=ended_cycle.id,
    )
    if not auto_advance:
        return None

    next_result = await session.execute(
        select(Cycle).where(
            Cycle.season_id == season.id,
            Cycle.order_index > ended_cycle.order_index,
            Cycle.status.in_([CycleStatus.DRAFT, CycleStatus.PAUSED]),
        ).order_by(Cycle.order_index)
    )
    next_cycle = next_result.scalars().first()
    if not next_cycle:
        return None

    started = await start_cycle(session, next_cycle, season)
    return {
        "cycle_id": str(next_cycle.id),
        "label": next_cycle.label,
        **started.to_dict(),
    }


async def advance_to_next_cycle(
    session: AsyncSession,
    current_cycle: Cycle,
    next_cycle: Cycle,
    season: Season,
) -> dict:
    """
    End the current cycle and start the next one in a single operation.
    Returns combined results from both transitions.
    """
    end_result = await end_cycle(session, current_cycle, season)
    start_result = await start_cycle(session, next_cycle, season)

    return {
        "ended": {
            "cycle_id": str(current_cycle.id),
            "label": current_cycle.label,
            **end_result.to_dict(),
        },
        "started": {
            "cycle_id": str(next_cycle.id),
            "label": next_cycle.label,
            **start_result.to_dict(),
        },
    }


async def broadcast_to_competition(
    session: AsyncSession,
    competition_id: uuid.UUID,
    title: str,
    message: str,
    priority: NotificationPriority = NotificationPriority.HIGH,
) -> int:
    """Send an announcement notification to all active members of a competition."""
    members = await _get_competition_members(session, competition_id)
    return await _notify_members(
        session,
        members,
        notification_type=NotificationType.ADMIN_ALERT,
        title=title,
        message=message,
        priority=priority,
    )


# ═══════════════════════════════════════════════════════════════════════════
# SEASON LIFECYCLE
# ═══════════════════════════════════════════════════════════════════════════


async def start_season(
    session: AsyncSession,
    season: Season,
    competition_id: uuid.UUID,
) -> dict:
    """
    Start a season — the full lifecycle event:
      1. Complete any other active season in the same competition
      2. Activate this season with starts_at = now
      3. Notify all competition members
    """
    now = now_riyadh_naive()

    # 1. Complete other active seasons in the same competition
    prev_result = await session.execute(
        select(Season).where(
            Season.competition_id == competition_id,
            Season.status == SeasonStatus.ACTIVE,
            Season.id != season.id,
        )
    )
    prev_seasons = prev_result.scalars().all()
    for s in prev_seasons:
        s.status = SeasonStatus.COMPLETED
        s.ends_at = now

    # 2. Activate this season
    season.status = SeasonStatus.ACTIVE
    season.starts_at = now

    # 3. Notify all active members
    members = await _get_competition_members(session, competition_id)
    notified = await _notify_members(
        session,
        members,
        notification_type=NotificationType.GENERAL,
        title="بداية موسم جديد",
        message=f"بدأ الموسم: {season.name}! استعد للمنافسة.",
        priority=NotificationPriority.HIGH,
        reference_type="season",
        reference_id=season.id,
    )

    return {
        "previous_seasons_completed": len(prev_seasons),
        "members_notified": notified,
    }


async def end_season(
    session: AsyncSession,
    season: Season,
    competition_id: uuid.UUID,
) -> dict:
    """
    End a season — the full lifecycle event:
      1. End all active cycles in this season (with full cycle-end effects)
      2. Mark season as COMPLETED with ends_at = now
      3. Notify all competition members
    """
    now = now_riyadh_naive()

    # 1. End all active cycles in this season (with full lifecycle events)
    active_cycles_result = await session.execute(
        select(Cycle).where(
            Cycle.season_id == season.id,
            Cycle.status == CycleStatus.ACTIVE,
        )
    )
    active_cycles = active_cycles_result.scalars().all()
    cycle_results = []
    for cycle in active_cycles:
        cr = await end_cycle(session, cycle, season)
        cycle_results.append({
            "cycle_id": str(cycle.id),
            "label": cycle.label,
            **cr.to_dict(),
        })

    # 2. Complete the season
    season.status = SeasonStatus.COMPLETED
    season.ends_at = now

    # 3. Notify all active members
    members = await _get_competition_members(session, competition_id)
    notified = await _notify_members(
        session,
        members,
        notification_type=NotificationType.GENERAL,
        title="انتهى الموسم",
        message=f"انتهى الموسم: {season.name}. شكراً لمشاركتك!",
        priority=NotificationPriority.NORMAL,
        reference_type="season",
        reference_id=season.id,
    )

    return {
        "cycles_ended": cycle_results,
        "members_notified": notified,
    }


async def close_expired_cycles(
    session: AsyncSession,
    competition_id: uuid.UUID,
) -> list[dict]:
    """
    Find all cycles that are still ACTIVE but whose ends_at has passed,
    and close them with full lifecycle events.

    Returns a list of closure results (one per auto-closed cycle).
    Call this at key operational points (cycle start, advance) as a
    lazy auto-close mechanism.
    """
    now = now_riyadh_naive()
    expired_result = await session.execute(
        select(Cycle, Season)
        .join(Season, Cycle.season_id == Season.id)
        .where(
            Season.competition_id == competition_id,
            Cycle.status == CycleStatus.ACTIVE,
            Cycle.ends_at != None,  # noqa: E711
            Cycle.ends_at < now,
        )
    )
    expired_rows = expired_result.all()

    results = []
    for cycle, season in expired_rows:
        cr = await end_cycle(session, cycle, season)
        results.append({
            "cycle_id": str(cycle.id),
            "label": cycle.label,
            "auto_closed": True,
            **cr.to_dict(),
        })

    return results
