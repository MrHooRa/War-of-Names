"""
Leaderboard, player profile, and member identity endpoints.

All endpoints require authentication.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.core.auth import get_current_account
from app.core.database import async_session
from app.modules.attacks.models import AttackAttempt, AttackExposure
from app.modules.auth.models import Account
from app.modules.competitions.models import Membership

router = APIRouter(prefix="/api/competitions/{competition_id}", tags=["leaderboard"])
CurrentAccount = Annotated[Account, Depends(get_current_account)]


@router.get("/leaderboard")
async def get_leaderboard(competition_id: uuid.UUID, account: CurrentAccount):
    async with async_session() as session:
        result = await session.execute(
            select(Membership, Account)
            .join(Account, Membership.account_id == Account.id)
            .where(
                Membership.competition_id == competition_id,
                Membership.status == "active",
            )
            .order_by(Membership.current_balance.desc())
        )
        rows = result.all()

    players = []
    for rank, (membership, acc) in enumerate(rows, start=1):
        players.append({
            "rank": rank,
            "membership_id": str(membership.id),
            "alias": membership.current_alias or acc.username,
            "balance": membership.current_balance,
            "protection": membership.protection,
            "is_bankrupt": membership.is_bankrupt,
        })

    return {"success": True, "data": players}


@router.get("/players/{membership_id}")
async def get_player_profile(
    competition_id: uuid.UUID,
    membership_id: uuid.UUID,
    account: CurrentAccount,
):
    async with async_session() as session:
        membership = await session.get(Membership, membership_id)
        if not membership or str(membership.competition_id) != str(competition_id):
            raise HTTPException(status_code=404, detail="اللاعب غير موجود")

        acc = await session.get(Account, membership.account_id)

        # Exposure
        exp_result = await session.execute(
            select(AttackExposure)
            .where(AttackExposure.membership_id == membership_id)
            .order_by(AttackExposure.updated_at.desc())
            .limit(1)
        )
        exposure = exp_result.scalars().first()

        # Recent attacks received
        atk_result = await session.execute(
            select(AttackAttempt)
            .where(AttackAttempt.target_id == membership_id)
            .order_by(AttackAttempt.executed_at.desc())
            .limit(10)
        )
        recent_attacks = atk_result.scalars().all()

    return {
        "success": True,
        "data": {
            "membership_id": str(membership.id),
            "alias": membership.current_alias or acc.username,
            "balance": membership.current_balance,
            "protection": membership.protection,
            "is_bankrupt": membership.is_bankrupt,
            "exposure": {
                "successful_attack_count": exposure.successful_attack_count if exposure else 0,
                "current_reward_stage": exposure.current_reward_stage if exposure else 0,
                "max_attacks_reached": exposure.max_attacks_reached if exposure else False,
            },
            "recent_attacks": [
                {
                    "attempt_id": str(a.id),
                    "outcome": a.outcome,
                    "reward_amount": a.reward_amount,
                    "penalty_amount": a.penalty_amount,
                    "executed_at": a.executed_at.isoformat(),
                }
                for a in recent_attacks
            ],
        },
    }


@router.get("/members/identities")
async def get_member_identities(competition_id: uuid.UUID, account: CurrentAccount):
    async with async_session() as session:
        result = await session.execute(
            select(Membership, Account)
            .join(Account, Membership.account_id == Account.id)
            .where(
                Membership.competition_id == competition_id,
                Membership.status == "active",
            )
            .order_by(Account.real_name)
        )
        rows = result.all()

    identities = [
        {
            "membership_id": str(m.id),
            "alias": m.current_alias or acc.username,
            "account_id": str(acc.id),
            "real_name": acc.real_name,
        }
        for m, acc in rows
    ]

    return {"success": True, "data": identities}
