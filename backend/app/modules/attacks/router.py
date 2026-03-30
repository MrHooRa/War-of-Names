"""FastAPI router for the attack engine."""

import uuid
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.core.auth import get_current_account
from app.core.database import async_session
from app.core.enums import MembershipStatus
from app.core.utils import now_riyadh_naive
from app.modules.attacks.schemas import (
    AttackExecuteRequest,
    AttackPreviewRequest,
)
from app.modules.attacks.models import AttackAttempt
from app.modules.attacks.service import execute_attack, get_attack_preview
from app.modules.auth.models import Account
from app.modules.competitions.models import Cycle, Membership, Season
from app.modules.settings.service import get_setting

router = APIRouter(prefix="/api/competitions/{competition_id}/attacks", tags=["attacks"])
CurrentAccount = Annotated[Account, Depends(get_current_account)]


async def _get_active_season_cycle(session, competition_id: uuid.UUID):
    season_result = await session.execute(
        select(Season).where(
            Season.competition_id == competition_id,
            Season.status == "active",
        ).limit(1)
    )
    season = season_result.scalars().first()
    if not season:
        return None, None

    cycle_result = await session.execute(
        select(Cycle).where(
            Cycle.season_id == season.id,
            Cycle.status == "active",
        ).limit(1)
    )
    cycle = cycle_result.scalars().first()
    return season, cycle


async def _get_membership(session, account_id, competition_id):
    """Resolve authenticated user's membership in this competition."""
    result = await session.execute(
        select(Membership).where(
            Membership.account_id == account_id,
            Membership.competition_id == competition_id,
            Membership.status == MembershipStatus.ACTIVE,
        )
    )
    return result.scalars().first()


@router.post("/preview")
async def preview_attack(
    competition_id: uuid.UUID,
    body: AttackPreviewRequest,
    account: CurrentAccount,
):
    async with async_session() as session:
        membership = await _get_membership(session, account.id, competition_id)
        if not membership:
            raise HTTPException(status_code=403, detail="أنت لست عضواً في هذه المنافسة")

        season, cycle = await _get_active_season_cycle(session, competition_id)

        preview = await get_attack_preview(
            session,
            attacker_membership_id=membership.id,
            target_membership_id=body.target_membership_id,
            competition_id=competition_id,
            season_id=season.id if season else None,
            cycle_id=cycle.id if cycle else None,
        )

    return {"success": True, "data": preview}


@router.post("/execute")
async def execute_attack_endpoint(
    competition_id: uuid.UUID,
    body: AttackExecuteRequest,
    account: CurrentAccount,
):
    async with async_session() as session:
        membership = await _get_membership(session, account.id, competition_id)
        if not membership:
            raise HTTPException(status_code=403, detail="أنت لست عضواً في هذه المنافسة")

        # Bug fix: prevent self-attack (DB has chk_attack_self but hitting it causes 500)
        if str(membership.id) == str(body.target_membership_id):
            raise HTTPException(status_code=400, detail="لا يمكنك مهاجمة نفسك")

        season, cycle = await _get_active_season_cycle(session, competition_id)
        if not season or not cycle:
            raise HTTPException(
                status_code=400,
                detail="لا توجد دورة نشطة في هذه المنافسة — لا يمكن تنفيذ الهجوم",
            )

        cooldown_seconds = int(
            await get_setting(
                session,
                "attack_cooldown_seconds",
                competition_id=competition_id,
                season_id=season.id,
                cycle_id=cycle.id,
            ) or 0
        )
        now = now_riyadh_naive()
        if cooldown_seconds > 0:
            cooldown_cutoff = now - timedelta(seconds=cooldown_seconds)
            latest_result = await session.execute(
                select(AttackAttempt).where(
                    AttackAttempt.attacker_id == membership.id,
                    AttackAttempt.cycle_id == cycle.id,
                    AttackAttempt.created_at >= cooldown_cutoff,
                ).order_by(AttackAttempt.created_at.desc()).limit(1)
            )
            latest_attempt = latest_result.scalars().first()
            if latest_attempt:
                remaining = max(
                    1,
                    cooldown_seconds - int((now - latest_attempt.created_at).total_seconds()),
                )
                raise HTTPException(
                    status_code=429,
                    detail=f"انتظر {remaining} ثانية قبل تنفيذ هجوم جديد",
                )

        # Prevent rapid duplicate submissions (same attacker+target+guess within 5 seconds)
        recent_cutoff = now - timedelta(seconds=5)
        dup_result = await session.execute(
            select(AttackAttempt).where(
                AttackAttempt.attacker_id == membership.id,
                AttackAttempt.target_id == body.target_membership_id,
                AttackAttempt.guessed_account_id == body.guessed_account_id,
                AttackAttempt.created_at >= recent_cutoff,
            ).limit(1)
        )
        if dup_result.scalars().first():
            raise HTTPException(status_code=429, detail="انتظر قليلاً قبل تكرار نفس الهجوم")

        result = await execute_attack(
            session,
            attacker_membership_id=membership.id,
            target_membership_id=body.target_membership_id,
            guessed_account_id=body.guessed_account_id,
            competition_id=competition_id,
            season_id=season.id,
            cycle_id=cycle.id,
        )

    return {"success": True, "data": result}
