"""WebSocket router for the minigame engine.

Endpoint: /ws/minigames/{competition_id}/{game_type}?token=<JWT>

Auth uses the same JWT secret as the REST API — token is passed as a query
parameter because browsers cannot set custom headers on WebSocket connections.

All DB and service imports are deferred to function bodies to keep startup fast
and allow unit tests to import this module without a running environment.

Connection/lobby managers are pure Python and safe to import at module level.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.modules.minigames.connection_manager import manager
from app.modules.minigames.lobby_manager import lobby_mgr

logger = logging.getLogger("minigames.ws")

# TODO(sprint-b): N-player refactor — several handlers below still reference
# mg_session.player_1_membership_id / player_2_membership_id / reconnect_token_p1
# / reconnect_token_p2 and pass them into create_session(). Those attribute
# reads will fail at runtime until Sprint B rewrites them against
# MinigameSessionParticipant. The file parses cleanly and is not exercised by
# any pure test.

ws_router = APIRouter()


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------


async def _authenticate_ws(websocket: WebSocket, token: str | None) -> dict | None:
    """Validate the JWT token and return {"account_id": UUID} or None.

    On failure the WebSocket is closed with code 4001 before returning None.
    """
    if not token:
        await websocket.close(code=4001)
        return None

    try:
        from jose import jwt, JWTError  # noqa: PLC0415
        from app.config import settings  # noqa: PLC0415

        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        account_id = uuid.UUID(payload["sub"])
        return {"account_id": account_id}
    except Exception:
        await websocket.close(code=4001)
        return None


# ---------------------------------------------------------------------------
# Membership resolution
# ---------------------------------------------------------------------------


async def _resolve_membership(account_id: uuid.UUID, competition_id: uuid.UUID) -> dict | None:
    """Query the DB for an active membership.

    Returns a dict with membership_id, alias, balance, is_bankrupt, or None
    when no active membership exists (WebSocket is NOT closed here — caller
    is responsible for closing with 4003).
    """
    from sqlalchemy import select  # noqa: PLC0415
    from app.core.database import async_session  # noqa: PLC0415
    from app.core.enums import MembershipStatus  # noqa: PLC0415
    from app.modules.competitions.models import Membership  # noqa: PLC0415

    async with async_session() as session:
        result = await session.execute(
            select(Membership).where(
                Membership.account_id == account_id,
                Membership.competition_id == competition_id,
                Membership.status == MembershipStatus.ACTIVE,
            )
        )
        membership = result.scalars().first()

    if membership is None:
        return None

    return {
        "membership_id": membership.id,
        "alias": membership.current_alias or "مجهول",
        "balance": membership.current_balance,
        "is_bankrupt": membership.is_bankrupt,
    }


# ---------------------------------------------------------------------------
# Error helper
# ---------------------------------------------------------------------------


async def _send_error(websocket: WebSocket, code: str, message_ar: str) -> None:
    """Send a structured error message over the WebSocket."""
    try:
        await websocket.send_json(
            {"type": "error", "code": code, "message": message_ar}
        )
    except Exception:
        pass


async def _broadcast_lobby_state(lobby_key: str, exclude: uuid.UUID | None = None) -> None:
    """Broadcast a fresh lobby snapshot to connected lobby members."""
    await manager.broadcast(
        lobby_key,
        {"type": "lobby_state", "state": lobby_mgr.get_lobby_state(lobby_key)},
        exclude=exclude,
    )


async def _get_active_season_cycle(session, competition_id: uuid.UUID):
    """Return the active (season, cycle) tuple for a competition."""
    from sqlalchemy import select  # noqa: PLC0415
    from app.core.enums import CycleStatus, SeasonStatus  # noqa: PLC0415
    from app.modules.competitions.models import Cycle, Season  # noqa: PLC0415

    season_result = await session.execute(
        select(Season).where(
            Season.competition_id == competition_id,
            Season.status == SeasonStatus.ACTIVE,
        ).limit(1)
    )
    season = season_result.scalars().first()
    if season is None:
        return None, None

    cycle_result = await session.execute(
        select(Cycle).where(
            Cycle.season_id == season.id,
            Cycle.status == CycleStatus.ACTIVE,
        ).limit(1)
    )
    cycle = cycle_result.scalars().first()
    return season, cycle


async def _restore_matchmaking_state(
    lobby_key: str,
    *,
    matched_ids: tuple[uuid.UUID, uuid.UUID],
    requeue_ids: tuple[uuid.UUID, ...] = (),
) -> None:
    """Reset matched players back to idle, optionally re-queueing safe players."""
    for membership_id in matched_ids:
        lobby_mgr.queue_leave(lobby_key, membership_id)
        if lobby_mgr.is_in_lobby(lobby_key, membership_id):
            lobby_mgr.set_status(lobby_key, membership_id, "idle")

    for membership_id in requeue_ids:
        if lobby_mgr.is_in_lobby(lobby_key, membership_id):
            lobby_mgr.queue_join(lobby_key, membership_id)

    await _broadcast_lobby_state(lobby_key)


def _enum_value(value):
    return value.value if hasattr(value, "value") else value


async def _send_session_state_snapshots(
    *,
    session_id: uuid.UUID,
    lobby_key: str,
    session_room: str,
    plugin,
    state: dict,
    phase,
    revision: int,
    current_turn,
    turn_number: int,
    player_1_membership_id: uuid.UUID,
    player_2_membership_id: uuid.UUID,
    reconnect_token_p1: str | None = None,
    reconnect_token_p2: str | None = None,
) -> None:
    current_turn_value = _enum_value(current_turn)
    phase_value = _enum_value(phase)
    p1_msg = {
        "type": "game_state",
        "session_id": str(session_id),
        "phase": phase_value,
        "revision": revision,
        "current_turn": current_turn_value,
        "turn_number": turn_number,
        "state": plugin.build_public_view(state, player_1_membership_id),
    }
    p2_msg = {
        "type": "game_state",
        "session_id": str(session_id),
        "phase": phase_value,
        "revision": revision,
        "current_turn": current_turn_value,
        "turn_number": turn_number,
        "state": plugin.build_public_view(state, player_2_membership_id),
    }
    if reconnect_token_p1 is not None:
        p1_msg["reconnect_token"] = reconnect_token_p1
    if reconnect_token_p2 is not None:
        p2_msg["reconnect_token"] = reconnect_token_p2

    sent_p1 = await manager.send_to_player(session_room, player_1_membership_id, p1_msg)
    if not sent_p1:
        await manager.send_to_player(lobby_key, player_1_membership_id, p1_msg)

    sent_p2 = await manager.send_to_player(session_room, player_2_membership_id, p2_msg)
    if not sent_p2:
        await manager.send_to_player(lobby_key, player_2_membership_id, p2_msg)


# ---------------------------------------------------------------------------
# Queue + session creation
# ---------------------------------------------------------------------------


async def _handle_queue_match(
    lobby_key: str,
    competition_id: uuid.UUID,
    game_type: str,
    p1_id: uuid.UUID,
    p2_id: uuid.UUID,
) -> None:
    """Create a minigame session for a matched pair and notify both players."""
    from sqlalchemy import select  # noqa: PLC0415
    from app.core.database import async_session  # noqa: PLC0415
    from app.core.enums import (  # noqa: PLC0415
        MembershipStatus,
        MinigameMatchType,
        MinigameSessionPhase as Phase,
        MinigameTypeStatus,
    )
    from app.modules.competitions.models import Membership  # noqa: PLC0415
    from app.modules.minigames.models import MinigameType  # noqa: PLC0415
    from app.modules.minigames.policy_service import (  # noqa: PLC0415
        count_opponent_matches_this_cycle,
        count_player_matches_today,
        run_all_checks,
    )
    from app.modules.minigames.registry import GameTypeRegistry  # noqa: PLC0415
    from app.modules.minigames.session_service import create_session  # noqa: PLC0415
    from app.modules.minigames.session_service import (  # noqa: PLC0415
        transition_session,
        validate_session_creation,
    )
    from app.modules.minigames.settings_helper import (  # noqa: PLC0415
        check_kill_switch,
        get_minigame_settings,
    )

    try:
        async with async_session() as db:
            game_type_result = await db.execute(
                select(MinigameType).where(MinigameType.id == game_type)
            )
            game_type_obj = game_type_result.scalars().first()
            if game_type_obj is None:
                raise ValueError(f"نوع اللعبة '{game_type}' غير موجود")
            if game_type_obj.status != MinigameTypeStatus.ACTIVE:
                raise ValueError("هذه اللعبة غير متاحة حالياً")

            plugin = GameTypeRegistry.get(game_type)
            if plugin is None:
                raise ValueError("نوع اللعبة غير مسجل في المحرك")

            season, cycle = await _get_active_season_cycle(db, competition_id)

            settings_snapshot = await get_minigame_settings(
                db,
                competition_id=competition_id,
                season_id=season.id if season else None,
                cycle_id=cycle.id if cycle else None,
            )

            kill_switch = check_kill_switch(settings_snapshot.get("minigame_kill_switch"))
            if not settings_snapshot.get("minigame_enabled"):
                raise ValueError("الألعاب المصغرة غير مفعلة في هذه المسابقة")
            if not kill_switch.can_matchmake:
                raise ValueError(kill_switch.message_ar or "التوفيق معطل حالياً")

            memberships_result = await db.execute(
                select(Membership).where(
                    Membership.id.in_([p1_id, p2_id]),
                    Membership.competition_id == competition_id,
                    Membership.status == MembershipStatus.ACTIVE,
                )
            )
            memberships = {membership.id: membership for membership in memberships_result.scalars().all()}
            if p1_id not in memberships or p2_id not in memberships:
                raise ValueError("أحد اللاعبين لم يعد نشطاً في هذه المسابقة")

            buy_in_amount = int(settings_snapshot["minigame_buy_in"])
            daily_cap = int(settings_snapshot["minigame_daily_limit"])
            same_opponent_limit = int(settings_snapshot["minigame_same_opponent_limit"])

            player_errors: dict[uuid.UUID, str] = {}
            for membership_id, membership in memberships.items():
                plugin_status = (
                    game_type_obj.status.value
                    if hasattr(game_type_obj.status, "value")
                    else str(game_type_obj.status)
                )
                creation_errors = validate_session_creation(
                    game_type_id=game_type,
                    plugin_exists=True,
                    plugin_status=plugin_status,
                    player_balance=membership.current_balance,
                    buy_in_amount=buy_in_amount,
                    is_bankrupt=membership.is_bankrupt,
                )

                matches_today = await count_player_matches_today(
                    db,
                    membership_id=membership.id,
                    game_type=game_type,
                    competition_id=competition_id,
                )
                matches_with_opponent = 0
                if cycle is not None:
                    opponent_id = p2_id if membership_id == p1_id else p1_id
                    matches_with_opponent = await count_opponent_matches_this_cycle(
                        db,
                        membership_id=membership.id,
                        opponent_membership_id=opponent_id,
                        game_type=game_type,
                        competition_id=competition_id,
                        cycle_id=cycle.id,
                    )

                policy_blocks = run_all_checks(
                    matches_today=matches_today,
                    daily_cap=daily_cap,
                    matches_with_opponent_this_cycle=matches_with_opponent,
                    same_opponent_limit=same_opponent_limit,
                    player_balance=membership.current_balance,
                    buy_in_amount=buy_in_amount,
                    is_bankrupt=membership.is_bankrupt,
                )

                error_messages = creation_errors + [block.message_ar for block in policy_blocks]
                if error_messages:
                    player_errors[membership_id] = error_messages[0]

            if player_errors:
                requeue_ids = tuple(
                    membership_id for membership_id in (p1_id, p2_id) if membership_id not in player_errors
                )
                await _restore_matchmaking_state(
                    lobby_key,
                    matched_ids=(p1_id, p2_id),
                    requeue_ids=requeue_ids,
                )
                for membership_id, message_ar in player_errors.items():
                    await manager.send_to_player(
                        lobby_key,
                        membership_id,
                        {"type": "error", "code": "MATCHMAKING_BLOCKED", "message": message_ar},
                    )
                return

            mg_session = await create_session(
                db,
                game_type=game_type,
                competition_id=competition_id,
                player_1_membership_id=p1_id,
                player_2_membership_id=p2_id,
                season_id=season.id if season else None,
                cycle_id=cycle.id if cycle else None,
                match_type=MinigameMatchType.QUEUE,
                buy_in_amount=buy_in_amount,
                settings_snapshot=settings_snapshot,
                turn_duration_ms=int(settings_snapshot["minigame_turn_duration_sec"]) * 1000,
                grace_timer_ms=int(settings_snapshot["minigame_grace_timer_sec"]) * 1000,
            )

            init_config = {
                "session_id": str(mg_session.id),
                "competition_id": str(competition_id),
                "game_type": game_type,
                "player_1_membership_id": str(p1_id),
                "player_2_membership_id": str(p2_id),
                "buy_in": buy_in_amount,
                "settings": settings_snapshot,
            }
            if game_type == "mutaraha":
                from app.modules.minigames.mutaraha.service import load_active_word_bank  # noqa: PLC0415

                init_config["word_bank_words"] = await load_active_word_bank(db)

            initial_state = plugin.init_session_state(init_config)
            if not isinstance(initial_state, dict):
                raise ValueError("الحالة الأولية للعبة غير صالحة")

            mg_session.game_state = initial_state
            await db.flush()

            for phase in (Phase.WAITING, Phase.READY, Phase.IN_PROGRESS):
                mg_session = await transition_session(
                    db,
                    session_id=mg_session.id,
                    expected_revision=mg_session.revision,
                    target_phase=phase,
                    actor_type="system",
                )
                if mg_session is None:
                    raise RuntimeError("فشل تهيئة الجلسة بسبب تعارض متزامن")

            await db.commit()
            await db.refresh(mg_session)

        session_id = str(mg_session.id)
        session_room = f"session:{session_id}"
        p1_ws = manager.get_websocket(lobby_key, p1_id)
        p2_ws = manager.get_websocket(lobby_key, p2_id)
        if p1_ws is not None:
            manager.connect(session_room, p1_id, p1_ws)
        if p2_ws is not None:
            manager.connect(session_room, p2_id, p2_ws)

        p1_alias = memberships[p1_id].current_alias or "مجهول"
        p2_alias = memberships[p2_id].current_alias or "مجهول"

        p1_match_msg = {
            "type": "match_found",
            "session_id": session_id,
            "game_type": game_type,
            "competition_id": str(competition_id),
            "opponent_membership_id": str(p2_id),
            "opponent_alias": p2_alias,
        }
        p2_match_msg = {
            "type": "match_found",
            "session_id": session_id,
            "game_type": game_type,
            "competition_id": str(competition_id),
            "opponent_membership_id": str(p1_id),
            "opponent_alias": p1_alias,
        }

        await manager.send_to_player(session_room, p1_id, p1_match_msg)
        await manager.send_to_player(session_room, p2_id, p2_match_msg)
        await _send_session_state_snapshots(
            session_id=mg_session.id,
            lobby_key=lobby_key,
            session_room=session_room,
            plugin=plugin,
            state=mg_session.game_state,
            phase=mg_session.phase,
            revision=mg_session.revision,
            current_turn=mg_session.current_turn,
            turn_number=mg_session.turn_number,
            player_1_membership_id=p1_id,
            player_2_membership_id=p2_id,
            reconnect_token_p1=mg_session.reconnect_token_p1,
            reconnect_token_p2=mg_session.reconnect_token_p2,
        )

        await _broadcast_lobby_state(lobby_key)

    except Exception as exc:
        logger.exception("Failed to create session for match %s vs %s: %s", p1_id, p2_id, exc)
        await _restore_matchmaking_state(
            lobby_key,
            matched_ids=(p1_id, p2_id),
            requeue_ids=(p1_id, p2_id),
        )
        error_msg = "فشل إنشاء الجلسة — يرجى المحاولة مجدداً"
        await manager.send_to_player(
            lobby_key,
            p1_id,
            {"type": "error", "code": "SESSION_CREATE_FAILED", "message": error_msg},
        )
        await manager.send_to_player(
            lobby_key,
            p2_id,
            {"type": "error", "code": "SESSION_CREATE_FAILED", "message": error_msg},
        )


# ---------------------------------------------------------------------------
# Action submit
# ---------------------------------------------------------------------------


async def _handle_action_submit(
    websocket: WebSocket,
    msg: dict,
    competition_id: uuid.UUID,
    game_type: str,
    membership_info: dict,
) -> None:
    """Validate + process action via plugin then notify opponent."""
    from sqlalchemy import select  # noqa: PLC0415
    from app.core.database import async_session  # noqa: PLC0415
    from app.modules.minigames.models import MinigameSession  # noqa: PLC0415
    from app.modules.minigames.action_service import (  # noqa: PLC0415
        validate_action_envelope,
        check_idempotency,
        process_action,
    )
    from app.modules.minigames.registry import GameTypeRegistry  # noqa: PLC0415

    envelope = msg.get("envelope", {})
    session_id_raw = msg.get("session_id") or envelope.get("session_id")

    if not session_id_raw:
        await _send_error(websocket, "MISSING_SESSION_ID", "معرف الجلسة مفقود")
        return

    try:
        session_id = uuid.UUID(str(session_id_raw))
    except ValueError:
        await _send_error(websocket, "INVALID_SESSION_ID", "معرف الجلسة غير صالح")
        return

    envelope["session_id"] = session_id
    envelope["actor_membership_id"] = membership_info["membership_id"]
    if "state_revision" in envelope:
        try:
            envelope["state_revision"] = int(envelope["state_revision"])
        except (TypeError, ValueError):
            pass
    if "client_seq" in envelope:
        try:
            envelope["client_seq"] = int(envelope["client_seq"])
        except (TypeError, ValueError):
            pass

    action_id_raw = envelope.get("action_id")
    try:
        action_id = uuid.UUID(str(action_id_raw)) if action_id_raw else None
    except ValueError:
        await _send_error(websocket, "INVALID_ACTION_ID", "معرف الإجراء غير صالح")
        return
    if action_id is not None:
        envelope["action_id"] = action_id

    async with async_session() as db:
        # Load session
        result = await db.execute(
            select(MinigameSession).where(
                MinigameSession.id == session_id,
                MinigameSession.competition_id == competition_id,
                MinigameSession.game_type == game_type,
            )
        )
        mg_session = result.scalar_one_or_none()

        if mg_session is None:
            await _send_error(websocket, "SESSION_NOT_FOUND", "الجلسة غير موجودة")
            return

        # Check idempotency first
        if action_id:
            cached = await check_idempotency(db, action_id)
            if cached is not None:
                await websocket.send_json(
                    {
                        "type": "action_ack",
                        "action_id": str(action_id),
                        "result": cached,
                        "cached": True,
                    }
                )
                return

        # Validate envelope (pure)
        error = validate_action_envelope(
            envelope=envelope,
            session_phase=mg_session.phase,
            session_revision=mg_session.revision,
            current_turn=mg_session.current_turn,
            player_1_membership_id=mg_session.player_1_membership_id,
            player_2_membership_id=mg_session.player_2_membership_id,
        )
        if error:
            await _send_error(websocket, error.code, error.message_ar)
            return

        # Load plugin
        plugin = GameTypeRegistry.get(game_type)
        if plugin is None:
            await _send_error(websocket, "PLUGIN_NOT_FOUND", "نوع اللعبة غير معروف")
            return

        # Process action
        try:
            result_payload = await process_action(
                db,
                mg_session=mg_session,
                plugin=plugin,
                envelope=envelope,
            )
            await db.commit()
        except ValueError as exc:
            await db.rollback()
            await _send_error(websocket, "INVALID_ACTION", str(exc))
            return
        except RuntimeError as exc:
            await db.rollback()
            await _send_error(websocket, "STALE_STATE", str(exc))
            return

    authoritative_state = result_payload.pop("_state", getattr(mg_session, "game_state", {}))
    current_turn = result_payload.pop("_current_turn", getattr(mg_session, "current_turn", None))
    turn_number = result_payload.pop("_turn_number", getattr(mg_session, "turn_number", 0))
    actor_action = envelope.get("action", {}) or {}

    # Notify sender
    lobby_key = f"{game_type}:{competition_id}"
    session_room = f"session:{session_id}"
    await websocket.send_json(
        {
            "type": "action_ack",
            "action_id": str(action_id) if action_id else None,
            "result": result_payload,
            "cached": False,
        }
    )

    # Notify opponent if it's a 1v1 game
    if mg_session.player_2_membership_id:
        my_id = membership_info["membership_id"]
        opponent_id = (
            mg_session.player_2_membership_id
            if my_id == mg_session.player_1_membership_id
            else mg_session.player_1_membership_id
        )
        opponent_msg = {
            "type": "opponent_action",
            "session_id": str(session_id),
            "revision": result_payload.get("revision"),
            "action_type": actor_action.get("type"),
            "actor_membership_id": str(my_id),
        }
        sent = await manager.send_to_player(session_room, opponent_id, opponent_msg)
        if not sent:
            await manager.send_to_player(lobby_key, opponent_id, opponent_msg)
        await _send_session_state_snapshots(
            session_id=session_id,
            lobby_key=lobby_key,
            session_room=session_room,
            plugin=plugin,
            state=authoritative_state,
            phase=mg_session.phase,
            revision=result_payload["revision"],
            current_turn=current_turn,
            turn_number=turn_number,
            player_1_membership_id=mg_session.player_1_membership_id,
            player_2_membership_id=mg_session.player_2_membership_id,
        )


# ---------------------------------------------------------------------------
# Message dispatcher
# ---------------------------------------------------------------------------


async def _handle_message(
    websocket: WebSocket,
    msg: dict,
    competition_id: uuid.UUID,
    game_type: str,
    membership_info: dict,
) -> None:
    """Dispatch an incoming WebSocket message by its type field."""
    msg_type = msg.get("type")
    membership_id: uuid.UUID = membership_info["membership_id"]
    alias: str = membership_info["alias"]
    lobby_key = f"{game_type}:{competition_id}"

    if msg_type == "lobby_join":
        was_in_lobby = lobby_mgr.is_in_lobby(lobby_key, membership_id)
        lobby_mgr.join(lobby_key, membership_id, alias, stats=msg.get("stats"))
        manager.connect(lobby_key, membership_id, websocket)
        state = lobby_mgr.get_lobby_state(lobby_key)
        await websocket.send_json({"type": "lobby_state", "state": state})
        if not was_in_lobby:
            await manager.broadcast(
                lobby_key,
                {"type": "player_joined", "membership_id": str(membership_id), "alias": alias},
                exclude=membership_id,
            )
        await _broadcast_lobby_state(lobby_key, exclude=membership_id)

    elif msg_type == "lobby_leave":
        lobby_mgr.leave(lobby_key, membership_id)
        manager.disconnect(lobby_key, membership_id)
        await manager.broadcast(
            lobby_key,
            {"type": "player_left", "membership_id": str(membership_id), "alias": alias},
        )
        await _broadcast_lobby_state(lobby_key)

    elif msg_type == "queue_join":
        if not lobby_mgr.is_in_lobby(lobby_key, membership_id) or not manager.is_connected(lobby_key, membership_id):
            await _send_error(websocket, "NOT_IN_LOBBY", "يجب دخول اللوبي قبل الطابور")
            return
        lobby_mgr.queue_join(lobby_key, membership_id)
        await manager.broadcast(
            lobby_key,
            {"type": "status_changed", "membership_id": str(membership_id), "status": "in_queue"},
        )
        matched = lobby_mgr.try_match(lobby_key)
        if matched:
            p1_id, p2_id = matched
            await _handle_queue_match(lobby_key, competition_id, game_type, p1_id, p2_id)
        else:
            await _broadcast_lobby_state(lobby_key)

    elif msg_type == "queue_leave":
        lobby_mgr.queue_leave(lobby_key, membership_id)
        await manager.broadcast(
            lobby_key,
            {"type": "status_changed", "membership_id": str(membership_id), "status": "idle"},
        )
        await _broadcast_lobby_state(lobby_key)

    elif msg_type == "challenge_send":
        if not lobby_mgr.is_in_lobby(lobby_key, membership_id) or not manager.is_connected(lobby_key, membership_id):
            await _send_error(websocket, "NOT_IN_LOBBY", "يجب دخول اللوبي قبل إرسال التحدي")
            return
        target_id_raw = msg.get("target_membership_id")
        if not target_id_raw:
            await _send_error(websocket, "MISSING_TARGET", "معرف المستهدف مفقود")
            return
        try:
            target_id = uuid.UUID(str(target_id_raw))
        except ValueError:
            await _send_error(websocket, "INVALID_TARGET", "معرف المستهدف غير صالح")
            return
        lobby_mgr.set_status(lobby_key, membership_id, "challenging")
        challenge_msg = {
            "type": "challenge_received",
            "from_membership_id": str(membership_id),
            "from_alias": alias,
            "game_type": game_type,
        }
        sent = await manager.send_to_player(lobby_key, target_id, challenge_msg)
        if not sent:
            lobby_mgr.set_status(lobby_key, membership_id, "idle")
            await _send_error(websocket, "TARGET_OFFLINE", "اللاعب المستهدف غير متصل")
            await _broadcast_lobby_state(lobby_key)
            return
        await _broadcast_lobby_state(lobby_key)

    elif msg_type == "heartbeat":
        await websocket.send_json({"type": "heartbeat_ack"})

    elif msg_type == "action_submit":
        await _handle_action_submit(websocket, msg, competition_id, game_type, membership_info)

    else:
        await _send_error(websocket, "UNKNOWN_MESSAGE_TYPE", f"نوع الرسالة '{msg_type}' غير معروف")


# ---------------------------------------------------------------------------
# Main WebSocket endpoint
# ---------------------------------------------------------------------------


@ws_router.websocket("/ws/minigames/{competition_id}/{game_type}")
async def minigame_websocket(
    websocket: WebSocket,
    competition_id: uuid.UUID,
    game_type: str,
    token: str | None = Query(default=None),
) -> None:
    """Main WebSocket endpoint for minigame lobby, queue, and action streaming."""
    await websocket.accept()

    # 1. Authenticate
    auth = await _authenticate_ws(websocket, token)
    if auth is None:
        return  # Socket already closed with 4001

    account_id: uuid.UUID = auth["account_id"]

    # 2. Resolve membership
    membership_info = await _resolve_membership(account_id, competition_id)
    if membership_info is None:
        await websocket.close(code=4003)
        return

    membership_id: uuid.UUID = membership_info["membership_id"]
    lobby_key = f"{game_type}:{competition_id}"

    logger.info(
        "WS connected: account=%s membership=%s lobby=%s",
        account_id,
        membership_id,
        lobby_key,
    )

    try:
        while True:
            data = await websocket.receive_json()
            await _handle_message(websocket, data, competition_id, game_type, membership_info)

    except WebSocketDisconnect:
        logger.info("WS disconnected: membership=%s lobby=%s", membership_id, lobby_key)

    except Exception as exc:
        logger.exception("WS error for membership=%s: %s", membership_id, exc)

    finally:
        # Clean up lobby presence first so remaining lobby members see the disconnect.
        if lobby_mgr.is_in_lobby(lobby_key, membership_id) or manager.is_connected(lobby_key, membership_id):
            lobby_mgr.leave(lobby_key, membership_id)
            manager.disconnect(lobby_key, membership_id)
            await manager.broadcast(
                lobby_key,
                {"type": "player_left", "membership_id": str(membership_id), "alias": membership_info["alias"]},
            )
            await _broadcast_lobby_state(lobby_key)

        # Clean up any non-lobby rooms (for example session rooms).
        manager.disconnect_all(membership_id)
