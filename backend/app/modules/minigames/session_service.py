"""Minigame session service — creation and phase transitions.

Pure functions (sync, no DB) are defined first for easy unit testing.
Async functions that touch the database follow.

Import strategy: only ``app.core.enums`` and ``app.modules.minigames.state_machine``
are imported at module level (both are stdlib-only dependency chains).
Everything that pulls in pydantic_settings or SQLAlchemy is deferred to the
function body so that pure-function tests can import this module without a
running application environment.
"""

from __future__ import annotations

import secrets
import uuid
from typing import TYPE_CHECKING, Any

from app.core.enums import MinigameMatchType, MinigameSessionPhase as Phase
from app.modules.minigames.state_machine import is_terminal, validate_transition

# N-player model: turn tracking uses current_turn_index (int) on MinigameSession,
# and participant rows live in minigame_session_participants with per-slot
# reconnect tokens. create_session accepts a list of membership ids.

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.modules.minigames.models import MinigameSession


def _now():
    """Lazy wrapper around now_riyadh_naive() to avoid top-level import."""
    from app.core.utils import now_riyadh_naive  # noqa: PLC0415
    return now_riyadh_naive()


# ---------------------------------------------------------------------------
# Pure validation / computation helpers (sync, no DB)
# ---------------------------------------------------------------------------


def validate_session_creation(
    *,
    game_type_id: str,
    plugin_exists: bool,
    plugin_status: str,
    player_balance: int,
    buy_in_amount: int,
    is_bankrupt: bool,
) -> list[str]:
    """Validate inputs for creating a new minigame session.

    Returns a list of Arabic error strings. An empty list means the inputs
    are valid. Callers should check the list before proceeding.
    """
    errors: list[str] = []

    if not plugin_exists:
        errors.append(f"نوع اللعبة '{game_type_id}' غير موجود")
        # No point checking further plugin-related rules.
        return errors

    if plugin_status == "disabled":
        errors.append("هذه اللعبة معطلة حالياً")

    if is_bankrupt:
        errors.append("اللاعب مفلس ولا يمكنه الدخول في مبارزة")

    if player_balance < buy_in_amount:
        errors.append(f"رصيد غير كافٍ — تحتاج {buy_in_amount} نقطة للدخول")

    return errors


def compute_transition_update(
    *,
    current_phase: Phase | str,
    target_phase: Phase | str,
    current_revision: int,
    terminal_reason: str | None = None,
    winner_slot_index: int | None = None,
) -> dict[str, Any]:
    """Compute the field updates required for a phase transition.

    Calls ``validate_transition`` from the state machine — raises
    ``ValueError`` if the transition is not allowed.

    Returns a dict of column-value pairs that should be applied to the
    session row. Does NOT mutate any model; the caller is responsible for
    applying the returned dict.
    """
    # Normalize enum-like inputs so transition-specific field updates behave
    # the same for ORM enums and raw string phases.
    if isinstance(current_phase, str):
        current_phase_enum = Phase(current_phase)
    else:
        current_phase_enum = current_phase

    # Normalize to enum for is_terminal check.
    if isinstance(target_phase, str):
        target_phase_enum = Phase(target_phase)
    else:
        target_phase_enum = target_phase

    # Raises ValueError on illegal transition.
    validate_transition(current_phase, target_phase)

    now = _now()

    updates: dict[str, Any] = {
        "phase": target_phase_enum,
        "revision": current_revision + 1,
        "updated_at": now,
    }

    if is_terminal(target_phase_enum):
        updates["completed_at"] = now
        updates["terminal_reason"] = terminal_reason
        # winner_slot_index passed by caller if known (None for cancellations).
        if winner_slot_index is not None:
            updates["winner_slot_index"] = winner_slot_index

    if target_phase_enum == Phase.IN_PROGRESS:
        updates["turn_started_at"] = now
        if current_phase_enum == Phase.READY:
            updates["started_at"] = now
            updates["current_turn_index"] = 0

    if target_phase_enum == Phase.OVERTIME:
        updates["turn_started_at"] = now

    return updates


# ---------------------------------------------------------------------------
# Async database functions
# ---------------------------------------------------------------------------


async def create_session(
    session: AsyncSession,
    *,
    game_type: str,
    competition_id: uuid.UUID,
    player_membership_ids: list[uuid.UUID],
    match_type: MinigameMatchType,
    buy_in_amount: int,
    settings_snapshot: dict,
    min_players: int = 2,
    max_players: int = 2,
    season_id: uuid.UUID | None = None,
    cycle_id: uuid.UUID | None = None,
    turn_duration_ms: int = 30000,
    grace_timer_ms: int = 60000,
) -> MinigameSession:
    """Create a new ``MinigameSession`` with N participants (1-8 players).

    Creates one :class:`MinigameSessionParticipant` row per player with
    ``slot_index`` ``0..N-1``. Generates a unique ``reconnect_token`` per
    participant. Returns the created session (with participants flushed but
    not eagerly loaded).
    """
    from app.modules.minigames.models import (  # noqa: PLC0415
        MinigameSession as _MinigameSession,
        MinigameSessionParticipant as _MinigameSessionParticipant,
    )

    num_players = len(player_membership_ids)
    if num_players < 1 or num_players > 8:
        raise ValueError(
            f"عدد اللاعبين يجب أن يكون بين 1 و 8 (تم إعطاء {num_players})"
        )

    # Check for duplicate participants.
    if len(set(player_membership_ids)) != num_players:
        raise ValueError("لا يمكن أن يكون نفس اللاعب في جلسة واحدة أكثر من مرة")

    mg_session = _MinigameSession(
        game_type=game_type,
        competition_id=competition_id,
        season_id=season_id,
        cycle_id=cycle_id,
        phase=Phase.CREATED,
        revision=0,
        num_players=num_players,
        min_players=min_players,
        max_players=max_players,
        current_turn_index=None,  # Set when transitioning to IN_PROGRESS.
        match_type=match_type,
        buy_in_amount=buy_in_amount,
        settings_snapshot=settings_snapshot,
        turn_duration_ms=turn_duration_ms,
        grace_timer_ms=grace_timer_ms,
        correlation_id=uuid.uuid4(),
    )
    session.add(mg_session)
    await session.flush()  # Get mg_session.id.

    # Create participant rows — one per player, with unique reconnect tokens.
    for slot_index, membership_id in enumerate(player_membership_ids):
        participant = _MinigameSessionParticipant(
            session_id=mg_session.id,
            membership_id=membership_id,
            slot_index=slot_index,
            reconnect_token=secrets.token_urlsafe(48),
        )
        session.add(participant)

    await session.flush()
    return mg_session


async def get_session_participants(
    session: AsyncSession,
    session_id: uuid.UUID,
) -> list[dict]:
    """Load all participants for a session, ordered by ``slot_index``.

    Returns a list of dicts:
    ``[{"membership_id", "slot_index", "reconnect_token"}, ...]``.
    """
    from sqlalchemy import select  # noqa: PLC0415
    from app.modules.minigames.models import (  # noqa: PLC0415
        MinigameSessionParticipant as _MinigameSessionParticipant,
    )

    result = await session.execute(
        select(_MinigameSessionParticipant)
        .where(_MinigameSessionParticipant.session_id == session_id)
        .order_by(_MinigameSessionParticipant.slot_index)
    )
    participants = result.scalars().all()
    return [
        {
            "membership_id": p.membership_id,
            "slot_index": p.slot_index,
            "reconnect_token": p.reconnect_token,
        }
        for p in participants
    ]


async def transition_session(
    session: AsyncSession,
    *,
    session_id: uuid.UUID,
    expected_revision: int,
    target_phase: Phase | str,
    terminal_reason: str | None = None,
    winner_slot_index: int | None = None,
    actor_type: str = "system",
    actor_membership_id: uuid.UUID | None = None,
    extra_updates: dict[str, Any] | None = None,
    event_type: str = "transition",
    payload: dict[str, Any] | None = None,
    result: dict[str, Any] | None = None,
) -> MinigameSession | None:
    """Attempt an optimistic-locked phase transition on a session.

    Loads the session row and verifies the revision matches
    ``expected_revision``.  If not (concurrent update), returns ``None``
    — the caller should treat this as an optimistic lock failure and retry
    or surface an appropriate error.

    On success:
    - Issues a WHERE-guarded UPDATE (id = session_id AND revision = expected_revision).
    - Appends a ``MinigameSessionEvent`` to the audit log.
    - Returns the refreshed ``MinigameSession`` instance.

    Raises ``ValueError`` if the transition is not allowed by the state
    machine (propagated from ``compute_transition_update``).
    """
    from sqlalchemy import select, update  # noqa: PLC0415
    from app.modules.minigames.models import (  # noqa: PLC0415
        MinigameSession as _MinigameSession,
        MinigameSessionEvent as _MinigameSessionEvent,
    )

    # Load current session state.
    result = await session.execute(
        select(_MinigameSession).where(_MinigameSession.id == session_id)
    )
    mg_session = result.scalar_one_or_none()
    if mg_session is None:
        return None

    # Optimistic lock check at application layer.
    if mg_session.revision != expected_revision:
        return None

    from_phase = mg_session.phase

    # Compute updates — raises ValueError for invalid transition.
    updates = compute_transition_update(
        current_phase=from_phase,
        target_phase=target_phase,
        current_revision=expected_revision,
        terminal_reason=terminal_reason,
        winner_slot_index=winner_slot_index,
    )
    if extra_updates:
        for key, value in extra_updates.items():
            if key in {"phase", "revision"}:
                continue
            updates[key] = value

    # Optimistic-locked UPDATE at database layer.
    stmt = (
        update(_MinigameSession)
        .where(
            _MinigameSession.id == session_id,
            _MinigameSession.revision == expected_revision,
        )
        .values(**updates)
        .returning(_MinigameSession.revision)
    )
    update_result = await session.execute(stmt)
    updated_row = update_result.fetchone()

    if updated_row is None:
        # Another process won the race — revision no longer matches.
        return None

    # Log the transition event.
    event = _MinigameSessionEvent(
        session_id=session_id,
        revision=updates["revision"],
        event_type=event_type,
        actor_type=actor_type,
        actor_membership_id=actor_membership_id,
        payload=payload or {},
        result=result or {},
        from_phase=str(from_phase),
        to_phase=str(updates["phase"]),
        correlation_id=mg_session.correlation_id,
    )
    session.add(event)

    # Refresh in-memory state to reflect the applied updates.
    await session.refresh(mg_session)
    return mg_session
