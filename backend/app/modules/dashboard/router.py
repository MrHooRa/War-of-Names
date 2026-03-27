"""Dashboard read-model endpoint — aggregates player stats for the home page."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select

from app.core.auth import get_current_account
from app.core.database import async_session
from app.core.enums import AttackOutcome, CycleStatus, MembershipStatus, OwnedItemStatus, SeasonStatus
from app.modules.attacks.models import AttackAttempt
from app.modules.auth.models import Account
from app.modules.competitions.models import Competition, Cycle, Membership, Season
from app.modules.notifications.models import Notification
from app.modules.store.models import ItemDefinition, OwnedItem

router = APIRouter(tags=["dashboard"])
CurrentAccount = Annotated[Account, Depends(get_current_account)]


@router.get("/api/me/dashboard")
async def get_dashboard(account: CurrentAccount, competition_id: str | None = None):
    import uuid as _uuid

    async with async_session() as session:
        # Active membership
        query = (
            select(Membership, Competition)
            .join(Competition, Membership.competition_id == Competition.id)
            .where(
                Membership.account_id == account.id,
                Membership.status == MembershipStatus.ACTIVE,
                Competition.status == "active",
            )
        )
        if competition_id:
            try:
                cid = _uuid.UUID(competition_id)
                query = query.where(Competition.id == cid)
            except ValueError:
                pass
        query = query.limit(1)
        mem_result = await session.execute(query)
        row = mem_result.first()
        if not row:
            return {"success": True, "data": None}

        membership, competition = row

        # Active season + cycle
        season = (await session.execute(
            select(Season).where(
                Season.competition_id == competition.id,
                Season.status == SeasonStatus.ACTIVE,
            ).limit(1)
        )).scalars().first()

        cycle = None
        next_cycle = None
        if season:
            cycle = (await session.execute(
                select(Cycle).where(
                    Cycle.season_id == season.id,
                    Cycle.status == CycleStatus.ACTIVE,
                ).limit(1)
            )).scalars().first()

            if cycle:
                next_cycle = (await session.execute(
                    select(Cycle).where(
                        Cycle.season_id == season.id,
                        Cycle.status.in_([CycleStatus.DRAFT, CycleStatus.PAUSED]),
                        Cycle.order_index > cycle.order_index,
                    ).order_by(Cycle.order_index).limit(1)
                )).scalars().first()

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

        # Inventory count (AVAILABLE + ACTIVATED + PENDING — matches all inventory views)
        inventory_count = (await session.execute(
            select(func.count()).where(
                OwnedItem.membership_id == membership.id,
                OwnedItem.status.in_([OwnedItemStatus.AVAILABLE, OwnedItemStatus.ACTIVATED, OwnedItemStatus.PENDING]),
            )
        )).scalar() or 0

        # Unread notifications
        unread_notif = (await session.execute(
            select(func.count()).where(
                Notification.recipient_id == account.id,
                Notification.is_read == False,  # noqa: E712
                Notification.membership_id == membership.id,
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
            "season_id": str(season.id) if season else None,
            "season_name": season.name if season else None,
            "cycle_id": str(cycle.id) if cycle else None,
            "cycle_label": cycle.label if cycle else None,
            "cycle_starts_at": cycle.starts_at.isoformat() if cycle and cycle.starts_at else None,
            "cycle_ends_at": cycle.ends_at.isoformat() if cycle and cycle.ends_at else None,
            "next_cycle_label": next_cycle.label if next_cycle else None,
            "next_cycle_starts_at": next_cycle.starts_at.isoformat() if next_cycle and next_cycle.starts_at else None,
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


@router.get("/api/me/attacks")
async def get_my_attacks(account: CurrentAccount, competition_id: str | None = None):
    """Get current player's recent battle history (as attacker or target)."""
    import uuid as _uuid

    async with async_session() as session:
        query = (
            select(Membership)
            .join(Competition, Membership.competition_id == Competition.id)
            .where(
                Membership.account_id == account.id,
                Membership.status == MembershipStatus.ACTIVE,
                Competition.status == "active",
            )
        )
        if competition_id:
            try:
                cid = _uuid.UUID(competition_id)
                query = query.where(Competition.id == cid)
            except ValueError:
                pass
        query = query.limit(1)
        mem_result = await session.execute(query)
        membership = mem_result.scalars().first()
        if not membership:
            return {"success": True, "data": []}

        attacks_result = await session.execute(
            select(AttackAttempt).where(
                (AttackAttempt.attacker_id == membership.id) | (AttackAttempt.target_id == membership.id)
            ).order_by(AttackAttempt.created_at.desc()).limit(20)
        )
        attacks = attacks_result.scalars().all()

        data = []
        for a in attacks:
            is_attacker = str(a.attacker_id) == str(membership.id)
            opponent_id = a.target_id if is_attacker else a.attacker_id
            opponent_mem = await session.get(Membership, opponent_id)

            data.append({
                "id": str(a.id),
                "role": "attacker" if is_attacker else "target",
                "opponent_alias": opponent_mem.current_alias if opponent_mem else "?",
                "opponent_membership_id": str(opponent_id),
                "outcome": a.outcome,
                "reward_amount": a.reward_amount,
                "penalty_amount": a.penalty_amount,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            })

    return {"success": True, "data": data}


@router.get("/api/me/inventory-details")
async def get_my_inventory_details(account: CurrentAccount, competition_id: str | None = None):
    """Get player's inventory with item details (name, rarity, description)."""
    import uuid as _uuid

    async with async_session() as session:
        query = (
            select(Membership)
            .join(Competition, Membership.competition_id == Competition.id)
            .where(
                Membership.account_id == account.id,
                Membership.status == MembershipStatus.ACTIVE,
                Competition.status == "active",
            )
        )
        if competition_id:
            try:
                cid = _uuid.UUID(competition_id)
                query = query.where(Competition.id == cid)
            except ValueError:
                pass
        query = query.limit(1)
        mem_result = await session.execute(query)
        membership = mem_result.scalars().first()
        if not membership:
            return {"success": True, "data": []}

        result = await session.execute(
            select(OwnedItem, ItemDefinition)
            .join(ItemDefinition, OwnedItem.item_definition_id == ItemDefinition.id)
            .where(
                OwnedItem.membership_id == membership.id,
                OwnedItem.status.in_([OwnedItemStatus.AVAILABLE, OwnedItemStatus.ACTIVATED, OwnedItemStatus.PENDING]),
            )
            .order_by(OwnedItem.acquired_at.desc())
        )
        rows = result.all()

        data = [{
            "id": str(oi.id),
            "owned_item_id": str(oi.id),
            "item_definition_id": str(item.id),
            "name": item.name,
            "description": item.description,
            "rarity": item.rarity,
            "category": item.category,
            "usage_type": item.usage_type,
            "status": oi.status,
            "can_use": oi.status == OwnedItemStatus.AVAILABLE,
            "uses_remaining": oi.uses_remaining,
            "acquired_at": oi.acquired_at.isoformat() if oi.acquired_at else None,
            "expires_at": oi.expires_at.isoformat() if oi.expires_at else None,
        } for oi, item in rows]

    return {"success": True, "data": data}
