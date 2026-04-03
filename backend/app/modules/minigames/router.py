"""FastAPI router for the minigame engine.

Endpoints:

  Player
  ------
  GET  /api/minigames                                                    — list active game types
  GET  /api/competitions/{competition_id}/minigames/{game_type}/leaderboard
  GET  /api/competitions/{competition_id}/minigames/{game_type}/stats
  GET  /api/competitions/{competition_id}/minigames/{game_type}/sessions
  POST /api/competitions/{competition_id}/minigames/{game_type}/challenge
  POST /api/competitions/{competition_id}/minigames/{game_type}/challenge/{session_id}/respond

  Admin
  -----
  GET  /api/admin/minigames
  GET  /api/admin/minigames/{game_type}/sessions
  POST /api/admin/minigames/{game_type}/sessions/{session_id}/cancel
"""

from __future__ import annotations

import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import or_, select

from app.core.auth import get_admin_account, get_current_account
from app.core.database import async_session
from app.core.enums import (
    MinigameMatchType,
    MinigameSessionPhase,
    MinigameTypeStatus,
    MembershipStatus,
)
from app.modules.auth.models import Account
from app.modules.competitions.models import Cycle, Membership, Season
from app.modules.minigames.models import MinigameLeaderboard, MinigameSession, MinigameType

router = APIRouter(tags=["minigames"])

CurrentAccount = Annotated[Account, Depends(get_current_account)]
AdminAccount = Annotated[Account, Depends(get_admin_account)]

# ---------------------------------------------------------------------------
# Hardcoded limits (Sprint 3 will migrate these to settings)
# ---------------------------------------------------------------------------

_DEFAULT_BUY_IN = 500
_DAILY_CAP = 2
_SAME_OPPONENT_LIMIT = 1


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class ChallengeRequest(BaseModel):
    target_membership_id: uuid.UUID


class ChallengeResponse(BaseModel):
    accept: bool


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


async def _get_membership(session, account_id, competition_id):
    """Resolve the authenticated user's active membership in a competition."""
    result = await session.execute(
        select(Membership).where(
            Membership.account_id == account_id,
            Membership.competition_id == competition_id,
            Membership.status == MembershipStatus.ACTIVE,
        )
    )
    return result.scalars().first()


async def _get_active_season_cycle(session, competition_id: uuid.UUID):
    """Return (season, cycle) for the active season/cycle in the competition."""
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


def _serialize_session(s: MinigameSession) -> dict:
    return {
        "id": str(s.id),
        "game_type": s.game_type,
        "competition_id": str(s.competition_id),
        "phase": s.phase.value if hasattr(s.phase, "value") else s.phase,
        "match_type": s.match_type.value if hasattr(s.match_type, "value") else s.match_type,
        "player_1_membership_id": str(s.player_1_membership_id),
        "player_2_membership_id": str(s.player_2_membership_id) if s.player_2_membership_id else None,
        "winner_membership_id": str(s.winner_membership_id) if s.winner_membership_id else None,
        "buy_in_amount": s.buy_in_amount,
        "turn_number": s.turn_number,
        "revision": s.revision,
        "terminal_reason": s.terminal_reason,
        "started_at": s.started_at.isoformat() if s.started_at else None,
        "completed_at": s.completed_at.isoformat() if s.completed_at else None,
        "created_at": s.created_at.isoformat(),
        "updated_at": s.updated_at.isoformat(),
    }


def _serialize_leaderboard_entry(entry: MinigameLeaderboard) -> dict:
    return {
        "id": str(entry.id),
        "membership_id": str(entry.membership_id),
        "wins": entry.wins,
        "losses": entry.losses,
        "current_streak": entry.current_streak,
        "best_streak": entry.best_streak,
        "total_matches": entry.total_matches,
        "avg_tools_used": entry.avg_tools_used,
        "avg_match_duration_sec": entry.avg_match_duration_sec,
        "elo_rating": entry.elo_rating,
        "updated_at": entry.updated_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Player endpoints
# ---------------------------------------------------------------------------


@router.get("/api/minigames")
async def list_active_game_types(current_account: CurrentAccount):
    """Return all game types with status=active."""
    async with async_session() as session:
        result = await session.execute(
            select(MinigameType).where(MinigameType.status == MinigameTypeStatus.ACTIVE)
        )
        types = result.scalars().all()
        return {
            "success": True,
            "data": [
                {
                    "id": gt.id,
                    "name": gt.name,
                    "description": gt.description,
                    "min_players": gt.min_players,
                    "max_players": gt.max_players,
                    "supports_overtime": gt.supports_overtime,
                    "supports_spectators": gt.supports_spectators,
                    "supports_ranked": gt.supports_ranked,
                    "supports_team_mode": gt.supports_team_mode,
                    "status": gt.status.value,
                }
                for gt in types
            ],
        }


@router.get("/api/competitions/{competition_id}/minigames/{game_type}/leaderboard")
async def get_game_leaderboard(
    competition_id: uuid.UUID,
    game_type: str,
    current_account: CurrentAccount,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    """Return the ranked leaderboard for a specific game type in a competition."""
    async with async_session() as session:
        membership = await _get_membership(session, current_account.id, competition_id)
        if not membership:
            raise HTTPException(status_code=403, detail="لست عضواً في هذه المسابقة")

        from app.modules.minigames import leaderboard_service  # noqa: PLC0415

        entries = await leaderboard_service.get_leaderboard(
            session,
            game_type=game_type,
            competition_id=competition_id,
            limit=limit,
            offset=offset,
        )
        return {
            "success": True,
            "data": [_serialize_leaderboard_entry(e) for e in entries],
        }


@router.get("/api/competitions/{competition_id}/minigames/{game_type}/stats")
async def get_my_stats(
    competition_id: uuid.UUID,
    game_type: str,
    current_account: CurrentAccount,
):
    """Return the authenticated player's leaderboard stats for a game type."""
    async with async_session() as session:
        membership = await _get_membership(session, current_account.id, competition_id)
        if not membership:
            raise HTTPException(status_code=403, detail="لست عضواً في هذه المسابقة")

        result = await session.execute(
            select(MinigameLeaderboard).where(
                MinigameLeaderboard.game_type == game_type,
                MinigameLeaderboard.competition_id == competition_id,
                MinigameLeaderboard.membership_id == membership.id,
            )
        )
        entry = result.scalars().first()

        if entry is None:
            return {
                "success": True,
                "data": {
                    "membership_id": str(membership.id),
                    "wins": 0,
                    "losses": 0,
                    "current_streak": 0,
                    "best_streak": 0,
                    "total_matches": 0,
                    "avg_tools_used": 0.0,
                    "avg_match_duration_sec": 0.0,
                    "elo_rating": None,
                },
            }

        return {"success": True, "data": _serialize_leaderboard_entry(entry)}


@router.get("/api/competitions/{competition_id}/minigames/{game_type}/sessions")
async def get_my_sessions(
    competition_id: uuid.UUID,
    game_type: str,
    current_account: CurrentAccount,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """Return session history for the authenticated player in a game type."""
    async with async_session() as session:
        membership = await _get_membership(session, current_account.id, competition_id)
        if not membership:
            raise HTTPException(status_code=403, detail="لست عضواً في هذه المسابقة")

        result = await session.execute(
            select(MinigameSession)
            .where(
                MinigameSession.game_type == game_type,
                MinigameSession.competition_id == competition_id,
                or_(
                    MinigameSession.player_1_membership_id == membership.id,
                    MinigameSession.player_2_membership_id == membership.id,
                ),
            )
            .order_by(MinigameSession.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        sessions = result.scalars().all()
        return {
            "success": True,
            "data": [_serialize_session(s) for s in sessions],
        }


@router.post("/api/competitions/{competition_id}/minigames/{game_type}/challenge")
async def send_challenge(
    competition_id: uuid.UUID,
    game_type: str,
    body: ChallengeRequest,
    current_account: CurrentAccount,
):
    """Send a challenge to another player in the same competition."""
    from app.modules.minigames import policy_service, session_service  # noqa: PLC0415

    async with async_session() as session:
        # Resolve challenger membership
        membership = await _get_membership(session, current_account.id, competition_id)
        if not membership:
            raise HTTPException(status_code=403, detail="لست عضواً في هذه المسابقة")

        # Block self-challenge
        if membership.id == body.target_membership_id:
            raise HTTPException(status_code=400, detail="لا يمكنك تحدي نفسك")

        # Resolve target membership
        target_result = await session.execute(
            select(Membership).where(
                Membership.id == body.target_membership_id,
                Membership.competition_id == competition_id,
                Membership.status == MembershipStatus.ACTIVE,
            )
        )
        target = target_result.scalars().first()
        if not target:
            raise HTTPException(status_code=404, detail="الخصم غير موجود أو غير نشط في هذه المسابقة")

        # Verify game type exists and is active
        game_type_result = await session.execute(
            select(MinigameType).where(MinigameType.id == game_type)
        )
        game_type_obj = game_type_result.scalars().first()
        if not game_type_obj:
            raise HTTPException(status_code=404, detail=f"نوع اللعبة '{game_type}' غير موجود")
        if game_type_obj.status != MinigameTypeStatus.ACTIVE:
            raise HTTPException(status_code=400, detail="هذه اللعبة غير متاحة حالياً")

        # Get active season/cycle
        season, cycle = await _get_active_season_cycle(session, competition_id)

        # Run session creation validation
        creation_errors = session_service.validate_session_creation(
            game_type_id=game_type,
            plugin_exists=True,
            plugin_status=game_type_obj.status.value,
            player_balance=membership.current_balance,
            buy_in_amount=_DEFAULT_BUY_IN,
            is_bankrupt=False,
        )
        if creation_errors:
            raise HTTPException(status_code=400, detail=creation_errors[0])

        # Run policy checks
        matches_today = await policy_service.count_player_matches_today(
            session,
            membership_id=membership.id,
            game_type=game_type,
            competition_id=competition_id,
        )

        opponent_matches = 0
        if cycle:
            opponent_matches = await policy_service.count_opponent_matches_this_cycle(
                session,
                membership_id=membership.id,
                opponent_membership_id=body.target_membership_id,
                game_type=game_type,
                competition_id=competition_id,
                cycle_id=cycle.id,
            )

        policy_blocks = policy_service.run_all_checks(
            matches_today=matches_today,
            daily_cap=_DAILY_CAP,
            matches_with_opponent_this_cycle=opponent_matches,
            same_opponent_limit=_SAME_OPPONENT_LIMIT,
            player_balance=membership.current_balance,
            buy_in_amount=_DEFAULT_BUY_IN,
            is_bankrupt=False,
        )
        if policy_blocks:
            raise HTTPException(status_code=400, detail=policy_blocks[0].message_ar)

        # Create challenge session
        mg_session = await session_service.create_session(
            session,
            game_type=game_type,
            competition_id=competition_id,
            player_1_membership_id=membership.id,
            match_type=MinigameMatchType.CHALLENGE,
            buy_in_amount=_DEFAULT_BUY_IN,
            settings_snapshot={
                "buy_in": _DEFAULT_BUY_IN,
                "daily_cap": _DAILY_CAP,
                "same_opponent_limit": _SAME_OPPONENT_LIMIT,
            },
            season_id=season.id if season else None,
            cycle_id=cycle.id if cycle else None,
            player_2_membership_id=body.target_membership_id,
        )
        await session.commit()

        return {
            "success": True,
            "data": _serialize_session(mg_session),
        }


@router.post(
    "/api/competitions/{competition_id}/minigames/{game_type}/challenge/{session_id}/respond"
)
async def respond_to_challenge(
    competition_id: uuid.UUID,
    game_type: str,
    session_id: uuid.UUID,
    body: ChallengeResponse,
    current_account: CurrentAccount,
):
    """Accept or decline a pending challenge.

    Accept: CREATED → WAITING
    Decline: CREATED → CANCELLED
    """
    from app.modules.minigames import session_service  # noqa: PLC0415

    async with async_session() as session:
        membership = await _get_membership(session, current_account.id, competition_id)
        if not membership:
            raise HTTPException(status_code=403, detail="لست عضواً في هذه المسابقة")

        # Load the session
        result = await session.execute(
            select(MinigameSession).where(
                MinigameSession.id == session_id,
                MinigameSession.game_type == game_type,
                MinigameSession.competition_id == competition_id,
            )
        )
        mg_session = result.scalars().first()
        if not mg_session:
            raise HTTPException(status_code=404, detail="الجلسة غير موجودة")

        # Only player 2 (the challenged player) may respond
        if mg_session.player_2_membership_id != membership.id:
            raise HTTPException(status_code=403, detail="لا يحق لك الرد على هذا التحدي")

        # Must be in CREATED phase
        current_phase = (
            mg_session.phase.value
            if hasattr(mg_session.phase, "value")
            else mg_session.phase
        )
        if current_phase != MinigameSessionPhase.CREATED.value:
            raise HTTPException(status_code=400, detail="التحدي لم يعد في انتظار الرد")

        # Compute transition
        target_phase = (
            MinigameSessionPhase.WAITING if body.accept else MinigameSessionPhase.CANCELLED
        )
        try:
            updates = session_service.compute_transition_update(
                current_phase=mg_session.phase,
                target_phase=target_phase,
                current_revision=mg_session.revision,
                terminal_reason=None if body.accept else "declined",
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        for field, value in updates.items():
            setattr(mg_session, field, value)

        await session.commit()
        await session.refresh(mg_session)

        return {
            "success": True,
            "data": _serialize_session(mg_session),
        }


# ---------------------------------------------------------------------------
# Admin endpoints
# ---------------------------------------------------------------------------


@router.get("/api/admin/minigames")
async def admin_list_game_types(admin: AdminAccount):
    """List all game types with their current status."""
    async with async_session() as session:
        result = await session.execute(select(MinigameType))
        types = result.scalars().all()
        return {
            "success": True,
            "data": [
                {
                    "id": gt.id,
                    "name": gt.name,
                    "description": gt.description,
                    "status": gt.status.value,
                    "min_players": gt.min_players,
                    "max_players": gt.max_players,
                    "supports_overtime": gt.supports_overtime,
                    "supports_spectators": gt.supports_spectators,
                    "supports_ranked": gt.supports_ranked,
                    "supports_team_mode": gt.supports_team_mode,
                    "plugin_api_version": gt.plugin_api_version,
                    "settings_schema_version": gt.settings_schema_version,
                    "created_at": gt.created_at.isoformat(),
                    "updated_at": gt.updated_at.isoformat(),
                }
                for gt in types
            ],
        }


@router.get("/api/admin/minigames/{game_type}/sessions")
async def admin_list_sessions(
    game_type: str,
    admin: AdminAccount,
    competition_id: Optional[uuid.UUID] = Query(default=None),
    phase: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    """List sessions for a game type with optional filters."""
    async with async_session() as session:
        stmt = select(MinigameSession).where(MinigameSession.game_type == game_type)

        if competition_id is not None:
            stmt = stmt.where(MinigameSession.competition_id == competition_id)

        if phase is not None:
            # Validate the phase value
            try:
                phase_enum = MinigameSessionPhase(phase)
                stmt = stmt.where(MinigameSession.phase == phase_enum)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"مرحلة غير صالحة: {phase}")

        stmt = stmt.order_by(MinigameSession.created_at.desc()).limit(limit).offset(offset)
        result = await session.execute(stmt)
        sessions = result.scalars().all()

        return {
            "success": True,
            "data": [_serialize_session(s) for s in sessions],
        }


@router.post("/api/admin/minigames/{game_type}/sessions/{session_id}/cancel")
async def admin_cancel_session(
    game_type: str,
    session_id: uuid.UUID,
    admin: AdminAccount,
):
    """Admin-cancel a session and execute a refund settlement."""
    from app.modules.minigames import session_service, settlement_service  # noqa: PLC0415

    async with async_session() as session:
        result = await session.execute(
            select(MinigameSession).where(
                MinigameSession.id == session_id,
                MinigameSession.game_type == game_type,
            )
        )
        mg_session = result.scalars().first()
        if not mg_session:
            raise HTTPException(status_code=404, detail="الجلسة غير موجودة")

        current_phase = (
            mg_session.phase.value
            if hasattr(mg_session.phase, "value")
            else mg_session.phase
        )

        # Cannot cancel already-terminal sessions
        from app.modules.minigames.state_machine import is_terminal  # noqa: PLC0415

        if is_terminal(current_phase):
            raise HTTPException(status_code=400, detail="الجلسة منتهية بالفعل ولا يمكن إلغاؤها")

        # Transition to CANCELLED
        try:
            updates = session_service.compute_transition_update(
                current_phase=mg_session.phase,
                target_phase=MinigameSessionPhase.CANCELLED,
                current_revision=mg_session.revision,
                terminal_reason="admin_cancel",
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        for field, value in updates.items():
            setattr(mg_session, field, value)

        await session.flush()

        # Execute settlement (refund)
        settlement = await settlement_service.execute_settlement(
            session,
            mg_session=mg_session,
        )
        await session.commit()

        return {
            "success": True,
            "data": {
                "session": _serialize_session(mg_session),
                "settlement": {
                    "id": str(settlement.id),
                    "settlement_state": (
                        settlement.settlement_state.value
                        if hasattr(settlement.settlement_state, "value")
                        else settlement.settlement_state
                    ),
                    "winner_payout": settlement.winner_payout,
                    "loser_penalty": settlement.loser_penalty,
                    "settled_at": settlement.settled_at.isoformat() if settlement.settled_at else None,
                },
            },
        }
