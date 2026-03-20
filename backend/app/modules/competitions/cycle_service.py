"""
Cycle lifecycle service — start, end, advance cycles with real operational events.

Every cycle transition triggers:
  - Protection resets (clear temporary protections at cycle rollover)
  - Bankruptcy recovery (clear is_bankrupt flags)
  - Member notifications (CYCLE_STARTED / CYCLE_ENDED)
  - Status cascading (deactivate previous active cycle in season)
"""

import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import (
    BankruptcyState,
    CycleStatus,
    MembershipStatus,
    NotificationPriority,
    NotificationType,
    ProtectionType,
)
from app.modules.attacks.models import BankruptcyRecord
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
            Membership.protection != ProtectionType.NONE,
        )
    )
    protected = result.scalars().all()
    for m in protected:
        m.protection = ProtectionType.NONE
    return len(protected)


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
            .values(status=BankruptcyState.CLEARED, resolved_at=datetime.utcnow())
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
        .values(status=CycleStatus.COMPLETED, ends_at=datetime.utcnow())
    )

    # 2. Activate this cycle
    cycle.status = CycleStatus.ACTIVE
    cycle.starts_at = datetime.utcnow()

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
    cycle.ends_at = datetime.utcnow()

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
