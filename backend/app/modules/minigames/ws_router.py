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

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

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
    from app.modules.competitions.models import Membership  # noqa: PLC0415

    async with async_session() as session:
        result = await session.execute(
            select(Membership).where(
                Membership.account_id == account_id,
                Membership.competition_id == competition_id,
                Membership.status == "active",
            )
        )
        membership = result.scalar_one_or_none()

    if membership is None:
        return None

    return {
        "membership_id": membership.id,
        "alias": membership.alias,
        "balance": membership.balance,
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


# ---------------------------------------------------------------------------
# Queue + session creation
# ---------------------------------------------------------------------------


async def _handle_queue_match(
    websocket: WebSocket,
    lobby_key: str,
    competition_id: uuid.UUID,
    game_type: str,
    p1_id: uuid.UUID,
    p2_id: uuid.UUID,
) -> None:
    """Create a minigame session for a matched pair and notify both players."""
    from sqlalchemy import select  # noqa: PLC0415
    from app.core.database import async_session  # noqa: PLC0415
    from app.modules.competitions.models import Membership  # noqa: PLC0415
    from app.modules.minigames.session_service import create_session  # noqa: PLC0415
    from app.modules.minigames.settings_helper import get_minigame_settings  # noqa: PLC0415
    from app.core.enums import MinigameMatchType  # noqa: PLC0415

    try:
        async with async_session() as db:
            settings_snapshot = await get_minigame_settings(db, game_type, str(competition_id))

            buy_in_amount = int(settings_snapshot.get("buy_in_amount", 0))

            mg_session = await create_session(
                db,
                game_type=game_type,
                competition_id=competition_id,
                player_1_membership_id=p1_id,
                player_2_membership_id=p2_id,
                match_type=MinigameMatchType.RANKED,
                buy_in_amount=buy_in_amount,
                settings_snapshot=settings_snapshot,
            )
            await db.commit()
            await db.refresh(mg_session)

        session_id = str(mg_session.id)
        match_msg = {
            "type": "match_found",
            "session_id": session_id,
            "game_type": game_type,
            "competition_id": str(competition_id),
            "player_1_membership_id": str(p1_id),
            "player_2_membership_id": str(p2_id),
        }

        await manager.send_to_player(lobby_key, p1_id, match_msg)
        await manager.send_to_player(lobby_key, p2_id, match_msg)

    except Exception as exc:
        logger.exception("Failed to create session for match %s vs %s: %s", p1_id, p2_id, exc)
        # Re-queue both players so they can try again
        lobby_mgr.queue_join(lobby_key, p1_id)
        lobby_mgr.queue_join(lobby_key, p2_id)
        await _send_error(websocket, "SESSION_CREATE_FAILED", "فشل إنشاء الجلسة — يرجى المحاولة مجدداً")


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
    from app.modules.minigames.registry import get_plugin  # noqa: PLC0415

    envelope = msg.get("envelope", {})
    session_id_raw = msg.get("session_id")

    if not session_id_raw:
        await _send_error(websocket, "MISSING_SESSION_ID", "معرف الجلسة مفقود")
        return

    try:
        session_id = uuid.UUID(str(session_id_raw))
    except ValueError:
        await _send_error(websocket, "INVALID_SESSION_ID", "معرف الجلسة غير صالح")
        return

    action_id_raw = envelope.get("action_id")
    try:
        action_id = uuid.UUID(str(action_id_raw)) if action_id_raw else None
    except ValueError:
        action_id = None

    async with async_session() as db:
        # Load session
        result = await db.execute(
            select(MinigameSession).where(
                MinigameSession.id == session_id,
                MinigameSession.competition_id == competition_id,
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
                await websocket.send_json({"type": "action_ack", "result": cached, "cached": True})
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
        plugin = get_plugin(game_type)
        if plugin is None:
            await _send_error(websocket, "PLUGIN_NOT_FOUND", "نوع اللعبة غير معروف")
            return

        # Process action
        result_payload = await process_action(
            db,
            mg_session=mg_session,
            plugin=plugin,
            envelope=envelope,
        )
        await db.commit()

    # Notify sender
    lobby_key = f"{game_type}:{competition_id}"
    await websocket.send_json({"type": "action_ack", "result": result_payload, "cached": False})

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
            "result": result_payload,
        }
        # Try game session room first, fall back to lobby room
        game_room = f"session:{session_id}"
        sent = await manager.send_to_player(game_room, opponent_id, opponent_msg)
        if not sent:
            await manager.send_to_player(lobby_key, opponent_id, opponent_msg)


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
        lobby_mgr.join(lobby_key, membership_id, alias, stats=msg.get("stats"))
        manager.connect(lobby_key, membership_id, websocket)
        state = lobby_mgr.get_lobby_state(lobby_key)
        await websocket.send_json({"type": "lobby_state", "state": state})
        await manager.broadcast(
            lobby_key,
            {"type": "player_joined", "membership_id": str(membership_id), "alias": alias},
            exclude=membership_id,
        )

    elif msg_type == "lobby_leave":
        lobby_mgr.leave(lobby_key, membership_id)
        manager.disconnect(lobby_key, membership_id)
        await manager.broadcast(
            lobby_key,
            {"type": "player_left", "membership_id": str(membership_id), "alias": alias},
        )

    elif msg_type == "queue_join":
        lobby_mgr.queue_join(lobby_key, membership_id)
        await manager.broadcast(
            lobby_key,
            {"type": "status_changed", "membership_id": str(membership_id), "status": "in_queue"},
        )
        matched = lobby_mgr.try_match(lobby_key)
        if matched:
            p1_id, p2_id = matched
            await _handle_queue_match(websocket, lobby_key, competition_id, game_type, p1_id, p2_id)

    elif msg_type == "queue_leave":
        lobby_mgr.queue_leave(lobby_key, membership_id)
        await manager.broadcast(
            lobby_key,
            {"type": "status_changed", "membership_id": str(membership_id), "status": "idle"},
        )

    elif msg_type == "challenge_send":
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
        await manager.send_to_player(lobby_key, target_id, challenge_msg)

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
        # Clean up all rooms and lobby state
        manager.disconnect_all(membership_id)
        lobby_mgr.leave(lobby_key, membership_id)
