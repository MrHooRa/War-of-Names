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

# TODO(sprint-b): N-player refactor — MinigameTurnSide enum removed.
# Turn tracking now uses current_turn_index (int) on MinigameSession.
# create_session / transition_session still hold the legacy 1v1 shape and
# will be rewritten in Sprint B against the new participants table.

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
    winner_membership_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Compute the field updates required for a phase transition.

    Calls ``validate_transition`` from the state machine — raises
    ``ValueError`` if the transition is not allowed.

    Returns a dict of column-value pairs that should be applied to the
    session row. Does NOT mutate any model; the caller is responsible for
    applying the returned dict.
    """
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
        # TODO(sprint-b): replace legacy winner_membership_id with
        # winner_slot_index on MinigameSession.
        updates["winner_membership_id"] = winner_membership_id

    if target_phase_enum == Phase.IN_PROGRESS:
        updates["started_at"] = now
        updates["turn_started_at"] = now
        # TODO(sprint-b): set current_turn_index = 0 for N-player sessions.
        updates["current_turn"] = "player_1"

    return updates


# ---------------------------------------------------------------------------
# Async database functions
# ---------------------------------------------------------------------------


async def create_session(
    session: AsyncSession,
    *,
    game_type: str,
    competition_id: uuid.UUID,
    player_1_membership_id: uuid.UUID,
    match_type: MinigameMatchType,
    buy_in_amount: int,
    settings_snapshot: dict,
    season_id: uuid.UUID | None = None,
    cycle_id: uuid.UUID | None = None,
    player_2_membership_id: uuid.UUID | None = None,
    turn_duration_ms: int = 30000,
    grace_timer_ms: int = 60000,
) -> MinigameSession:
    """Persist a new ``MinigameSession`` in the CREATED phase.

    TODO(sprint-b): N-player refactor — this function still constructs the
    legacy 1v1 row with ``player_1_membership_id`` / ``player_2_membership_id``
    / ``reconnect_token_p1`` / ``reconnect_token_p2`` kwargs that no longer
    exist on :class:`MinigameSession`. Sprint B will rewrite it to accept a
    list of participant memberships and insert rows in
    ``minigame_session_participants`` with per-slot reconnect tokens.
    """
    del (  # silence unused-arg warnings until Sprint B rewrite
        session, game_type, competition_id, player_1_membership_id, match_type,
        buy_in_amount, settings_snapshot, season_id, cycle_id,
        player_2_membership_id, turn_duration_ms, grace_timer_ms,
    )
    _ = secrets  # keep import reachable
    raise NotImplementedError(
        "create_session is awaiting N-player rewrite in Sprint B"
    )


async def transition_session(
    session: AsyncSession,
    *,
    session_id: uuid.UUID,
    expected_revision: int,
    target_phase: Phase | str,
    terminal_reason: str | None = None,
    winner_membership_id: uuid.UUID | None = None,
    actor_type: str = "system",
    actor_membership_id: uuid.UUID | None = None,
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
        winner_membership_id=winner_membership_id,
    )

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
        event_type="transition",
        actor_type=actor_type,
        actor_membership_id=actor_membership_id,
        from_phase=str(from_phase),
        to_phase=str(updates["phase"]),
        correlation_id=mg_session.correlation_id,
    )
    session.add(event)

    # Refresh in-memory state to reflect the applied updates.
    await session.refresh(mg_session)
    return mg_session
