"""Admin panel endpoints — dashboard, competitions, players, attacks, quiz, store, ledger, settings."""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select, update, case, literal
from sqlalchemy.orm import selectinload

from app.core.auth import get_admin_account
from app.core.database import async_session
from app.core.enums import (
    AccountStatus,
    AnswerEvalStatus,
    AttackOutcome,
    CompetitionStatus,
    CycleStatus,
    InviteStatus,
    InviteType,
    ItemRarity,
    ItemStatus,
    LedgerDirection,
    LedgerEntryType,
    ListingStatus,
    MembershipStatus,
    NotificationPriority,
    NotificationType,
    OwnedItemStatus,
    QuestionStatus,
    SeasonStatus,
    SessionStatus,
    SessionType,
    SettingScope,
)
from app.modules.attacks.models import AttackAttempt
from app.modules.auth.models import Account
from app.modules.competitions.models import Competition, CompetitionInvite, Cycle, Membership, Season
from app.modules.notifications.models import Notification
from app.modules.quiz.models import AnswerSubmission, Question, QuestionGroup, QuizSession, SessionQuestion
from app.modules.scoring.models import LedgerEntry
from app.modules.settings.models import SettingDefinition, SettingValue
from app.modules.store.models import ItemDefinition, ItemEffect, OwnedItem, StoreListing

router = APIRouter(prefix="/api/admin", tags=["admin"])
AdminAccount = Annotated[Account, Depends(get_admin_account)]


# ═══════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/dashboard")
async def admin_dashboard(admin: AdminAccount):
    """Admin dashboard summary — key counts, active state, recent activity."""
    async with async_session() as session:
        # Total accounts (exclude system)
        total_accounts = (await session.execute(
            select(func.count()).where(Account.username != "_system", Account.username != "admin")
        )).scalar() or 0

        # Active competition
        comp_result = await session.execute(
            select(Competition).where(Competition.status == CompetitionStatus.ACTIVE).limit(1)
        )
        active_comp = comp_result.scalars().first()

        comp_data = None
        active_season_data = None
        active_cycle_data = None
        total_members = 0
        bankrupt_count = 0

        if active_comp:
            comp_data = {
                "id": str(active_comp.id),
                "name": active_comp.name,
                "status": active_comp.status,
                "registration_open": active_comp.registration_open,
            }

            total_members = (await session.execute(
                select(func.count()).where(
                    Membership.competition_id == active_comp.id,
                    Membership.status == MembershipStatus.ACTIVE,
                )
            )).scalar() or 0

            bankrupt_count = (await session.execute(
                select(func.count()).where(
                    Membership.competition_id == active_comp.id,
                    Membership.is_bankrupt == True,
                )
            )).scalar() or 0

            # Active season
            season_result = await session.execute(
                select(Season).where(
                    Season.competition_id == active_comp.id,
                    Season.status == SeasonStatus.ACTIVE,
                ).limit(1)
            )
            active_season = season_result.scalars().first()
            if active_season:
                active_season_data = {
                    "id": str(active_season.id),
                    "name": active_season.name,
                    "status": active_season.status,
                }

                # Active cycle
                cycle_result = await session.execute(
                    select(Cycle).where(
                        Cycle.season_id == active_season.id,
                        Cycle.status == CycleStatus.ACTIVE,
                    ).limit(1)
                )
                active_cycle = cycle_result.scalars().first()
                if active_cycle:
                    active_cycle_data = {
                        "id": str(active_cycle.id),
                        "label": active_cycle.label,
                        "status": active_cycle.status,
                    }

        # Total attacks
        total_attacks = (await session.execute(select(func.count()).select_from(AttackAttempt))).scalar() or 0
        successful_attacks = (await session.execute(
            select(func.count()).where(AttackAttempt.outcome == AttackOutcome.SUCCEEDED)
        )).scalar() or 0

        # Total quiz answers
        total_answers = (await session.execute(select(func.count()).select_from(AnswerSubmission))).scalar() or 0
        correct_answers = (await session.execute(
            select(func.count()).where(AnswerSubmission.is_correct == True)
        )).scalar() or 0

        # Total purchases (owned items from purchase source)
        total_purchases = (await session.execute(
            select(func.count()).where(OwnedItem.source_type == "purchase")
        )).scalar() or 0

        # Total ledger movements
        total_credits = (await session.execute(
            select(func.coalesce(func.sum(LedgerEntry.amount), 0)).where(
                LedgerEntry.direction == LedgerDirection.CREDIT
            )
        )).scalar() or 0
        total_debits = (await session.execute(
            select(func.coalesce(func.sum(LedgerEntry.amount), 0)).where(
                LedgerEntry.direction == LedgerDirection.DEBIT
            )
        )).scalar() or 0

        # Unread notifications count
        unread_notifications = (await session.execute(
            select(func.count()).where(Notification.is_read == False)
        )).scalar() or 0

        # Recent attacks (last 5)
        recent_attacks_result = await session.execute(
            select(AttackAttempt).order_by(AttackAttempt.created_at.desc()).limit(5)
        )
        recent_attacks_rows = recent_attacks_result.scalars().all()

        recent_attacks = []
        for a in recent_attacks_rows:
            # Resolve aliases
            attacker_mem = await session.get(Membership, a.attacker_id)
            target_mem = await session.get(Membership, a.target_id)
            recent_attacks.append({
                "id": str(a.id),
                "attacker_alias": attacker_mem.current_alias if attacker_mem else "?",
                "target_alias": target_mem.current_alias if target_mem else "?",
                "outcome": a.outcome,
                "reward_amount": a.reward_amount,
                "penalty_amount": a.penalty_amount,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            })

    return {
        "success": True,
        "data": {
            "total_accounts": total_accounts,
            "total_members": total_members,
            "bankrupt_count": bankrupt_count,
            "active_competition": comp_data,
            "active_season": active_season_data,
            "active_cycle": active_cycle_data,
            "total_attacks": total_attacks,
            "successful_attacks": successful_attacks,
            "total_answers": total_answers,
            "correct_answers": correct_answers,
            "total_purchases": total_purchases,
            "total_credits": total_credits,
            "total_debits": total_debits,
            "unread_notifications": unread_notifications,
            "recent_attacks": recent_attacks,
        },
    }


# ═══════════════════════════════════════════════════════════════════════════
# COMPETITIONS
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/competitions")
async def list_competitions(admin: AdminAccount):
    """List all competitions with key stats."""
    async with async_session() as session:
        result = await session.execute(
            select(Competition).order_by(Competition.created_at.desc())
        )
        comps = result.scalars().all()

        data = []
        for c in comps:
            member_count = (await session.execute(
                select(func.count()).where(
                    Membership.competition_id == c.id,
                    Membership.status == MembershipStatus.ACTIVE,
                )
            )).scalar() or 0

            season_count = (await session.execute(
                select(func.count()).where(Season.competition_id == c.id)
            )).scalar() or 0

            data.append({
                "id": str(c.id),
                "name": c.name,
                "description": c.description,
                "status": c.status,
                "registration_open": c.registration_open,
                "visibility": c.visibility,
                "member_count": member_count,
                "season_count": season_count,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            })

    return {"success": True, "data": data}


@router.get("/competitions/{competition_id}")
async def get_competition_detail(competition_id: uuid.UUID, admin: AdminAccount):
    """Get competition detail with seasons, cycles, and invites."""
    async with async_session() as session:
        comp = await session.get(Competition, competition_id)
        if not comp:
            raise HTTPException(status_code=404, detail="المنافسة غير موجودة")

        # Seasons
        seasons_result = await session.execute(
            select(Season).where(Season.competition_id == competition_id)
            .order_by(Season.order_index)
        )
        seasons = seasons_result.scalars().all()

        seasons_data = []
        for s in seasons:
            # Cycles for this season
            cycles_result = await session.execute(
                select(Cycle).where(Cycle.season_id == s.id).order_by(Cycle.order_index)
            )
            cycles = cycles_result.scalars().all()

            seasons_data.append({
                "id": str(s.id),
                "name": s.name,
                "order_index": s.order_index,
                "status": s.status,
                "starts_at": s.starts_at.isoformat() if s.starts_at else None,
                "ends_at": s.ends_at.isoformat() if s.ends_at else None,
                "cycles": [{
                    "id": str(c.id),
                    "label": c.label,
                    "order_index": c.order_index,
                    "status": c.status,
                    "starts_at": c.starts_at.isoformat() if c.starts_at else None,
                    "ends_at": c.ends_at.isoformat() if c.ends_at else None,
                } for c in cycles],
            })

        # Invites
        invites_result = await session.execute(
            select(CompetitionInvite).where(CompetitionInvite.competition_id == competition_id)
        )
        invites = invites_result.scalars().all()

        invites_data = [{
            "id": str(inv.id),
            "code": inv.code,
            "invite_type": inv.invite_type,
            "status": inv.status,
            "max_uses": inv.max_uses,
            "use_count": inv.use_count,
            "expires_at": inv.expires_at.isoformat() if inv.expires_at else None,
        } for inv in invites]

        # Member count
        member_count = (await session.execute(
            select(func.count()).where(
                Membership.competition_id == competition_id,
                Membership.status == MembershipStatus.ACTIVE,
            )
        )).scalar() or 0

    return {
        "success": True,
        "data": {
            "id": str(comp.id),
            "name": comp.name,
            "description": comp.description,
            "status": comp.status,
            "registration_open": comp.registration_open,
            "visibility": comp.visibility,
            "member_count": member_count,
            "seasons": seasons_data,
            "invites": invites_data,
            "created_at": comp.created_at.isoformat() if comp.created_at else None,
        },
    }


class CompetitionUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    registration_open: bool | None = None
    visibility: str | None = None


class CreateCompetitionRequest(BaseModel):
    name: str
    description: str | None = None
    visibility: str = "private"


@router.post("/competitions", status_code=201)
async def create_competition(body: CreateCompetitionRequest, admin: AdminAccount):
    """Create a new competition."""
    async with async_session() as session:
        comp = Competition(
            name=body.name,
            description=body.description,
            visibility=body.visibility,
            status=CompetitionStatus.DRAFT,
            created_by=admin.id,
        )
        session.add(comp)
        await session.commit()
        await session.refresh(comp)
    return {"success": True, "data": {"id": str(comp.id)}, "message": "تم إنشاء المنافسة بنجاح"}


@router.patch("/competitions/{competition_id}")
async def update_competition(competition_id: uuid.UUID, body: CompetitionUpdateRequest, admin: AdminAccount):
    """Update competition status or registration."""
    async with async_session() as session:
        comp = await session.get(Competition, competition_id)
        if not comp:
            raise HTTPException(status_code=404, detail="المنافسة غير موجودة")

        if body.name is not None:
            comp.name = body.name
        if body.description is not None:
            comp.description = body.description
        if body.status is not None:
            comp.status = body.status
        if body.registration_open is not None:
            comp.registration_open = body.registration_open
        if body.visibility is not None:
            comp.visibility = body.visibility

        await session.commit()

    return {"success": True, "message": "تم تحديث المنافسة بنجاح"}


class CreateSeasonRequest(BaseModel):
    competition_id: uuid.UUID
    name: str


@router.post("/seasons", status_code=201)
async def create_season(body: CreateSeasonRequest, admin: AdminAccount):
    """Create a new season for a competition."""
    async with async_session() as session:
        comp = await session.get(Competition, body.competition_id)
        if not comp:
            raise HTTPException(status_code=404, detail="المنافسة غير موجودة")

        max_order = (await session.execute(
            select(func.coalesce(func.max(Season.order_index), 0))
            .where(Season.competition_id == body.competition_id)
        )).scalar()

        season = Season(
            competition_id=body.competition_id,
            name=body.name,
            order_index=max_order + 1,
            status=SeasonStatus.DRAFT,
        )
        session.add(season)
        await session.commit()
        await session.refresh(season)
    return {"success": True, "data": {"id": str(season.id)}, "message": "تم إنشاء الموسم بنجاح"}


class CreateCycleRequest(BaseModel):
    season_id: uuid.UUID
    label: str


@router.post("/cycles", status_code=201)
async def create_cycle(body: CreateCycleRequest, admin: AdminAccount):
    """Create a new cycle for a season."""
    async with async_session() as session:
        season = await session.get(Season, body.season_id)
        if not season:
            raise HTTPException(status_code=404, detail="الموسم غير موجود")

        max_order = (await session.execute(
            select(func.coalesce(func.max(Cycle.order_index), 0))
            .where(Cycle.season_id == body.season_id)
        )).scalar()

        cycle = Cycle(
            season_id=body.season_id,
            label=body.label,
            order_index=max_order + 1,
            status=CycleStatus.DRAFT,
        )
        session.add(cycle)
        await session.commit()
        await session.refresh(cycle)
    return {"success": True, "data": {"id": str(cycle.id)}, "message": "تم إنشاء الدورة بنجاح"}


class CreateInviteRequest(BaseModel):
    competition_id: uuid.UUID
    code: str
    max_uses: int | None = None


@router.post("/invites", status_code=201)
async def create_invite(body: CreateInviteRequest, admin: AdminAccount):
    """Create a new invite code for a competition."""
    async with async_session() as session:
        comp = await session.get(Competition, body.competition_id)
        if not comp:
            raise HTTPException(status_code=404, detail="المنافسة غير موجودة")

        existing = (await session.execute(
            select(CompetitionInvite).where(CompetitionInvite.code == body.code)
        )).scalars().first()
        if existing:
            raise HTTPException(status_code=400, detail="رمز الدعوة مستخدم بالفعل")

        invite = CompetitionInvite(
            competition_id=body.competition_id,
            invite_type=InviteType.CODE,
            code=body.code,
            status=InviteStatus.ACTIVE,
            max_uses=body.max_uses,
            created_by=admin.id,
        )
        session.add(invite)
        await session.commit()
        await session.refresh(invite)
    return {"success": True, "data": {"id": str(invite.id)}, "message": "تم إنشاء رمز الدعوة بنجاح"}


class UpdateSeasonRequest(BaseModel):
    name: str | None = None
    status: str | None = None
    starts_at: str | None = None
    ends_at: str | None = None


class UpdateCycleRequest(BaseModel):
    label: str | None = None
    status: str | None = None
    starts_at: str | None = None
    ends_at: str | None = None


class UpdateInviteRequest(BaseModel):
    status: str | None = None
    max_uses: int | None = None


@router.patch("/seasons/{season_id}")
async def update_season(season_id: uuid.UUID, body: UpdateSeasonRequest, admin: AdminAccount):
    """Update season name, status, or dates."""
    async with async_session() as session:
        season = await session.get(Season, season_id)
        if not season:
            raise HTTPException(status_code=404, detail="الموسم غير موجود")
        if body.name is not None:
            season.name = body.name
        if body.status is not None:
            season.status = body.status
        if body.starts_at is not None:
            season.starts_at = datetime.fromisoformat(body.starts_at) if body.starts_at else None
        if body.ends_at is not None:
            season.ends_at = datetime.fromisoformat(body.ends_at) if body.ends_at else None
        await session.commit()
    return {"success": True, "message": "تم تحديث الموسم بنجاح"}


@router.patch("/cycles/{cycle_id}")
async def update_cycle(cycle_id: uuid.UUID, body: UpdateCycleRequest, admin: AdminAccount):
    """Update cycle label, status, or dates."""
    async with async_session() as session:
        cycle = await session.get(Cycle, cycle_id)
        if not cycle:
            raise HTTPException(status_code=404, detail="الدورة غير موجودة")
        if body.label is not None:
            cycle.label = body.label
        if body.status is not None:
            cycle.status = body.status
        if body.starts_at is not None:
            cycle.starts_at = datetime.fromisoformat(body.starts_at) if body.starts_at else None
        if body.ends_at is not None:
            cycle.ends_at = datetime.fromisoformat(body.ends_at) if body.ends_at else None
        await session.commit()
    return {"success": True, "message": "تم تحديث الدورة بنجاح"}


@router.patch("/invites/{invite_id}")
async def update_invite(invite_id: uuid.UUID, body: UpdateInviteRequest, admin: AdminAccount):
    """Update invite status or max uses."""
    async with async_session() as session:
        invite = await session.get(CompetitionInvite, invite_id)
        if not invite:
            raise HTTPException(status_code=404, detail="رمز الدعوة غير موجود")
        if body.status is not None:
            invite.status = body.status
        if body.max_uses is not None:
            invite.max_uses = body.max_uses
        await session.commit()
    return {"success": True, "message": "تم تحديث رمز الدعوة بنجاح"}


# ═══════════════════════════════════════════════════════════════════════════
# PLAYERS / MEMBERSHIPS
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/players")
async def list_players(admin: AdminAccount, competition_id: uuid.UUID | None = None):
    """List all players with their membership data."""
    async with async_session() as session:
        query = (
            select(Membership, Account)
            .join(Account, Membership.account_id == Account.id)
            .order_by(Membership.current_balance.desc())
        )
        if competition_id:
            query = query.where(Membership.competition_id == competition_id)

        result = await session.execute(query)
        rows = result.all()

        # Get ranks (by competition)
        data = []
        for membership, account in rows:
            # Count attacks sent
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

            attacks_received = (await session.execute(
                select(func.count()).where(
                    AttackAttempt.target_id == membership.id,
                    AttackAttempt.outcome == AttackOutcome.SUCCEEDED,
                )
            )).scalar() or 0

            data.append({
                "membership_id": str(membership.id),
                "account_id": str(account.id),
                "username": account.username,
                "real_name": account.real_name,
                "alias": membership.current_alias,
                "balance": membership.current_balance,
                "status": membership.status,
                "protection": membership.protection,
                "is_bankrupt": membership.is_bankrupt,
                "competition_id": str(membership.competition_id),
                "attacks_sent": attacks_sent,
                "attacks_won": attacks_won,
                "attacks_received": attacks_received,
                "joined_at": membership.updated_at.isoformat() if membership.updated_at else None,
            })

    return {"success": True, "data": data}


@router.get("/players/{membership_id}")
async def get_player_detail(membership_id: uuid.UUID, admin: AdminAccount):
    """Get detailed player info with ledger and attack history."""
    async with async_session() as session:
        membership = await session.get(Membership, membership_id)
        if not membership:
            raise HTTPException(status_code=404, detail="اللاعب غير موجود")

        account = await session.get(Account, membership.account_id)

        # Recent ledger entries
        ledger_result = await session.execute(
            select(LedgerEntry)
            .where(LedgerEntry.membership_id == membership_id)
            .order_by(LedgerEntry.created_at.desc())
            .limit(20)
        )
        ledger_rows = ledger_result.scalars().all()
        ledger_data = [{
            "id": str(le.id),
            "entry_type": le.entry_type,
            "amount": le.amount,
            "direction": le.direction,
            "balance_before": le.balance_before,
            "balance_after": le.balance_after,
            "source_type": le.source_type,
            "reason": le.reason,
            "created_at": le.created_at.isoformat() if le.created_at else None,
        } for le in ledger_rows]

        # Recent attacks (as attacker or target)
        attacks_result = await session.execute(
            select(AttackAttempt).where(
                (AttackAttempt.attacker_id == membership_id) | (AttackAttempt.target_id == membership_id)
            ).order_by(AttackAttempt.created_at.desc()).limit(10)
        )
        attacks_rows = attacks_result.scalars().all()

        attacks_data = []
        for a in attacks_rows:
            attacker_mem = await session.get(Membership, a.attacker_id)
            target_mem = await session.get(Membership, a.target_id)
            attacks_data.append({
                "id": str(a.id),
                "role": "attacker" if str(a.attacker_id) == str(membership_id) else "target",
                "attacker_alias": attacker_mem.current_alias if attacker_mem else "?",
                "target_alias": target_mem.current_alias if target_mem else "?",
                "outcome": a.outcome,
                "reward_amount": a.reward_amount,
                "penalty_amount": a.penalty_amount,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            })

        # Inventory
        inv_result = await session.execute(
            select(OwnedItem, ItemDefinition)
            .join(ItemDefinition, OwnedItem.item_definition_id == ItemDefinition.id)
            .where(OwnedItem.membership_id == membership_id)
            .order_by(OwnedItem.acquired_at.desc())
        )
        inv_rows = inv_result.all()
        inventory_data = [{
            "id": str(oi.id),
            "name": item.name,
            "rarity": item.rarity,
            "status": oi.status,
            "acquired_at": oi.acquired_at.isoformat() if oi.acquired_at else None,
        } for oi, item in inv_rows]

    return {
        "success": True,
        "data": {
            "membership_id": str(membership.id),
            "account_id": str(account.id) if account else None,
            "username": account.username if account else "?",
            "real_name": account.real_name if account else "?",
            "alias": membership.current_alias,
            "balance": membership.current_balance,
            "status": membership.status,
            "protection": membership.protection,
            "is_bankrupt": membership.is_bankrupt,
            "competition_id": str(membership.competition_id),
            "joined_at": membership.updated_at.isoformat() if membership.updated_at else None,
            "ledger": ledger_data,
            "attacks": attacks_data,
            "inventory": inventory_data,
        },
    }


class AdminAdjustBalanceRequest(BaseModel):
    amount: int
    reason: str


@router.post("/players/{membership_id}/adjust-balance")
async def adjust_balance(membership_id: uuid.UUID, body: AdminAdjustBalanceRequest, admin: AdminAccount):
    """Admin balance adjustment — positive = credit, negative = debit."""
    async with async_session() as session:
        membership = await session.get(Membership, membership_id)
        if not membership:
            raise HTTPException(status_code=404, detail="اللاعب غير موجود")

        direction = LedgerDirection.CREDIT if body.amount > 0 else LedgerDirection.DEBIT
        abs_amount = abs(body.amount)
        balance_before = membership.current_balance
        balance_after = balance_before + body.amount

        ledger = LedgerEntry(
            membership_id=membership.id,
            competition_id=membership.competition_id,
            entry_type=LedgerEntryType.ADMIN_ADJUSTMENT,
            amount=abs_amount,
            direction=direction,
            balance_before=balance_before,
            balance_after=balance_after,
            source_type="admin_adjustment",
            reason=body.reason,
            actor_id=admin.id,
        )
        session.add(ledger)
        membership.current_balance = balance_after
        await session.commit()

    return {
        "success": True,
        "data": {"balance_after": balance_after},
        "message": f"تم تعديل الرصيد: {balance_before} → {balance_after}",
    }


class AdminPlayerStatusRequest(BaseModel):
    status: str


@router.patch("/players/{membership_id}/status")
async def update_player_status(membership_id: uuid.UUID, body: AdminPlayerStatusRequest, admin: AdminAccount):
    """Update player membership status (suspend, remove, etc.)."""
    async with async_session() as session:
        membership = await session.get(Membership, membership_id)
        if not membership:
            raise HTTPException(status_code=404, detail="اللاعب غير موجود")

        membership.status = body.status
        await session.commit()

    return {"success": True, "message": f"تم تحديث حالة اللاعب إلى {body.status}"}


# ═══════════════════════════════════════════════════════════════════════════
# ATTACKS
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/attacks")
async def list_attacks(admin: AdminAccount, competition_id: uuid.UUID | None = None, limit: int = 50):
    """List all attacks with resolved aliases."""
    async with async_session() as session:
        query = select(AttackAttempt).order_by(AttackAttempt.created_at.desc()).limit(limit)
        if competition_id:
            query = query.where(AttackAttempt.competition_id == competition_id)

        result = await session.execute(query)
        attacks = result.scalars().all()

        data = []
        for a in attacks:
            attacker_mem = await session.get(Membership, a.attacker_id)
            target_mem = await session.get(Membership, a.target_id)

            # Resolve real names
            attacker_account = await session.get(Account, attacker_mem.account_id) if attacker_mem else None
            target_account = await session.get(Account, target_mem.account_id) if target_mem else None

            data.append({
                "id": str(a.id),
                "attacker_alias": attacker_mem.current_alias if attacker_mem else "?",
                "attacker_real_name": attacker_account.real_name if attacker_account else "?",
                "target_alias": target_mem.current_alias if target_mem else "?",
                "target_real_name": target_account.real_name if target_account else "?",
                "outcome": a.outcome,
                "reward_amount": a.reward_amount,
                "penalty_amount": a.penalty_amount,
                "attacker_membership_id": str(a.attacker_id),
                "target_membership_id": str(a.target_id),
                "created_at": a.created_at.isoformat() if a.created_at else None,
            })

    return {"success": True, "data": data}


# ═══════════════════════════════════════════════════════════════════════════
# QUIZ / QUESTIONS
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/questions/groups")
async def list_question_groups(admin: AdminAccount):
    """List all question groups with question counts."""
    async with async_session() as session:
        result = await session.execute(
            select(QuestionGroup).order_by(QuestionGroup.created_at.desc())
        )
        groups = result.scalars().all()

        data = []
        for g in groups:
            q_count = (await session.execute(
                select(func.count()).where(Question.group_id == g.id)
            )).scalar() or 0

            data.append({
                "id": str(g.id),
                "title": g.title,
                "description": g.description,
                "status": g.status,
                "question_count": q_count,
                "competition_id": str(g.competition_id) if g.competition_id else None,
                "created_at": g.created_at.isoformat() if g.created_at else None,
            })

    return {"success": True, "data": data}


@router.get("/questions")
async def list_questions(admin: AdminAccount, group_id: uuid.UUID | None = None):
    """List questions, optionally filtered by group."""
    async with async_session() as session:
        query = select(Question).order_by(Question.created_at.desc())
        if group_id:
            query = query.where(Question.group_id == group_id)

        result = await session.execute(query)
        questions = result.scalars().all()

        data = [{
            "id": str(q.id),
            "group_id": str(q.group_id) if q.group_id else None,
            "question_type": q.question_type,
            "prompt": q.prompt,
            "options": q.options,
            "correct_answer": q.correct_answer,
            "score_value": q.score_value,
            "difficulty": q.difficulty,
            "category": q.category,
            "status": q.status,
            "created_at": q.created_at.isoformat() if q.created_at else None,
        } for q in questions]

    return {"success": True, "data": data}


class CreateQuestionRequest(BaseModel):
    group_id: uuid.UUID
    prompt: str
    question_type: str = "multiple_choice"
    options: dict
    correct_answer: dict
    score_value: int = 100
    difficulty: str = "medium"
    category: str | None = None


@router.post("/questions")
async def create_question(body: CreateQuestionRequest, admin: AdminAccount):
    """Create a new question in a group. Supports multiple_choice and true_false types."""
    async with async_session() as session:
        group = await session.get(QuestionGroup, body.group_id)
        if not group:
            raise HTTPException(status_code=404, detail="مجموعة الأسئلة غير موجودة")

        q = Question(
            group_id=body.group_id,
            question_type=body.question_type,
            prompt=body.prompt,
            options=body.options,
            correct_answer=body.correct_answer,
            score_value=body.score_value,
            difficulty=body.difficulty,
            category=body.category,
            status=QuestionStatus.ACTIVE,
        )
        session.add(q)
        await session.commit()
        await session.refresh(q)

    return {
        "success": True,
        "data": {"id": str(q.id)},
        "message": "تم إنشاء السؤال بنجاح",
    }


@router.get("/quiz-sessions")
async def list_quiz_sessions(admin: AdminAccount):
    """List all quiz sessions with participation stats."""
    async with async_session() as session:
        result = await session.execute(
            select(QuizSession).order_by(QuizSession.created_at.desc())
        )
        sessions = result.scalars().all()

        data = []
        for qs in sessions:
            q_count = (await session.execute(
                select(func.count()).where(SessionQuestion.session_id == qs.id)
            )).scalar() or 0

            # Unique participants who answered
            participant_count = (await session.execute(
                select(func.count(func.distinct(AnswerSubmission.membership_id)))
                .where(AnswerSubmission.session_id == qs.id)
            )).scalar() or 0

            total_submissions = (await session.execute(
                select(func.count()).where(AnswerSubmission.session_id == qs.id)
            )).scalar() or 0

            correct_submissions = (await session.execute(
                select(func.count()).where(
                    AnswerSubmission.session_id == qs.id,
                    AnswerSubmission.is_correct == True,
                )
            )).scalar() or 0

            data.append({
                "id": str(qs.id),
                "title": qs.title,
                "status": qs.status,
                "session_type": qs.session_type,
                "question_count": q_count,
                "participant_count": participant_count,
                "total_submissions": total_submissions,
                "correct_submissions": correct_submissions,
                "answer_duration_seconds": qs.answer_duration_seconds,
                "starts_at": qs.starts_at.isoformat() if qs.starts_at else None,
                "ends_at": qs.ends_at.isoformat() if qs.ends_at else None,
                "created_at": qs.created_at.isoformat() if qs.created_at else None,
            })

    return {"success": True, "data": data}


class UpdateQuizSessionRequest(BaseModel):
    status: str | None = None
    title: str | None = None


@router.patch("/quiz-sessions/{session_id}")
async def update_quiz_session(session_id: uuid.UUID, body: UpdateQuizSessionRequest, admin: AdminAccount):
    """Update quiz session status or title."""
    async with async_session() as session:
        qs = await session.get(QuizSession, session_id)
        if not qs:
            raise HTTPException(status_code=404, detail="جلسة الأسئلة غير موجودة")
        if body.status is not None:
            qs.status = body.status
        if body.title is not None:
            qs.title = body.title
        await session.commit()
    return {"success": True, "message": "تم تحديث جلسة الأسئلة"}


class CreateQuestionGroupRequest(BaseModel):
    title: str
    description: str | None = None
    competition_id: uuid.UUID | None = None


@router.post("/questions/groups", status_code=201)
async def create_question_group(body: CreateQuestionGroupRequest, admin: AdminAccount):
    """Create a new question group."""
    async with async_session() as session:
        group = QuestionGroup(
            title=body.title,
            description=body.description,
            competition_id=body.competition_id,
            status=QuestionStatus.ACTIVE,
        )
        session.add(group)
        await session.commit()
        await session.refresh(group)
    return {"success": True, "data": {"id": str(group.id)}, "message": "تم إنشاء مجموعة الأسئلة بنجاح"}


class UpdateQuestionRequest(BaseModel):
    prompt: str | None = None
    options: dict | None = None
    correct_answer: dict | None = None
    score_value: int | None = None
    difficulty: str | None = None
    category: str | None = None
    status: str | None = None


@router.patch("/questions/{question_id}")
async def update_question(question_id: uuid.UUID, body: UpdateQuestionRequest, admin: AdminAccount):
    """Edit an existing question."""
    async with async_session() as session:
        q = await session.get(Question, question_id)
        if not q:
            raise HTTPException(status_code=404, detail="السؤال غير موجود")
        if body.prompt is not None:
            q.prompt = body.prompt
        if body.options is not None:
            q.options = body.options
        if body.correct_answer is not None:
            q.correct_answer = body.correct_answer
        if body.score_value is not None:
            q.score_value = body.score_value
        if body.difficulty is not None:
            q.difficulty = body.difficulty
        if body.category is not None:
            q.category = body.category
        if body.status is not None:
            q.status = body.status
        await session.commit()
    return {"success": True, "message": "تم تحديث السؤال بنجاح"}


@router.delete("/questions/{question_id}")
async def delete_question(question_id: uuid.UUID, admin: AdminAccount):
    """Archive a question (set status to archived)."""
    async with async_session() as session:
        q = await session.get(Question, question_id)
        if not q:
            raise HTTPException(status_code=404, detail="السؤال غير موجود")
        q.status = QuestionStatus.ARCHIVED
        await session.commit()
    return {"success": True, "message": "تم حذف السؤال"}


class CreateQuizSessionRequest(BaseModel):
    competition_id: uuid.UUID
    title: str
    source_group_id: uuid.UUID
    answer_duration_seconds: int = 30
    session_type: str = "timed_window"


@router.post("/quiz-sessions", status_code=201)
async def create_quiz_session(body: CreateQuizSessionRequest, admin: AdminAccount):
    """Create a new quiz session from a question group, auto-populating session questions."""
    async with async_session() as session:
        group = await session.get(QuestionGroup, body.source_group_id)
        if not group:
            raise HTTPException(status_code=404, detail="مجموعة الأسئلة غير موجودة")

        # Get active season/cycle for this competition
        season_result = await session.execute(
            select(Season).where(Season.competition_id == body.competition_id, Season.status == SeasonStatus.ACTIVE).limit(1)
        )
        active_season = season_result.scalars().first()
        active_cycle = None
        if active_season:
            cycle_result = await session.execute(
                select(Cycle).where(Cycle.season_id == active_season.id, Cycle.status == CycleStatus.ACTIVE).limit(1)
            )
            active_cycle = cycle_result.scalars().first()

        qs = QuizSession(
            competition_id=body.competition_id,
            season_id=active_season.id if active_season else None,
            cycle_id=active_cycle.id if active_cycle else None,
            session_type=body.session_type,
            title=body.title,
            status=SessionStatus.DRAFT,
            answer_duration_seconds=body.answer_duration_seconds,
            source_group_id=body.source_group_id,
            created_by=admin.id,
        )
        session.add(qs)
        await session.flush()

        # Auto-populate session questions from the group
        questions_result = await session.execute(
            select(Question).where(
                Question.group_id == body.source_group_id,
                Question.status == QuestionStatus.ACTIVE,
            ).order_by(Question.display_order)
        )
        questions = questions_result.scalars().all()

        for idx, q in enumerate(questions):
            sq = SessionQuestion(
                session_id=qs.id,
                question_id=q.id,
                delivery_order=idx,
                effective_score_value=q.score_value,
                effective_prompt_snapshot=q.prompt,
                effective_options_snapshot=q.options,
            )
            session.add(sq)

        await session.commit()
        await session.refresh(qs)

    return {
        "success": True,
        "data": {"id": str(qs.id), "question_count": len(questions)},
        "message": "تم إنشاء جلسة الأسئلة بنجاح",
    }


@router.delete("/quiz-sessions/{session_id}")
async def delete_quiz_session(session_id: uuid.UUID, admin: AdminAccount):
    """Cancel a quiz session."""
    async with async_session() as session:
        qs = await session.get(QuizSession, session_id)
        if not qs:
            raise HTTPException(status_code=404, detail="جلسة الأسئلة غير موجودة")
        qs.status = SessionStatus.CANCELLED
        await session.commit()
    return {"success": True, "message": "تم إلغاء جلسة الأسئلة"}


# ═══════════════════════════════════════════════════════════════════════════
# STORE / ITEMS
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/store/items")
async def list_item_definitions(admin: AdminAccount):
    """List all item definitions."""
    async with async_session() as session:
        result = await session.execute(
            select(ItemDefinition).order_by(ItemDefinition.created_at.desc())
        )
        items = result.scalars().all()

        data = [{
            "id": str(item.id),
            "name": item.name,
            "description": item.description,
            "rarity": item.rarity,
            "status": item.status,
            "category": item.category,
            "usage_type": item.usage_type,
            "max_uses": item.max_uses,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        } for item in items]

    return {"success": True, "data": data}


@router.get("/store/listings")
async def list_store_listings(admin: AdminAccount, competition_id: uuid.UUID | None = None):
    """List all store listings with item details and sales stats."""
    async with async_session() as session:
        query = (
            select(StoreListing, ItemDefinition)
            .join(ItemDefinition, StoreListing.item_definition_id == ItemDefinition.id)
            .order_by(StoreListing.created_at.desc())
        )
        if competition_id:
            query = query.where(StoreListing.competition_id == competition_id)

        result = await session.execute(query)
        rows = result.all()

        data = []
        for listing, item in rows:
            data.append({
                "listing_id": str(listing.id),
                "item_id": str(item.id),
                "item_name": item.name,
                "item_rarity": item.rarity,
                "status": listing.status,
                "price": listing.price,
                "max_per_participant": listing.max_per_participant,
                "total_stock": listing.total_stock,
                "sold_count": listing.sold_count,
                "competition_id": str(listing.competition_id) if listing.competition_id else None,
                "created_at": listing.created_at.isoformat() if listing.created_at else None,
            })

    return {"success": True, "data": data}


class UpdateListingRequest(BaseModel):
    status: str | None = None
    price: int | None = None
    total_stock: int | None = None


@router.patch("/store/listings/{listing_id}")
async def update_listing(listing_id: uuid.UUID, body: UpdateListingRequest, admin: AdminAccount):
    """Update store listing status, price, or stock."""
    async with async_session() as session:
        listing = await session.get(StoreListing, listing_id)
        if not listing:
            raise HTTPException(status_code=404, detail="العنصر غير موجود في المتجر")
        if body.status is not None:
            listing.status = body.status
        if body.price is not None:
            listing.price = body.price
        if body.total_stock is not None:
            listing.total_stock = body.total_stock
        await session.commit()
    return {"success": True, "message": "تم تحديث العنصر في المتجر"}


class CreateItemDefinitionRequest(BaseModel):
    name: str
    description: str | None = None
    rarity: str = "common"
    category: str | None = None
    usage_type: str = "consumable"
    max_uses: int | None = None


@router.post("/store/items", status_code=201)
async def create_item_definition(body: CreateItemDefinitionRequest, admin: AdminAccount):
    """Create a new item definition."""
    async with async_session() as session:
        item = ItemDefinition(
            name=body.name,
            description=body.description,
            rarity=body.rarity,
            category=body.category,
            usage_type=body.usage_type,
            max_uses=body.max_uses,
            status=ItemStatus.ACTIVE,
        )
        session.add(item)
        await session.commit()
        await session.refresh(item)
    return {"success": True, "data": {"id": str(item.id)}, "message": "تم إنشاء العنصر بنجاح"}


class UpdateItemDefinitionRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    rarity: str | None = None
    category: str | None = None
    usage_type: str | None = None
    max_uses: int | None = None
    status: str | None = None


@router.patch("/store/items/{item_id}")
async def update_item_definition(item_id: uuid.UUID, body: UpdateItemDefinitionRequest, admin: AdminAccount):
    """Edit an item definition."""
    async with async_session() as session:
        item = await session.get(ItemDefinition, item_id)
        if not item:
            raise HTTPException(status_code=404, detail="العنصر غير موجود")
        if body.name is not None:
            item.name = body.name
        if body.description is not None:
            item.description = body.description
        if body.rarity is not None:
            item.rarity = body.rarity
        if body.category is not None:
            item.category = body.category
        if body.usage_type is not None:
            item.usage_type = body.usage_type
        if body.max_uses is not None:
            item.max_uses = body.max_uses
        if body.status is not None:
            item.status = body.status
        await session.commit()
    return {"success": True, "message": "تم تحديث العنصر بنجاح"}


@router.delete("/store/items/{item_id}")
async def delete_item_definition(item_id: uuid.UUID, admin: AdminAccount):
    """Archive an item definition."""
    async with async_session() as session:
        item = await session.get(ItemDefinition, item_id)
        if not item:
            raise HTTPException(status_code=404, detail="العنصر غير موجود")
        item.status = ItemStatus.ARCHIVED
        await session.commit()
    return {"success": True, "message": "تم حذف العنصر"}


class CreateStoreListingRequest(BaseModel):
    item_definition_id: uuid.UUID
    competition_id: uuid.UUID
    price: int
    total_stock: int | None = None
    max_per_participant: int | None = None


@router.post("/store/listings", status_code=201)
async def create_store_listing(body: CreateStoreListingRequest, admin: AdminAccount):
    """Create a new store listing for an item."""
    async with async_session() as session:
        item = await session.get(ItemDefinition, body.item_definition_id)
        if not item:
            raise HTTPException(status_code=404, detail="العنصر غير موجود")
        comp = await session.get(Competition, body.competition_id)
        if not comp:
            raise HTTPException(status_code=404, detail="المنافسة غير موجودة")

        listing = StoreListing(
            item_definition_id=body.item_definition_id,
            competition_id=body.competition_id,
            price=body.price,
            total_stock=body.total_stock,
            max_per_participant=body.max_per_participant,
            status=ListingStatus.ACTIVE,
        )
        session.add(listing)
        await session.commit()
        await session.refresh(listing)
    return {"success": True, "data": {"id": str(listing.id)}, "message": "تم إنشاء العرض في المتجر بنجاح"}


@router.delete("/store/listings/{listing_id}")
async def delete_store_listing(listing_id: uuid.UUID, admin: AdminAccount):
    """Hide a store listing."""
    async with async_session() as session:
        listing = await session.get(StoreListing, listing_id)
        if not listing:
            raise HTTPException(status_code=404, detail="العنصر غير موجود في المتجر")
        listing.status = ListingStatus.HIDDEN
        await session.commit()
    return {"success": True, "message": "تم إخفاء العنصر من المتجر"}


# ═══════════════════════════════════════════════════════════════════════════
# LEDGER
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/ledger")
async def list_ledger(
    admin: AdminAccount,
    membership_id: uuid.UUID | None = None,
    entry_type: str | None = None,
    limit: int = 50,
):
    """Browse ledger entries with optional filters."""
    async with async_session() as session:
        query = select(LedgerEntry).order_by(LedgerEntry.created_at.desc()).limit(limit)

        if membership_id:
            query = query.where(LedgerEntry.membership_id == membership_id)
        if entry_type:
            query = query.where(LedgerEntry.entry_type == entry_type)

        result = await session.execute(query)
        entries = result.scalars().all()

        data = []
        for le in entries:
            # Resolve player alias
            membership = await session.get(Membership, le.membership_id)
            data.append({
                "id": str(le.id),
                "player_alias": membership.current_alias if membership else "?",
                "membership_id": str(le.membership_id),
                "entry_type": le.entry_type,
                "amount": le.amount,
                "direction": le.direction,
                "balance_before": le.balance_before,
                "balance_after": le.balance_after,
                "source_type": le.source_type,
                "reason": le.reason,
                "created_at": le.created_at.isoformat() if le.created_at else None,
            })

    return {"success": True, "data": data}


# ═══════════════════════════════════════════════════════════════════════════
# NOTIFICATIONS (system-wide view)
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/notifications")
async def list_all_notifications(admin: AdminAccount, limit: int = 50):
    """List all notifications system-wide, newest first."""
    async with async_session() as session:
        result = await session.execute(
            select(Notification, Account)
            .join(Account, Notification.recipient_id == Account.id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
        rows = result.all()

        data = [{
            "id": str(n.id),
            "recipient_username": acct.username,
            "notification_type": n.notification_type,
            "title": n.title,
            "message": n.message,
            "is_read": n.is_read,
            "priority": n.priority,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        } for n, acct in rows]

    return {"success": True, "data": data}


# ═══════════════════════════════════════════════════════════════════════════
# SETTINGS / CONFIG
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/settings/game-info")
async def get_game_settings(admin: AdminAccount):
    """Get game info and key configuration."""
    from app.core.models import GameInfo
    async with async_session() as session:
        result = await session.execute(select(GameInfo).limit(1))
        info = result.scalars().first()

        # Count key stats for overview
        total_accounts = (await session.execute(
            select(func.count()).where(Account.username != "_system", Account.username != "admin")
        )).scalar() or 0

        total_competitions = (await session.execute(
            select(func.count()).select_from(Competition)
        )).scalar() or 0

    data = {
        "game_info": {
            "title": info.title if info else None,
            "subtitle": info.subtitle if info else None,
            "current_season": info.current_season if info else None,
            "status": info.status if info else None,
            "announcement": info.announcement if info else None,
        },
        "system_stats": {
            "total_accounts": total_accounts,
            "total_competitions": total_competitions,
        },
        "attack_config": {
            "base_reward": 500,
            "decay_factor": 0.8,
            "base_penalty": 100,
            "max_attacks_per_cycle": 3,
            "bankruptcy_threshold": 0,
            "initial_balance": 1000,
        },
    }
    return {"success": True, "data": data}


class UpdateGameInfoRequest(BaseModel):
    title: str | None = None
    subtitle: str | None = None
    current_season: str | None = None
    announcement: str | None = None
    status: str | None = None


@router.patch("/settings/game-info")
async def update_game_info(body: UpdateGameInfoRequest, admin: AdminAccount):
    """Update game info."""
    from app.core.models import GameInfo
    async with async_session() as session:
        result = await session.execute(select(GameInfo).limit(1))
        info = result.scalars().first()
        if not info:
            raise HTTPException(status_code=404, detail="بيانات اللعبة غير موجودة")

        if body.title is not None:
            info.title = body.title
        if body.subtitle is not None:
            info.subtitle = body.subtitle
        if body.current_season is not None:
            info.current_season = body.current_season
        if body.announcement is not None:
            info.announcement = body.announcement
        if body.status is not None:
            info.status = body.status

        await session.commit()
    return {"success": True, "message": "تم تحديث بيانات اللعبة"}


@router.get("/settings")
async def list_settings(admin: AdminAccount):
    """List all setting definitions with their current values."""
    async with async_session() as session:
        result = await session.execute(
            select(SettingDefinition).order_by(SettingDefinition.category, SettingDefinition.key)
        )
        definitions = result.scalars().all()

        data = []
        for d in definitions:
            # Get current value (global scope)
            val_result = await session.execute(
                select(SettingValue).where(
                    SettingValue.setting_definition_id == d.id,
                    SettingValue.scope == SettingScope.GLOBAL,
                )
            )
            sv = val_result.scalars().first()

            data.append({
                "id": str(d.id),
                "key": d.key,
                "category": d.category,
                "data_type": d.data_type,
                "default_value": d.default_value,
                "current_value": sv.value if sv else d.default_value,
                "description": d.description,
                "is_per_competition": d.is_per_competition,
            })

    return {"success": True, "data": data}


class UpdateSettingRequest(BaseModel):
    value: dict  # JSONB value wrapper


@router.patch("/settings/{setting_key}")
async def update_setting(setting_key: str, body: UpdateSettingRequest, admin: AdminAccount):
    """Update a setting's value (global scope)."""
    async with async_session() as session:
        defn_result = await session.execute(
            select(SettingDefinition).where(SettingDefinition.key == setting_key)
        )
        defn = defn_result.scalars().first()
        if not defn:
            raise HTTPException(status_code=404, detail="الإعداد غير موجود")

        # Upsert value
        val_result = await session.execute(
            select(SettingValue).where(
                SettingValue.setting_definition_id == defn.id,
                SettingValue.scope == SettingScope.GLOBAL,
            )
        )
        sv = val_result.scalars().first()

        if sv:
            sv.value = body.value
            sv.updated_by = admin.id
        else:
            sv = SettingValue(
                setting_definition_id=defn.id,
                scope=SettingScope.GLOBAL,
                value=body.value,
                updated_by=admin.id,
            )
            session.add(sv)

        await session.commit()
    return {"success": True, "message": f"تم تحديث الإعداد: {setting_key}"}


# ═══════════════════════════════════════════════════════════════════════════
# ADMIN NOTIFICATIONS
# ═══════════════════════════════════════════════════════════════════════════

class SendNotificationRequest(BaseModel):
    recipient_id: uuid.UUID | None = None  # None = broadcast to all
    title: str
    message: str
    priority: str = "normal"


# ═══════════════════════════════════════════════════════════════════════════
# ACCOUNTS (Group B — Account != Membership distinction)
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/accounts")
async def list_accounts(admin: AdminAccount):
    """List all user accounts (platform-level, separate from membership)."""
    async with async_session() as session:
        result = await session.execute(
            select(Account)
            .where(Account.username != "_system")
            .order_by(Account.created_at.desc())
        )
        accounts = result.scalars().all()

        data = []
        for a in accounts:
            # Count memberships
            mem_count = (await session.execute(
                select(func.count()).where(Membership.account_id == a.id)
            )).scalar() or 0

            data.append({
                "id": str(a.id),
                "username": a.username,
                "real_name": a.real_name,
                "status": a.status,
                "is_admin": a.is_admin,
                "membership_count": mem_count,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "last_login_at": a.last_login_at.isoformat() if a.last_login_at else None,
            })

    return {"success": True, "data": data}


@router.get("/accounts/{account_id}")
async def get_account_detail(account_id: uuid.UUID, admin: AdminAccount):
    """Get account detail with all linked memberships."""
    async with async_session() as session:
        acct = await session.get(Account, account_id)
        if not acct:
            raise HTTPException(status_code=404, detail="الحساب غير موجود")

        # Get all memberships for this account
        mem_result = await session.execute(
            select(Membership, Competition)
            .join(Competition, Membership.competition_id == Competition.id)
            .where(Membership.account_id == account_id)
            .order_by(Membership.joined_at.desc())
        )
        memberships = []
        for mem, comp in mem_result.all():
            memberships.append({
                "membership_id": str(mem.id),
                "competition_id": str(comp.id),
                "competition_name": comp.name,
                "alias": mem.current_alias,
                "balance": mem.current_balance,
                "status": mem.status,
                "protection": mem.protection,
                "is_bankrupt": mem.is_bankrupt,
                "joined_at": mem.joined_at.isoformat() if mem.joined_at else None,
            })

    return {
        "success": True,
        "data": {
            "id": str(acct.id),
            "username": acct.username,
            "real_name": acct.real_name,
            "status": acct.status,
            "is_admin": acct.is_admin,
            "created_at": acct.created_at.isoformat() if acct.created_at else None,
            "last_login_at": acct.last_login_at.isoformat() if acct.last_login_at else None,
            "memberships": memberships,
        },
    }


class UpdateAccountStatusRequest(BaseModel):
    status: str


@router.patch("/accounts/{account_id}/status")
async def update_account_status(account_id: uuid.UUID, body: UpdateAccountStatusRequest, admin: AdminAccount):
    """Update account status (suspend, disable, archive). Account != Membership."""
    async with async_session() as session:
        acct = await session.get(Account, account_id)
        if not acct:
            raise HTTPException(status_code=404, detail="الحساب غير موجود")
        if acct.is_admin:
            raise HTTPException(status_code=400, detail="لا يمكن تغيير حالة حساب المشرف")
        acct.status = body.status
        await session.commit()
    return {"success": True, "message": f"تم تحديث حالة الحساب إلى {body.status}"}


@router.post("/notifications/send", status_code=201)
async def send_notification(body: SendNotificationRequest, admin: AdminAccount):
    """Send a notification from admin. If recipient_id is null, broadcast to all active members."""
    async with async_session() as session:
        if body.recipient_id:
            notif = Notification(
                recipient_id=body.recipient_id,
                notification_type=NotificationType.ADMIN_ALERT,
                title=body.title,
                message=body.message,
                priority=body.priority,
            )
            session.add(notif)
            count = 1
        else:
            # Broadcast to all accounts (excluding system)
            accounts_result = await session.execute(
                select(Account.id).where(
                    Account.status == AccountStatus.ACTIVE,
                    Account.username != "_system",
                )
            )
            account_ids = [row[0] for row in accounts_result.all()]
            count = 0
            for aid in account_ids:
                notif = Notification(
                    recipient_id=aid,
                    notification_type=NotificationType.ADMIN_ALERT,
                    title=body.title,
                    message=body.message,
                    priority=body.priority,
                )
                session.add(notif)
                count += 1

        await session.commit()
    return {"success": True, "data": {"sent_count": count}, "message": f"تم إرسال {count} إشعار"}


# ═══════════════════════════════════════════════════════════════════════════
# QUESTION GROUP MANAGEMENT (Group C closure)
# ═══════════════════════════════════════════════════════════════════════════

class UpdateQuestionGroupRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None


@router.patch("/questions/groups/{group_id}")
async def update_question_group(group_id: uuid.UUID, body: UpdateQuestionGroupRequest, admin: AdminAccount):
    """Update a question group's title, description, or status."""
    async with async_session() as session:
        group = await session.get(QuestionGroup, group_id)
        if not group:
            raise HTTPException(status_code=404, detail="مجموعة الأسئلة غير موجودة")
        if body.title is not None:
            group.title = body.title
        if body.description is not None:
            group.description = body.description
        if body.status is not None:
            group.status = body.status
        await session.commit()
    return {"success": True, "message": "تم تحديث مجموعة الأسئلة بنجاح"}


@router.delete("/questions/groups/{group_id}")
async def delete_question_group(group_id: uuid.UUID, admin: AdminAccount):
    """Archive a question group (set status to archived)."""
    async with async_session() as session:
        group = await session.get(QuestionGroup, group_id)
        if not group:
            raise HTTPException(status_code=404, detail="مجموعة الأسئلة غير موجودة")
        group.status = QuestionStatus.ARCHIVED
        await session.commit()
    return {"success": True, "message": "تم أرشفة مجموعة الأسئلة"}


# ═══════════════════════════════════════════════════════════════════════════
# ITEM EFFECTS MANAGEMENT (Group D closure — critical gap)
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/store/items/{item_id}")
async def get_item_detail(item_id: uuid.UUID, admin: AdminAccount):
    """Get full item definition with all its effects."""
    async with async_session() as session:
        item = await session.get(ItemDefinition, item_id)
        if not item:
            raise HTTPException(status_code=404, detail="العنصر غير موجود")

        # Get effects
        effects_result = await session.execute(
            select(ItemEffect)
            .where(ItemEffect.item_definition_id == item_id)
            .order_by(ItemEffect.order_index)
        )
        effects = effects_result.scalars().all()

        effects_data = [{
            "id": str(e.id),
            "effect_type": e.effect_type,
            "parameters": e.parameters,
            "target_scope": e.target_scope,
            "duration_minutes": e.duration_minutes,
            "is_stackable": e.is_stackable,
            "trigger_on": e.trigger_on,
            "order_index": e.order_index,
        } for e in effects]

    return {
        "success": True,
        "data": {
            "id": str(item.id),
            "name": item.name,
            "description": item.description,
            "rarity": item.rarity,
            "status": item.status,
            "category": item.category,
            "usage_type": item.usage_type,
            "max_uses": item.max_uses,
            "is_stackable": item.is_stackable,
            "expires_after_minutes": item.expires_after_minutes,
            "effects": effects_data,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        },
    }


class CreateItemEffectRequest(BaseModel):
    effect_type: str
    parameters: dict = {}
    target_scope: str = "self"
    duration_minutes: int | None = None
    is_stackable: bool = False
    trigger_on: str = "activation"
    order_index: int = 0


@router.post("/store/items/{item_id}/effects", status_code=201)
async def create_item_effect(item_id: uuid.UUID, body: CreateItemEffectRequest, admin: AdminAccount):
    """Add an effect to an item definition."""
    async with async_session() as session:
        item = await session.get(ItemDefinition, item_id)
        if not item:
            raise HTTPException(status_code=404, detail="العنصر غير موجود")

        effect = ItemEffect(
            item_definition_id=item_id,
            effect_type=body.effect_type,
            parameters=body.parameters,
            target_scope=body.target_scope,
            duration_minutes=body.duration_minutes,
            is_stackable=body.is_stackable,
            trigger_on=body.trigger_on,
            order_index=body.order_index,
        )
        session.add(effect)
        await session.commit()
        await session.refresh(effect)

    return {"success": True, "data": {"id": str(effect.id)}, "message": "تم إضافة التأثير بنجاح"}


class UpdateItemEffectRequest(BaseModel):
    effect_type: str | None = None
    parameters: dict | None = None
    target_scope: str | None = None
    duration_minutes: int | None = None
    is_stackable: bool | None = None
    trigger_on: str | None = None
    order_index: int | None = None


@router.patch("/store/items/{item_id}/effects/{effect_id}")
async def update_item_effect(
    item_id: uuid.UUID, effect_id: uuid.UUID, body: UpdateItemEffectRequest, admin: AdminAccount
):
    """Update an existing item effect."""
    async with async_session() as session:
        effect = await session.get(ItemEffect, effect_id)
        if not effect or str(effect.item_definition_id) != str(item_id):
            raise HTTPException(status_code=404, detail="التأثير غير موجود")
        if body.effect_type is not None:
            effect.effect_type = body.effect_type
        if body.parameters is not None:
            effect.parameters = body.parameters
        if body.target_scope is not None:
            effect.target_scope = body.target_scope
        if body.duration_minutes is not None:
            effect.duration_minutes = body.duration_minutes
        if body.is_stackable is not None:
            effect.is_stackable = body.is_stackable
        if body.trigger_on is not None:
            effect.trigger_on = body.trigger_on
        if body.order_index is not None:
            effect.order_index = body.order_index
        await session.commit()
    return {"success": True, "message": "تم تحديث التأثير بنجاح"}


@router.delete("/store/items/{item_id}/effects/{effect_id}")
async def delete_item_effect(item_id: uuid.UUID, effect_id: uuid.UUID, admin: AdminAccount):
    """Delete an item effect."""
    async with async_session() as session:
        effect = await session.get(ItemEffect, effect_id)
        if not effect or str(effect.item_definition_id) != str(item_id):
            raise HTTPException(status_code=404, detail="التأثير غير موجود")
        await session.delete(effect)
        await session.commit()
    return {"success": True, "message": "تم حذف التأثير"}
