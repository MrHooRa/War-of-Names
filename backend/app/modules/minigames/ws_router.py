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
    matched_ids: list[uuid.UUID] | tuple[uuid.UUID, ...],
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


def _session_room_key(session_id: uuid.UUID) -> str:
    """Return the connection-manager room key for a session."""
    return f"session:{session_id}"


async def _send_session_state_snapshots(
    *,
    session_id: uuid.UUID,
    plugin,
    state: dict,
    participants: list[dict],
    current_turn_index: int | None,
    lobby_key: str,
    phase=None,
    revision: int | None = None,
    turn_number: int | None = None,
) -> None:
    """Send per-player ``game_state`` snapshots to each connected participant.

    ``participants`` is a list of dicts with ``membership_id``, ``slot_index``
    and ``reconnect_token`` keys (as returned by
    :func:`session_service.get_session_participants`). For each participant we
    build a plugin-rendered public view and deliver it to the session room
    first, falling back to the lobby room (reconnection case).
    """
    session_room = _session_room_key(session_id)
    phase_value = _enum_value(phase) if phase is not None else None
    for p in participants:
        mid = p["membership_id"]
        msg: dict = {
            "type": "game_state",
            "session_id": str(session_id),
            "slot_index": p["slot_index"],
            "current_turn_index": current_turn_index,
            "state": plugin.build_public_view(state, mid),
        }
        if phase_value is not None:
            msg["phase"] = phase_value
        if revision is not None:
            msg["revision"] = revision
        if turn_number is not None:
            msg["turn_number"] = turn_number
        if p.get("reconnect_token"):
            msg["reconnect_token"] = p["reconnect_token"]

        sent = await manager.send_to_player(session_room, mid, msg)
        if not sent:
            # Fallback: try to send via lobby room (reconnection case).
            await manager.send_to_player(lobby_key, mid, msg)


# ---------------------------------------------------------------------------
# Queue + session creation
# ---------------------------------------------------------------------------


async def _handle_queue_match(
    lobby_key: str,
    competition_id: uuid.UUID,
    game_type: str,
    matched_ids: list[uuid.UUID],
) -> None:
    """Handle a successful matchmaking pairing/grouping — create session, notify players.

    ``matched_ids`` is the ordered list of membership IDs returned from
    :meth:`LobbyManager.try_match`. Slot indices are assigned in the same
    order (``matched_ids[0]`` becomes slot 0, etc.). For 1v1 games the list
    will have length 2; future N-player games can pass longer lists.
    """
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
    from app.modules.minigames.session_service import (  # noqa: PLC0415
        create_session,
        get_session_participants,
        transition_session,
        validate_session_creation,
    )
    from app.modules.minigames.settings_helper import (  # noqa: PLC0415
        check_kill_switch,
        get_minigame_settings,
    )

    if not matched_ids:
        logger.warning("_handle_queue_match called with empty matched_ids")
        return

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
                    Membership.id.in_(matched_ids),
                    Membership.competition_id == competition_id,
                    Membership.status == MembershipStatus.ACTIVE,
                )
            )
            memberships = {membership.id: membership for membership in memberships_result.scalars().all()}
            if any(mid not in memberships for mid in matched_ids):
                raise ValueError("أحد اللاعبين لم يعد نشطاً في هذه المسابقة")

            buy_in_amount = int(settings_snapshot["minigame_buy_in"])
            daily_cap = int(settings_snapshot["minigame_daily_limit"])
            same_opponent_limit = int(settings_snapshot["minigame_same_opponent_limit"])

            player_errors: dict[uuid.UUID, str] = {}
            for membership_id in matched_ids:
                membership = memberships[membership_id]
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
                    # For 2-player games the opponent is the other player; for
                    # N-player games use the first non-self participant as a
                    # representative opponent for the "same opponent" check.
                    opponent_id = next(
                        (mid for mid in matched_ids if mid != membership_id),
                        None,
                    )
                    if opponent_id is not None:
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
                    membership_id for membership_id in matched_ids if membership_id not in player_errors
                )
                await _restore_matchmaking_state(
                    lobby_key,
                    matched_ids=matched_ids,
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
                player_membership_ids=list(matched_ids),
                season_id=season.id if season else None,
                cycle_id=cycle.id if cycle else None,
                match_type=MinigameMatchType.QUEUE,
                buy_in_amount=buy_in_amount,
                settings_snapshot=settings_snapshot,
                turn_duration_ms=int(settings_snapshot["minigame_turn_duration_sec"]) * 1000,
                grace_timer_ms=int(settings_snapshot["minigame_grace_timer_sec"]) * 1000,
            )

            # Load the freshly-created participants (slot_index + reconnect_token).
            participants = await get_session_participants(db, mg_session.id)

            init_config = {
                "session_id": str(mg_session.id),
                "competition_id": str(competition_id),
                "game_type": game_type,
                "participants": [
                    {
                        "membership_id": str(p["membership_id"]),
                        "slot_index": p["slot_index"],
                    }
                    for p in participants
                ],
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
        session_room = _session_room_key(mg_session.id)

        # Hook each connected player into the new session room and notify them.
        for p in participants:
            mid = p["membership_id"]
            ws = manager.get_websocket(lobby_key, mid)
            if ws is not None:
                manager.connect(session_room, mid, ws)

        for p in participants:
            mid = p["membership_id"]
            # Build an "others" list so clients can render opponent slots.
            others = [
                {
                    "membership_id": str(other["membership_id"]),
                    "slot_index": other["slot_index"],
                    "alias": memberships[other["membership_id"]].current_alias or "مجهول",
                }
                for other in participants
                if other["membership_id"] != mid
            ]
            match_msg: dict = {
                "type": "match_found",
                "session_id": session_id,
                "game_type": game_type,
                "competition_id": str(competition_id),
                "slot_index": p["slot_index"],
                "participants": others,
            }
            # Back-compat convenience for 1v1 clients expecting a single opponent.
            if len(others) == 1:
                match_msg["opponent_membership_id"] = others[0]["membership_id"]
                match_msg["opponent_alias"] = others[0]["alias"]
            await manager.send_to_player(session_room, mid, match_msg)

        await _send_session_state_snapshots(
            session_id=mg_session.id,
            plugin=plugin,
            state=mg_session.game_state,
            participants=participants,
            current_turn_index=mg_session.current_turn_index,
            lobby_key=lobby_key,
            phase=mg_session.phase,
            revision=mg_session.revision,
            turn_number=mg_session.turn_number,
        )

        await _broadcast_lobby_state(lobby_key)

    except Exception as exc:
        logger.exception("Failed to create session for match %s: %s", matched_ids, exc)
        await _restore_matchmaking_state(
            lobby_key,
            matched_ids=matched_ids,
            requeue_ids=tuple(matched_ids),
        )
        error_msg = "فشل إنشاء الجلسة — يرجى المحاولة مجدداً"
        for membership_id in matched_ids:
            await manager.send_to_player(
                lobby_key,
                membership_id,
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
    """Validate + process action via plugin, then notify every other participant."""
    from sqlalchemy import select  # noqa: PLC0415
    from app.core.database import async_session  # noqa: PLC0415
    from app.modules.minigames.models import MinigameSession  # noqa: PLC0415
    from app.modules.minigames.action_service import (  # noqa: PLC0415
        validate_action_envelope,
        check_idempotency,
        process_action,
    )
    from app.modules.minigames.registry import GameTypeRegistry  # noqa: PLC0415
    from app.modules.minigames.session_service import (  # noqa: PLC0415
        get_session_participants,
    )

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

        # Load participants once — used for validation, process_action, and
        # the post-processing broadcast loop below.
        participants = await get_session_participants(db, mg_session.id)

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
            current_turn_index=mg_session.current_turn_index,
            participants=participants,
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
                participants=participants,
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
    next_turn_index = result_payload.get(
        "next_turn_index", getattr(mg_session, "current_turn_index", None)
    )
    turn_number = result_payload.pop("_turn_number", getattr(mg_session, "turn_number", 0))
    actor_action = envelope.get("action", {}) or {}
    actor_id: uuid.UUID = membership_info["membership_id"]

    # Notify sender
    lobby_key = f"{game_type}:{competition_id}"
    session_room = _session_room_key(session_id)
    await websocket.send_json(
        {
            "type": "action_ack",
            "action_id": str(action_id) if action_id else None,
            "result": result_payload,
            "cached": False,
        }
    )

    # Notify every OTHER participant of the action, then push fresh snapshots
    # to all connected participants (including the actor).
    opponent_msg = {
        "type": "opponent_action",
        "session_id": str(session_id),
        "revision": result_payload.get("revision"),
        "action_type": actor_action.get("type"),
        "actor_membership_id": str(actor_id),
    }
    for p in participants:
        if p["membership_id"] == actor_id:
            continue
        sent = await manager.send_to_player(session_room, p["membership_id"], opponent_msg)
        if not sent:
            await manager.send_to_player(lobby_key, p["membership_id"], opponent_msg)

    await _send_session_state_snapshots(
        session_id=session_id,
        plugin=plugin,
        state=authoritative_state,
        participants=participants,
        current_turn_index=next_turn_index,
        lobby_key=lobby_key,
        phase=mg_session.phase,
        revision=result_payload["revision"],
        turn_number=turn_number,
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
            await _handle_queue_match(
                lobby_key,
                competition_id,
                game_type,
                matched_ids=matched,
            )
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
