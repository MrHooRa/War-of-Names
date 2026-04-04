"""WebSocket router for the minigame engine.

Endpoint: /ws/minigames/{competition_id}/{game_type}?token=<JWT>

Auth uses the same JWT secret as the REST API — token is passed as a query
parameter because browsers cannot set custom headers on WebSocket connections.

All DB and service imports are deferred to function bodies to keep startup fast
and allow unit tests to import this module without a running environment.

Connection/lobby managers are pure Python and safe to import at module level.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.modules.minigames.connection_manager import manager
from app.modules.minigames.lobby_manager import lobby_mgr
from app.modules.minigames.runtime_state import (
    resolve_state_timer_duration_ms,
    stamp_phase_deadlines,
)

logger = logging.getLogger("minigames.ws")

ws_router = APIRouter()

ACTION_RATE_LIMIT_PER_SECOND = 5
ACTION_RATE_LIMIT_WINDOW_SEC = 1.0

_action_windows: dict[tuple[str, uuid.UUID], list[float]] = {}
_grace_tasks: dict[uuid.UUID, asyncio.Task] = {}
_session_timer_tasks: dict[uuid.UUID, asyncio.Task] = {}
_challenge_tasks: dict[uuid.UUID, asyncio.Task] = {}
_queue_tasks: dict[tuple[str, uuid.UUID], asyncio.Task] = {}


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


def _check_action_rate_limit(session_id: uuid.UUID, membership_id: uuid.UUID) -> bool:
    """Allow a bounded number of actions per player per second."""
    now = time.monotonic()
    window_key = (str(session_id), membership_id)
    timestamps = _action_windows.setdefault(window_key, [])
    fresh_cutoff = now - ACTION_RATE_LIMIT_WINDOW_SEC
    timestamps[:] = [stamp for stamp in timestamps if stamp >= fresh_cutoff]
    if len(timestamps) >= ACTION_RATE_LIMIT_PER_SECOND:
        return False
    timestamps.append(now)
    return True


def _clear_action_rate_window(session_id: uuid.UUID, membership_id: uuid.UUID) -> None:
    _action_windows.pop((str(session_id), membership_id), None)


def _clear_all_action_rate_windows(membership_id: uuid.UUID) -> None:
    stale_keys = [
        key
        for key in _action_windows
        if key[1] == membership_id
    ]
    for key in stale_keys:
        _action_windows.pop(key, None)


def _cancel_session_timer(session_id: uuid.UUID) -> None:
    task = _session_timer_tasks.pop(session_id, None)
    if task is not None:
        task.cancel()


def _queue_task_key(lobby_key: str, membership_id: uuid.UUID) -> tuple[str, uuid.UUID]:
    return lobby_key, membership_id


def _cancel_queue_expiry(lobby_key: str, membership_id: uuid.UUID) -> None:
    task = _queue_tasks.pop(_queue_task_key(lobby_key, membership_id), None)
    if task is not None:
        task.cancel()


def _cancel_challenge_expiry(session_id: uuid.UUID) -> None:
    task = _challenge_tasks.pop(session_id, None)
    if task is not None:
        task.cancel()


async def _schedule_queue_expiry(
    *,
    lobby_key: str,
    membership_id: uuid.UUID,
    delay_seconds: float,
) -> None:
    """Expire a queued player if they remain unmatched beyond the queue timeout."""

    async def _runner() -> None:
        try:
            await asyncio.sleep(max(0.0, delay_seconds))
            if not lobby_mgr.is_in_lobby(lobby_key, membership_id):
                return
            if not lobby_mgr.is_queued(lobby_key, membership_id):
                return
            lobby_mgr.queue_leave(lobby_key, membership_id)
            await manager.send_to_player(
                lobby_key,
                membership_id,
                {"type": "queue_expired", "membership_id": str(membership_id)},
            )
            await _broadcast_lobby_state(lobby_key)
        except asyncio.CancelledError:
            return
        finally:
            _queue_tasks.pop(_queue_task_key(lobby_key, membership_id), None)

    _cancel_queue_expiry(lobby_key, membership_id)
    _queue_tasks[_queue_task_key(lobby_key, membership_id)] = asyncio.create_task(_runner())


async def _schedule_challenge_expiry(
    *,
    session_id: uuid.UUID,
    competition_id: uuid.UUID,
    game_type: str,
    delay_seconds: float,
) -> None:
    """Expire a pending challenge when it is not answered before its deadline."""

    async def _runner() -> None:
        try:
            await asyncio.sleep(max(0.0, delay_seconds))
            await _resolve_challenge_expiry(
                session_id=session_id,
                competition_id=competition_id,
                game_type=game_type,
            )
        except asyncio.CancelledError:
            return
        finally:
            _challenge_tasks.pop(session_id, None)

    _cancel_challenge_expiry(session_id)
    _challenge_tasks[session_id] = asyncio.create_task(_runner())


async def _send_action_reject(
    websocket: WebSocket,
    *,
    action_id,
    code: str,
    message_ar: str,
    current_state: dict | None = None,
) -> None:
    """Send a structured action rejection payload."""
    payload = {
        "type": "action_reject",
        "action_id": str(action_id) if action_id else None,
        "reason": {
            "code": code,
            "message": message_ar,
        },
    }
    if current_state is not None:
        payload["current_state"] = current_state
    try:
        await websocket.send_json(payload)
    except Exception:
        pass


async def _send_lobby_update(
    lobby_key: str,
    *,
    update_type: str,
    data: dict,
    exclude: uuid.UUID | None = None,
) -> None:
    """Broadcast a BRD-style differential lobby update."""
    await manager.broadcast(
        lobby_key,
        {
            "type": "lobby_update",
            "update_type": update_type,
            "data": data,
        },
        exclude=exclude,
    )


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


def _build_public_state_message(
    *,
    session_id: uuid.UUID,
    plugin,
    state: dict,
    participant: dict,
    current_turn_index: int | None,
    phase=None,
    revision: int | None = None,
    turn_number: int | None = None,
    message_type: str = "game_state",
) -> dict:
    """Build a per-player state message."""
    phase_value = _enum_value(phase) if phase is not None else None
    msg: dict = {
        "type": message_type,
        "session_id": str(session_id),
        "slot_index": participant["slot_index"],
        "current_turn_index": current_turn_index,
        "state": plugin.build_public_view(state, participant["membership_id"]),
    }
    if phase_value is not None:
        msg["phase"] = phase_value
    if revision is not None:
        msg["revision"] = revision
    if turn_number is not None:
        msg["turn_number"] = turn_number
    if participant.get("reconnect_token"):
        msg["reconnect_token"] = participant["reconnect_token"]
    return msg


async def _send_to_participant(
    *,
    session_id: uuid.UUID,
    lobby_key: str,
    membership_id: uuid.UUID,
    message: dict,
) -> None:
    """Send a message via the session room first, then fall back to lobby."""
    sent = await manager.send_to_player(_session_room_key(session_id), membership_id, message)
    if not sent:
        await manager.send_to_player(lobby_key, membership_id, message)


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
    for p in participants:
        msg = _build_public_state_message(
            session_id=session_id,
            plugin=plugin,
            state=state,
            participant=p,
            current_turn_index=current_turn_index,
            phase=phase,
            revision=revision,
            turn_number=turn_number,
            message_type="game_state",
        )
        await _send_to_participant(
            session_id=session_id,
            lobby_key=lobby_key,
            membership_id=p["membership_id"],
            message=msg,
        )


async def _send_state_patches(
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
    """Broadcast BRD-style state patches using full sanitized deltas."""
    phase_value = _enum_value(phase) if phase is not None else None
    for participant in participants:
        patch_msg = {
            "type": "state_patch",
            "session_id": str(session_id),
            "revision": revision,
            "delta": plugin.build_public_view(state, participant["membership_id"]),
            "turn_info": {
                "phase": phase_value,
                "current_turn_index": current_turn_index,
                "turn_number": turn_number,
            },
        }
        await _send_to_participant(
            session_id=session_id,
            lobby_key=lobby_key,
            membership_id=participant["membership_id"],
            message=patch_msg,
        )


async def _broadcast_transition_event(
    *,
    session_id: uuid.UUID,
    participants: list[dict],
    lobby_key: str,
    from_phase,
    to_phase,
    data: dict | None = None,
) -> None:
    """Broadcast a phase transition event to all participants."""
    message = {
        "type": "transition_event",
        "session_id": str(session_id),
        "from_phase": _enum_value(from_phase),
        "to_phase": _enum_value(to_phase),
        "data": data or {},
    }
    for participant in participants:
        await _send_to_participant(
            session_id=session_id,
            lobby_key=lobby_key,
            membership_id=participant["membership_id"],
            message=message,
        )


async def _broadcast_timer_sync(
    *,
    session_id: uuid.UUID,
    participants: list[dict],
    lobby_key: str,
    remaining_ms: int | None,
    phase=None,
) -> None:
    """Broadcast server-authoritative timer metadata."""
    if remaining_ms is None:
        return
    message = {
        "type": "timer_sync",
        "session_id": str(session_id),
        "phase": _enum_value(phase) if phase is not None else None,
        "remaining_ms": max(0, int(remaining_ms)),
        "server_time": datetime.utcnow().isoformat(),
    }
    for participant in participants:
        await _send_to_participant(
            session_id=session_id,
            lobby_key=lobby_key,
            membership_id=participant["membership_id"],
            message=message,
        )


def _remaining_turn_ms(mg_session) -> int | None:
    """Return remaining turn time for the current phase, if any."""
    if not getattr(mg_session, "turn_started_at", None):
        return None
    duration_ms = getattr(mg_session, "turn_duration_ms", None)
    if duration_ms is None:
        return None
    from app.core.utils import now_riyadh_naive  # noqa: PLC0415

    elapsed_ms = int((now_riyadh_naive() - mg_session.turn_started_at).total_seconds() * 1000)
    return max(0, int(duration_ms) - elapsed_ms)


def _remaining_grace_ms(mg_session) -> int | None:
    """Return remaining grace time for a paused session."""
    pause_info = {}
    if isinstance(getattr(mg_session, "game_state", None), dict):
        pause_info = mg_session.game_state.get("pause_info", {}) or {}
    deadline_raw = pause_info.get("grace_deadline_at")
    if not deadline_raw:
        return None
    from app.core.utils import now_riyadh_naive  # noqa: PLC0415

    try:
        deadline = datetime.fromisoformat(deadline_raw)
    except ValueError:
        return None
    remaining_ms = int((deadline - now_riyadh_naive()).total_seconds() * 1000)
    return max(0, remaining_ms)


def _set_lobby_status_for_participants(
    lobby_key: str,
    participants: list[dict],
    *,
    status: str,
) -> None:
    """Update lobby player statuses for connected participants."""
    for participant in participants:
        membership_id = participant["membership_id"]
        if lobby_mgr.is_in_lobby(lobby_key, membership_id):
            lobby_mgr.set_status(lobby_key, membership_id, status)


async def _broadcast_settlement_result(
    *,
    session_id: uuid.UUID,
    participants: list[dict],
    lobby_key: str,
    participant_results: list[dict],
    stats_update: dict,
) -> None:
    """Broadcast settlement data to all session participants."""
    result_by_mid = {}
    for result in participant_results:
        membership_id = str(result.get("membership_id")) if result.get("membership_id") else None
        if membership_id:
            result_by_mid[membership_id] = result

    for participant in participants:
        membership_id = str(participant["membership_id"])
        player_result = result_by_mid.get(membership_id, {})
        await _send_to_participant(
            session_id=session_id,
            lobby_key=lobby_key,
            membership_id=participant["membership_id"],
            message={
                "type": "settlement_result",
                "session_id": str(session_id),
                "winner_membership_id": next(
                    (
                        result.get("membership_id")
                        for result in participant_results
                        if result.get("rank") == 1
                    ),
                    None,
                ),
                "payout": player_result.get("payout", 0),
                "rank": player_result.get("rank"),
                "stats_update": stats_update.get(membership_id, {}),
            },
        )


# ---------------------------------------------------------------------------
# Timeout helpers
# ---------------------------------------------------------------------------


async def _persist_system_state_update(
    db,
    *,
    mg_session,
    new_state: dict,
    current_turn_index: int | None,
    turn_number: int,
    event_type: str,
    action_type: str,
    payload: dict | None = None,
    result: dict | None = None,
):
    """Persist a system-authored state change with optimistic locking + audit log."""
    from sqlalchemy import update  # noqa: PLC0415
    from app.core.utils import now_riyadh_naive  # noqa: PLC0415
    from app.modules.minigames.models import MinigameSession, MinigameSessionEvent  # noqa: PLC0415

    now = now_riyadh_naive()
    turn_duration_ms = resolve_state_timer_duration_ms(
        new_state,
        fallback_ms=getattr(mg_session, "turn_duration_ms", None),
    )
    stamped_state = stamp_phase_deadlines(
        new_state,
        started_at=now,
        duration_ms=turn_duration_ms,
    )
    new_revision = mg_session.revision + 1

    stmt = (
        update(MinigameSession)
        .where(
            MinigameSession.id == mg_session.id,
            MinigameSession.revision == mg_session.revision,
        )
        .values(
            game_state=stamped_state,
            current_turn_index=current_turn_index,
            turn_number=turn_number,
            turn_started_at=now,
            turn_duration_ms=turn_duration_ms,
            revision=new_revision,
            updated_at=now,
        )
        .returning(MinigameSession.revision)
    )
    update_result = await db.execute(stmt)
    if update_result.fetchone() is None:
        raise RuntimeError("تعذر حفظ تحديث النظام بسبب تعارض متزامن")

    db.add(
        MinigameSessionEvent(
            session_id=mg_session.id,
            revision=new_revision,
            event_type=event_type,
            actor_type="system",
            action_type=action_type,
            payload=payload or {},
            result=result or {},
            correlation_id=mg_session.correlation_id,
        )
    )

    mg_session.game_state = stamped_state
    mg_session.current_turn_index = current_turn_index
    mg_session.turn_number = turn_number
    mg_session.turn_started_at = now
    mg_session.turn_duration_ms = turn_duration_ms
    mg_session.revision = new_revision
    mg_session.updated_at = now
    return mg_session


async def _resolve_challenge_expiry(
    *,
    session_id: uuid.UUID,
    competition_id: uuid.UUID,
    game_type: str,
) -> None:
    """Cancel an unanswered challenge once its timeout elapses."""
    from sqlalchemy import select  # noqa: PLC0415
    from app.core.database import async_session  # noqa: PLC0415
    from app.core.enums import MinigameSessionPhase as Phase  # noqa: PLC0415
    from app.modules.minigames.live_service import get_session_participants_with_balances  # noqa: PLC0415
    from app.modules.minigames.models import MinigameSession  # noqa: PLC0415
    from app.modules.minigames.session_service import transition_session  # noqa: PLC0415

    lobby_key = f"{game_type}:{competition_id}"
    async with async_session() as db:
        result = await db.execute(
            select(MinigameSession).where(
                MinigameSession.id == session_id,
                MinigameSession.competition_id == competition_id,
                MinigameSession.game_type == game_type,
            )
        )
        mg_session = result.scalar_one_or_none()
        if mg_session is None or _enum_value(mg_session.phase) != Phase.CREATED.value:
            return

        transitioned = await transition_session(
            db,
            session_id=mg_session.id,
            expected_revision=mg_session.revision,
            target_phase=Phase.CANCELLED,
            terminal_reason="challenge_timeout",
            actor_type="system",
        )
        if transitioned is None:
            return
        mg_session = transitioned
        participants = await get_session_participants_with_balances(db, session_id)
        await db.commit()

    _set_lobby_status_for_participants(lobby_key, participants, status="idle")
    await _broadcast_transition_event(
        session_id=session_id,
        participants=participants,
        lobby_key=lobby_key,
        from_phase=Phase.CREATED,
        to_phase=mg_session.phase,
        data={"terminal_reason": "challenge_timeout"},
    )
    for participant in participants:
        await manager.send_to_player(
            lobby_key,
            participant["membership_id"],
            {
                "type": "challenge_expired",
                "session_id": str(session_id),
                "terminal_reason": "challenge_timeout",
            },
        )
    await _broadcast_lobby_state(lobby_key)


async def _resolve_session_phase_timeout(
    *,
    session_id: uuid.UUID,
    competition_id: uuid.UUID,
    game_type: str,
) -> None:
    """Resolve the currently-active playable timer for a live session."""
    from sqlalchemy import select  # noqa: PLC0415
    from app.core.database import async_session  # noqa: PLC0415
    from app.core.enums import MinigameSessionPhase as Phase  # noqa: PLC0415
    from app.modules.minigames.live_service import (
        enter_overtime,
        finalize_session,
        get_session_participants_with_balances,
    )  # noqa: PLC0415
    from app.modules.minigames.models import MinigameSession  # noqa: PLC0415
    from app.modules.minigames.registry import GameTypeRegistry  # noqa: PLC0415

    lobby_key = f"{game_type}:{competition_id}"
    async with async_session() as db:
        result = await db.execute(
            select(MinigameSession).where(
                MinigameSession.id == session_id,
                MinigameSession.competition_id == competition_id,
                MinigameSession.game_type == game_type,
            )
        )
        mg_session = result.scalar_one_or_none()
        if mg_session is None:
            return
        if _enum_value(mg_session.phase) not in {Phase.IN_PROGRESS.value, Phase.OVERTIME.value}:
            return
        if (_remaining_turn_ms(mg_session) or 0) > 0:
            return

        plugin = GameTypeRegistry.get(game_type)
        if plugin is None:
            return
        participants = await get_session_participants_with_balances(db, session_id)
        current_turn_index = mg_session.current_turn_index
        side_effects: list[dict] = []
        overtime_started = False
        finalization = None

        game_phase = (mg_session.game_state or {}).get("game_phase")
        if game_phase == "word_selection" and hasattr(plugin, "resolve_selection_timeout"):
            timeout_result = plugin.resolve_selection_timeout(mg_session.game_state)
            if not timeout_result:
                return
            mg_session = await _persist_system_state_update(
                db,
                mg_session=mg_session,
                new_state=timeout_result["state"],
                current_turn_index=timeout_result.get("current_turn_index"),
                turn_number=mg_session.turn_number,
                event_type="timeout",
                action_type="selection_timeout",
                result={"side_effects": timeout_result.get("side_effects", [])},
            )
            side_effects = timeout_result.get("side_effects", [])
        elif game_phase in {"battle", "overtime"} and hasattr(plugin, "resolve_turn_timeout"):
            timeout_result = plugin.resolve_turn_timeout(mg_session.game_state, current_turn_index)
            if not timeout_result:
                return
            num_players = max(len(participants), int(getattr(mg_session, "num_players", 0) or 0), 1)
            if current_turn_index is None:
                next_turn_index = 0 if num_players > 0 else None
            elif num_players <= 1:
                next_turn_index = current_turn_index
            else:
                next_turn_index = (current_turn_index + 1) % num_players

            mg_session = await _persist_system_state_update(
                db,
                mg_session=mg_session,
                new_state=timeout_result["state"],
                current_turn_index=next_turn_index,
                turn_number=(mg_session.turn_number or 0) + 1,
                event_type="timeout",
                action_type="turn_timeout",
                payload={"skipped_slot_index": current_turn_index},
                result={"side_effects": timeout_result.get("side_effects", [])},
            )
            side_effects = timeout_result.get("side_effects", [])

            terminal_result = plugin.evaluate_terminal(mg_session.game_state)
            if terminal_result is not None:
                finalization = await finalize_session(
                    db,
                    mg_session=mg_session,
                    plugin=plugin,
                    participants=participants,
                    terminal_result=terminal_result,
                    target_phase=Phase.COMPLETED,
                    terminal_reason=terminal_result.get("reason"),
                    actor_type="system",
                )
                mg_session = finalization["session"]
            elif getattr(plugin, "supports_overtime", False):
                overtime_session = await enter_overtime(
                    db,
                    mg_session=mg_session,
                    plugin=plugin,
                    actor_type="system",
                )
                if overtime_session is not None:
                    overtime_started = True
                    mg_session = overtime_session
        else:
            return

        await db.commit()

    if finalization is not None:
        _cancel_session_timer(session_id)
        _set_lobby_status_for_participants(lobby_key, participants, status="idle")
        lobby_result = finalization.get("lobby_result")
        if lobby_result and finalization.get("participant_results"):
            lobby_mgr.add_result(lobby_key, lobby_result)
            await _send_lobby_update(
                lobby_key,
                update_type="result",
                data=lobby_result,
            )
        await _broadcast_transition_event(
            session_id=session_id,
            participants=participants,
            lobby_key=lobby_key,
            from_phase=Phase.OVERTIME if game_phase == "overtime" else Phase.IN_PROGRESS,
            to_phase=mg_session.phase,
            data={
                "terminal_reason": mg_session.terminal_reason,
                "winner_slot_index": mg_session.winner_slot_index,
            },
        )
        await _send_session_state_snapshots(
            session_id=session_id,
            plugin=plugin,
            state=mg_session.game_state,
            participants=participants,
            current_turn_index=mg_session.current_turn_index,
            lobby_key=lobby_key,
            phase=mg_session.phase,
            revision=mg_session.revision,
            turn_number=mg_session.turn_number,
        )
        await _broadcast_settlement_result(
            session_id=session_id,
            participants=participants,
            lobby_key=lobby_key,
            participant_results=finalization.get("participant_results", []),
            stats_update=finalization.get("stats_update", {}),
        )
        await _broadcast_lobby_state(lobby_key)
        return

    if overtime_started:
        await _broadcast_transition_event(
            session_id=session_id,
            participants=participants,
            lobby_key=lobby_key,
            from_phase=Phase.IN_PROGRESS,
            to_phase=mg_session.phase,
            data={"overtime": True},
        )

    await _send_state_patches(
        session_id=session_id,
        plugin=plugin,
        state=mg_session.game_state,
        participants=participants,
        current_turn_index=mg_session.current_turn_index,
        lobby_key=lobby_key,
        phase=mg_session.phase,
        revision=mg_session.revision,
        turn_number=mg_session.turn_number,
    )
    await _send_session_state_snapshots(
        session_id=session_id,
        plugin=plugin,
        state=mg_session.game_state,
        participants=participants,
        current_turn_index=mg_session.current_turn_index,
        lobby_key=lobby_key,
        phase=mg_session.phase,
        revision=mg_session.revision,
        turn_number=mg_session.turn_number,
    )
    await _broadcast_timer_sync(
        session_id=session_id,
        participants=participants,
        lobby_key=lobby_key,
        remaining_ms=_remaining_turn_ms(mg_session),
        phase=mg_session.phase,
    )
    await _schedule_session_phase_timer(
        session_id=session_id,
        competition_id=competition_id,
        game_type=game_type,
        delay_seconds=(mg_session.turn_duration_ms or 0) / 1000,
    )


async def _schedule_session_phase_timer(
    *,
    session_id: uuid.UUID,
    competition_id: uuid.UUID,
    game_type: str,
    delay_seconds: float,
) -> None:
    """Schedule the current live-session timer resolution."""

    async def _runner() -> None:
        try:
            await asyncio.sleep(max(0.0, delay_seconds))
            await _resolve_session_phase_timeout(
                session_id=session_id,
                competition_id=competition_id,
                game_type=game_type,
            )
        except asyncio.CancelledError:
            return
        finally:
            _session_timer_tasks.pop(session_id, None)

    _cancel_session_timer(session_id)
    _session_timer_tasks[session_id] = asyncio.create_task(_runner())


# ---------------------------------------------------------------------------
# Queue + session creation
# ---------------------------------------------------------------------------


async def _publish_match_start(
    *,
    lobby_key: str,
    competition_id: uuid.UUID,
    game_type: str,
    mg_session,
    participants: list[dict],
    memberships_by_id: dict,
    plugin,
) -> None:
    """Attach players to the session room and broadcast match-start payloads."""
    session_id = str(mg_session.id)
    session_room = _session_room_key(mg_session.id)

    for participant in participants:
        membership_id = participant["membership_id"]
        _cancel_queue_expiry(lobby_key, membership_id)
        if lobby_mgr.is_in_lobby(lobby_key, membership_id):
            lobby_mgr.set_status(lobby_key, membership_id, "in_match")
        ws = manager.get_websocket(lobby_key, membership_id)
        if ws is not None:
            manager.connect(session_room, membership_id, ws)

    for participant in participants:
        membership_id = participant["membership_id"]
        others = [
            {
                "membership_id": str(other["membership_id"]),
                "slot_index": other["slot_index"],
                "alias": memberships_by_id[other["membership_id"]].current_alias or "مجهول",
            }
            for other in participants
            if other["membership_id"] != membership_id
        ]
        message: dict = {
            "type": "match_found",
            "session_id": session_id,
            "game_type": game_type,
            "competition_id": str(competition_id),
            "slot_index": participant["slot_index"],
            "participants": others,
        }
        if len(others) == 1:
            message["opponent_membership_id"] = others[0]["membership_id"]
            message["opponent_alias"] = others[0]["alias"]
        await _send_to_participant(
            session_id=mg_session.id,
            lobby_key=lobby_key,
            membership_id=membership_id,
            message=message,
        )

    await _broadcast_transition_event(
        session_id=mg_session.id,
        participants=participants,
        lobby_key=lobby_key,
        from_phase="ready",
        to_phase=mg_session.phase,
        data={"turn_number": mg_session.turn_number},
    )
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
    await _broadcast_timer_sync(
        session_id=mg_session.id,
        participants=participants,
        lobby_key=lobby_key,
        remaining_ms=_remaining_turn_ms(mg_session),
        phase=mg_session.phase,
    )
    await _schedule_session_phase_timer(
        session_id=mg_session.id,
        competition_id=competition_id,
        game_type=game_type,
        delay_seconds=(mg_session.turn_duration_ms or 0) / 1000,
    )
    await _broadcast_lobby_state(lobby_key)


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
    from app.modules.minigames.live_service import start_session  # noqa: PLC0415
    from app.modules.minigames.policy_service import (  # noqa: PLC0415
        count_opponent_matches_this_cycle,
        count_player_matches_today,
        run_all_checks,
    )
    from app.modules.minigames.registry import GameTypeRegistry  # noqa: PLC0415
    from app.modules.minigames.session_service import (  # noqa: PLC0415
        create_session,
        get_session_participants,
        validate_session_creation,
    )
    from app.modules.minigames.settings_helper import (  # noqa: PLC0415
        check_kill_switch,
        get_effective_setting,
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
                game_type=game_type,
            )

            kill_switch = check_kill_switch(settings_snapshot.get("minigame_kill_switch"))
            if not get_effective_setting(
                settings_snapshot,
                generic_key="minigame_enabled",
                game_key=f"{game_type}_enabled",
                default=False,
            ):
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

            buy_in_amount = int(
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
            same_opponent_limit = int(
                get_effective_setting(
                    settings_snapshot,
                    generic_key="minigame_same_opponent_limit",
                    game_key=f"{game_type}_same_opponent_limit",
                    default=1,
                )
            )

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
                    opponent_counts: list[int] = []
                    for opponent_id in matched_ids:
                        if opponent_id == membership_id:
                            continue
                        opponent_counts.append(
                            await count_opponent_matches_this_cycle(
                                db,
                                membership_id=membership.id,
                                opponent_membership_id=opponent_id,
                                game_type=game_type,
                                competition_id=competition_id,
                                cycle_id=cycle.id,
                            )
                        )
                    matches_with_opponent = max(opponent_counts, default=0)

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
                queue_timeout_sec = int(settings_snapshot.get(f"{game_type}_queue_timeout_sec", 120))
                for membership_id in requeue_ids:
                    await _schedule_queue_expiry(
                        lobby_key=lobby_key,
                        membership_id=membership_id,
                        delay_seconds=queue_timeout_sec,
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
                turn_duration_ms=int(
                    get_effective_setting(
                        settings_snapshot,
                        generic_key="minigame_turn_duration_sec",
                        game_key=f"{game_type}_turn_duration_sec",
                        default=30,
                    )
                )
                * 1000,
                grace_timer_ms=int(
                    get_effective_setting(
                        settings_snapshot,
                        generic_key="minigame_grace_timer_sec",
                        game_key=f"{game_type}_grace_timer_sec",
                        default=60,
                    )
                )
                * 1000,
            )

            # Load the freshly-created participants (slot_index + reconnect_token).
            participants = await get_session_participants(db, mg_session.id)
            participants = [
                {
                    **participant,
                    "balance": memberships[participant["membership_id"]].current_balance,
                    "alias": memberships[participant["membership_id"]].current_alias or "مجهول",
                }
                for participant in participants
            ]
            mg_session, participants = await start_session(
                db,
                mg_session=mg_session,
                plugin=plugin,
                participants=participants,
                actor_type="system",
            )

            await db.commit()
            await db.refresh(mg_session)

        await _publish_match_start(
            lobby_key=lobby_key,
            competition_id=competition_id,
            game_type=game_type,
            mg_session=mg_session,
            participants=participants,
            memberships_by_id=memberships,
            plugin=plugin,
        )

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


def _build_pause_state(
    current_state: dict,
    *,
    disconnected_membership_id: uuid.UUID,
    grace_timer_ms: int,
    resume_phase,
    remaining_turn_ms: int | None = None,
) -> dict:
    """Return a paused game_state with grace metadata."""
    from app.core.utils import now_riyadh_naive  # noqa: PLC0415

    deadline = now_riyadh_naive() + timedelta(milliseconds=grace_timer_ms)
    new_state = dict(current_state or {})
    new_state["pause_info"] = {
        "disconnected_membership_id": str(disconnected_membership_id),
        "grace_deadline_at": deadline.isoformat(),
        "resume_phase": _enum_value(resume_phase),
        "remaining_turn_ms": remaining_turn_ms,
    }
    return new_state


def _current_state_payload(
    *,
    mg_session,
    plugin,
    viewer_membership_id: uuid.UUID,
    slot_index: int | None = None,
) -> dict:
    """Build the authoritative current_state payload for action_reject."""
    return {
        "session_id": str(mg_session.id),
        "slot_index": slot_index,
        "phase": _enum_value(mg_session.phase),
        "revision": mg_session.revision,
        "current_turn_index": mg_session.current_turn_index,
        "turn_number": mg_session.turn_number,
        "state": plugin.build_public_view(mg_session.game_state, viewer_membership_id),
    }


async def _handle_action_submit(
    websocket: WebSocket,
    msg: dict,
    competition_id: uuid.UUID,
    game_type: str,
    membership_info: dict,
) -> None:
    """Validate + process action via plugin, then notify every other participant."""
    from sqlalchemy import select  # noqa: PLC0415
    from app.core.enums import MinigameSessionPhase as Phase  # noqa: PLC0415
    from app.core.database import async_session  # noqa: PLC0415
    from app.modules.minigames.action_service import (  # noqa: PLC0415
        check_idempotency,
        get_expected_client_seq,
        process_action,
        validate_action_envelope,
    )
    from app.modules.minigames.models import (  # noqa: PLC0415
        MinigameActionReceipt,
        MinigameSession,
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
    client_seq = envelope.get("client_seq")
    if not isinstance(client_seq, int):
        await _send_error(websocket, "INVALID_SEQUENCE", "تسلسل الإجراء غير صالح")
        return

    action_id_raw = envelope.get("action_id")
    try:
        action_id = uuid.UUID(str(action_id_raw)) if action_id_raw else None
    except ValueError:
        await _send_error(websocket, "INVALID_ACTION_ID", "معرف الإجراء غير صالح")
        return
    if action_id is not None:
        envelope["action_id"] = action_id

    lobby_key = f"{game_type}:{competition_id}"
    actor_id: uuid.UUID = membership_info["membership_id"]
    cached_response = None
    authoritative_state = None
    final_session = None
    participants: list[dict] = []
    plugin = None
    transition_from_phase = None
    finalization = None
    overtime_started = False
    current_state_payload = None

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
        actor_slot_index = next(
            (
                participant["slot_index"]
                for participant in participants
                if participant["membership_id"] == actor_id
            ),
            None,
        )

        plugin = GameTypeRegistry.get(game_type)
        if plugin is None:
            await _send_error(websocket, "PLUGIN_NOT_FOUND", "نوع اللعبة غير معروف")
            return

        current_state_payload = _current_state_payload(
            mg_session=mg_session,
            plugin=plugin,
            viewer_membership_id=actor_id,
            slot_index=actor_slot_index,
        )

        # Check idempotency first
        cached_response = await check_idempotency(
            db,
            action_id,
            session_id=mg_session.id,
            actor_membership_id=actor_id,
            client_seq=client_seq,
        )
        if cached_response is not None:
            await websocket.send_json(
                {
                    "type": "action_ack",
                    "action_id": str(action_id) if action_id else None,
                    "result": cached_response,
                    "cached": True,
                }
            )
            return

        expected_client_seq = await get_expected_client_seq(
            db,
            session_id=mg_session.id,
            actor_membership_id=actor_id,
        )
        if client_seq != expected_client_seq:
            await _send_action_reject(
                websocket,
                action_id=action_id,
                code="INVALID_SEQUENCE",
                message_ar="تسلسل الإجراء غير صالح",
                current_state=current_state_payload,
            )
            return

        if not _check_action_rate_limit(session_id, actor_id):
            await _send_action_reject(
                websocket,
                action_id=action_id,
                code="RATE_LIMITED",
                message_ar="عدد الإجراءات سريع جداً — حاول بعد لحظة",
                current_state=current_state_payload,
            )
            return

        # Validate envelope (pure)
        error = validate_action_envelope(
            envelope=envelope,
            session_phase=mg_session.phase,
            session_revision=mg_session.revision,
            current_turn_index=mg_session.current_turn_index,
            participants=participants,
            state=mg_session.game_state,
        )
        if error:
            await _send_action_reject(
                websocket,
                action_id=action_id,
                code=error.code,
                message_ar=error.message_ar,
                current_state=current_state_payload,
            )
            return

        # Process action
        _cancel_session_timer(session_id)
        try:
            result_payload = await process_action(
                db,
                mg_session=mg_session,
                plugin=plugin,
                envelope=envelope,
                participants=participants,
            )
        except ValueError as exc:
            await db.rollback()
            await _schedule_session_phase_timer(
                session_id=session_id,
                competition_id=competition_id,
                game_type=game_type,
                delay_seconds=(_remaining_turn_ms(mg_session) or 0) / 1000,
            )
            await _send_action_reject(
                websocket,
                action_id=action_id,
                code="INVALID_ACTION",
                message_ar=str(exc),
                current_state=current_state_payload,
            )
            return
        except RuntimeError as exc:
            await db.rollback()
            refreshed_result = await db.execute(
                select(MinigameSession).where(MinigameSession.id == session_id)
            )
            latest_session = refreshed_result.scalar_one_or_none()
            if latest_session is not None:
                await _schedule_session_phase_timer(
                    session_id=session_id,
                    competition_id=competition_id,
                    game_type=game_type,
                    delay_seconds=(_remaining_turn_ms(latest_session) or 0) / 1000,
                )
                current_state_payload = _current_state_payload(
                    mg_session=latest_session,
                    plugin=plugin,
                    viewer_membership_id=actor_id,
                    slot_index=actor_slot_index,
                )
            await _send_action_reject(
                websocket,
                action_id=action_id,
                code="STALE_STATE",
                message_ar=str(exc),
                current_state=current_state_payload,
            )
            return

        authoritative_state = result_payload.pop("_state", None)
        if authoritative_state is None:
            await db.rollback()
            await _schedule_session_phase_timer(
                session_id=session_id,
                competition_id=competition_id,
                game_type=game_type,
                delay_seconds=(_remaining_turn_ms(mg_session) or 0) / 1000,
            )
            await _send_error(websocket, "SERVER_ERROR", "تعذر مزامنة حالة الجلسة")
            return

        transition_from_phase = mg_session.phase
        final_session = mg_session
        terminal_result = result_payload.get("terminal_result")
        if terminal_result is not None:
            from app.modules.minigames.live_service import finalize_session  # noqa: PLC0415

            finalization = await finalize_session(
                db,
                mg_session=mg_session,
                plugin=plugin,
                participants=participants,
                terminal_result=terminal_result,
                target_phase=Phase.COMPLETED,
                terminal_reason=terminal_result.get("reason"),
                actor_type="participant",
                actor_membership_id=actor_id,
            )
            final_session = finalization["session"]
            authoritative_state = final_session.game_state
            result_payload["revision"] = final_session.revision
            result_payload["next_turn_index"] = final_session.current_turn_index
            result_payload["turn_number"] = final_session.turn_number
            result_payload["phase"] = _enum_value(final_session.phase)
            result_payload["settlement"] = {
                "participant_results": finalization.get("participant_results", []),
                "total_pool": getattr(finalization["settlement"], "total_pool", 0),
            }
        elif getattr(plugin, "supports_overtime", False):
            from app.modules.minigames.live_service import enter_overtime  # noqa: PLC0415

            overtime_session = await enter_overtime(
                db,
                mg_session=mg_session,
                plugin=plugin,
                actor_type="participant",
                actor_membership_id=actor_id,
            )
            if overtime_session is not None:
                overtime_started = True
                final_session = overtime_session
                authoritative_state = overtime_session.game_state
                result_payload["revision"] = overtime_session.revision
                result_payload["next_turn_index"] = overtime_session.current_turn_index
                result_payload["turn_number"] = overtime_session.turn_number
                result_payload["phase"] = _enum_value(overtime_session.phase)
                result_payload["overtime"] = True

        receipt_result = await db.execute(
            select(MinigameActionReceipt).where(
                MinigameActionReceipt.session_id == mg_session.id,
                MinigameActionReceipt.actor_membership_id == actor_id,
                MinigameActionReceipt.client_seq == client_seq,
            )
        )
        receipt = receipt_result.scalar_one_or_none()
        if receipt is not None:
            receipt.response = dict(result_payload)

        await db.commit()

    result_payload = dict(result_payload)
    if authoritative_state is None:
        await _send_error(websocket, "SERVER_ERROR", "تعذر مزامنة حالة الجلسة")
        return
    next_turn_index = result_payload.get(
        "next_turn_index", getattr(final_session, "current_turn_index", None)
    )
    turn_number = result_payload.get(
        "turn_number", getattr(final_session, "turn_number", 0)
    )
    actor_action = envelope.get("action", {}) or {}

    # Notify sender
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
        await _send_to_participant(
            session_id=session_id,
            lobby_key=lobby_key,
            membership_id=p["membership_id"],
            message=opponent_msg,
        )

    if finalization is not None:
        _cancel_session_timer(session_id)
        _set_lobby_status_for_participants(lobby_key, participants, status="idle")
        lobby_result = finalization.get("lobby_result")
        if lobby_result and finalization.get("participant_results"):
            lobby_mgr.add_result(lobby_key, lobby_result)
            await _send_lobby_update(
                lobby_key,
                update_type="result",
                data=lobby_result,
            )
        await _broadcast_transition_event(
            session_id=session_id,
            participants=participants,
            lobby_key=lobby_key,
            from_phase=transition_from_phase,
            to_phase=final_session.phase,
            data={
                "terminal_reason": final_session.terminal_reason,
                "winner_slot_index": final_session.winner_slot_index,
            },
        )
        await _send_session_state_snapshots(
            session_id=session_id,
            plugin=plugin,
            state=authoritative_state,
            participants=participants,
            current_turn_index=final_session.current_turn_index,
            lobby_key=lobby_key,
            phase=final_session.phase,
            revision=final_session.revision,
            turn_number=final_session.turn_number,
        )
        await _broadcast_settlement_result(
            session_id=session_id,
            participants=participants,
            lobby_key=lobby_key,
            participant_results=finalization.get("participant_results", []),
            stats_update=finalization.get("stats_update", {}),
        )
        await _broadcast_lobby_state(lobby_key)
        return

    if overtime_started:
        await _broadcast_transition_event(
            session_id=session_id,
            participants=participants,
            lobby_key=lobby_key,
            from_phase=transition_from_phase,
            to_phase=final_session.phase,
            data={"overtime": True},
        )

    await _send_state_patches(
        session_id=session_id,
        plugin=plugin,
        state=authoritative_state,
        participants=participants,
        current_turn_index=next_turn_index,
        lobby_key=lobby_key,
        phase=final_session.phase,
        revision=result_payload["revision"],
        turn_number=turn_number,
    )
    await _send_session_state_snapshots(
        session_id=session_id,
        plugin=plugin,
        state=authoritative_state,
        participants=participants,
        current_turn_index=next_turn_index,
        lobby_key=lobby_key,
        phase=final_session.phase,
        revision=result_payload["revision"],
        turn_number=turn_number,
    )
    await _broadcast_timer_sync(
        session_id=session_id,
        participants=participants,
        lobby_key=lobby_key,
        remaining_ms=_remaining_turn_ms(final_session),
        phase=final_session.phase,
    )
    await _schedule_session_phase_timer(
        session_id=session_id,
        competition_id=competition_id,
        game_type=game_type,
        delay_seconds=(getattr(final_session, "turn_duration_ms", 0) or 0) / 1000,
    )


def _cancel_grace_task(session_id: uuid.UUID) -> None:
    task = _grace_tasks.pop(session_id, None)
    if task is not None:
        task.cancel()


async def _schedule_grace_resolution(
    *,
    session_id: uuid.UUID,
    competition_id: uuid.UUID,
    game_type: str,
    delay_seconds: float,
) -> None:
    """Schedule a single in-process grace-timeout task."""

    async def _runner() -> None:
        try:
            await asyncio.sleep(max(0.0, delay_seconds))
            await _resolve_grace_timeout(
                session_id=session_id,
                competition_id=competition_id,
                game_type=game_type,
            )
        except asyncio.CancelledError:
            return
        finally:
            _grace_tasks.pop(session_id, None)

    _cancel_grace_task(session_id)
    _grace_tasks[session_id] = asyncio.create_task(_runner())


async def _resolve_grace_timeout(
    *,
    session_id: uuid.UUID,
    competition_id: uuid.UUID,
    game_type: str,
) -> None:
    """Resolve a paused session after its reconnect grace period expires."""
    from sqlalchemy import select  # noqa: PLC0415
    from app.core.database import async_session  # noqa: PLC0415
    from app.core.enums import MinigameSessionPhase as Phase  # noqa: PLC0415
    from app.modules.minigames.live_service import (  # noqa: PLC0415
        build_forfeit_terminal_result,
        finalize_session,
        get_session_participants_with_balances,
    )
    from app.modules.minigames.models import MinigameSession  # noqa: PLC0415
    from app.modules.minigames.registry import GameTypeRegistry  # noqa: PLC0415

    lobby_key = f"{game_type}:{competition_id}"
    async with async_session() as db:
        result = await db.execute(
            select(MinigameSession).where(
                MinigameSession.id == session_id,
                MinigameSession.competition_id == competition_id,
                MinigameSession.game_type == game_type,
            )
        )
        mg_session = result.scalar_one_or_none()
        if mg_session is None or _enum_value(mg_session.phase) != Phase.PAUSED.value:
            return

        plugin = GameTypeRegistry.get(game_type)
        if plugin is None:
            return

        participants = await get_session_participants_with_balances(db, mg_session.id)
        session_room = _session_room_key(mg_session.id)
        connected_ids = [
            participant["membership_id"]
            for participant in participants
            if manager.is_connected(session_room, participant["membership_id"])
            or manager.is_connected(lobby_key, participant["membership_id"])
        ]

        if len(connected_ids) == 1 and len(participants) >= 2:
            terminal_result = build_forfeit_terminal_result(
                participants=participants,
                winner_membership_id=connected_ids[0],
                buy_in_amount=mg_session.buy_in_amount,
            )
            finalization = await finalize_session(
                db,
                mg_session=mg_session,
                plugin=plugin,
                participants=participants,
                terminal_result=terminal_result,
                target_phase=Phase.ABANDONED,
                terminal_reason="grace_timeout",
                actor_type="system",
            )
        else:
            finalization = await finalize_session(
                db,
                mg_session=mg_session,
                plugin=plugin,
                participants=participants,
                terminal_result=None,
                target_phase=Phase.CANCELLED,
                terminal_reason="grace_timeout",
                actor_type="system",
            )

        mg_session = finalization["session"]
        await db.commit()

    _set_lobby_status_for_participants(lobby_key, participants, status="idle")
    lobby_result = finalization.get("lobby_result")
    if lobby_result and finalization.get("participant_results"):
        lobby_mgr.add_result(lobby_key, lobby_result)
        await _send_lobby_update(
            lobby_key,
            update_type="result",
            data=lobby_result,
        )
    await _broadcast_transition_event(
        session_id=session_id,
        participants=participants,
        lobby_key=lobby_key,
        from_phase=Phase.PAUSED,
        to_phase=mg_session.phase,
        data={
            "terminal_reason": mg_session.terminal_reason,
            "winner_slot_index": mg_session.winner_slot_index,
        },
    )
    await _send_session_state_snapshots(
        session_id=session_id,
        plugin=plugin,
        state=mg_session.game_state,
        participants=participants,
        current_turn_index=mg_session.current_turn_index,
        lobby_key=lobby_key,
        phase=mg_session.phase,
        revision=mg_session.revision,
        turn_number=mg_session.turn_number,
    )
    await _broadcast_settlement_result(
        session_id=session_id,
        participants=participants,
        lobby_key=lobby_key,
        participant_results=finalization.get("participant_results", []),
        stats_update=finalization.get("stats_update", {}),
    )
    await _broadcast_lobby_state(lobby_key)


async def _pause_session_for_disconnect(
    *,
    session_id: uuid.UUID,
    competition_id: uuid.UUID,
    game_type: str,
    membership_id: uuid.UUID,
) -> None:
    """Pause an in-flight session and schedule its grace-timeout resolution."""
    from sqlalchemy import select  # noqa: PLC0415
    from app.core.database import async_session  # noqa: PLC0415
    from app.core.enums import MinigameSessionPhase as Phase  # noqa: PLC0415
    from app.modules.minigames.live_service import get_session_participants_with_balances  # noqa: PLC0415
    from app.modules.minigames.models import MinigameSession  # noqa: PLC0415
    from app.modules.minigames.registry import GameTypeRegistry  # noqa: PLC0415
    from app.modules.minigames.session_service import transition_session  # noqa: PLC0415

    lobby_key = f"{game_type}:{competition_id}"
    async with async_session() as db:
        result = await db.execute(
            select(MinigameSession).where(
                MinigameSession.id == session_id,
                MinigameSession.competition_id == competition_id,
                MinigameSession.game_type == game_type,
            )
        )
        mg_session = result.scalar_one_or_none()
        if mg_session is None:
            return

        plugin = GameTypeRegistry.get(game_type)
        if plugin is None:
            return

        participants = await get_session_participants_with_balances(db, mg_session.id)
        current_phase = _enum_value(mg_session.phase)
        if current_phase == Phase.PAUSED.value:
            delay_seconds = (_remaining_grace_ms(mg_session) or 0) / 1000
            await _schedule_grace_resolution(
                session_id=session_id,
                competition_id=competition_id,
                game_type=game_type,
                delay_seconds=delay_seconds,
            )
            return

        if current_phase not in {Phase.IN_PROGRESS.value, Phase.OVERTIME.value}:
            return

        _cancel_session_timer(session_id)
        pause_state = _build_pause_state(
            mg_session.game_state,
            disconnected_membership_id=membership_id,
            grace_timer_ms=mg_session.grace_timer_ms,
            resume_phase=mg_session.phase,
            remaining_turn_ms=_remaining_turn_ms(mg_session),
        )
        transitioned = await transition_session(
            db,
            session_id=mg_session.id,
            expected_revision=mg_session.revision,
            target_phase=Phase.PAUSED,
            actor_type="system",
            actor_membership_id=membership_id,
            extra_updates={"game_state": pause_state},
            payload={"pause_info": pause_state.get("pause_info", {})},
            result={"disconnected_membership_id": str(membership_id)},
        )
        if transitioned is None:
            return
        mg_session = transitioned
        await db.commit()

    await _broadcast_transition_event(
        session_id=session_id,
        participants=participants,
        lobby_key=lobby_key,
        from_phase=current_phase,
        to_phase=mg_session.phase,
        data=mg_session.game_state.get("pause_info", {}),
    )
    await _send_session_state_snapshots(
        session_id=session_id,
        plugin=plugin,
        state=mg_session.game_state,
        participants=participants,
        current_turn_index=mg_session.current_turn_index,
        lobby_key=lobby_key,
        phase=mg_session.phase,
        revision=mg_session.revision,
        turn_number=mg_session.turn_number,
    )
    await _broadcast_timer_sync(
        session_id=session_id,
        participants=participants,
        lobby_key=lobby_key,
        remaining_ms=_remaining_grace_ms(mg_session),
        phase=mg_session.phase,
    )
    await _schedule_grace_resolution(
        session_id=session_id,
        competition_id=competition_id,
        game_type=game_type,
        delay_seconds=mg_session.grace_timer_ms / 1000,
    )


async def _handle_challenge_send(
    websocket: WebSocket,
    msg: dict,
    competition_id: uuid.UUID,
    game_type: str,
    membership_info: dict,
) -> None:
    """Create a challenge session and notify the target player."""
    membership_id = membership_info["membership_id"]
    lobby_key = f"{game_type}:{competition_id}"
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
    if target_id == membership_id:
        await _send_error(websocket, "INVALID_TARGET", "لا يمكنك تحدي نفسك")
        return
    if not manager.is_connected(lobby_key, target_id):
        await _send_error(websocket, "TARGET_OFFLINE", "اللاعب المستهدف غير متصل")
        return

    from sqlalchemy import select  # noqa: PLC0415
    from app.core.database import async_session  # noqa: PLC0415
    from app.core.enums import MembershipStatus, MinigameMatchType, MinigameTypeStatus  # noqa: PLC0415
    from app.modules.competitions.models import Membership  # noqa: PLC0415
    from app.modules.minigames.live_service import (  # noqa: PLC0415
        build_challenge_expiry,
        get_memberships_by_ids,
        initialize_session_state,
        validate_match_candidate,
    )
    from app.modules.minigames.models import MinigameType  # noqa: PLC0415
    from app.modules.minigames.registry import GameTypeRegistry  # noqa: PLC0415
    from app.modules.minigames.session_service import create_session, get_session_participants  # noqa: PLC0415
    from app.modules.minigames.settings_helper import check_kill_switch, get_minigame_settings  # noqa: PLC0415
    from app.modules.minigames.settings_helper import get_effective_setting  # noqa: PLC0415

    async with async_session() as db:
        game_type_result = await db.execute(
            select(MinigameType).where(MinigameType.id == game_type)
        )
        game_type_obj = game_type_result.scalars().first()
        if game_type_obj is None:
            await _send_error(websocket, "GAME_TYPE_NOT_FOUND", "نوع اللعبة غير موجود")
            return
        if game_type_obj.status != MinigameTypeStatus.ACTIVE:
            await _send_error(websocket, "GAME_TYPE_DISABLED", "هذه اللعبة غير متاحة حالياً")
            return

        plugin = GameTypeRegistry.get(game_type)
        if plugin is None:
            await _send_error(websocket, "PLUGIN_NOT_FOUND", "نوع اللعبة غير معروف")
            return

        memberships_result = await db.execute(
            select(Membership).where(
                Membership.id.in_([membership_id, target_id]),
                Membership.competition_id == competition_id,
                Membership.status == MembershipStatus.ACTIVE,
            )
        )
        memberships = {
            membership.id: membership
            for membership in memberships_result.scalars().all()
        }
        if target_id not in memberships or membership_id not in memberships:
            await _send_error(websocket, "TARGET_NOT_FOUND", "الخصم غير موجود أو غير نشط")
            return

        season, cycle = await _get_active_season_cycle(db, competition_id)
        settings_snapshot = await get_minigame_settings(
            db,
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
            await _send_error(websocket, "MINIGAMES_DISABLED", "الألعاب المصغرة غير مفعلة في هذه المسابقة")
            return
        if not kill_switch.can_create_session:
            await _send_error(
                websocket,
                "MINIGAME_BLOCKED",
                kill_switch.message_ar or "الألعاب المصغرة معطلة حالياً",
            )
            return

        buy_in_amount = int(
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
        same_opponent_limit = int(
            get_effective_setting(
                settings_snapshot,
                generic_key="minigame_same_opponent_limit",
                game_key=f"{game_type}_same_opponent_limit",
                default=1,
            )
        )
        for candidate, opponents in (
            (memberships[membership_id], [target_id]),
            (memberships[target_id], [membership_id]),
        ):
            validation_error = await validate_match_candidate(
                db,
                membership=candidate,
                game_type=game_type,
                plugin_status=game_type_obj.status.value,
                competition_id=competition_id,
                buy_in_amount=buy_in_amount,
                daily_cap=daily_cap,
                same_opponent_limit=same_opponent_limit,
                opponent_membership_ids=opponents,
                cycle_id=cycle.id if cycle else None,
            )
            if validation_error:
                await _send_error(websocket, "CHALLENGE_BLOCKED", validation_error)
                return

        mg_session = await create_session(
            db,
            game_type=game_type,
            competition_id=competition_id,
            player_membership_ids=[membership_id, target_id],
            season_id=season.id if season else None,
            cycle_id=cycle.id if cycle else None,
            match_type=MinigameMatchType.CHALLENGE,
            buy_in_amount=buy_in_amount,
            settings_snapshot=settings_snapshot,
            turn_duration_ms=int(
                get_effective_setting(
                    settings_snapshot,
                    generic_key="minigame_turn_duration_sec",
                    game_key=f"{game_type}_turn_duration_sec",
                    default=30,
                )
            )
            * 1000,
            grace_timer_ms=int(
                get_effective_setting(
                    settings_snapshot,
                    generic_key="minigame_grace_timer_sec",
                    game_key=f"{game_type}_grace_timer_sec",
                    default=60,
                )
            )
            * 1000,
        )
        participants = await get_session_participants(db, mg_session.id)
        await initialize_session_state(
            db,
            mg_session=mg_session,
            plugin=plugin,
            participants=participants,
        )
        mg_session.game_state = {
            **mg_session.game_state,
            "challenge_expires_at": build_challenge_expiry(
                created_at=mg_session.created_at,
                timeout_seconds=int(
                    get_effective_setting(
                        settings_snapshot,
                        generic_key="",
                        game_key=f"{game_type}_challenge_timeout_sec",
                        default=60,
                    )
                ),
            ),
        }
        await db.commit()
        memberships = await get_memberships_by_ids(db, [membership_id, target_id])

    lobby_mgr.set_status(lobby_key, membership_id, "challenging")
    challenge_msg = {
        "type": "challenge_received",
        "from_membership_id": str(membership_id),
        "from_alias": membership_info["alias"],
        "game_type": game_type,
        "session_id": str(mg_session.id),
        "expires_at": mg_session.game_state.get("challenge_expires_at"),
    }
    sent = await manager.send_to_player(lobby_key, target_id, challenge_msg)
    if not sent:
        lobby_mgr.set_status(lobby_key, membership_id, "idle")
        await _schedule_challenge_expiry(
            session_id=mg_session.id,
            competition_id=competition_id,
            game_type=game_type,
            delay_seconds=int(
                get_effective_setting(
                    settings_snapshot,
                    generic_key="",
                    game_key=f"{game_type}_challenge_timeout_sec",
                    default=60,
                )
            ),
        )
        await _send_error(websocket, "TARGET_OFFLINE", "اللاعب المستهدف غير متصل")
        await _broadcast_lobby_state(lobby_key)
        return
    await websocket.send_json(
        {
            "type": "challenge_sent",
            "session_id": str(mg_session.id),
            "target_membership_id": str(target_id),
            "target_alias": memberships[target_id].current_alias or "مجهول",
            "expires_at": mg_session.game_state.get("challenge_expires_at"),
        }
    )
    await _schedule_challenge_expiry(
        session_id=mg_session.id,
        competition_id=competition_id,
        game_type=game_type,
        delay_seconds=int(
            get_effective_setting(
                settings_snapshot,
                generic_key="",
                game_key=f"{game_type}_challenge_timeout_sec",
                default=60,
            )
        ),
    )
    await _broadcast_lobby_state(lobby_key)


async def _handle_challenge_respond(
    websocket: WebSocket,
    msg: dict,
    competition_id: uuid.UUID,
    game_type: str,
    membership_info: dict,
) -> None:
    """Accept or decline a challenge from the websocket transport."""
    from sqlalchemy import select  # noqa: PLC0415
    from app.core.database import async_session  # noqa: PLC0415
    from app.core.enums import MinigameSessionPhase as Phase  # noqa: PLC0415
    from app.modules.competitions.models import Membership  # noqa: PLC0415
    from app.modules.minigames.live_service import (  # noqa: PLC0415
        get_memberships_by_ids,
        get_session_participants_with_balances,
        start_session,
        validate_match_candidate,
    )
    from app.modules.minigames.models import (  # noqa: PLC0415
        MinigameSession,
        MinigameSessionParticipant,
        MinigameType,
    )
    from app.modules.minigames.registry import GameTypeRegistry  # noqa: PLC0415
    from app.modules.minigames.session_service import transition_session  # noqa: PLC0415
    from app.modules.minigames.settings_helper import (  # noqa: PLC0415
        get_effective_setting,
        get_minigame_settings,
    )

    session_id_raw = msg.get("session_id")
    if not session_id_raw:
        await _send_error(websocket, "MISSING_SESSION_ID", "معرف الجلسة مفقود")
        return
    try:
        session_id = uuid.UUID(str(session_id_raw))
    except ValueError:
        await _send_error(websocket, "INVALID_SESSION_ID", "معرف الجلسة غير صالح")
        return

    accept = bool(msg.get("accept"))
    membership_id = membership_info["membership_id"]
    lobby_key = f"{game_type}:{competition_id}"

    async with async_session() as db:
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

        participant_result = await db.execute(
            select(MinigameSessionParticipant).where(
                MinigameSessionParticipant.session_id == session_id,
                MinigameSessionParticipant.slot_index == 1,
            )
        )
        target_participant = participant_result.scalar_one_or_none()
        if target_participant is None or target_participant.membership_id != membership_id:
            await _send_error(websocket, "FORBIDDEN", "لا يحق لك الرد على هذا التحدي")
            return
        if _enum_value(mg_session.phase) != Phase.CREATED.value:
            await _send_error(websocket, "SESSION_NOT_PENDING", "التحدي لم يعد في انتظار الرد")
            return

        challenge_expires_at = (mg_session.game_state or {}).get("challenge_expires_at")
        if challenge_expires_at:
            try:
                from app.core.utils import now_riyadh_naive  # noqa: PLC0415

                if datetime.fromisoformat(challenge_expires_at) <= now_riyadh_naive():
                    await _send_error(websocket, "CHALLENGE_EXPIRED", "انتهت مهلة هذا التحدي")
                    return
            except ValueError:
                pass

        if accept:
            plugin = GameTypeRegistry.get(game_type)
            if plugin is None:
                await _send_error(websocket, "PLUGIN_NOT_FOUND", "نوع اللعبة غير معروف")
                return
            game_type_result = await db.execute(
                select(MinigameType).where(MinigameType.id == game_type)
            )
            game_type_obj = game_type_result.scalar_one_or_none()
            if game_type_obj is None:
                await _send_error(websocket, "GAME_TYPE_NOT_FOUND", "نوع اللعبة غير موجود")
                return

            season, cycle = await _get_active_season_cycle(db, competition_id)
            settings_snapshot = await get_minigame_settings(
                db,
                competition_id=competition_id,
                season_id=season.id if season else None,
                cycle_id=cycle.id if cycle else None,
                game_type=game_type,
            )
            buy_in_amount = int(
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
            same_opponent_limit = int(
                get_effective_setting(
                    settings_snapshot,
                    generic_key="minigame_same_opponent_limit",
                    game_key=f"{game_type}_same_opponent_limit",
                    default=1,
                )
            )

            participants = await get_session_participants_with_balances(db, session_id)
            memberships = await get_memberships_by_ids(
                db,
                [participant["membership_id"] for participant in participants],
            )
            for participant in participants:
                candidate = memberships.get(participant["membership_id"])
                if candidate is None:
                    await _send_error(websocket, "PARTICIPANT_MISSING", "أحد المشاركين غير متاح")
                    return
                validation_error = await validate_match_candidate(
                    db,
                    membership=candidate,
                    game_type=game_type,
                    plugin_status=game_type_obj.status.value,
                    competition_id=competition_id,
                    buy_in_amount=buy_in_amount,
                    daily_cap=daily_cap,
                    same_opponent_limit=same_opponent_limit,
                    opponent_membership_ids=[
                        other["membership_id"]
                        for other in participants
                        if other["membership_id"] != participant["membership_id"]
                    ],
                    cycle_id=cycle.id if cycle else None,
                )
                if validation_error:
                    await _send_error(websocket, "CHALLENGE_BLOCKED", validation_error)
                    return

            mg_session, participants = await start_session(
                db,
                mg_session=mg_session,
                plugin=plugin,
                participants=participants,
                actor_type="participant",
                actor_membership_id=membership_id,
            )
            await db.commit()
            memberships = await get_memberships_by_ids(
                db,
                [participant["membership_id"] for participant in participants],
            )
        else:
            transitioned = await transition_session(
                db,
                session_id=mg_session.id,
                expected_revision=mg_session.revision,
                target_phase=Phase.CANCELLED,
                terminal_reason="declined",
                actor_type="participant",
                actor_membership_id=membership_id,
            )
            if transitioned is None:
                await _send_error(websocket, "CONFLICT", "تعذر تحديث الجلسة بسبب تعارض متزامن")
                return
            mg_session = transitioned
            await db.commit()
            participants = await get_session_participants_with_balances(db, session_id)
            memberships = await get_memberships_by_ids(
                db,
                [participant["membership_id"] for participant in participants],
            )

    if accept:
        _cancel_challenge_expiry(session_id)
        _cancel_grace_task(session_id)
        await _publish_match_start(
            lobby_key=lobby_key,
            competition_id=competition_id,
            game_type=game_type,
            mg_session=mg_session,
            participants=participants,
            memberships_by_id=memberships,
            plugin=plugin,
        )
        return

    _cancel_challenge_expiry(session_id)
    _set_lobby_status_for_participants(lobby_key, participants, status="idle")
    await _broadcast_transition_event(
        session_id=session_id,
        participants=participants,
        lobby_key=lobby_key,
        from_phase=Phase.CREATED,
        to_phase=mg_session.phase,
        data={"terminal_reason": "declined"},
    )
    await _broadcast_lobby_state(lobby_key)


async def _handle_reconnect_claim(
    websocket: WebSocket,
    msg: dict,
    competition_id: uuid.UUID,
    game_type: str,
    membership_info: dict,
) -> None:
    """Claim a reconnect token and resume a paused session when valid."""
    from sqlalchemy import select  # noqa: PLC0415
    from app.core.database import async_session  # noqa: PLC0415
    from app.core.enums import MinigameSessionPhase as Phase  # noqa: PLC0415
    from app.modules.minigames.live_service import get_session_participants_with_balances  # noqa: PLC0415
    from app.modules.minigames.models import MinigameSession, MinigameSessionParticipant  # noqa: PLC0415
    from app.modules.minigames.registry import GameTypeRegistry  # noqa: PLC0415
    from app.modules.minigames.session_service import transition_session  # noqa: PLC0415

    session_id_raw = msg.get("session_id")
    reconnect_token = msg.get("reconnect_token")
    if not session_id_raw or not reconnect_token:
        await _send_error(websocket, "INVALID_RECONNECT", "بيانات إعادة الاتصال غير مكتملة")
        return
    try:
        session_id = uuid.UUID(str(session_id_raw))
    except ValueError:
        await _send_error(websocket, "INVALID_SESSION_ID", "معرف الجلسة غير صالح")
        return

    membership_id = membership_info["membership_id"]
    lobby_key = f"{game_type}:{competition_id}"
    resumed = False
    from_phase = None

    async with async_session() as db:
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

        participant_result = await db.execute(
            select(MinigameSessionParticipant).where(
                MinigameSessionParticipant.session_id == session_id,
                MinigameSessionParticipant.membership_id == membership_id,
                MinigameSessionParticipant.reconnect_token == reconnect_token,
            )
        )
        participant_row = participant_result.scalar_one_or_none()
        if participant_row is None:
            await _send_error(websocket, "INVALID_RECONNECT", "رمز إعادة الاتصال غير صالح")
            return

        plugin = GameTypeRegistry.get(game_type)
        if plugin is None:
            await _send_error(websocket, "PLUGIN_NOT_FOUND", "نوع اللعبة غير معروف")
            return

        participants = await get_session_participants_with_balances(db, session_id)
        from_phase = mg_session.phase
        if _enum_value(mg_session.phase) == Phase.PAUSED.value:
            remaining_grace_ms = _remaining_grace_ms(mg_session)
            if remaining_grace_ms == 0:
                await _send_error(websocket, "RECONNECT_EXPIRED", "انتهت مهلة إعادة الاتصال")
                return
            resume_phase = Phase.IN_PROGRESS
            pause_info = (mg_session.game_state or {}).get("pause_info", {}) or {}
            resume_phase_raw = pause_info.get("resume_phase")
            if resume_phase_raw:
                try:
                    resume_phase = Phase(resume_phase_raw)
                except ValueError:
                    resume_phase = Phase.IN_PROGRESS
            resumed_state = dict(mg_session.game_state or {})
            resumed_state.pop("pause_info", None)
            remaining_turn_ms = pause_info.get("remaining_turn_ms")
            extra_updates = {"game_state": resumed_state}
            if isinstance(remaining_turn_ms, int) and remaining_turn_ms > 0:
                from app.core.utils import now_riyadh_naive  # noqa: PLC0415

                resumed_state = stamp_phase_deadlines(
                    resumed_state,
                    started_at=now_riyadh_naive(),
                    duration_ms=remaining_turn_ms,
                )
                extra_updates["game_state"] = resumed_state
                extra_updates["turn_duration_ms"] = remaining_turn_ms
            transitioned = await transition_session(
                db,
                session_id=mg_session.id,
                expected_revision=mg_session.revision,
                target_phase=resume_phase,
                actor_type="participant",
                actor_membership_id=membership_id,
                extra_updates=extra_updates,
                payload={"reconnect_claimed": True},
                result={"resumed_by": str(membership_id)},
            )
            if transitioned is None:
                await _send_error(websocket, "CONFLICT", "تعذر استئناف الجلسة بسبب تعارض متزامن")
                return
            mg_session = transitioned
            resumed = True
            await db.commit()

    manager.connect(_session_room_key(session_id), membership_id, websocket)
    _set_lobby_status_for_participants(lobby_key, participants, status="in_match")
    _cancel_grace_task(session_id)
    if resumed:
        await _broadcast_transition_event(
            session_id=session_id,
            participants=participants,
            lobby_key=lobby_key,
            from_phase=from_phase,
            to_phase=mg_session.phase,
            data={"resumed_by": str(membership_id)},
        )

    await _send_session_state_snapshots(
        session_id=session_id,
        plugin=plugin,
        state=mg_session.game_state,
        participants=participants,
        current_turn_index=mg_session.current_turn_index,
        lobby_key=lobby_key,
        phase=mg_session.phase,
        revision=mg_session.revision,
        turn_number=mg_session.turn_number,
    )
    await _broadcast_timer_sync(
        session_id=session_id,
        participants=participants,
        lobby_key=lobby_key,
        remaining_ms=(
            _remaining_grace_ms(mg_session)
            if _enum_value(mg_session.phase) == Phase.PAUSED.value
            else _remaining_turn_ms(mg_session)
        ),
        phase=mg_session.phase,
    )
    if resumed:
        await _schedule_session_phase_timer(
            session_id=session_id,
            competition_id=competition_id,
            game_type=game_type,
            delay_seconds=(getattr(mg_session, "turn_duration_ms", 0) or 0) / 1000,
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
            await _send_lobby_update(
                lobby_key,
                update_type="join",
                data={"membership_id": str(membership_id), "alias": alias},
                exclude=membership_id,
            )
        await _broadcast_lobby_state(lobby_key, exclude=membership_id)

    elif msg_type == "lobby_leave":
        _cancel_queue_expiry(lobby_key, membership_id)
        lobby_mgr.leave(lobby_key, membership_id)
        manager.disconnect(lobby_key, membership_id)
        await manager.broadcast(
            lobby_key,
            {"type": "player_left", "membership_id": str(membership_id), "alias": alias},
        )
        await _send_lobby_update(
            lobby_key,
            update_type="leave",
            data={"membership_id": str(membership_id), "alias": alias},
        )
        await _broadcast_lobby_state(lobby_key)

    elif msg_type == "queue_join":
        if not lobby_mgr.is_in_lobby(lobby_key, membership_id) or not manager.is_connected(lobby_key, membership_id):
            await _send_error(websocket, "NOT_IN_LOBBY", "يجب دخول اللوبي قبل الطابور")
            return
        from app.core.database import async_session  # noqa: PLC0415
        from app.modules.minigames.settings_helper import (  # noqa: PLC0415
            check_kill_switch,
            get_effective_setting,
            get_minigame_settings,
        )

        async with async_session() as db:
            season, cycle = await _get_active_season_cycle(db, competition_id)
            settings_snapshot = await get_minigame_settings(
                db,
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
            await _send_error(websocket, "MINIGAMES_DISABLED", "الألعاب المصغرة غير مفعلة في هذه المسابقة")
            return
        if not kill_switch.can_matchmake:
            await _send_error(websocket, "MATCHMAKING_DISABLED", kill_switch.message_ar or "التوفيق معطل حالياً")
            return
        queue_timeout_sec = int(settings_snapshot.get(f"{game_type}_queue_timeout_sec", 120))
        lobby_mgr.queue_join(lobby_key, membership_id)
        await websocket.send_json({"type": "queue_status", "queued": True})
        matched = lobby_mgr.try_match(lobby_key)
        if matched:
            await _handle_queue_match(
                lobby_key,
                competition_id,
                game_type,
                matched_ids=matched,
            )
        else:
            await _schedule_queue_expiry(
                lobby_key=lobby_key,
                membership_id=membership_id,
                delay_seconds=queue_timeout_sec,
            )
            await _broadcast_lobby_state(lobby_key)

    elif msg_type == "queue_leave":
        _cancel_queue_expiry(lobby_key, membership_id)
        lobby_mgr.queue_leave(lobby_key, membership_id)
        await websocket.send_json({"type": "queue_status", "queued": False})
        await _broadcast_lobby_state(lobby_key)

    elif msg_type == "challenge_send":
        await _handle_challenge_send(websocket, msg, competition_id, game_type, membership_info)

    elif msg_type == "challenge_respond":
        await _handle_challenge_respond(websocket, msg, competition_id, game_type, membership_info)

    elif msg_type == "reconnect_claim":
        await _handle_reconnect_claim(websocket, msg, competition_id, game_type, membership_info)

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
        session_rooms = [
            room
            for room in manager.get_player_rooms(membership_id)
            if room.startswith("session:")
        ]
        _cancel_queue_expiry(lobby_key, membership_id)

        # Clean up lobby presence first so remaining lobby members see the disconnect.
        if lobby_mgr.is_in_lobby(lobby_key, membership_id) or manager.is_connected(lobby_key, membership_id):
            lobby_mgr.leave(lobby_key, membership_id)
            manager.disconnect(lobby_key, membership_id)
            await manager.broadcast(
                lobby_key,
                {"type": "player_left", "membership_id": str(membership_id), "alias": membership_info["alias"]},
            )
            await _send_lobby_update(
                lobby_key,
                update_type="leave",
                data={"membership_id": str(membership_id), "alias": membership_info["alias"]},
            )
            await _broadcast_lobby_state(lobby_key)

        # Remove the player from active session rooms before pause handling so
        # grace resolution can see the remaining connected peers accurately.
        for room in session_rooms:
            manager.disconnect(room, membership_id)

        for room in session_rooms:
            try:
                session_id = uuid.UUID(room.split(":", 1)[1])
            except (IndexError, ValueError):
                continue
            await _pause_session_for_disconnect(
                session_id=session_id,
                competition_id=competition_id,
                game_type=game_type,
                membership_id=membership_id,
            )

        # Clean up any leftover non-lobby rooms.
        manager.disconnect_all(membership_id)
        _clear_all_action_rate_windows(membership_id)
