"""Dashboard read-model endpoint — aggregates player stats for the home page."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select

from app.core.auth import get_current_account
from app.core.database import async_session
from app.core.enums import AttackOutcome, MembershipStatus, OwnedItemStatus
from app.modules.attacks.models import AttackAttempt
from app.modules.auth.models import Account
from app.modules.competitions.models import Competition, Membership
from app.modules.notifications.models import Notification
from app.modules.store.models import OwnedItem

router = APIRouter(tags=["dashboard"])
CurrentAccount = Annotated[Account, Depends(get_current_account)]


@router.get("/api/me/dashboard")
async def get_dashboard(account: CurrentAccount):
    async with async_session() as session:
        # Active membership
        mem_result = await session.execute(
            select(Membership, Competition)
            .join(Competition, Membership.competition_id == Competition.id)
            .where(
                Membership.account_id == account.id,
                Membership.status == MembershipStatus.ACTIVE,
                Competition.status == "active",
            )
            .limit(1)
        )
        row = mem_result.first()
        if not row:
            return {"success": True, "data": None}

        membership, competition = row

        # Rank
        rank_result = await session.execute(
            select(func.count()).where(
                Membership.competition_id == competition.id,
                Membership.status == MembershipStatus.ACTIVE,
                Membership.current_balance > membership.current_balance,
            )
        )
        rank = (rank_result.scalar() or 0) + 1

        # Total active members
        total_members = (await session.execute(
            select(func.count()).where(
                Membership.competition_id == competition.id,
                Membership.status == MembershipStatus.ACTIVE,
            )
        )).scalar() or 0

        # Attacks sent
        attacks_sent = (await session.execute(
            select(func.count()).where(
                AttackAttempt.attacker_id == membership.id,
                AttackAttempt.outcome.in_([AttackOutcome.SUCCEEDED, AttackOutcome.FAILED]),
            )
        )).scalar() or 0

        attacks_won = (await session.execute(
            select(func.count()).where(
                AttackAttempt.attacker_id == membership.id,
                AttackAttempt.outcome == AttackOutcome.SUCCEEDED,
            )
        )).scalar() or 0

        # Attacks received
        attacks_received = (await session.execute(
            select(func.count()).where(
                AttackAttempt.target_id == membership.id,
                AttackAttempt.outcome.in_([AttackOutcome.SUCCEEDED, AttackOutcome.FAILED]),
            )
        )).scalar() or 0

        attacks_defended = (await session.execute(
            select(func.count()).where(
                AttackAttempt.target_id == membership.id,
                AttackAttempt.outcome == AttackOutcome.FAILED,
            )
        )).scalar() or 0

        # Inventory count
        inventory_count = (await session.execute(
            select(func.count()).where(
                OwnedItem.membership_id == membership.id,
                OwnedItem.status == OwnedItemStatus.AVAILABLE,
            )
        )).scalar() or 0

        # Unread notifications
        unread_notif = (await session.execute(
            select(func.count()).where(
                Notification.recipient_id == account.id,
                Notification.is_read == False,
            )
        )).scalar() or 0

        win_rate = round((attacks_won / attacks_sent * 100) if attacks_sent > 0 else 0)

    return {
        "success": True,
        "data": {
            "account_id": str(account.id),
            "username": account.username,
            "real_name": account.real_name,
            "membership_id": str(membership.id),
            "competition_id": str(competition.id),
            "competition_name": competition.name,
            "alias": membership.current_alias or account.username,
            "balance": membership.current_balance,
            "rank": rank,
            "total_members": total_members,
            "protection": membership.protection,
            "is_bankrupt": membership.is_bankrupt,
            "attacks_sent": attacks_sent,
            "attacks_won": attacks_won,
            "attacks_received": attacks_received,
            "attacks_defended": attacks_defended,
            "win_rate": win_rate,
            "inventory_count": inventory_count,
            "unread_notifications": unread_notif,
        },
    }
