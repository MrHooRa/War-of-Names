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
    LedgerDirection,
    LedgerEntryType,
    ListingStatus,
    MembershipStatus,
    OwnedItemStatus,
    QuestionStatus,
    SeasonStatus,
    SessionStatus,
)
from app.modules.attacks.models import AttackAttempt
from app.modules.auth.models import Account
from app.modules.competitions.models import Competition, CompetitionInvite, Cycle, Membership, Season
from app.modules.notifications.models import Notification
from app.modules.quiz.models import AnswerSubmission, Question, QuestionGroup, QuizSession, SessionQuestion
from app.modules.scoring.models import LedgerEntry
from app.modules.store.models import ItemDefinition, OwnedItem, StoreListing

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
    status: str | None = None
    registration_open: bool | None = None


@router.patch("/competitions/{competition_id}")
async def update_competition(competition_id: uuid.UUID, body: CompetitionUpdateRequest, admin: AdminAccount):
    """Update competition status or registration."""
    async with async_session() as session:
        comp = await session.get(Competition, competition_id)
        if not comp:
            raise HTTPException(status_code=404, detail="المنافسة غير موجودة")

        if body.status is not None:
            comp.status = body.status
        if body.registration_open is not None:
            comp.registration_open = body.registration_open

        await session.commit()

    return {"success": True, "message": "تم تحديث المنافسة بنجاح"}


class CycleStatusRequest(BaseModel):
    status: str


@router.patch("/seasons/{season_id}")
async def update_season(season_id: uuid.UUID, body: CycleStatusRequest, admin: AdminAccount):
    """Update season status."""
    async with async_session() as session:
        season = await session.get(Season, season_id)
        if not season:
            raise HTTPException(status_code=404, detail="الموسم غير موجود")
        season.status = body.status
        await session.commit()
    return {"success": True, "message": "تم تحديث الموسم بنجاح"}


@router.patch("/cycles/{cycle_id}")
async def update_cycle(cycle_id: uuid.UUID, body: CycleStatusRequest, admin: AdminAccount):
    """Update cycle status."""
    async with async_session() as session:
        cycle = await session.get(Cycle, cycle_id)
        if not cycle:
            raise HTTPException(status_code=404, detail="الدورة غير موجودة")
        cycle.status = body.status
        await session.commit()
    return {"success": True, "message": "تم تحديث الدورة بنجاح"}


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
    options: dict
    correct_answer: dict
    score_value: int = 100
    difficulty: str = "medium"
    category: str | None = None


@router.post("/questions")
async def create_question(body: CreateQuestionRequest, admin: AdminAccount):
    """Create a new question in a group."""
    async with async_session() as session:
        group = await session.get(QuestionGroup, body.group_id)
        if not group:
            raise HTTPException(status_code=404, detail="مجموعة الأسئلة غير موجودة")

        q = Question(
            group_id=body.group_id,
            question_type="multiple_choice",
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
