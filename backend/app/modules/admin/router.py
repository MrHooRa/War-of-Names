"""Admin panel endpoints — dashboard, competitions, players, attacks, quiz, store, ledger, settings."""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
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
from app.modules.competitions.models import AliasRecord, Competition, CompetitionInvite, Cycle, Membership, Season
from app.modules.notifications.models import Notification
from app.modules.quiz.models import AnswerSubmission, Question, QuestionGroup, QuizSession, SessionQuestion
from app.modules.scoring.models import LedgerEntry
from app.modules.settings.models import SettingDefinition, SettingValue
from app.modules.store.models import ItemDefinition, ItemEffect, OwnedItem, StoreListing
from app.modules.audit.service import write_audit
from app.modules.competitions.invite_service import (
    create_invite as create_invite_svc,
    get_active_invite,
    get_invite_state,
    regenerate_invite,
)
from app.modules.store.effect_config import validate_effect, generate_effect_summary, get_effect_types_schema

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
    auto_activate: bool = False


@router.post("/competitions", status_code=201)
async def create_competition(body: CreateCompetitionRequest, admin: AdminAccount):
    """Create a new competition with full lifecycle initialization.

    Auto-creates: initial season, initial cycle, join code, invite link.
    If auto_activate=true, sets everything to ACTIVE + registration_open.
    """
    async with async_session() as session:
        initial_status = CompetitionStatus.ACTIVE if body.auto_activate else CompetitionStatus.DRAFT
        season_status = SeasonStatus.ACTIVE if body.auto_activate else SeasonStatus.DRAFT
        cycle_status = CycleStatus.ACTIVE if body.auto_activate else CycleStatus.DRAFT
        now = datetime.utcnow()

        # 1. Create competition
        comp = Competition(
            name=body.name,
            description=body.description,
            visibility=body.visibility,
            status=initial_status,
            registration_open=body.auto_activate,
            created_by=admin.id,
        )
        session.add(comp)
        await session.flush()

        # 2. Create initial season
        season = Season(
            competition_id=comp.id,
            name="الموسم الأول",
            order_index=1,
            status=season_status,
            starts_at=now if body.auto_activate else None,
        )
        session.add(season)
        await session.flush()

        # 3. Create initial cycle
        cycle = Cycle(
            season_id=season.id,
            label="الدورة الأولى",
            order_index=1,
            status=cycle_status,
            starts_at=now if body.auto_activate else None,
        )
        session.add(cycle)

        # 4. Create join code + invite link
        invite_code = await create_invite_svc(
            session, comp.id, InviteType.CODE, created_by=admin.id,
        )
        invite_link = await create_invite_svc(
            session, comp.id, InviteType.LINK, created_by=admin.id,
        )

        # 5. Audit trail
        await write_audit(
            session,
            actor_id=admin.id,
            subject_type="competition",
            subject_id=comp.id,
            event_type="competition_created",
            summary=f"إنشاء منافسة جديدة: {comp.name}",
            after_state={
                "name": comp.name,
                "status": str(comp.status),
                "registration_open": comp.registration_open,
                "season_id": str(season.id),
                "cycle_id": str(cycle.id),
                "join_code": invite_code.code,
            },
        )

        await session.commit()

    return {
        "success": True,
        "data": {
            "id": str(comp.id),
            "join_code": invite_code.code,
            "invite_link_token": invite_link.code,
            "season_id": str(season.id),
            "cycle_id": str(cycle.id),
        },
        "message": "تم إنشاء المنافسة بنجاح مع الموسم والدورة ورمز الدعوة",
    }


@router.patch("/competitions/{competition_id}")
async def update_competition(competition_id: uuid.UUID, body: CompetitionUpdateRequest, admin: AdminAccount):
    """Update competition status or registration."""
    async with async_session() as session:
        comp = await session.get(Competition, competition_id)
        if not comp:
            raise HTTPException(status_code=404, detail="المنافسة غير موجودة")

        before = {"status": str(comp.status), "registration_open": comp.registration_open, "name": comp.name}

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

        await write_audit(
            session,
            actor_id=admin.id,
            subject_type="competition",
            subject_id=comp.id,
            event_type="competition_updated",
            summary=f"تحديث المنافسة: {comp.name}",
            before_state=before,
            after_state={"status": str(comp.status), "registration_open": comp.registration_open, "name": comp.name},
        )
        await session.commit()

    return {"success": True, "message": "تم تحديث المنافسة بنجاح"}


# ── Invite Management ─────────────────────────────────────────────────────


@router.get("/competitions/{competition_id}/invite-state")
async def admin_invite_state(competition_id: uuid.UUID, admin: AdminAccount):
    """Get the current active join code and invite link for a competition."""
    async with async_session() as session:
        comp = await session.get(Competition, competition_id)
        if not comp:
            raise HTTPException(status_code=404, detail="المنافسة غير موجودة")

        state = await get_invite_state(session, competition_id)

    return {
        "success": True,
        "data": {
            "competition_id": str(competition_id),
            "registration_open": comp.registration_open,
            **state,
        },
    }


@router.post("/competitions/{competition_id}/invite/regenerate-code")
async def admin_regenerate_code(competition_id: uuid.UUID, admin: AdminAccount):
    """Regenerate the active join code — disables the old one."""
    async with async_session() as session:
        comp = await session.get(Competition, competition_id)
        if not comp:
            raise HTTPException(status_code=404, detail="المنافسة غير موجودة")

        old_invite = await get_active_invite(session, competition_id, InviteType.CODE)
        old_code = old_invite.code if old_invite else None

        new_invite = await regenerate_invite(
            session, competition_id, InviteType.CODE, created_by=admin.id,
        )

        await write_audit(
            session,
            actor_id=admin.id,
            subject_type="competition_invite",
            subject_id=comp.id,
            event_type="invite_code_regenerated",
            summary=f"تجديد رمز الدعوة للمنافسة: {comp.name}",
            before_state={"code": old_code},
            after_state={"code": new_invite.code},
        )
        await session.commit()

    return {
        "success": True,
        "data": {"code": new_invite.code},
        "message": "تم تجديد رمز الدعوة بنجاح",
    }


@router.post("/competitions/{competition_id}/invite/regenerate-link")
async def admin_regenerate_link(competition_id: uuid.UUID, admin: AdminAccount):
    """Regenerate the active invite link — disables the old one."""
    async with async_session() as session:
        comp = await session.get(Competition, competition_id)
        if not comp:
            raise HTTPException(status_code=404, detail="المنافسة غير موجودة")

        old_invite = await get_active_invite(session, competition_id, InviteType.LINK)
        old_token = old_invite.code if old_invite else None

        new_invite = await regenerate_invite(
            session, competition_id, InviteType.LINK, created_by=admin.id,
        )

        await write_audit(
            session,
            actor_id=admin.id,
            subject_type="competition_invite",
            subject_id=comp.id,
            event_type="invite_link_regenerated",
            summary=f"تجديد رابط الدعوة للمنافسة: {comp.name}",
            before_state={"token": old_token},
            after_state={"token": new_invite.code},
        )
        await session.commit()

    return {
        "success": True,
        "data": {"token": new_invite.code},
        "message": "تم تجديد رابط الدعوة بنجاح",
    }


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

    @field_validator("code")
    @classmethod
    def code_clean(cls, v: str) -> str:
        return v.strip().upper()


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


class BroadcastBody(BaseModel):
    title: str
    message: str


@router.patch("/seasons/{season_id}")
async def update_season(season_id: uuid.UUID, body: UpdateSeasonRequest, admin: AdminAccount):
    """Update season name, status, or dates. Use /start and /end for lifecycle transitions."""
    async with async_session() as session:
        season = await session.get(Season, season_id)
        if not season:
            raise HTTPException(status_code=404, detail="الموسم غير موجود")

        old_status = season.status

        if body.name is not None:
            season.name = body.name
        if body.status is not None:
            # Guard: don't allow direct ACTIVE transition — force use of /start
            if body.status == SeasonStatus.ACTIVE and old_status != SeasonStatus.ACTIVE:
                raise HTTPException(
                    status_code=400,
                    detail="استخدم نقطة النهاية /start لتفعيل الموسم — لا يمكن التفعيل مباشرة",
                )
            season.status = body.status
        if body.starts_at is not None:
            season.starts_at = datetime.fromisoformat(body.starts_at) if body.starts_at else None
        if body.ends_at is not None:
            season.ends_at = datetime.fromisoformat(body.ends_at) if body.ends_at else None

        # Audit trail on status changes
        if body.status is not None and body.status != old_status:
            await write_audit(
                session,
                actor_id=admin.id,
                subject_type="season",
                subject_id=season.id,
                event_type="season_status_changed",
                summary=f"تغيير حالة الموسم: {old_status} → {body.status}",
                before_state={"status": str(old_status)},
                after_state={"status": body.status},
            )

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
    """Get detailed player info with full operational state, ledger, attacks, and inventory."""
    async with async_session() as session:
        membership = await session.get(Membership, membership_id)
        if not membership:
            raise HTTPException(status_code=404, detail="اللاعب غير موجود")

        account = await session.get(Account, membership.account_id)
        competition = await session.get(Competition, membership.competition_id)

        # Rank within competition
        rank = (await session.execute(
            select(func.count()).where(
                Membership.competition_id == membership.competition_id,
                Membership.status == MembershipStatus.ACTIVE,
                Membership.current_balance > membership.current_balance,
            )
        )).scalar() + 1
        total_active = (await session.execute(
            select(func.count()).where(
                Membership.competition_id == membership.competition_id,
                Membership.status == MembershipStatus.ACTIVE,
            )
        )).scalar() or 0

        # Attack stats
        attacks_sent = (await session.execute(
            select(func.count()).where(
                AttackAttempt.attacker_id == membership_id,
                AttackAttempt.outcome.in_([AttackOutcome.SUCCEEDED, AttackOutcome.FAILED]),
            )
        )).scalar() or 0
        attacks_won = (await session.execute(
            select(func.count()).where(
                AttackAttempt.attacker_id == membership_id,
                AttackAttempt.outcome == AttackOutcome.SUCCEEDED,
            )
        )).scalar() or 0
        attacks_received = (await session.execute(
            select(func.count()).where(
                AttackAttempt.target_id == membership_id,
                AttackAttempt.outcome == AttackOutcome.SUCCEEDED,
            )
        )).scalar() or 0

        # Notification stats for this membership
        notif_count = (await session.execute(
            select(func.count()).where(Notification.membership_id == membership_id)
        )).scalar() or 0
        unread_notifs = (await session.execute(
            select(func.count()).where(
                Notification.membership_id == membership_id,
                Notification.is_read == False,
            )
        )).scalar() or 0

        # Active season / cycle context
        active_season_data = None
        active_cycle_data = None
        if competition:
            season_res = await session.execute(
                select(Season).where(
                    Season.competition_id == competition.id,
                    Season.status == SeasonStatus.ACTIVE,
                ).limit(1)
            )
            active_season = season_res.scalars().first()
            if active_season:
                active_season_data = {"id": str(active_season.id), "name": active_season.name}
                cycle_res = await session.execute(
                    select(Cycle).where(
                        Cycle.season_id == active_season.id,
                        Cycle.status == CycleStatus.ACTIVE,
                    ).limit(1)
                )
                active_cycle = cycle_res.scalars().first()
                if active_cycle:
                    active_cycle_data = {"id": str(active_cycle.id), "label": active_cycle.label}

        # Recent ledger entries
        ledger_result = await session.execute(
            select(LedgerEntry)
            .where(LedgerEntry.membership_id == membership_id)
            .order_by(LedgerEntry.created_at.desc())
            .limit(30)
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
            ).order_by(AttackAttempt.created_at.desc()).limit(15)
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

        # Inventory (enriched with item detail)
        inv_result = await session.execute(
            select(OwnedItem, ItemDefinition)
            .join(ItemDefinition, OwnedItem.item_definition_id == ItemDefinition.id)
            .where(OwnedItem.membership_id == membership_id)
            .order_by(OwnedItem.acquired_at.desc())
        )
        inv_rows = inv_result.all()
        inventory_data = [{
            "id": str(oi.id),
            "item_definition_id": str(item.id),
            "name": item.name,
            "description": item.description,
            "rarity": item.rarity,
            "category": item.category,
            "usage_type": item.usage_type,
            "status": oi.status,
            "source_type": oi.source_type,
            "quantity": oi.quantity,
            "uses_remaining": oi.uses_remaining,
            "acquired_at": oi.acquired_at.isoformat() if oi.acquired_at else None,
            "activated_at": oi.activated_at.isoformat() if oi.activated_at else None,
            "expires_at": oi.expires_at.isoformat() if oi.expires_at else None,
            "consumed_at": oi.consumed_at.isoformat() if oi.consumed_at else None,
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
            "competition_name": competition.name if competition else "?",
            "competition_status": competition.status if competition else None,
            "rank": rank,
            "total_active_members": total_active,
            "attacks_sent": attacks_sent,
            "attacks_won": attacks_won,
            "attacks_received": attacks_received,
            "notification_count": notif_count,
            "unread_notifications": unread_notifs,
            "active_season": active_season_data,
            "active_cycle": active_cycle_data,
            "joined_at": membership.joined_at.isoformat() if membership.joined_at else None,
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

        await write_audit(
            session,
            actor_id=admin.id,
            subject_type="membership",
            subject_id=membership.id,
            event_type="balance_adjusted",
            summary=f"تعديل رصيد: {balance_before} → {balance_after}",
            reason=body.reason,
            before_state={"balance": balance_before},
            after_state={"balance": balance_after},
            related_type="competition",
            related_id=membership.competition_id,
        )
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

        old_status = membership.status
        membership.status = body.status

        await write_audit(
            session,
            actor_id=admin.id,
            subject_type="membership",
            subject_id=membership.id,
            event_type="status_changed",
            summary=f"تغيير حالة اللاعب: {old_status} → {body.status}",
            before_state={"status": str(old_status)},
            after_state={"status": body.status},
            related_type="competition",
            related_id=membership.competition_id,
        )
        await session.commit()

    return {"success": True, "message": f"تم تحديث حالة اللاعب إلى {body.status}"}


class AdminPlayerProtectionRequest(BaseModel):
    protection: str  # "none", "partial", "full"


@router.patch("/players/{membership_id}/protection")
async def update_player_protection(membership_id: uuid.UUID, body: AdminPlayerProtectionRequest, admin: AdminAccount):
    """Set or clear protection on a player."""
    valid = {"none", "partial", "full"}
    if body.protection not in valid:
        raise HTTPException(status_code=400, detail=f"الحماية يجب أن تكون: {', '.join(valid)}")

    async with async_session() as session:
        membership = await session.get(Membership, membership_id)
        if not membership:
            raise HTTPException(status_code=404, detail="اللاعب غير موجود")

        old_protection = membership.protection
        membership.protection = body.protection

        await write_audit(
            session,
            actor_id=admin.id,
            subject_type="membership",
            subject_id=membership.id,
            event_type="protection_changed",
            summary=f"تغيير الحماية: {old_protection} → {body.protection}",
            before_state={"protection": str(old_protection)},
            after_state={"protection": body.protection},
            related_type="competition",
            related_id=membership.competition_id,
        )
        await session.commit()

    labels = {"none": "بدون حماية", "partial": "حماية جزئية", "full": "حماية كاملة"}
    return {"success": True, "message": f"تم تحديث الحماية إلى: {labels.get(body.protection, body.protection)}"}


# ═══════════════════════════════════════════════════════════════════════════
# INVENTORY MANAGEMENT (admin grant / revoke items)
# ═══════════════════════════════════════════════════════════════════════════

class AdminGrantItemRequest(BaseModel):
    item_definition_id: uuid.UUID
    quantity: int = 1
    reason: str = ""


@router.post("/players/{membership_id}/grant-item", status_code=201)
async def grant_item_to_player(membership_id: uuid.UUID, body: AdminGrantItemRequest, admin: AdminAccount):
    """Grant an item to a player via admin action. Creates OwnedItem with source=admin_grant."""
    if body.quantity < 1:
        raise HTTPException(status_code=400, detail="الكمية يجب أن تكون 1 على الأقل")

    async with async_session() as session:
        membership = await session.get(Membership, membership_id)
        if not membership:
            raise HTTPException(status_code=404, detail="اللاعب غير موجود")

        item_def = await session.get(ItemDefinition, body.item_definition_id)
        if not item_def:
            raise HTTPException(status_code=404, detail="العنصر غير موجود")
        if item_def.status not in (ItemStatus.ACTIVE, ItemStatus.DRAFT):
            raise HTTPException(status_code=400, detail="لا يمكن منح عنصر مؤرشف أو معطّل")

        # Check if player already owns a stackable version
        existing = None
        if item_def.is_stackable:
            existing_result = await session.execute(
                select(OwnedItem).where(
                    OwnedItem.membership_id == membership_id,
                    OwnedItem.item_definition_id == body.item_definition_id,
                    OwnedItem.status == OwnedItemStatus.AVAILABLE,
                ).limit(1)
            )
            existing = existing_result.scalars().first()

        if existing:
            existing.quantity += body.quantity
            owned_item_id = existing.id
        else:
            owned = OwnedItem(
                membership_id=membership_id,
                item_definition_id=body.item_definition_id,
                source_type="admin_grant",
                source_id=admin.id,
                quantity=body.quantity,
                uses_remaining=item_def.max_uses,
                status=OwnedItemStatus.AVAILABLE,
            )
            session.add(owned)
            await session.flush()
            owned_item_id = owned.id

        # Create notification for recipient
        notif = Notification(
            recipient_id=membership.account_id,
            membership_id=membership_id,
            notification_type=NotificationType.ITEM_RECEIVED,
            title="عنصر جديد من المشرف",
            message=f"تم منحك {body.quantity}x {item_def.name}" + (f" — {body.reason}" if body.reason else ""),
            priority=NotificationPriority.NORMAL,
        )
        session.add(notif)

        await write_audit(
            session,
            actor_id=admin.id,
            subject_type="membership",
            subject_id=membership_id,
            event_type="item_granted",
            summary=f"منح عنصر: {item_def.name} x{body.quantity}",
            reason=body.reason,
            before_state={},
            after_state={"item": item_def.name, "quantity": body.quantity, "owned_item_id": str(owned_item_id)},
            related_type="competition",
            related_id=membership.competition_id,
        )
        await session.commit()

    return {
        "success": True,
        "data": {"owned_item_id": str(owned_item_id)},
        "message": f"تم منح {body.quantity}x {item_def.name} بنجاح",
    }


class AdminRevokeItemRequest(BaseModel):
    reason: str = ""


@router.post("/players/{membership_id}/revoke-item/{owned_item_id}")
async def revoke_item_from_player(
    membership_id: uuid.UUID,
    owned_item_id: uuid.UUID,
    body: AdminRevokeItemRequest,
    admin: AdminAccount,
):
    """Revoke an owned item from a player. Sets status to consumed with admin trace."""
    async with async_session() as session:
        membership = await session.get(Membership, membership_id)
        if not membership:
            raise HTTPException(status_code=404, detail="اللاعب غير موجود")

        owned_item = await session.get(OwnedItem, owned_item_id)
        if not owned_item or str(owned_item.membership_id) != str(membership_id):
            raise HTTPException(status_code=404, detail="العنصر غير موجود في مخزون اللاعب")

        if owned_item.status in (OwnedItemStatus.CONSUMED, OwnedItemStatus.EXPIRED):
            raise HTTPException(status_code=400, detail="العنصر مستهلك أو منتهي بالفعل")

        # Get item name for messages
        item_def = await session.get(ItemDefinition, owned_item.item_definition_id)
        item_name = item_def.name if item_def else "عنصر"

        old_status = owned_item.status
        old_quantity = owned_item.quantity
        owned_item.status = OwnedItemStatus.CONSUMED
        owned_item.consumed_at = datetime.utcnow()

        # Create notification for player
        notif = Notification(
            recipient_id=membership.account_id,
            membership_id=membership_id,
            notification_type=NotificationType.ADMIN_CHANGE,
            title="تمت مصادرة عنصر",
            message=f"تمت مصادرة {item_name} من مخزونك" + (f" — {body.reason}" if body.reason else ""),
            priority=NotificationPriority.HIGH,
        )
        session.add(notif)

        await write_audit(
            session,
            actor_id=admin.id,
            subject_type="membership",
            subject_id=membership_id,
            event_type="item_revoked",
            summary=f"مصادرة عنصر: {item_name}",
            reason=body.reason,
            before_state={"status": str(old_status), "quantity": old_quantity},
            after_state={"status": "consumed"},
            related_type="competition",
            related_id=membership.competition_id,
        )
        await session.commit()

    return {"success": True, "message": f"تمت مصادرة {item_name} بنجاح"}


class AdminBulkRevokeRequest(BaseModel):
    reason: str = ""


@router.post("/store/items/{item_id}/revoke-all")
async def bulk_revoke_owned_items(item_id: uuid.UUID, body: AdminBulkRevokeRequest, admin: AdminAccount):
    """
    Revoke all active owned instances of an item definition across all players.

    Useful after archiving an item — removes it from every player's inventory.
    Only affects AVAILABLE / ACTIVATED / PENDING items (already consumed/expired are untouched).
    Each affected player receives a notification.
    """
    async with async_session() as session:
        item_def = await session.get(ItemDefinition, item_id)
        if not item_def:
            raise HTTPException(status_code=404, detail="العنصر غير موجود")

        # Find all active owned instances
        result = await session.execute(
            select(OwnedItem)
            .where(
                OwnedItem.item_definition_id == item_id,
                OwnedItem.status.in_([
                    OwnedItemStatus.AVAILABLE,
                    OwnedItemStatus.ACTIVATED,
                    OwnedItemStatus.PENDING,
                ]),
            )
        )
        owned_items = result.scalars().all()

        if not owned_items:
            return {"success": True, "message": "لا توجد عناصر نشطة لمصادرتها", "data": {"revoked_count": 0}}

        now = datetime.utcnow()
        affected_membership_ids = set()

        for owned in owned_items:
            owned.status = OwnedItemStatus.CONSUMED
            owned.consumed_at = now
            affected_membership_ids.add(owned.membership_id)

        # Send notification to each affected player
        for mid in affected_membership_ids:
            membership = await session.get(Membership, mid)
            if membership:
                notif = Notification(
                    recipient_id=membership.account_id,
                    membership_id=mid,
                    notification_type=NotificationType.ADMIN_CHANGE,
                    title="تمت مصادرة عنصر",
                    message=f"تمت مصادرة {item_def.name} من مخزونك بواسطة المشرف"
                        + (f" — {body.reason}" if body.reason else ""),
                    priority=NotificationPriority.HIGH,
                )
                session.add(notif)

        await write_audit(
            session,
            actor_id=admin.id,
            subject_type="item_definition",
            subject_id=item_id,
            event_type="bulk_item_revoked",
            summary=f"مصادرة جماعية: {item_def.name} — {len(owned_items)} نسخة من {len(affected_membership_ids)} لاعب",
            reason=body.reason,
            before_state={"active_count": len(owned_items)},
            after_state={"active_count": 0, "revoked_count": len(owned_items)},
        )
        await session.commit()

    return {
        "success": True,
        "message": f"تمت مصادرة {len(owned_items)} نسخة من {item_def.name}",
        "data": {
            "revoked_count": len(owned_items),
            "players_affected": len(affected_membership_ids),
        },
    }


# ═══════════════════════════════════════════════════════════════════════════
# ADMIN PLAYER NOTIFICATIONS (targeted alert)
# ═══════════════════════════════════════════════════════════════════════════

class AdminPlayerAlertRequest(BaseModel):
    title: str
    message: str
    priority: str = "normal"


@router.post("/players/{membership_id}/send-alert", status_code=201)
async def send_player_alert(membership_id: uuid.UUID, body: AdminPlayerAlertRequest, admin: AdminAccount):
    """Send a direct alert/notification to a specific player within a competition context."""
    valid_priorities = {"low", "normal", "high", "urgent"}
    if body.priority not in valid_priorities:
        raise HTTPException(status_code=400, detail=f"الأولوية يجب أن تكون: {', '.join(valid_priorities)}")

    async with async_session() as session:
        membership = await session.get(Membership, membership_id)
        if not membership:
            raise HTTPException(status_code=404, detail="اللاعب غير موجود")

        notif = Notification(
            recipient_id=membership.account_id,
            membership_id=membership_id,
            notification_type=NotificationType.ADMIN_ALERT,
            title=body.title,
            message=body.message,
            priority=body.priority,
        )
        session.add(notif)

        await write_audit(
            session,
            actor_id=admin.id,
            subject_type="membership",
            subject_id=membership_id,
            event_type="admin_alert_sent",
            summary=f"إرسال تنبيه: {body.title}",
            before_state={},
            after_state={"title": body.title, "priority": body.priority},
            related_type="competition",
            related_id=membership.competition_id,
        )
        await session.commit()

    return {"success": True, "message": "تم إرسال التنبيه بنجاح"}


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
        await session.flush()
        await write_audit(
            session,
            actor_id=admin.id,
            subject_type="question",
            subject_id=q.id,
            event_type="question_created",
            summary=f"أنشأ سؤال في مجموعة {group.title}",
            after_state={"prompt": body.prompt, "type": body.question_type, "score": body.score_value},
        )
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
    starts_at: str | None = None
    ends_at: str | None = None


@router.patch("/quiz-sessions/{session_id}")
async def update_quiz_session(session_id: uuid.UUID, body: UpdateQuizSessionRequest, admin: AdminAccount):
    """Update quiz session status or title."""
    async with async_session() as session:
        qs = await session.get(QuizSession, session_id)
        if not qs:
            raise HTTPException(status_code=404, detail="جلسة الأسئلة غير موجودة")
        before = {"status": str(qs.status), "title": qs.title}
        if body.status is not None:
            qs.status = body.status
        if body.title is not None:
            qs.title = body.title
        if body.starts_at is not None:
            qs.starts_at = datetime.fromisoformat(body.starts_at.replace('Z', '+00:00')).replace(tzinfo=None) if body.starts_at else None
        if body.ends_at is not None:
            qs.ends_at = datetime.fromisoformat(body.ends_at.replace('Z', '+00:00')).replace(tzinfo=None) if body.ends_at else None
        after = {"status": str(qs.status), "title": qs.title}
        await write_audit(
            session,
            actor_id=admin.id,
            subject_type="quiz_session",
            subject_id=qs.id,
            event_type="quiz_session_updated",
            summary=f"حدّث جلسة أسئلة: {qs.title}",
            before_state=before,
            after_state=after,
        )
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
        await session.flush()
        await write_audit(
            session,
            actor_id=admin.id,
            subject_type="question_group",
            subject_id=group.id,
            event_type="question_group_created",
            summary=f"أنشأ مجموعة أسئلة: {group.title}",
            after_state={"title": group.title, "description": group.description},
        )
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
        before = {"prompt": q.prompt, "score_value": q.score_value, "difficulty": str(q.difficulty), "status": str(q.status)}
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
        after = {"prompt": q.prompt, "score_value": q.score_value, "difficulty": str(q.difficulty), "status": str(q.status)}
        await write_audit(
            session,
            actor_id=admin.id,
            subject_type="question",
            subject_id=q.id,
            event_type="question_updated",
            summary=f"حدّث سؤال: {q.prompt[:50]}",
            before_state=before,
            after_state=after,
        )
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
        await write_audit(
            session,
            actor_id=admin.id,
            subject_type="question",
            subject_id=q.id,
            event_type="question_archived",
            summary=f"أرشف سؤال: {q.prompt[:50]}",
            before_state={"status": "active"},
            after_state={"status": "archived"},
        )
        await session.commit()
    return {"success": True, "message": "تم حذف السؤال"}


class CreateQuizSessionRequest(BaseModel):
    competition_id: uuid.UUID
    title: str
    source_group_id: uuid.UUID
    answer_duration_seconds: int = 30
    session_type: str = "timed_window"
    starts_at: str | None = None  # ISO datetime string
    ends_at: str | None = None    # ISO datetime string


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
        if body.starts_at:
            qs.starts_at = datetime.fromisoformat(body.starts_at.replace('Z', '+00:00')).replace(tzinfo=None)
        if body.ends_at:
            qs.ends_at = datetime.fromisoformat(body.ends_at.replace('Z', '+00:00')).replace(tzinfo=None)
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

        await write_audit(
            session,
            actor_id=admin.id,
            subject_type="quiz_session",
            subject_id=qs.id,
            event_type="quiz_session_created",
            summary=f"أنشأ جلسة أسئلة: {body.title} ({len(questions)} سؤال)",
            after_state={"title": body.title, "question_count": len(questions), "competition_id": str(body.competition_id)},
        )
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
        await write_audit(
            session,
            actor_id=admin.id,
            subject_type="quiz_session",
            subject_id=qs.id,
            event_type="quiz_session_cancelled",
            summary=f"ألغى جلسة أسئلة: {qs.title}",
            before_state={"status": str(qs.status)},
            after_state={"status": "cancelled"},
        )
        await session.commit()
    return {"success": True, "message": "تم إلغاء جلسة الأسئلة"}


# ═══════════════════════════════════════════════════════════════════════════
# STORE / ITEMS
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/store/items")
async def list_item_definitions(admin: AdminAccount):
    """List all item definitions with effect counts and listing counts."""
    async with async_session() as session:
        result = await session.execute(
            select(ItemDefinition).order_by(ItemDefinition.created_at.desc())
        )
        items = result.scalars().all()

        data = []
        for item in items:
            # Count effects
            effect_count = (await session.execute(
                select(func.count()).where(ItemEffect.item_definition_id == item.id)
            )).scalar() or 0
            # Count active listings
            listing_count = (await session.execute(
                select(func.count()).where(
                    StoreListing.item_definition_id == item.id,
                    StoreListing.status == ListingStatus.ACTIVE,
                )
            )).scalar() or 0
            # Count total owned (available + activated + pending)
            owned_count = (await session.execute(
                select(func.count()).where(
                    OwnedItem.item_definition_id == item.id,
                    OwnedItem.status.in_([OwnedItemStatus.AVAILABLE, OwnedItemStatus.ACTIVATED, OwnedItemStatus.PENDING]),
                )
            )).scalar() or 0

            data.append({
                "id": str(item.id),
                "name": item.name,
                "description": item.description,
                "rarity": item.rarity,
                "status": item.status,
                "category": item.category,
                "usage_type": item.usage_type,
                "max_uses": item.max_uses,
                "effect_count": effect_count,
                "listing_count": listing_count,
                "owned_count": owned_count,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            })

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
            remaining = None
            if listing.total_stock is not None:
                remaining = max(0, listing.total_stock - (listing.sold_count or 0))
            data.append({
                "listing_id": str(listing.id),
                "item_id": str(item.id),
                "item_name": item.name,
                "item_description": item.description,
                "item_rarity": item.rarity,
                "item_category": item.category,
                "status": listing.status,
                "price": listing.price,
                "max_per_participant": listing.max_per_participant,
                "total_stock": listing.total_stock,
                "remaining_stock": remaining,
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
        before = {"status": listing.status, "price": listing.price, "total_stock": listing.total_stock}
        if body.status is not None:
            listing.status = body.status
        if body.price is not None:
            listing.price = body.price
        if body.total_stock is not None:
            listing.total_stock = body.total_stock

        await write_audit(
            session, actor_id=admin.id, subject_type="store_listing", subject_id=listing_id,
            event_type="listing_updated",
            summary="عدّل عرض متجر",
            before_state=before,
            after_state={"status": listing.status, "price": listing.price, "total_stock": listing.total_stock},
        )
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
        await session.flush()

        await write_audit(
            session, actor_id=admin.id, subject_type="item_definition", subject_id=item.id,
            event_type="item_definition_created",
            summary=f"أنشأ عنصر: {item.name}",
            after_state={"name": item.name, "rarity": body.rarity, "category": body.category, "usage_type": body.usage_type},
        )
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
        before = {"name": item.name, "rarity": item.rarity, "category": item.category, "status": item.status}
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

        await write_audit(
            session, actor_id=admin.id, subject_type="item_definition", subject_id=item_id,
            event_type="item_definition_updated",
            summary=f"عدّل عنصر: {item.name}",
            before_state=before,
            after_state={"name": item.name, "rarity": item.rarity, "category": item.category, "status": item.status},
        )
        await session.commit()
    return {"success": True, "message": "تم تحديث العنصر بنجاح"}


@router.delete("/store/items/{item_id}")
async def archive_item_definition(item_id: uuid.UUID, admin: AdminAccount):
    """
    Archive an item definition.

    Side effects:
      - All ACTIVE store listings for this item are set to HIDDEN.
      - Existing owned items remain intact (historical integrity).
      - Future grants and new listings are blocked (grant endpoint
        rejects archived items; listing creation should check status).
    """
    async with async_session() as session:
        item = await session.get(ItemDefinition, item_id)
        if not item:
            raise HTTPException(status_code=404, detail="العنصر غير موجود")

        if item.status == ItemStatus.ARCHIVED:
            return {"success": True, "message": "العنصر مؤرشف بالفعل"}

        old_status = item.status
        item.status = ItemStatus.ARCHIVED

        # ── Cascade: deactivate all ACTIVE listings for this item ──
        listing_result = await session.execute(
            select(StoreListing).where(
                StoreListing.item_definition_id == item_id,
                StoreListing.status == ListingStatus.ACTIVE,
            )
        )
        deactivated_listings = listing_result.scalars().all()
        for listing in deactivated_listings:
            listing.status = ListingStatus.HIDDEN

        # Count active owned items for informational response
        owned_count = (await session.execute(
            select(func.count()).select_from(OwnedItem).where(
                OwnedItem.item_definition_id == item_id,
                OwnedItem.status.in_([
                    OwnedItemStatus.AVAILABLE,
                    OwnedItemStatus.ACTIVATED,
                    OwnedItemStatus.PENDING,
                ]),
            )
        )).scalar() or 0

        await write_audit(
            session, actor_id=admin.id, subject_type="item_definition", subject_id=item_id,
            event_type="item_definition_archived",
            summary=f"أرشف عنصر: {item.name}",
            before_state={"name": item.name, "status": str(old_status)},
            after_state={
                "name": item.name,
                "status": "archived",
                "listings_deactivated": len(deactivated_listings),
                "owned_items_remaining": owned_count,
            },
        )
        await session.commit()

    return {
        "success": True,
        "message": f"تم أرشفة العنصر «{item.name}»",
        "data": {
            "listings_deactivated": len(deactivated_listings),
            "owned_items_remaining": owned_count,
        },
    }


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
        if item.status == ItemStatus.ARCHIVED:
            raise HTTPException(status_code=400, detail="لا يمكن إنشاء عرض لعنصر مؤرشف")
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
        await session.flush()

        await write_audit(
            session, actor_id=admin.id, subject_type="store_listing", subject_id=listing.id,
            event_type="listing_created",
            summary=f"أنشأ عرض متجر: {item.name} بسعر {body.price}",
            after_state={"item": item.name, "price": body.price, "stock": body.total_stock, "competition_id": str(body.competition_id)},
        )
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
        old_status = listing.status
        listing.status = ListingStatus.HIDDEN

        await write_audit(
            session, actor_id=admin.id, subject_type="store_listing", subject_id=listing_id,
            event_type="listing_hidden",
            summary="أخفى عرض متجر",
            before_state={"status": old_status},
            after_state={"status": "hidden"},
        )
        await session.commit()
    return {"success": True, "message": "تم إخفاء العنصر من المتجر"}


@router.get("/store/ownership")
async def list_store_ownership(admin: AdminAccount, competition_id: uuid.UUID | None = None):
    """List all owned items across a competition — who owns what, source, status."""
    async with async_session() as session:
        query = (
            select(OwnedItem, ItemDefinition, Membership, Account)
            .join(ItemDefinition, OwnedItem.item_definition_id == ItemDefinition.id)
            .join(Membership, OwnedItem.membership_id == Membership.id)
            .join(Account, Membership.account_id == Account.id)
            .order_by(OwnedItem.acquired_at.desc())
        )
        if competition_id:
            query = query.where(Membership.competition_id == competition_id)

        result = await session.execute(query)
        rows = result.all()

        data = []
        for owned, item, membership, account in rows:
            data.append({
                "id": str(owned.id),
                "item_name": item.name,
                "item_rarity": item.rarity,
                "item_category": item.category,
                "player_alias": membership.current_alias,
                "player_username": account.username,
                "membership_id": str(membership.id),
                "status": owned.status,
                "source_type": owned.source_type,
                "quantity": owned.quantity,
                "uses_remaining": owned.uses_remaining,
                "acquired_at": owned.acquired_at.isoformat() if owned.acquired_at else None,
                "consumed_at": owned.consumed_at.isoformat() if owned.consumed_at else None,
            })

    return {"success": True, "data": data}


# ═══════════════════════════════════════════════════════════════════════════
# LEDGER
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/ledger")
async def list_ledger(
    admin: AdminAccount,
    membership_id: uuid.UUID | None = None,
    competition_id: uuid.UUID | None = None,
    entry_type: str | None = None,
    limit: int = 50,
):
    """Browse ledger entries with optional filters."""
    async with async_session() as session:
        query = select(LedgerEntry).order_by(LedgerEntry.created_at.desc()).limit(limit)

        if competition_id:
            query = query.where(LedgerEntry.competition_id == competition_id)
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
async def list_all_notifications(admin: AdminAccount, competition_id: uuid.UUID | None = None, limit: int = 50):
    """List all notifications, optionally filtered by competition (via membership)."""
    async with async_session() as session:
        query = (
            select(Notification, Account)
            .join(Account, Notification.recipient_id == Account.id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
        if competition_id:
            query = query.join(Membership, Notification.membership_id == Membership.id).where(Membership.competition_id == competition_id)

        result = await session.execute(query)
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

    # Read attack config from settings (DB with cascade)
    from app.modules.settings.service import get_settings_batch
    async with async_session() as settings_session:
        cfg = await get_settings_batch(
            settings_session,
            ["attack_base_reward", "attack_decay_factor", "attack_base_penalty",
             "attack_max_per_cycle", "score_bankruptcy_threshold", "score_initial_balance"],
        )

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
            "base_reward": cfg.get("attack_base_reward", 500),
            "decay_factor": cfg.get("attack_decay_factor", 0.8),
            "base_penalty": cfg.get("attack_base_penalty", 100),
            "max_attacks_per_cycle": cfg.get("attack_max_per_cycle", 3),
            "bankruptcy_threshold": cfg.get("score_bankruptcy_threshold", 0),
            "initial_balance": cfg.get("score_initial_balance", 1000),
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
    """Get account detail with all linked memberships and competition context."""
    async with async_session() as session:
        acct = await session.get(Account, account_id)
        if not acct:
            raise HTTPException(status_code=404, detail="الحساب غير موجود")

        # Get all memberships for this account with competition data
        mem_result = await session.execute(
            select(Membership, Competition)
            .join(Competition, Membership.competition_id == Competition.id)
            .where(Membership.account_id == account_id)
            .order_by(Membership.joined_at.desc())
        )
        memberships = []
        competitions_seen = {}
        for mem, comp in mem_result.all():
            # Count attacks for this membership
            attacks_sent = (await session.execute(
                select(func.count()).where(
                    AttackAttempt.attacker_id == mem.id,
                    AttackAttempt.outcome.in_([AttackOutcome.SUCCEEDED, AttackOutcome.FAILED]),
                )
            )).scalar() or 0
            attacks_won = (await session.execute(
                select(func.count()).where(
                    AttackAttempt.attacker_id == mem.id,
                    AttackAttempt.outcome == AttackOutcome.SUCCEEDED,
                )
            )).scalar() or 0

            # Count inventory
            item_count = (await session.execute(
                select(func.count()).where(OwnedItem.membership_id == mem.id)
            )).scalar() or 0

            # Rank within competition (by balance, desc)
            rank = (await session.execute(
                select(func.count()).where(
                    Membership.competition_id == comp.id,
                    Membership.status == MembershipStatus.ACTIVE,
                    Membership.current_balance > mem.current_balance,
                )
            )).scalar() + 1

            memberships.append({
                "membership_id": str(mem.id),
                "competition_id": str(comp.id),
                "competition_name": comp.name,
                "competition_status": comp.status,
                "alias": mem.current_alias,
                "balance": mem.current_balance,
                "status": mem.status,
                "protection": mem.protection,
                "is_bankrupt": mem.is_bankrupt,
                "rank": rank,
                "attacks_sent": attacks_sent,
                "attacks_won": attacks_won,
                "item_count": item_count,
                "joined_at": mem.joined_at.isoformat() if mem.joined_at else None,
            })

            # Track unique competitions
            comp_id_str = str(comp.id)
            if comp_id_str not in competitions_seen:
                competitions_seen[comp_id_str] = {
                    "id": comp_id_str,
                    "name": comp.name,
                    "status": comp.status,
                    "registration_open": comp.registration_open,
                }

        # Total notifications for this account
        notif_count = (await session.execute(
            select(func.count()).where(Notification.recipient_id == account_id)
        )).scalar() or 0
        unread_notif_count = (await session.execute(
            select(func.count()).where(
                Notification.recipient_id == account_id,
                Notification.is_read == False,
            )
        )).scalar() or 0

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
            "notification_count": notif_count,
            "unread_notification_count": unread_notif_count,
            "memberships": memberships,
            "competitions": list(competitions_seen.values()),
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

        old_status = acct.status
        acct.status = body.status

        await write_audit(
            session,
            actor_id=admin.id,
            subject_type="account",
            subject_id=acct.id,
            event_type="account_status_changed",
            summary=f"تغيير حالة الحساب: {old_status} → {body.status}",
            before_state={"status": str(old_status)},
            after_state={"status": body.status},
        )
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
        before = {"title": group.title, "description": group.description, "status": str(group.status)}
        if body.title is not None:
            group.title = body.title
        if body.description is not None:
            group.description = body.description
        if body.status is not None:
            group.status = body.status
        after = {"title": group.title, "description": group.description, "status": str(group.status)}
        await write_audit(
            session,
            actor_id=admin.id,
            subject_type="question_group",
            subject_id=group.id,
            event_type="question_group_updated",
            summary=f"حدّث مجموعة أسئلة: {group.title}",
            before_state=before,
            after_state=after,
        )
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
        await write_audit(
            session,
            actor_id=admin.id,
            subject_type="question_group",
            subject_id=group.id,
            event_type="question_group_archived",
            summary=f"أرشف مجموعة أسئلة: {group.title}",
            before_state={"status": "active"},
            after_state={"status": "archived"},
        )
        await session.commit()
    return {"success": True, "message": "تم أرشفة مجموعة الأسئلة"}


# ═══════════════════════════════════════════════════════════════════════════
# ITEM EFFECTS MANAGEMENT (Group D closure — critical gap)
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/store/effect-types")
async def list_effect_types(admin: AdminAccount):
    """Return the full schema for all supported effect types (for frontend form generation)."""
    return {"success": True, "data": get_effect_types_schema()}


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
            "summary": generate_effect_summary(e.effect_type, e.parameters or {}, e.duration_minutes, e.target_scope or "self", e.trigger_on or "activation"),
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
    # Validate effect configuration
    errors = validate_effect(body.effect_type, body.parameters, body.target_scope, body.duration_minutes, body.trigger_on)
    if errors:
        raise HTTPException(status_code=422, detail={"errors": errors})

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
        await session.flush()

        await write_audit(
            session, actor_id=admin.id, subject_type="item_effect", subject_id=effect.id,
            event_type="item_effect_created",
            summary=f"أضاف تأثير {body.effect_type} لعنصر {item.name}",
            after_state={"effect_type": body.effect_type, "parameters": body.parameters, "target_scope": body.target_scope, "trigger_on": body.trigger_on},
            related_type="item_definition", related_id=item_id,
        )
        await session.commit()
        await session.refresh(effect)

    summary = generate_effect_summary(body.effect_type, body.parameters, body.duration_minutes, body.target_scope, body.trigger_on)
    return {
        "success": True,
        "data": {"id": str(effect.id), "summary": summary},
        "message": "تم إضافة التأثير بنجاح",
    }


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

        # Merge current values with updates for validation
        final_type = body.effect_type if body.effect_type is not None else effect.effect_type
        final_params = body.parameters if body.parameters is not None else effect.parameters
        final_scope = body.target_scope if body.target_scope is not None else effect.target_scope
        final_duration = body.duration_minutes if body.duration_minutes is not None else effect.duration_minutes
        final_trigger = body.trigger_on if body.trigger_on is not None else effect.trigger_on

        errors = validate_effect(final_type, final_params, final_scope, final_duration, final_trigger)
        if errors:
            raise HTTPException(status_code=422, detail={"errors": errors})

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

        item = await session.get(ItemDefinition, item_id)
        await write_audit(
            session, actor_id=admin.id, subject_type="item_effect", subject_id=effect_id,
            event_type="item_effect_updated",
            summary=f"عدّل تأثير {final_type} لعنصر {item.name if item else '?'}",
            after_state={"effect_type": final_type, "parameters": final_params, "target_scope": final_scope, "trigger_on": final_trigger},
            related_type="item_definition", related_id=item_id,
        )
        await session.commit()

    summary = generate_effect_summary(final_type, final_params, final_duration, final_scope, final_trigger)
    return {"success": True, "data": {"summary": summary}, "message": "تم تحديث التأثير بنجاح"}


@router.delete("/store/items/{item_id}/effects/{effect_id}")
async def delete_item_effect(item_id: uuid.UUID, effect_id: uuid.UUID, admin: AdminAccount):
    """Delete an item effect."""
    async with async_session() as session:
        effect = await session.get(ItemEffect, effect_id)
        if not effect or str(effect.item_definition_id) != str(item_id):
            raise HTTPException(status_code=404, detail="التأثير غير موجود")

        item = await session.get(ItemDefinition, item_id)
        await write_audit(
            session, actor_id=admin.id, subject_type="item_effect", subject_id=effect_id,
            event_type="item_effect_deleted",
            summary=f"حذف تأثير {effect.effect_type} من عنصر {item.name if item else '?'}",
            before_state={"effect_type": str(effect.effect_type), "parameters": effect.parameters, "target_scope": effect.target_scope},
            related_type="item_definition", related_id=item_id,
        )
        await session.delete(effect)
        await session.commit()
    return {"success": True, "message": "تم حذف التأثير"}


# ═══════════════════════════════════════════════════════════════════════════
# SEASON DETAIL
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/seasons/{season_id}")
async def get_season_detail(season_id: uuid.UUID, admin: AdminAccount):
    """Get season detail with cycles, member stats, and competition info."""
    async with async_session() as session:
        season = await session.get(Season, season_id)
        if not season:
            raise HTTPException(status_code=404, detail="الموسم غير موجود")

        # Cycles
        cycles_result = await session.execute(
            select(Cycle).where(Cycle.season_id == season_id).order_by(Cycle.order_index)
        )
        cycles = cycles_result.scalars().all()

        # Active members in this competition
        member_count = (await session.execute(
            select(func.count()).where(
                Membership.competition_id == season.competition_id,
                Membership.status == MembershipStatus.ACTIVE,
            )
        )).scalar() or 0

        # Attacks in this season
        attack_count = (await session.execute(
            select(func.count()).where(AttackAttempt.season_id == season_id)
        )).scalar() or 0

    return {
        "success": True,
        "data": {
            "id": str(season.id),
            "competition_id": str(season.competition_id),
            "name": season.name,
            "order_index": season.order_index,
            "status": season.status,
            "starts_at": season.starts_at.isoformat() if season.starts_at else None,
            "ends_at": season.ends_at.isoformat() if season.ends_at else None,
            "member_count": member_count,
            "attack_count": attack_count,
            "cycles": [{
                "id": str(c.id),
                "label": c.label,
                "order_index": c.order_index,
                "status": c.status,
                "starts_at": c.starts_at.isoformat() if c.starts_at else None,
                "ends_at": c.ends_at.isoformat() if c.ends_at else None,
            } for c in cycles],
        },
    }


# ═══════════════════════════════════════════════════════════════════════════
# SEASON LIFECYCLE
# ═══════════════════════════════════════════════════════════════════════════


@router.post("/seasons/{season_id}/start")
async def start_season_endpoint(season_id: uuid.UUID, admin: AdminAccount):
    """Start a season with full lifecycle events — completes other active seasons, notifies members."""
    from app.modules.competitions.cycle_service import start_season as do_start_season

    async with async_session() as session:
        season = await session.get(Season, season_id)
        if not season:
            raise HTTPException(status_code=404, detail="الموسم غير موجود")
        if season.status not in (SeasonStatus.DRAFT, SeasonStatus.PAUSED):
            raise HTTPException(status_code=400, detail="يمكن بدء المواسم ذات الحالة مسودة أو متوقفة فقط")

        result = await do_start_season(session, season, season.competition_id)

        await write_audit(
            session,
            actor_id=admin.id,
            subject_type="season",
            subject_id=season.id,
            event_type="season_started",
            summary=f"بدء الموسم: {season.name}",
            after_state={"status": str(season.status), "name": season.name},
            related_type="competition",
            related_id=season.competition_id,
        )
        await session.commit()

    return {
        "success": True,
        "data": result,
        "message": f"تم بدء الموسم: {season.name}",
    }


@router.post("/seasons/{season_id}/end")
async def end_season_endpoint(season_id: uuid.UUID, admin: AdminAccount):
    """End a season with full lifecycle events — ends active cycles, notifies members."""
    from app.modules.competitions.cycle_service import end_season as do_end_season

    async with async_session() as session:
        season = await session.get(Season, season_id)
        if not season:
            raise HTTPException(status_code=404, detail="الموسم غير موجود")
        if season.status != SeasonStatus.ACTIVE:
            raise HTTPException(status_code=400, detail="الموسم ليس نشطاً حالياً")

        result = await do_end_season(session, season, season.competition_id)

        await write_audit(
            session,
            actor_id=admin.id,
            subject_type="season",
            subject_id=season.id,
            event_type="season_ended",
            summary=f"إنهاء الموسم: {season.name}",
            after_state={"status": str(season.status), "name": season.name},
            related_type="competition",
            related_id=season.competition_id,
        )
        await session.commit()

    return {
        "success": True,
        "data": result,
        "message": f"تم إنهاء الموسم: {season.name}",
    }


# ═══════════════════════════════════════════════════════════════════════════
# CYCLE LIFECYCLE
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/cycles/{cycle_id}/start")
async def start_cycle_endpoint(cycle_id: uuid.UUID, admin: AdminAccount):
    """Start a cycle with full lifecycle events — clears protections, resets bankruptcy, notifies members."""
    from app.modules.competitions.cycle_service import (
        close_expired_cycles,
        start_cycle as do_start_cycle,
    )

    async with async_session() as session:
        cycle = await session.get(Cycle, cycle_id)
        if not cycle:
            raise HTTPException(status_code=404, detail="الدورة غير موجودة")
        if cycle.status not in (CycleStatus.DRAFT, CycleStatus.PAUSED):
            raise HTTPException(status_code=400, detail="يمكن بدء الدورات ذات الحالة مسودة أو متوقفة فقط")

        season = await session.get(Season, cycle.season_id)
        if not season:
            raise HTTPException(status_code=404, detail="الموسم غير موجود")

        # Auto-close any cycles past their ends_at before starting a new one
        await close_expired_cycles(session, season.competition_id)

        result = await do_start_cycle(session, cycle, season)

        await write_audit(
            session,
            actor_id=admin.id,
            subject_type="cycle",
            subject_id=cycle.id,
            event_type="cycle_started",
            summary=f"بدء الدورة: {cycle.label}",
            after_state={"status": str(cycle.status), "label": cycle.label},
            related_type="season",
            related_id=season.id,
        )
        await session.commit()

    return {
        "success": True,
        "data": result.to_dict(),
        "message": f"تم بدء {cycle.label} بنجاح",
    }


@router.post("/cycles/{cycle_id}/end")
async def end_cycle_endpoint(cycle_id: uuid.UUID, admin: AdminAccount):
    """End a cycle with full lifecycle events — clears protections, resets bankruptcy, notifies members."""
    from app.modules.competitions.cycle_service import end_cycle as do_end_cycle

    async with async_session() as session:
        cycle = await session.get(Cycle, cycle_id)
        if not cycle:
            raise HTTPException(status_code=404, detail="الدورة غير موجودة")
        if cycle.status != CycleStatus.ACTIVE:
            raise HTTPException(status_code=400, detail="الدورة ليست نشطة حالياً")

        season = await session.get(Season, cycle.season_id)
        if not season:
            raise HTTPException(status_code=404, detail="الموسم غير موجود")

        result = await do_end_cycle(session, cycle, season)

        await write_audit(
            session,
            actor_id=admin.id,
            subject_type="cycle",
            subject_id=cycle.id,
            event_type="cycle_ended",
            summary=f"إنهاء الدورة: {cycle.label}",
            after_state={"status": str(cycle.status), "label": cycle.label},
            related_type="season",
            related_id=season.id,
        )
        await session.commit()

    return {
        "success": True,
        "data": result.to_dict(),
        "message": f"تم إنهاء {cycle.label} بنجاح",
    }


@router.post("/cycles/{cycle_id}/pause")
async def pause_cycle_endpoint(cycle_id: uuid.UUID, admin: AdminAccount):
    """Pause an active cycle — preserves state, stops gameplay progression."""
    async with async_session() as session:
        cycle = await session.get(Cycle, cycle_id)
        if not cycle:
            raise HTTPException(status_code=404, detail="الدورة غير موجودة")
        if cycle.status != CycleStatus.ACTIVE:
            raise HTTPException(status_code=400, detail="يمكن إيقاف الدورات النشطة فقط")

        cycle.status = CycleStatus.PAUSED

        await write_audit(
            session,
            actor_id=admin.id,
            subject_type="cycle",
            subject_id=cycle.id,
            event_type="cycle_paused",
            summary=f"إيقاف الدورة مؤقتاً: {cycle.label}",
            before_state={"status": "active"},
            after_state={"status": "paused"},
        )
        await session.commit()

    return {"success": True, "message": f"تم إيقاف {cycle.label} مؤقتاً"}


@router.post("/cycles/{cycle_id}/activate")
async def activate_cycle(cycle_id: uuid.UUID, admin: AdminAccount):
    """Activate a draft cycle (simple status change, no lifecycle events). Use /start for full events."""
    async with async_session() as session:
        cycle = await session.get(Cycle, cycle_id)
        if not cycle:
            raise HTTPException(status_code=404, detail="الدورة غير موجودة")

        # Deactivate other active cycles in the same season
        await session.execute(
            update(Cycle).where(
                Cycle.season_id == cycle.season_id,
                Cycle.status == CycleStatus.ACTIVE,
                Cycle.id != cycle_id,
            ).values(status=CycleStatus.COMPLETED, ends_at=datetime.utcnow())
        )

        cycle.status = CycleStatus.ACTIVE
        cycle.starts_at = datetime.utcnow()
        await session.commit()

    return {"success": True, "message": f"تم تفعيل {cycle.label}"}


@router.post("/cycles/{cycle_id}/advance")
async def advance_cycle_endpoint(cycle_id: uuid.UUID, admin: AdminAccount):
    """End the currently active cycle in the same season and start this one. Full lifecycle events for both."""
    from app.modules.competitions.cycle_service import (
        advance_to_next_cycle,
        close_expired_cycles,
    )

    async with async_session() as session:
        next_cycle = await session.get(Cycle, cycle_id)
        if not next_cycle:
            raise HTTPException(status_code=404, detail="الدورة غير موجودة")
        if next_cycle.status not in (CycleStatus.DRAFT, CycleStatus.PAUSED):
            raise HTTPException(status_code=400, detail="الدورة التالية يجب أن تكون مسودة أو متوقفة")

        season = await session.get(Season, next_cycle.season_id)
        if not season:
            raise HTTPException(status_code=404, detail="الموسم غير موجود")

        # Auto-close any cycles past their ends_at
        await close_expired_cycles(session, season.competition_id)

        # Find the currently active cycle in this season
        active_result = await session.execute(
            select(Cycle).where(
                Cycle.season_id == season.id,
                Cycle.status == CycleStatus.ACTIVE,
            ).limit(1)
        )
        current_cycle = active_result.scalars().first()
        if not current_cycle:
            raise HTTPException(status_code=400, detail="لا توجد دورة نشطة حالياً للانتقال منها")

        result = await advance_to_next_cycle(session, current_cycle, next_cycle, season)
        await session.commit()

    return {
        "success": True,
        "data": result,
        "message": f"تم الانتقال من {current_cycle.label} إلى {next_cycle.label}",
    }


@router.post("/competitions/{competition_id}/broadcast")
async def broadcast_to_competition_endpoint(
    competition_id: uuid.UUID, body: BroadcastBody, admin: AdminAccount
):
    """Send an announcement notification to all active members of a competition."""
    from app.modules.competitions.cycle_service import broadcast_to_competition

    async with async_session() as session:
        comp = await session.get(Competition, competition_id)
        if not comp:
            raise HTTPException(status_code=404, detail="المنافسة غير موجودة")

        count = await broadcast_to_competition(
            session,
            competition_id=competition_id,
            title=body.title,
            message=body.message,
        )
        await session.commit()

    return {
        "success": True,
        "data": {"members_notified": count},
        "message": f"تم إرسال الإعلان إلى {count} عضو",
    }


# ═══════════════════════════════════════════════════════════════════════════
# PER-COMPETITION SETTINGS
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/competitions/{competition_id}/settings")
async def get_competition_settings(competition_id: uuid.UUID, admin: AdminAccount):
    """Get settings for a specific competition — shows effective values (competition override or global default)."""
    async with async_session() as session:
        comp = await session.get(Competition, competition_id)
        if not comp:
            raise HTTPException(status_code=404, detail="المنافسة غير موجودة")

        result = await session.execute(
            select(SettingDefinition).order_by(SettingDefinition.category, SettingDefinition.key)
        )
        definitions = result.scalars().all()

        data = []
        for d in definitions:
            # Check competition-level override first
            comp_val_result = await session.execute(
                select(SettingValue).where(
                    SettingValue.setting_definition_id == d.id,
                    SettingValue.scope == SettingScope.COMPETITION,
                    SettingValue.scope_id == competition_id,
                )
            )
            comp_sv = comp_val_result.scalars().first()

            # Global value fallback
            global_val_result = await session.execute(
                select(SettingValue).where(
                    SettingValue.setting_definition_id == d.id,
                    SettingValue.scope == SettingScope.GLOBAL,
                )
            )
            global_sv = global_val_result.scalars().first()

            effective_value = d.default_value
            source = "default"
            if global_sv:
                effective_value = global_sv.value
                source = "global"
            if comp_sv:
                effective_value = comp_sv.value
                source = "competition"

            data.append({
                "id": str(d.id),
                "key": d.key,
                "category": d.category,
                "data_type": d.data_type,
                "default_value": d.default_value,
                "global_value": global_sv.value if global_sv else d.default_value,
                "competition_value": comp_sv.value if comp_sv else None,
                "effective_value": effective_value,
                "source": source,
                "description": d.description,
                "is_per_competition": d.is_per_competition,
            })

    return {"success": True, "data": data}


@router.patch("/competitions/{competition_id}/settings/{setting_key}")
async def update_competition_setting(
    competition_id: uuid.UUID, setting_key: str, body: UpdateSettingRequest, admin: AdminAccount
):
    """Update a setting at competition scope."""
    async with async_session() as session:
        comp = await session.get(Competition, competition_id)
        if not comp:
            raise HTTPException(status_code=404, detail="المنافسة غير موجودة")

        defn_result = await session.execute(
            select(SettingDefinition).where(SettingDefinition.key == setting_key)
        )
        defn = defn_result.scalars().first()
        if not defn:
            raise HTTPException(status_code=404, detail="الإعداد غير موجود")

        # Upsert competition-scoped value
        val_result = await session.execute(
            select(SettingValue).where(
                SettingValue.setting_definition_id == defn.id,
                SettingValue.scope == SettingScope.COMPETITION,
                SettingValue.scope_id == competition_id,
            )
        )
        sv = val_result.scalars().first()

        old_value = sv.value if sv else None
        if sv:
            sv.value = body.value
            sv.updated_by = admin.id
        else:
            sv = SettingValue(
                setting_definition_id=defn.id,
                scope=SettingScope.COMPETITION,
                scope_id=competition_id,
                value=body.value,
                updated_by=admin.id,
            )
            session.add(sv)

        await write_audit(
            session,
            actor_id=admin.id,
            subject_type="setting",
            subject_id=defn.id,
            event_type="setting_updated",
            summary=f"تحديث إعداد: {setting_key}",
            before_state={"value": old_value},
            after_state={"value": body.value},
            related_type="competition",
            related_id=competition_id,
        )
        await session.commit()
    return {"success": True, "message": f"تم تحديث الإعداد: {setting_key} للمنافسة"}


@router.delete("/competitions/{competition_id}/settings/{setting_key}")
async def reset_competition_setting(
    competition_id: uuid.UUID, setting_key: str, admin: AdminAccount
):
    """Remove competition-level override — setting falls back to global/default."""
    async with async_session() as session:
        defn_result = await session.execute(
            select(SettingDefinition).where(SettingDefinition.key == setting_key)
        )
        defn = defn_result.scalars().first()
        if not defn:
            raise HTTPException(status_code=404, detail="الإعداد غير موجود")

        val_result = await session.execute(
            select(SettingValue).where(
                SettingValue.setting_definition_id == defn.id,
                SettingValue.scope == SettingScope.COMPETITION,
                SettingValue.scope_id == competition_id,
            )
        )
        sv = val_result.scalars().first()
        if sv:
            await write_audit(
                session,
                actor_id=admin.id,
                subject_type="setting",
                subject_id=defn.id,
                event_type="setting_reset",
                summary=f"إعادة تعيين إعداد: {setting_key} للافتراضي",
                before_state={"value": sv.value},
                after_state={"value": None},
                related_type="competition",
                related_id=competition_id,
            )
            await session.delete(sv)
            await session.commit()

    return {"success": True, "message": f"تم إعادة تعيين الإعداد: {setting_key} للافتراضي"}


# ═══════════════════════════════════════════════════════════════════════════
# AUDIT TRAIL
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/audit")
async def list_audit_events(
    admin: AdminAccount,
    subject_type: str | None = None,
    subject_id: uuid.UUID | None = None,
    event_type: str | None = None,
    limit: int = 50,
):
    """List audit events with optional filters."""
    from app.modules.audit.models import AuditEvent

    async with async_session() as session:
        query = select(AuditEvent).order_by(AuditEvent.created_at.desc())

        if subject_type:
            query = query.where(AuditEvent.subject_type == subject_type)
        if subject_id:
            query = query.where(AuditEvent.subject_id == subject_id)
        if event_type:
            query = query.where(AuditEvent.event_type == event_type)

        query = query.limit(limit)
        result = await session.execute(query)
        events = result.scalars().all()

        # Resolve actor usernames
        actor_ids = {e.actor_id for e in events if e.actor_id}
        actors = {}
        if actor_ids:
            actors_result = await session.execute(
                select(Account.id, Account.username).where(Account.id.in_(actor_ids))
            )
            actors = {row[0]: row[1] for row in actors_result.all()}

    data = []
    for e in events:
        data.append({
            "id": str(e.id),
            "actor_id": str(e.actor_id) if e.actor_id else None,
            "actor_username": actors.get(e.actor_id, "نظام"),
            "actor_type": e.actor_type,
            "subject_type": e.subject_type,
            "subject_id": str(e.subject_id) if e.subject_id else None,
            "event_type": e.event_type,
            "summary": e.summary,
            "reason": e.reason,
            "before_state": e.before_state,
            "after_state": e.after_state,
            "related_type": e.related_type,
            "related_id": str(e.related_id) if e.related_id else None,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        })

    return {"success": True, "data": data}


# ═══════════════════════════════════════════════════════════════════════════
# BULK PLAYER ACTIONS
# ═══════════════════════════════════════════════════════════════════════════


class BulkGivePointsRequest(BaseModel):
    amount: int
    reason: str

    @field_validator("reason")
    @classmethod
    def clean_reason(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 1:
            raise ValueError("السبب مطلوب")
        return v


class BulkSetBalanceRequest(BaseModel):
    amount: int
    reason: str

    @field_validator("reason")
    @classmethod
    def clean_reason(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 1:
            raise ValueError("السبب مطلوب")
        return v


@router.post("/competitions/{competition_id}/bulk/deactivate-all")
async def bulk_deactivate_all(competition_id: uuid.UUID, admin: AdminAccount):
    """Deactivate all active members in a competition."""
    async with async_session() as session:
        comp = await session.get(Competition, competition_id)
        if not comp:
            raise HTTPException(status_code=404, detail="المنافسة غير موجودة")

        result = await session.execute(
            select(Membership).where(
                Membership.competition_id == competition_id,
                Membership.status == MembershipStatus.ACTIVE,
            )
        )
        members = result.scalars().all()
        count = 0
        for m in members:
            m.status = MembershipStatus.SUSPENDED
            count += 1

        await write_audit(
            session,
            actor_id=admin.id,
            subject_type="competition",
            subject_id=competition_id,
            event_type="bulk_deactivate",
            summary=f"تعطيل جميع الأعضاء: {count} عضو",
            after_state={"deactivated_count": count},
        )
        await session.commit()

    return {
        "success": True,
        "data": {"deactivated_count": count},
        "message": f"تم تعطيل {count} عضو",
    }


@router.post("/competitions/{competition_id}/bulk/give-points")
async def bulk_give_points(
    competition_id: uuid.UUID, body: BulkGivePointsRequest, admin: AdminAccount
):
    """Give a fixed amount of points to all active members."""
    async with async_session() as session:
        comp = await session.get(Competition, competition_id)
        if not comp:
            raise HTTPException(status_code=404, detail="المنافسة غير موجودة")

        result = await session.execute(
            select(Membership).where(
                Membership.competition_id == competition_id,
                Membership.status == MembershipStatus.ACTIVE,
            )
        )
        members = result.scalars().all()
        direction = LedgerDirection.CREDIT if body.amount > 0 else LedgerDirection.DEBIT
        abs_amount = abs(body.amount)
        count = 0

        for m in members:
            balance_before = m.current_balance
            balance_after = balance_before + body.amount

            ledger = LedgerEntry(
                membership_id=m.id,
                competition_id=competition_id,
                entry_type=LedgerEntryType.ADMIN_ADJUSTMENT,
                amount=abs_amount,
                direction=direction,
                balance_before=balance_before,
                balance_after=balance_after,
                source_type="bulk_adjustment",
                reason=body.reason,
                actor_id=admin.id,
            )
            session.add(ledger)
            m.current_balance = balance_after
            count += 1

        await write_audit(
            session,
            actor_id=admin.id,
            subject_type="competition",
            subject_id=competition_id,
            event_type="bulk_give_points",
            summary=f"منح {body.amount} نقطة لـ {count} عضو",
            reason=body.reason,
            after_state={"amount": body.amount, "affected_count": count},
        )
        await session.commit()

    return {
        "success": True,
        "data": {"affected_count": count, "amount": body.amount},
        "message": f"تم منح {body.amount} نقطة لـ {count} عضو",
    }


@router.post("/competitions/{competition_id}/bulk/set-balance")
async def bulk_set_balance(
    competition_id: uuid.UUID, body: BulkSetBalanceRequest, admin: AdminAccount
):
    """Set all active members to a fixed balance amount."""
    async with async_session() as session:
        comp = await session.get(Competition, competition_id)
        if not comp:
            raise HTTPException(status_code=404, detail="المنافسة غير موجودة")

        result = await session.execute(
            select(Membership).where(
                Membership.competition_id == competition_id,
                Membership.status == MembershipStatus.ACTIVE,
            )
        )
        members = result.scalars().all()
        count = 0

        for m in members:
            balance_before = m.current_balance
            diff = body.amount - balance_before
            if diff == 0:
                continue

            direction = LedgerDirection.CREDIT if diff > 0 else LedgerDirection.DEBIT
            ledger = LedgerEntry(
                membership_id=m.id,
                competition_id=competition_id,
                entry_type=LedgerEntryType.ADMIN_ADJUSTMENT,
                amount=abs(diff),
                direction=direction,
                balance_before=balance_before,
                balance_after=body.amount,
                source_type="bulk_set_balance",
                reason=body.reason,
                actor_id=admin.id,
            )
            session.add(ledger)
            m.current_balance = body.amount
            count += 1

        await write_audit(
            session,
            actor_id=admin.id,
            subject_type="competition",
            subject_id=competition_id,
            event_type="bulk_set_balance",
            summary=f"تعيين رصيد {body.amount} لـ {count} عضو",
            reason=body.reason,
            after_state={"target_balance": body.amount, "affected_count": count},
        )
        await session.commit()

    return {
        "success": True,
        "data": {"affected_count": count, "target_balance": body.amount},
        "message": f"تم تعيين رصيد {body.amount} لـ {count} عضو",
    }


@router.post("/competitions/{competition_id}/bulk/reset-bankrupt")
async def bulk_reset_bankrupt(competition_id: uuid.UUID, admin: AdminAccount):
    """Reset all bankrupt players back to non-bankrupt status."""
    from app.modules.competitions.cycle_service import _clear_bankruptcies

    async with async_session() as session:
        comp = await session.get(Competition, competition_id)
        if not comp:
            raise HTTPException(status_code=404, detail="المنافسة غير موجودة")

        count = await _clear_bankruptcies(session, competition_id)

        await write_audit(
            session,
            actor_id=admin.id,
            subject_type="competition",
            subject_id=competition_id,
            event_type="bulk_reset_bankrupt",
            summary=f"إعادة تعيين الإفلاس: {count} لاعب",
            after_state={"cleared_count": count},
        )
        await session.commit()

    return {
        "success": True,
        "data": {"cleared_count": count},
        "message": f"تم إعادة تعيين {count} لاعب مفلس",
    }


# ═══════════════════════════════════════════════════════════════════════════
# ADMIN ALIAS OVERRIDE
# ═══════════════════════════════════════════════════════════════════════════


class AdminChangeAliasRequest(BaseModel):
    new_alias: str
    reason: str = ""

    @field_validator("new_alias")
    @classmethod
    def clean_alias(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2 or len(v) > 50:
            raise ValueError("اللقب يجب أن يكون بين 2-50 حرف")
        return v


@router.patch("/players/{membership_id}/alias")
async def admin_change_alias(
    membership_id: uuid.UUID, body: AdminChangeAliasRequest, admin: AdminAccount
):
    """Admin — override a player's alias. Uniqueness enforced, audit trail recorded."""
    async with async_session() as session:
        membership = await session.get(Membership, membership_id)
        if not membership:
            raise HTTPException(status_code=404, detail="اللاعب غير موجود")

        # Check uniqueness within competition
        conflict = await session.execute(
            select(Membership).where(
                Membership.competition_id == membership.competition_id,
                Membership.current_alias == body.new_alias,
                Membership.id != membership.id,
            )
        )
        if conflict.scalars().first():
            raise HTTPException(status_code=400, detail="هذا اللقب مستخدم بالفعل في المنافسة")

        old_alias = membership.current_alias
        membership.current_alias = body.new_alias

        # Create alias record
        alias_record = AliasRecord(
            membership_id=membership.id,
            alias_value=body.new_alias,
            is_active=True,
        )
        session.add(alias_record)

        await write_audit(
            session,
            actor_id=admin.id,
            subject_type="membership",
            subject_id=membership.id,
            event_type="alias_changed_by_admin",
            summary=f"تغيير لقب: {old_alias} → {body.new_alias}",
            reason=body.reason or "تغيير إداري",
            before_state={"alias": old_alias},
            after_state={"alias": body.new_alias},
            related_type="competition",
            related_id=membership.competition_id,
        )
        await session.commit()

    return {
        "success": True,
        "data": {"old_alias": old_alias, "new_alias": body.new_alias},
        "message": f"تم تغيير اللقب: {old_alias} → {body.new_alias}",
    }
