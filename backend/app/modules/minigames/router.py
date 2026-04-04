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
from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select

from app.core.auth import get_admin_account, get_current_account
from app.core.database import async_session
from app.core.enums import (
    MinigameMatchType,
    MinigameSessionPhase,
    MinigameTypeStatus,
    MembershipStatus,
)
from app.modules.auth.models import Account
from app.modules.competitions.models import Competition, Cycle, Membership, Season
from app.modules.minigames.models import (
    MinigameLeaderboard,
    MinigameSession,
    MinigameSessionParticipant,
    MinigameType,
)

router = APIRouter(tags=["minigames"])

CurrentAccount = Annotated[Account, Depends(get_current_account)]
AdminAccount = Annotated[Account, Depends(get_admin_account)]

# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class ChallengeRequest(BaseModel):
    target_membership_id: uuid.UUID


class ChallengeResponse(BaseModel):
    accept: bool


class CatalogConfigUpsertRequest(BaseModel):
    short_description: str
    icon_token: str
    accent_color: str
    hero_variant: str
    card_variant: str
    estimated_duration_sec: int | None = None
    featured: bool = False
    sort_order: int = 100
    availability_mode: str
    marketing_label: str | None = None
    expected_launch_at: datetime | None = None


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


async def _ensure_competition_exists(session, competition_id: uuid.UUID) -> Competition:
    """Return the Competition row or raise 404 with an Arabic message.

    Used by catalog/lobby endpoints where a missing competition must be a
    distinct error from "not a member". BRD §12.4.
    """
    result = await session.execute(
        select(Competition).where(Competition.id == competition_id)
    )
    competition = result.scalars().first()
    if competition is None:
        raise HTTPException(status_code=404, detail="المسابقة غير موجودة")
    return competition


async def _resolve_catalog_caller(
    session,
    *,
    account_id: uuid.UUID,
    competition_id: uuid.UUID,
) -> Membership:
    """Resolve the catalog caller's membership with Arabic error on failure.

    Validates in order:
      1. Competition exists → 404 "المسابقة غير موجودة"
      2. Caller is an active member → 403 "أنت لست عضواً في هذه المسابقة"

    Returns the membership on success so callers can read balance + bankruptcy.
    """
    await _ensure_competition_exists(session, competition_id)

    membership = await _get_membership(session, account_id, competition_id)
    if membership is None:
        raise HTTPException(
            status_code=403, detail="أنت لست عضواً في هذه المسابقة"
        )
    return membership


def _enum_value(value):
    return value.value if hasattr(value, "value") else value


def _serialize_session(s: MinigameSession) -> dict:
    return {
        "id": str(s.id),
        "game_type": s.game_type,
        "competition_id": str(s.competition_id),
        "phase": s.phase.value if hasattr(s.phase, "value") else s.phase,
        "match_type": s.match_type.value if hasattr(s.match_type, "value") else s.match_type,
        "num_players": s.num_players,
        "min_players": s.min_players,
        "max_players": s.max_players,
        "current_turn_index": s.current_turn_index,
        "winner_slot_index": s.winner_slot_index,
        "buy_in_amount": s.buy_in_amount,
        "turn_number": s.turn_number,
        "revision": s.revision,
        "terminal_reason": s.terminal_reason,
        "started_at": s.started_at.isoformat() if s.started_at else None,
        "completed_at": s.completed_at.isoformat() if s.completed_at else None,
        "created_at": s.created_at.isoformat(),
        "updated_at": s.updated_at.isoformat(),
    }


async def _serialize_session_with_participants(
    db_session, mg_session: MinigameSession
) -> dict:
    """Serialize a session and attach its participants list ordered by slot_index."""
    from app.modules.minigames import session_service  # noqa: PLC0415

    data = _serialize_session(mg_session)
    participants = await session_service.get_session_participants(db_session, mg_session.id)
    data["participants"] = [
        {
            "membership_id": str(p["membership_id"]),
            "slot_index": p["slot_index"],
        }
        for p in participants
    ]
    return data


async def _get_session_participants_with_balances(
    db_session,
    session_id: uuid.UUID,
) -> list[dict]:
    """Return session participants enriched with their current membership balances."""
    from app.modules.minigames.live_service import (  # noqa: PLC0415
        get_session_participants_with_balances,
    )

    return await get_session_participants_with_balances(db_session, session_id)


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


@router.get("/api/competitions/{competition_id}/minigames/catalog")
async def get_catalog_endpoint(
    competition_id: uuid.UUID,
    current_account: CurrentAccount,
):
    """Return the full minigames catalog for a player in a competition.

    This is the primary discovery surface — see BRD §12.1.
    The response is a scoped, enriched read model with:
      - buy-in resolved from competition settings
      - live presence/queue/active-match counts
      - the caller's personal stats and active session (if any)
      - a correlation_id for telemetry tracking

    For the legacy global game-type list, see ``GET /api/minigames`` (BRD §12.5).

    Errors (BRD §12.4):
      401 — JWT missing or invalid (handled by get_current_account dependency)
      403 — caller is not an active member of the competition
      404 — competition does not exist
    """
    from app.modules.minigames.catalog_read_model import catalog_response_to_dict  # noqa: PLC0415
    from app.modules.minigames.catalog_service import get_catalog  # noqa: PLC0415

    async with async_session() as session:
        membership = await _resolve_catalog_caller(
            session,
            account_id=current_account.id,
            competition_id=competition_id,
        )
        season, cycle = await _get_active_season_cycle(session, competition_id)

        response = await get_catalog(
            session,
            competition_id=competition_id,
            membership_id=membership.id,
            player_balance=membership.current_balance,
            is_bankrupt=membership.is_bankrupt,
            season_id=season.id if season else None,
            cycle_id=cycle.id if cycle else None,
        )

    return catalog_response_to_dict(response)


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


@router.get("/api/minigames/{game_type}")
async def get_game_type_detail(
    game_type: str,
    current_account: CurrentAccount,
):
    """Return metadata for a single minigame type."""
    from app.modules.minigames.registry import GameTypeRegistry  # noqa: PLC0415

    async with async_session() as session:
        result = await session.execute(
            select(MinigameType).where(MinigameType.id == game_type)
        )
        game_type_obj = result.scalars().first()
        if game_type_obj is None:
            raise HTTPException(status_code=404, detail="نوع اللعبة غير موجود")

        plugin = GameTypeRegistry.get(game_type)
        return {
            "success": True,
            "data": {
                "id": game_type_obj.id,
                "name": game_type_obj.name,
                "description": game_type_obj.description,
                "min_players": game_type_obj.min_players,
                "max_players": game_type_obj.max_players,
                "supports_overtime": game_type_obj.supports_overtime,
                "supports_spectators": game_type_obj.supports_spectators,
                "supports_ranked": game_type_obj.supports_ranked,
                "supports_team_mode": game_type_obj.supports_team_mode,
                "status": game_type_obj.status.value,
                "plugin_api_version": game_type_obj.plugin_api_version,
                "settings_schema_version": game_type_obj.settings_schema_version,
                "registered": plugin is not None,
            },
        }


@router.get("/api/competitions/{competition_id}/minigames/{game_type}/lobby")
async def get_lobby_detail_endpoint(
    competition_id: uuid.UUID,
    game_type: str,
    current_account: CurrentAccount,
):
    """Return the full lobby page read model for a single game.

    See BRD §8.2 for the response shape and §12.2 for the endpoint contract.

    Errors (BRD §12.4):
      401 — JWT missing or invalid
      403 — caller is not an active member of the competition
      404 — competition or game_type does not exist (or game is hidden)
    """
    from app.modules.minigames.catalog_service import get_lobby_detail  # noqa: PLC0415

    async with async_session() as session:
        membership = await _resolve_catalog_caller(
            session,
            account_id=current_account.id,
            competition_id=competition_id,
        )
        season, cycle = await _get_active_season_cycle(session, competition_id)

        try:
            response = await get_lobby_detail(
                session,
                game_type=game_type,
                competition_id=competition_id,
                membership_id=membership.id,
                player_balance=membership.current_balance,
                is_bankrupt=membership.is_bankrupt,
                season_id=season.id if season else None,
                cycle_id=cycle.id if cycle else None,
            )
        except LookupError:
            # Service raises LookupError when the game is missing or hidden.
            # Convert to a 404 with an Arabic message (BRD §12.4).
            raise HTTPException(status_code=404, detail="نوع اللعبة غير موجود")

    return {
        "correlation_id": response.correlation_id,
        "game": response.game,
        "my_state": response.my_state,
        "my_stats": response.my_stats,
        "lobby": response.lobby,
        "leaderboard_preview": response.leaderboard_preview,
        "how_to_play": response.how_to_play,
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
            .join(
                MinigameSessionParticipant,
                MinigameSessionParticipant.session_id == MinigameSession.id,
            )
            .where(
                MinigameSession.game_type == game_type,
                MinigameSession.competition_id == competition_id,
                MinigameSessionParticipant.membership_id == membership.id,
            )
            .distinct()
            .order_by(MinigameSession.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        sessions = result.scalars().all()
        return {
            "success": True,
            "data": [
                await _serialize_session_with_participants(session, s)
                for s in sessions
            ],
        }


@router.get("/api/competitions/{competition_id}/minigames/{game_type}/sessions/{session_id}")
async def get_session_detail(
    competition_id: uuid.UUID,
    game_type: str,
    session_id: uuid.UUID,
    current_account: CurrentAccount,
):
    """Return one session with participants for the authenticated member."""
    async with async_session() as session:
        membership = await _get_membership(session, current_account.id, competition_id)
        if not membership:
            raise HTTPException(status_code=403, detail="لست عضواً في هذه المسابقة")

        result = await session.execute(
            select(MinigameSession).where(
                MinigameSession.id == session_id,
                MinigameSession.competition_id == competition_id,
                MinigameSession.game_type == game_type,
            )
        )
        mg_session = result.scalars().first()
        if mg_session is None:
            raise HTTPException(status_code=404, detail="الجلسة غير موجودة")

        return {
            "success": True,
            "data": await _serialize_session_with_participants(session, mg_session),
        }


@router.post("/api/competitions/{competition_id}/minigames/{game_type}/queue")
async def queue_join(
    competition_id: uuid.UUID,
    game_type: str,
    current_account: CurrentAccount,
):
    """Join the in-memory matchmaking queue and trigger matching when possible."""
    from app.modules.minigames.settings_helper import (  # noqa: PLC0415
        check_kill_switch,
        get_effective_setting,
        get_minigame_settings,
    )
    from app.modules.minigames.ws_router import _schedule_queue_expiry  # noqa: PLC0415

    async with async_session() as session:
        membership = await _get_membership(session, current_account.id, competition_id)
        if not membership:
            raise HTTPException(status_code=403, detail="لست عضواً في هذه المسابقة")
        alias = membership.current_alias or "مجهول"
        season, cycle = await _get_active_season_cycle(session, competition_id)
        settings_snapshot = await get_minigame_settings(
            session,
            competition_id=competition_id,
            season_id=season.id if season else None,
            cycle_id=cycle.id if cycle else None,
            game_type=game_type,
        )
        kill_switch = check_kill_switch(settings_snapshot.get("minigame_kill_switch"))
        if not get_effective_setting(
            settings_snapshot,
            generic_key="minigame_enabled",
            game_key=f"{game_type}_enabled",
            default=False,
        ):
            raise HTTPException(status_code=403, detail="الألعاب المصغرة غير مفعلة في هذه المسابقة")
        if not kill_switch.can_matchmake:
            raise HTTPException(status_code=403, detail=kill_switch.message_ar or "التوفيق معطل حالياً")

    lobby_key = f"{game_type}:{competition_id}"
    if not lobby_mgr.is_in_lobby(lobby_key, membership.id):
        lobby_mgr.join(lobby_key, membership.id, alias)
    lobby_mgr.queue_join(lobby_key, membership.id)

    matched = lobby_mgr.try_match(lobby_key)
    if matched:
        from app.modules.minigames.ws_router import _handle_queue_match  # noqa: PLC0415

        await _handle_queue_match(
            lobby_key,
            competition_id,
            game_type,
            matched_ids=matched,
        )
    else:
        await _schedule_queue_expiry(
            lobby_key=lobby_key,
            membership_id=membership.id,
            delay_seconds=int(settings_snapshot.get(f"{game_type}_queue_timeout_sec", 120)),
        )

    return {
        "success": True,
        "data": {
            "queued": matched is None,
            "matched_membership_ids": [str(mid) for mid in matched] if matched else [],
            "lobby_state": lobby_mgr.get_lobby_state(lobby_key),
        },
    }


@router.delete("/api/competitions/{competition_id}/minigames/{game_type}/queue")
async def queue_leave(
    competition_id: uuid.UUID,
    game_type: str,
    current_account: CurrentAccount,
):
    """Leave the in-memory matchmaking queue."""
    from app.modules.minigames.ws_router import _cancel_queue_expiry  # noqa: PLC0415

    async with async_session() as session:
        membership = await _get_membership(session, current_account.id, competition_id)
        if not membership:
            raise HTTPException(status_code=403, detail="لست عضواً في هذه المسابقة")

    lobby_key = f"{game_type}:{competition_id}"
    _cancel_queue_expiry(lobby_key, membership.id)
    lobby_mgr.queue_leave(lobby_key, membership.id)
    return {
        "success": True,
        "data": {
            "queued": False,
            "lobby_state": lobby_mgr.get_lobby_state(lobby_key),
        },
    }


@router.post("/api/competitions/{competition_id}/minigames/{game_type}/challenge")
async def send_challenge(
    competition_id: uuid.UUID,
    game_type: str,
    body: ChallengeRequest,
    current_account: CurrentAccount,
):
    """Send a challenge to another player in the same competition."""
    from app.modules.minigames import session_service  # noqa: PLC0415
    from app.modules.minigames.live_service import (  # noqa: PLC0415
        build_challenge_expiry,
        initialize_session_state,
        validate_match_candidate,
    )
    from app.modules.minigames.registry import GameTypeRegistry  # noqa: PLC0415
    from app.modules.minigames.settings_helper import (  # noqa: PLC0415
        check_kill_switch,
        get_effective_setting,
        get_minigame_settings,
    )
    from app.modules.minigames.ws_router import _schedule_challenge_expiry  # noqa: PLC0415

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
        plugin = GameTypeRegistry.get(game_type)
        if plugin is None:
            raise HTTPException(status_code=400, detail="نوع اللعبة غير مسجل في المحرك")

        # Get active season/cycle
        season, cycle = await _get_active_season_cycle(session, competition_id)

        # Load settings via cascade
        mg_settings = await get_minigame_settings(
            session,
            competition_id=competition_id,
            season_id=season.id if season else None,
            cycle_id=cycle.id if cycle else None,
            game_type=game_type,
        )

        # Check kill switch
        ks = check_kill_switch(mg_settings.get("minigame_kill_switch"))
        if not ks.can_create_session:
            raise HTTPException(status_code=403, detail=ks.message_ar)

        # Check if minigames are enabled
        if not get_effective_setting(
            mg_settings,
            generic_key="minigame_enabled",
            game_key=f"{game_type}_enabled",
            default=False,
        ):
            raise HTTPException(status_code=403, detail="الألعاب المصغرة غير مفعلة في هذه المسابقة")

        buy_in = int(
            get_effective_setting(
                mg_settings,
                generic_key="minigame_buy_in",
                game_key=f"{game_type}_buy_in",
                default=500,
            )
        )
        daily_cap = int(
            get_effective_setting(
                mg_settings,
                generic_key="minigame_daily_limit",
                game_key=f"{game_type}_daily_limit",
                default=2,
            )
        )
        same_opp = int(
            get_effective_setting(
                mg_settings,
                generic_key="minigame_same_opponent_limit",
                game_key=f"{game_type}_same_opponent_limit",
                default=1,
            )
        )

        for candidate, opponent_membership_ids in (
            (membership, [target.id]),
            (target, [membership.id]),
        ):
            validation_error = await validate_match_candidate(
                session,
                membership=candidate,
                game_type=game_type,
                plugin_status=game_type_obj.status.value,
                competition_id=competition_id,
                buy_in_amount=buy_in,
                daily_cap=daily_cap,
                same_opponent_limit=same_opp,
                opponent_membership_ids=opponent_membership_ids,
                cycle_id=cycle.id if cycle else None,
            )
            if validation_error:
                raise HTTPException(status_code=400, detail=validation_error)

        # Create challenge session (2-player: challenger at slot 0, target at slot 1)
        mg_session = await session_service.create_session(
            session,
            game_type=game_type,
            competition_id=competition_id,
            player_membership_ids=[membership.id, body.target_membership_id],
            match_type=MinigameMatchType.CHALLENGE,
            buy_in_amount=buy_in,
            settings_snapshot={k: v for k, v in mg_settings.items()},
            min_players=2,
            max_players=2,
            season_id=season.id if season else None,
            cycle_id=cycle.id if cycle else None,
            turn_duration_ms=int(
                get_effective_setting(
                    mg_settings,
                    generic_key="minigame_turn_duration_sec",
                    game_key=f"{game_type}_turn_duration_sec",
                    default=30,
                )
            )
            * 1000,
            grace_timer_ms=int(
                get_effective_setting(
                    mg_settings,
                    generic_key="minigame_grace_timer_sec",
                    game_key=f"{game_type}_grace_timer_sec",
                    default=60,
                )
            )
            * 1000,
        )
        participants = await session_service.get_session_participants(session, mg_session.id)
        await initialize_session_state(
            session,
            mg_session=mg_session,
            plugin=plugin,
            participants=participants,
        )
        if isinstance(mg_session.game_state, dict):
            mg_session.game_state = {
                **mg_session.game_state,
                "challenge_expires_at": build_challenge_expiry(
                    created_at=mg_session.created_at,
                    timeout_seconds=int(
                        get_effective_setting(
                            mg_settings,
                            generic_key="",
                            game_key=f"{game_type}_challenge_timeout_sec",
                            default=60,
                        )
                    ),
                ),
            }
        await session.flush()
        await session.commit()
        await _schedule_challenge_expiry(
            session_id=mg_session.id,
            competition_id=competition_id,
            game_type=game_type,
            delay_seconds=int(
                get_effective_setting(
                    mg_settings,
                    generic_key="",
                    game_key=f"{game_type}_challenge_timeout_sec",
                    default=60,
                )
            ),
        )

        return {
            "success": True,
            "data": await _serialize_session_with_participants(session, mg_session),
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
    from app.modules.minigames.live_service import (  # noqa: PLC0415
        start_session,
        validate_match_candidate,
    )
    from app.modules.minigames.registry import GameTypeRegistry  # noqa: PLC0415
    from app.modules.minigames.settings_helper import (  # noqa: PLC0415
        get_effective_setting,
        get_minigame_settings,
    )
    from app.modules.minigames.ws_router import (  # noqa: PLC0415
        _cancel_challenge_expiry,
        _schedule_session_phase_timer,
    )

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

        # Only the challenged player (slot_index=1) may respond
        participant_result = await session.execute(
            select(MinigameSessionParticipant).where(
                MinigameSessionParticipant.session_id == mg_session.id,
                MinigameSessionParticipant.slot_index == 1,
            )
        )
        target_participant = participant_result.scalars().first()
        if target_participant is None or target_participant.membership_id != membership.id:
            raise HTTPException(status_code=403, detail="لا يحق لك الرد على هذا التحدي")

        # Must be in CREATED phase
        current_phase = (
            mg_session.phase.value
            if hasattr(mg_session.phase, "value")
            else mg_session.phase
        )
        if current_phase != MinigameSessionPhase.CREATED.value:
            raise HTTPException(status_code=400, detail="التحدي لم يعد في انتظار الرد")

        if body.accept and isinstance(mg_session.game_state, dict):
            expires_at = mg_session.game_state.get("challenge_expires_at")
            if expires_at:
                try:
                    from datetime import datetime  # noqa: PLC0415
                    from app.core.utils import now_riyadh_naive  # noqa: PLC0415

                    if datetime.fromisoformat(expires_at) < now_riyadh_naive():
                        raise HTTPException(status_code=400, detail="انتهت مهلة هذا التحدي")
                except ValueError:
                    pass

        if body.accept:
            game_type_result = await session.execute(
                select(MinigameType).where(MinigameType.id == game_type)
            )
            game_type_obj = game_type_result.scalars().first()
            if not game_type_obj:
                raise HTTPException(status_code=404, detail=f"نوع اللعبة '{game_type}' غير موجود")

            plugin = GameTypeRegistry.get(game_type)
            if plugin is None:
                raise HTTPException(status_code=400, detail="نوع اللعبة غير مسجل في المحرك")

            season, cycle = await _get_active_season_cycle(session, competition_id)
            settings_snapshot = await get_minigame_settings(
                session,
                competition_id=competition_id,
                season_id=season.id if season else None,
                cycle_id=cycle.id if cycle else None,
                game_type=game_type,
            )
            buy_in = int(
                get_effective_setting(
                    settings_snapshot,
                    generic_key="minigame_buy_in",
                    game_key=f"{game_type}_buy_in",
                    default=500,
                )
            )
            daily_cap = int(
                get_effective_setting(
                    settings_snapshot,
                    generic_key="minigame_daily_limit",
                    game_key=f"{game_type}_daily_limit",
                    default=2,
                )
            )
            same_opp = int(
                get_effective_setting(
                    settings_snapshot,
                    generic_key="minigame_same_opponent_limit",
                    game_key=f"{game_type}_same_opponent_limit",
                    default=1,
                )
            )

            participant_rows = await session.execute(
                select(MinigameSessionParticipant).where(
                    MinigameSessionParticipant.session_id == mg_session.id
                )
            )
            participant_membership_ids = [
                participant.membership_id
                for participant in participant_rows.scalars().all()
            ]
            memberships_result = await session.execute(
                select(Membership).where(Membership.id.in_(participant_membership_ids))
            )
            memberships = {
                participant.id: participant
                for participant in memberships_result.scalars().all()
            }
            for participant_id in participant_membership_ids:
                candidate = memberships.get(participant_id)
                if candidate is None:
                    raise HTTPException(status_code=404, detail="أحد المشاركين لم يعد متاحاً")
                validation_error = await validate_match_candidate(
                    session,
                    membership=candidate,
                    game_type=game_type,
                    plugin_status=game_type_obj.status.value,
                    competition_id=competition_id,
                    buy_in_amount=buy_in,
                    daily_cap=daily_cap,
                    same_opponent_limit=same_opp,
                    opponent_membership_ids=[
                        opponent_id
                        for opponent_id in participant_membership_ids
                        if opponent_id != participant_id
                    ],
                    cycle_id=cycle.id if cycle else None,
                )
                if validation_error:
                    raise HTTPException(status_code=400, detail=validation_error)

            participants = await _get_session_participants_with_balances(session, mg_session.id)
            try:
                mg_session, _ = await start_session(
                    session,
                    mg_session=mg_session,
                    plugin=plugin,
                    participants=participants,
                    actor_type="participant",
                    actor_membership_id=membership.id,
                )
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            except RuntimeError as exc:
                raise HTTPException(status_code=409, detail=str(exc)) from exc
        else:
            try:
                mg_session = await session_service.transition_session(
                    session,
                    session_id=mg_session.id,
                    expected_revision=mg_session.revision,
                    target_phase=MinigameSessionPhase.CANCELLED,
                    terminal_reason="declined",
                    actor_type="participant",
                    actor_membership_id=membership.id,
                )
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

            if mg_session is None:
                raise HTTPException(
                    status_code=409,
                    detail="تعذر تحديث الجلسة بسبب تعارض متزامن",
                )

        await session.commit()
        await session.refresh(mg_session)
        _cancel_challenge_expiry(session_id)
        if body.accept:
            await _schedule_session_phase_timer(
                session_id=mg_session.id,
                competition_id=competition_id,
                game_type=game_type,
                delay_seconds=(mg_session.turn_duration_ms or 0) / 1000,
            )

        return {
            "success": True,
            "data": await _serialize_session_with_participants(session, mg_session),
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


@router.get("/api/admin/minigames/{game_type}/settings/explain")
async def admin_explain_settings(
    game_type: str,
    admin: AdminAccount,
    competition_id: uuid.UUID,
    season_id: Optional[uuid.UUID] = Query(default=None),
    cycle_id: Optional[uuid.UUID] = Query(default=None),
):
    """Explain the resolved minigame settings and their winning scope."""
    from app.core.enums import SettingScope  # noqa: PLC0415
    from app.modules.minigames.settings_helper import (  # noqa: PLC0415
        get_setting_defaults_for_game,
        get_setting_keys_for_game,
        get_minigame_settings,
    )
    from app.modules.settings.models import SettingDefinition, SettingValue  # noqa: PLC0415

    setting_keys = get_setting_keys_for_game(game_type)
    setting_defaults = get_setting_defaults_for_game(game_type)
    async with async_session() as session:
        definitions_result = await session.execute(
            select(SettingDefinition).where(SettingDefinition.key.in_(setting_keys))
        )
        definitions = {
            definition.key: definition
            for definition in definitions_result.scalars().all()
        }
        definition_ids = [definition.id for definition in definitions.values()]
        values_result = await session.execute(
            select(SettingValue).where(SettingValue.setting_definition_id.in_(definition_ids))
        )
        setting_values = list(values_result.scalars().all())
        resolved = await get_minigame_settings(
            session,
            competition_id=competition_id,
            season_id=season_id,
            cycle_id=cycle_id,
            game_type=game_type,
        )

    sources = {}
    for key in setting_keys:
        definition = definitions.get(key)
        value_record = None
        for scope, scope_id in (
            (SettingScope.CYCLE, cycle_id),
            (SettingScope.SEASON, season_id),
            (SettingScope.COMPETITION, competition_id),
            (SettingScope.GLOBAL, None),
        ):
            if definition is None:
                break
            for setting_value in setting_values:
                if setting_value.setting_definition_id != definition.id:
                    continue
                if setting_value.scope != scope:
                    continue
                if scope_id is None and setting_value.scope_id is None:
                    value_record = setting_value
                    break
                if scope_id is not None and setting_value.scope_id == scope_id:
                    value_record = setting_value
                    break
            if value_record is not None:
                break

        if value_record is not None:
            sources[key] = {
                "scope": value_record.scope.value,
                "scope_id": str(value_record.scope_id) if value_record.scope_id else None,
                "value": value_record.value.get("v") if isinstance(value_record.value, dict) else value_record.value,
            }
        else:
            sources[key] = {
                "scope": "default",
                "scope_id": None,
                "value": setting_defaults[key],
            }

    return {
        "success": True,
        "data": {
            "game_type": game_type,
            "competition_id": str(competition_id),
            "season_id": str(season_id) if season_id else None,
            "cycle_id": str(cycle_id) if cycle_id else None,
            "resolved": resolved,
            "sources": sources,
        },
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
            "data": [
                await _serialize_session_with_participants(session, s)
                for s in sessions
            ],
        }


@router.post("/api/admin/minigames/{game_type}/sessions/{session_id}/cancel")
async def admin_cancel_session(
    game_type: str,
    session_id: uuid.UUID,
    admin: AdminAccount,
):
    """Admin-cancel a session and execute a refund settlement."""
    from app.modules.minigames.live_service import finalize_session  # noqa: PLC0415
    from app.modules.minigames.registry import GameTypeRegistry  # noqa: PLC0415
    from app.modules.minigames.state_machine import is_terminal  # noqa: PLC0415

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
        if is_terminal(current_phase):
            raise HTTPException(status_code=400, detail="الجلسة منتهية بالفعل ولا يمكن إلغاؤها")

        plugin = GameTypeRegistry.get(game_type)
        if plugin is None:
            raise HTTPException(status_code=400, detail="نوع اللعبة غير مسجل في المحرك")

        participants = await _get_session_participants_with_balances(session, mg_session.id)
        try:
            finalized = await finalize_session(
                session,
                mg_session=mg_session,
                plugin=plugin,
                participants=participants,
                terminal_result=None,
                target_phase=MinigameSessionPhase.CANCELLED,
                terminal_reason="admin_cancel",
                actor_type="admin",
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        await session.commit()
        settlement = finalized["settlement"]
        mg_session = finalized["session"]

        return {
            "success": True,
            "data": {
                "session": await _serialize_session_with_participants(session, mg_session),
                "settlement": {
                    "id": str(settlement.id),
                    "settlement_state": (
                        settlement.settlement_state.value
                        if hasattr(settlement.settlement_state, "value")
                        else settlement.settlement_state
                    ),
                    "participant_results": settlement.participant_results,
                    "total_pool": settlement.total_pool,
                    "settled_at": settlement.settled_at.isoformat() if settlement.settled_at else None,
                },
            },
        }


@router.post("/api/admin/minigames/{game_type}/sessions/{session_id}/settle")
async def admin_settle_session(
    game_type: str,
    session_id: uuid.UUID,
    admin: AdminAccount,
):
    """Idempotently settle a terminal session."""
    from app.modules.minigames.live_service import build_forfeit_terminal_result  # noqa: PLC0415
    from app.modules.minigames.registry import GameTypeRegistry  # noqa: PLC0415
    from app.modules.minigames.settlement_service import (  # noqa: PLC0415
        execute_cancel_settlement,
        execute_settlement,
    )
    from app.modules.minigames.state_machine import is_terminal  # noqa: PLC0415

    async with async_session() as session:
        result = await session.execute(
            select(MinigameSession).where(
                MinigameSession.id == session_id,
                MinigameSession.game_type == game_type,
            )
        )
        mg_session = result.scalars().first()
        if mg_session is None:
            raise HTTPException(status_code=404, detail="الجلسة غير موجودة")
        if not is_terminal(mg_session.phase):
            raise HTTPException(status_code=400, detail="لا يمكن تسوية جلسة غير نهائية")

        plugin = GameTypeRegistry.get(game_type)
        if plugin is None:
            raise HTTPException(status_code=400, detail="نوع اللعبة غير مسجل في المحرك")

        participants = await _get_session_participants_with_balances(session, mg_session.id)
        if _enum_value(mg_session.phase) == MinigameSessionPhase.CANCELLED.value:
            settlement = await execute_cancel_settlement(
                session,
                mg_session=mg_session,
                participants=participants,
            )
        else:
            terminal_result = plugin.evaluate_terminal(mg_session.game_state)
            if terminal_result is None and mg_session.winner_slot_index is not None:
                winner = next(
                    (
                        participant
                        for participant in participants
                        if participant["slot_index"] == mg_session.winner_slot_index
                    ),
                    None,
                )
                loser = next(
                    (
                        participant
                        for participant in participants
                        if participant["slot_index"] != mg_session.winner_slot_index
                    ),
                    None,
                )
                if winner is not None:
                    terminal_result = build_forfeit_terminal_result(
                        participants=participants,
                        winner_membership_id=winner["membership_id"],
                        loser_membership_id=loser["membership_id"] if loser else None,
                        reason=mg_session.terminal_reason or "admin_settle",
                        buy_in_amount=mg_session.buy_in_amount,
                    )
            if terminal_result is None:
                raise HTTPException(status_code=400, detail="تعذر اشتقاق نتيجة نهائية لهذه الجلسة")
            terminal_result = {
                **terminal_result,
                "buy_in": mg_session.buy_in_amount,
            }
            settlement = await execute_settlement(
                session,
                mg_session=mg_session,
                participants=participants,
                plugin_settlement=plugin.compute_settlement(terminal_result),
            )

        await session.commit()
        return {
            "success": True,
            "data": {
                "id": str(settlement.id),
                "session_id": str(mg_session.id),
                "settlement_state": (
                    settlement.settlement_state.value
                    if hasattr(settlement.settlement_state, "value")
                    else settlement.settlement_state
                ),
                "participant_results": settlement.participant_results,
                "total_pool": settlement.total_pool,
                "settled_at": settlement.settled_at.isoformat() if settlement.settled_at else None,
            },
        }


@router.get("/api/admin/minigames/{game_type}/dead-letters")
async def admin_list_dead_letters(
    game_type: str,
    admin: AdminAccount,
):
    """Return the dead-letter queue for this minigame type.

    The current single-process implementation does not persist dead letters yet,
    so this endpoint returns an empty list instead of failing the BRD surface.
    """
    return {"success": True, "data": []}


@router.post("/api/admin/minigames/{game_type}/dead-letters/{dead_letter_id}/retry")
async def admin_retry_dead_letter(
    game_type: str,
    dead_letter_id: uuid.UUID,
    admin: AdminAccount,
):
    """Retry a dead-lettered event.

    No persisted dead-letter queue exists in this single-process implementation.
    """
    raise HTTPException(status_code=404, detail="لا توجد أحداث ميتة معلقة لإعادة المحاولة")


class KillSwitchRequest(BaseModel):
    level: str  # "off", "soft", "hard", "emergency"
    competition_id: uuid.UUID


@router.patch("/api/admin/minigames/{game_type}/kill-switch")
async def admin_set_kill_switch(
    game_type: str,
    body: KillSwitchRequest,
    admin: AdminAccount,
):
    """Set kill switch level for a game type in a competition."""
    from app.modules.minigames.live_service import (
        finalize_session,
        get_session_participants_with_balances,
    )  # noqa: PLC0415
    from app.modules.minigames.registry import GameTypeRegistry  # noqa: PLC0415
    from app.modules.minigames.settings_helper import KillSwitchLevel  # noqa: PLC0415
    from app.modules.minigames.ws_router import (  # noqa: PLC0415
        _broadcast_lobby_state,
        _broadcast_settlement_result,
        _broadcast_transition_event,
        _cancel_challenge_expiry,
        _cancel_grace_task,
        _cancel_queue_expiry,
        _cancel_session_timer,
        _send_session_state_snapshots,
        _set_lobby_status_for_participants,
    )

    valid_levels = {e.value for e in KillSwitchLevel}
    if body.level not in valid_levels:
        raise HTTPException(status_code=400, detail=f"مستوى غير صالح. القيم المسموحة: {', '.join(sorted(valid_levels))}")

    finalizations: list[tuple[MinigameSession, dict, list[dict], object, str]] = []
    async with async_session() as session:
        from app.modules.settings.models import SettingDefinition, SettingValue  # noqa: PLC0415
        from app.core.enums import SettingScope, MinigameSessionPhase  # noqa: PLC0415

        # Find the setting definition
        result = await session.execute(
            select(SettingDefinition).where(SettingDefinition.key == "minigame_kill_switch")
        )
        defn = result.scalars().first()
        if not defn:
            raise HTTPException(status_code=500, detail="إعداد مفتاح الإيقاف غير موجود في النظام")

        # Upsert the setting value for this competition
        existing = await session.execute(
            select(SettingValue).where(
                SettingValue.setting_definition_id == defn.id,
                SettingValue.scope == SettingScope.COMPETITION,
                SettingValue.scope_id == body.competition_id,
            )
        )
        sv = existing.scalars().first()
        if sv:
            sv.value = {"v": body.level}
            sv.updated_by = admin.id
        else:
            sv = SettingValue(
                setting_definition_id=defn.id,
                scope=SettingScope.COMPETITION,
                scope_id=body.competition_id,
                value={"v": body.level},
                updated_by=admin.id,
            )
            session.add(sv)

        if body.level == KillSwitchLevel.EMERGENCY.value:
            plugin = GameTypeRegistry.get(game_type)
            if plugin is None:
                raise HTTPException(status_code=400, detail="نوع اللعبة غير مسجل في المحرك")

            active_result = await session.execute(
                select(MinigameSession).where(
                    MinigameSession.game_type == game_type,
                    MinigameSession.competition_id == body.competition_id,
                    MinigameSession.phase.in_(
                        [
                            MinigameSessionPhase.WAITING,
                            MinigameSessionPhase.READY,
                            MinigameSessionPhase.IN_PROGRESS,
                            MinigameSessionPhase.OVERTIME,
                            MinigameSessionPhase.PAUSED,
                        ]
                    ),
                )
            )
            active_sessions = list(active_result.scalars().all())
            for mg_session in active_sessions:
                participants = await get_session_participants_with_balances(session, mg_session.id)
                finalized = await finalize_session(
                    session,
                    mg_session=mg_session,
                    plugin=plugin,
                    participants=participants,
                    terminal_result=None,
                    target_phase=MinigameSessionPhase.CANCELLED,
                    terminal_reason="emergency_kill_switch",
                    actor_type="admin",
                )
                finalizations.append(
                    (finalized["session"], finalized, participants, plugin, f"{game_type}:{body.competition_id}")
                )

        await session.commit()

    if body.level == KillSwitchLevel.EMERGENCY.value:
        lobby_key = f"{game_type}:{body.competition_id}"
        queued_membership_ids = lobby_mgr.clear_queue(lobby_key)
        for membership_id in queued_membership_ids:
            _cancel_queue_expiry(lobby_key, membership_id)

        for mg_session, finalized, participants, plugin, session_lobby_key in finalizations:
            _cancel_challenge_expiry(mg_session.id)
            _cancel_grace_task(mg_session.id)
            _cancel_session_timer(mg_session.id)
            _set_lobby_status_for_participants(session_lobby_key, participants, status="idle")
            await _broadcast_transition_event(
                session_id=mg_session.id,
                participants=participants,
                lobby_key=session_lobby_key,
                from_phase="emergency",
                to_phase=mg_session.phase,
                data={"terminal_reason": mg_session.terminal_reason},
            )
            await _send_session_state_snapshots(
                session_id=mg_session.id,
                plugin=plugin,
                state=mg_session.game_state,
                participants=participants,
                current_turn_index=mg_session.current_turn_index,
                lobby_key=session_lobby_key,
                phase=mg_session.phase,
                revision=mg_session.revision,
                turn_number=mg_session.turn_number,
            )
            await _broadcast_settlement_result(
                session_id=mg_session.id,
                participants=participants,
                lobby_key=session_lobby_key,
                participant_results=finalized.get("participant_results", []),
                stats_update=finalized.get("stats_update", {}),
            )

        await _broadcast_lobby_state(lobby_key)

    return {"success": True, "data": {"level": body.level, "message": "تم تحديث مفتاح الإيقاف"}}


@router.get("/api/admin/minigames/{game_type}/metrics")
async def admin_get_metrics(
    game_type: str,
    admin: AdminAccount,
    competition_id: Optional[uuid.UUID] = Query(default=None),
):
    """Return high-level operational metrics for a minigame type."""
    from sqlalchemy import func  # noqa: PLC0415

    from app.modules.minigames.models import MinigameSessionSettlement  # noqa: PLC0415

    async with async_session() as session:
        session_stmt = select(MinigameSession.phase, func.count()).where(
            MinigameSession.game_type == game_type
        )
        settlement_stmt = select(
            MinigameSessionSettlement.settlement_state,
            func.count(),
        ).join(
            MinigameSession,
            MinigameSession.id == MinigameSessionSettlement.session_id,
        ).where(
            MinigameSession.game_type == game_type
        )
        if competition_id is not None:
            session_stmt = session_stmt.where(MinigameSession.competition_id == competition_id)
            settlement_stmt = settlement_stmt.where(MinigameSession.competition_id == competition_id)

        session_result = await session.execute(
            session_stmt.group_by(MinigameSession.phase)
        )
        settlement_result = await session.execute(
            settlement_stmt.group_by(MinigameSessionSettlement.settlement_state)
        )

    sessions_by_phase = {
        _enum_value(phase): count
        for phase, count in session_result.all()
    }
    settlements_by_state = {
        _enum_value(state): count
        for state, count in settlement_result.all()
    }
    return {
        "success": True,
        "data": {
            "game_type": game_type,
            "competition_id": str(competition_id) if competition_id else None,
            "sessions_by_phase": sessions_by_phase,
            "settlements_by_state": settlements_by_state,
            "dead_letters": 0,
        },
    }


@router.get("/api/admin/minigames/{game_type}/sessions/{session_id}/events")
async def admin_get_session_events(
    game_type: str,
    session_id: uuid.UUID,
    admin: AdminAccount,
):
    """Admin: view all events for a session, ordered by revision."""
    async with async_session() as session:
        from app.modules.minigames.models import MinigameSessionEvent  # noqa: PLC0415

        result = await session.execute(
            select(MinigameSessionEvent)
            .where(MinigameSessionEvent.session_id == session_id)
            .order_by(MinigameSessionEvent.revision.asc())
        )
        events = result.scalars().all()

    return {
        "success": True,
        "data": [
            {
                "id": str(e.id),
                "revision": e.revision,
                "event_type": e.event_type,
                "actor_type": e.actor_type,
                "actor_membership_id": str(e.actor_membership_id) if e.actor_membership_id else None,
                "action_type": e.action_type,
                "payload": e.payload,
                "result": e.result,
                "from_phase": e.from_phase,
                "to_phase": e.to_phase,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ],
    }


# ─── Catalog Config Admin CRUD ───────────────────────────────────────────────

@router.get("/api/admin/minigames/catalog-configs")
async def admin_list_catalog_configs(admin: AdminAccount):
    """List all minigame catalog configs (admin only).

    Returns rows sorted by sort_order ASC, then game_type ASC for stable ordering.
    """
    from app.modules.minigames.catalog_config_model import MinigameCatalogConfig  # noqa: PLC0415

    async with async_session() as session:
        result = await session.execute(
            select(MinigameCatalogConfig).order_by(
                MinigameCatalogConfig.sort_order.asc(),
                MinigameCatalogConfig.game_type.asc(),
            )
        )
        rows = result.scalars().all()

    return {
        "items": [
            {
                "game_type": row.game_type,
                "short_description": row.short_description,
                "icon_token": row.icon_token,
                "accent_color": row.accent_color,
                "hero_variant": (
                    row.hero_variant.value
                    if hasattr(row.hero_variant, "value")
                    else str(row.hero_variant)
                ),
                "card_variant": (
                    row.card_variant.value
                    if hasattr(row.card_variant, "value")
                    else str(row.card_variant)
                ),
                "estimated_duration_sec": row.estimated_duration_sec,
                "featured": row.featured,
                "sort_order": row.sort_order,
                "availability_mode": (
                    row.availability_mode.value
                    if hasattr(row.availability_mode, "value")
                    else str(row.availability_mode)
                ),
                "marketing_label": row.marketing_label,
                "expected_launch_at": (
                    row.expected_launch_at.isoformat() if row.expected_launch_at else None
                ),
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            }
            for row in rows
        ]
    }


@router.get("/api/admin/minigames/catalog-configs/{game_type}")
async def admin_get_catalog_config(game_type: str, admin: AdminAccount):
    """Get a single catalog config by game_type."""
    from app.modules.minigames.catalog_config_model import MinigameCatalogConfig  # noqa: PLC0415

    async with async_session() as session:
        row = await session.get(MinigameCatalogConfig, game_type)
        if row is None:
            raise HTTPException(status_code=404, detail="تهيئة الكاتالوج غير موجودة")

    return {
        "game_type": row.game_type,
        "short_description": row.short_description,
        "icon_token": row.icon_token,
        "accent_color": row.accent_color,
        "hero_variant": (
            row.hero_variant.value
            if hasattr(row.hero_variant, "value")
            else str(row.hero_variant)
        ),
        "card_variant": (
            row.card_variant.value
            if hasattr(row.card_variant, "value")
            else str(row.card_variant)
        ),
        "estimated_duration_sec": row.estimated_duration_sec,
        "featured": row.featured,
        "sort_order": row.sort_order,
        "availability_mode": (
            row.availability_mode.value
            if hasattr(row.availability_mode, "value")
            else str(row.availability_mode)
        ),
        "marketing_label": row.marketing_label,
        "expected_launch_at": (
            row.expected_launch_at.isoformat() if row.expected_launch_at else None
        ),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


@router.put("/api/admin/minigames/catalog-configs/{game_type}")
async def admin_upsert_catalog_config(
    game_type: str,
    body: CatalogConfigUpsertRequest,
    admin: AdminAccount,
):
    """Create or update a catalog config (admin only).

    Validates game_type exists in minigame_types.
    Enum values are validated against MinigameHeroVariant / MinigameCardVariant /
    MinigameCatalogAvailability. Invalid values return 400 with an Arabic message.
    """
    from app.core.enums import (  # noqa: PLC0415
        AuditActorType,
        MinigameCardVariant,
        MinigameCatalogAvailability,
        MinigameHeroVariant,
    )
    from app.modules.audit.service import write_audit  # noqa: PLC0415
    from app.modules.minigames.catalog_config_model import MinigameCatalogConfig  # noqa: PLC0415
    from app.modules.minigames.models import MinigameType  # noqa: PLC0415

    # Validate enums — raises 400 with Arabic message on failure
    try:
        hero = MinigameHeroVariant(body.hero_variant)
    except ValueError:
        valid = ", ".join(v.value for v in MinigameHeroVariant)
        raise HTTPException(status_code=400, detail=f"قيمة hero_variant غير صالحة. القيم المسموحة: {valid}")

    try:
        card = MinigameCardVariant(body.card_variant)
    except ValueError:
        valid = ", ".join(v.value for v in MinigameCardVariant)
        raise HTTPException(status_code=400, detail=f"قيمة card_variant غير صالحة. القيم المسموحة: {valid}")

    try:
        availability = MinigameCatalogAvailability(body.availability_mode)
    except ValueError:
        valid = ", ".join(v.value for v in MinigameCatalogAvailability)
        raise HTTPException(status_code=400, detail=f"قيمة availability_mode غير صالحة. القيم المسموحة: {valid}")

    async with async_session() as session:
        # Verify the game_type exists
        game_type_row = await session.get(MinigameType, game_type)
        if game_type_row is None:
            raise HTTPException(
                status_code=404,
                detail=f"نوع اللعبة '{game_type}' غير مسجل في المحرك",
            )

        existing = await session.get(MinigameCatalogConfig, game_type)
        was_created = existing is None
        before_state = None

        if existing is None:
            row = MinigameCatalogConfig(
                game_type=game_type,
                short_description=body.short_description,
                icon_token=body.icon_token,
                accent_color=body.accent_color,
                hero_variant=hero,
                card_variant=card,
                estimated_duration_sec=body.estimated_duration_sec,
                featured=body.featured,
                sort_order=body.sort_order,
                availability_mode=availability,
                marketing_label=body.marketing_label,
                expected_launch_at=body.expected_launch_at,
            )
            session.add(row)
        else:
            before_state = {
                "short_description": existing.short_description,
                "icon_token": existing.icon_token,
                "accent_color": existing.accent_color,
                "hero_variant": str(existing.hero_variant),
                "card_variant": str(existing.card_variant),
                "estimated_duration_sec": existing.estimated_duration_sec,
                "featured": existing.featured,
                "sort_order": existing.sort_order,
                "availability_mode": str(existing.availability_mode),
                "marketing_label": existing.marketing_label,
            }
            existing.short_description = body.short_description
            existing.icon_token = body.icon_token
            existing.accent_color = body.accent_color
            existing.hero_variant = hero
            existing.card_variant = card
            existing.estimated_duration_sec = body.estimated_duration_sec
            existing.featured = body.featured
            existing.sort_order = body.sort_order
            existing.availability_mode = availability
            existing.marketing_label = body.marketing_label
            existing.expected_launch_at = body.expected_launch_at
            row = existing

        after_state = {
            "short_description": row.short_description,
            "icon_token": row.icon_token,
            "accent_color": row.accent_color,
            "hero_variant": hero.value,
            "card_variant": card.value,
            "estimated_duration_sec": row.estimated_duration_sec,
            "featured": row.featured,
            "sort_order": row.sort_order,
            "availability_mode": availability.value,
            "marketing_label": row.marketing_label,
        }

        event_type = (
            "minigame_catalog_config_created"
            if was_created
            else "minigame_catalog_config_updated"
        )
        summary = (
            f"أنشأ تهيئة كاتالوج لـ {game_type}"
            if was_created
            else f"حدّث تهيئة كاتالوج لـ {game_type}"
        )

        await write_audit(
            session,
            actor_id=admin.id,
            actor_type=AuditActorType.ADMIN,
            subject_type="minigame_catalog_config",
            subject_id=None,
            event_type=event_type,
            summary=summary,
            before_state=before_state,
            after_state=after_state,
        )
        await session.commit()

    return {"message": "تم الحفظ", "game_type": game_type, "created": was_created}


@router.delete("/api/admin/minigames/catalog-configs/{game_type}")
async def admin_delete_catalog_config(game_type: str, admin: AdminAccount):
    """Delete a catalog config row (admin only)."""
    from app.core.enums import AuditActorType  # noqa: PLC0415
    from app.modules.audit.service import write_audit  # noqa: PLC0415
    from app.modules.minigames.catalog_config_model import MinigameCatalogConfig  # noqa: PLC0415

    async with async_session() as session:
        row = await session.get(MinigameCatalogConfig, game_type)
        if row is None:
            raise HTTPException(status_code=404, detail="تهيئة الكاتالوج غير موجودة")

        before_state = {
            "short_description": row.short_description,
            "availability_mode": str(row.availability_mode),
        }

        await session.delete(row)
        await write_audit(
            session,
            actor_id=admin.id,
            actor_type=AuditActorType.ADMIN,
            subject_type="minigame_catalog_config",
            subject_id=None,
            event_type="minigame_catalog_config_deleted",
            summary=f"حذف تهيئة كاتالوج لـ {game_type}",
            before_state=before_state,
            after_state=None,
        )
        await session.commit()

    return {"message": "تم الحذف", "game_type": game_type}
