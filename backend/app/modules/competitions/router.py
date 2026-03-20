"""Competition join + context endpoints."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select

from app.core.auth import get_current_account
from app.core.database import async_session
from app.core.enums import (
    CompetitionStatus,
    InviteStatus,
    LedgerDirection,
    LedgerEntryType,
    MembershipStatus,
    SeasonStatus,
    CycleStatus,
)
from app.modules.auth.models import Account
from app.modules.competitions.models import (
    AliasRecord,
    Competition,
    CompetitionInvite,
    Cycle,
    Membership,
    Season,
)
from app.modules.competitions.schemas import JoinRequest
from app.modules.scoring.models import LedgerEntry
from app.modules.settings.service import get_setting

router = APIRouter(tags=["competitions"])
CurrentAccount = Annotated[Account, Depends(get_current_account)]

_FALLBACK_INITIAL_BALANCE = 1000


@router.get("/api/competitions/active")
async def get_active_competition():
    """Public endpoint — returns the first active competition (for the join page)."""
    async with async_session() as session:
        result = await session.execute(
            select(Competition).where(
                Competition.status == "active",
                Competition.registration_open == True,
            ).limit(1)
        )
        comp = result.scalars().first()

    if not comp:
        return {"success": True, "data": None}

    return {
        "success": True,
        "data": {
            "competition_id": str(comp.id),
            "name": comp.name,
            "description": comp.description,
        },
    }


@router.post("/api/competitions/{competition_id}/join")
async def join_competition(
    competition_id: uuid.UUID,
    body: JoinRequest,
    account: CurrentAccount,
):
    async with async_session() as session:
        # Validate competition is active and accepting registrations
        comp = await session.get(Competition, competition_id)
        if not comp:
            raise HTTPException(status_code=404, detail="المنافسة غير موجودة")
        if comp.status != CompetitionStatus.ACTIVE and comp.status != CompetitionStatus.REGISTRATION_OPEN:
            raise HTTPException(status_code=400, detail="المنافسة غير مفتوحة للتسجيل حالياً")
        if not comp.registration_open:
            raise HTTPException(status_code=400, detail="التسجيل مغلق في هذه المنافسة")

        # Validate invite code
        invite_result = await session.execute(
            select(CompetitionInvite).where(
                CompetitionInvite.competition_id == competition_id,
                CompetitionInvite.code == body.invite_code,
                CompetitionInvite.status == InviteStatus.ACTIVE,
            )
        )
        invite = invite_result.scalars().first()
        if not invite:
            raise HTTPException(status_code=400, detail="رمز الدعوة غير صالح أو منتهي الصلاحية")

        if invite.max_uses and invite.use_count >= invite.max_uses:
            raise HTTPException(status_code=400, detail="رمز الدعوة وصل للحد الأقصى من الاستخدامات")

        # Check not already a member
        existing = await session.execute(
            select(Membership).where(
                Membership.account_id == account.id,
                Membership.competition_id == competition_id,
            )
        )
        if existing.scalars().first():
            raise HTTPException(status_code=400, detail="أنت مسجل بالفعل في هذه المنافسة")

        # Check alias uniqueness
        alias_conflict = await session.execute(
            select(Membership).where(
                Membership.competition_id == competition_id,
                Membership.current_alias == body.alias,
            )
        )
        if alias_conflict.scalars().first():
            raise HTTPException(status_code=400, detail="هذا اللقب مستخدم بالفعل في المنافسة")

        # Read initial balance from settings
        initial_balance = await get_setting(
            session, "score_initial_balance", competition_id=competition_id
        )
        if initial_balance is None:
            initial_balance = _FALLBACK_INITIAL_BALANCE
        initial_balance = int(initial_balance)

        # Create membership
        membership = Membership(
            account_id=account.id,
            competition_id=competition_id,
            status=MembershipStatus.ACTIVE,
            current_alias=body.alias,
            current_balance=initial_balance,
        )
        session.add(membership)
        await session.flush()

        # Get active season/cycle
        season = (await session.execute(
            select(Season).where(
                Season.competition_id == competition_id,
                Season.status == SeasonStatus.ACTIVE,
            ).limit(1)
        )).scalars().first()

        cycle = None
        if season:
            cycle = (await session.execute(
                select(Cycle).where(
                    Cycle.season_id == season.id,
                    Cycle.status == CycleStatus.ACTIVE,
                ).limit(1)
            )).scalars().first()

        # Grant initial balance via ledger
        ledger_entry = LedgerEntry(
            membership_id=membership.id,
            competition_id=competition_id,
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
            alias_value=body.alias,
            is_active=True,
            season_id=season.id if season else None,
            cycle_id=cycle.id if cycle else None,
        )
        session.add(alias_record)

        # Increment invite use count
        invite.use_count += 1

        await session.commit()

    return {
        "success": True,
        "data": {
            "membership_id": str(membership.id),
            "alias": membership.current_alias,
            "balance": membership.current_balance,
        },
        "message": f"أهلاً بك في المنافسة يا {body.alias}! رصيدك الابتدائي: {initial_balance} نقطة",
    }


@router.get("/api/me/memberships")
async def list_my_memberships(account: CurrentAccount):
    """Returns all memberships for the current user with competition info."""
    async with async_session() as session:
        result = await session.execute(
            select(Membership, Competition)
            .join(Competition, Membership.competition_id == Competition.id)
            .where(Membership.account_id == account.id)
            .order_by(Membership.joined_at.desc())
        )
        rows = result.all()

    return {
        "success": True,
        "data": [
            {
                "membership_id": str(mem.id),
                "competition_id": str(comp.id),
                "competition_name": comp.name,
                "competition_status": comp.status.value if hasattr(comp.status, 'value') else str(comp.status),
                "alias": mem.current_alias,
                "balance": mem.current_balance,
                "status": mem.status.value if hasattr(mem.status, 'value') else str(mem.status),
                "is_bankrupt": mem.is_bankrupt,
                "joined_at": mem.joined_at.isoformat() if mem.joined_at else None,
            }
            for mem, comp in rows
        ],
    }


@router.get("/api/me/competition-context")
async def get_competition_context(account: CurrentAccount):
    """Returns the active competition context for the current user."""
    async with async_session() as session:
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

        # Active season + cycle
        season = (await session.execute(
            select(Season).where(
                Season.competition_id == competition.id,
                Season.status == SeasonStatus.ACTIVE,
            ).limit(1)
        )).scalars().first()

        cycle = None
        if season:
            cycle = (await session.execute(
                select(Cycle).where(
                    Cycle.season_id == season.id,
                    Cycle.status == CycleStatus.ACTIVE,
                ).limit(1)
            )).scalars().first()

        # Next cycle (upcoming after the current one)
        next_cycle = None
        if season and cycle:
            next_cycle_result = await session.execute(
                select(Cycle).where(
                    Cycle.season_id == season.id,
                    Cycle.status.in_([CycleStatus.DRAFT, CycleStatus.PAUSED]),
                    Cycle.order_index > cycle.order_index,
                ).order_by(Cycle.order_index).limit(1)
            )
            next_cycle = next_cycle_result.scalars().first()

        # Compute rank
        rank_result = await session.execute(
            select(func.count()).where(
                Membership.competition_id == competition.id,
                Membership.status == MembershipStatus.ACTIVE,
                Membership.current_balance > membership.current_balance,
            )
        )
        rank = (rank_result.scalar() or 0) + 1

    return {
        "success": True,
        "data": {
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
            "membership_id": str(membership.id),
            "alias": membership.current_alias or account.username,
            "balance": membership.current_balance,
            "protection": membership.protection,
            "is_bankrupt": membership.is_bankrupt,
            "rank": rank,
        },
    }
