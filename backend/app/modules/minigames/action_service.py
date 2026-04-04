"""Minigame action service — envelope validation, idempotency, and action processing.

Pure functions (sync, no DB):
    ActionError              — structured error dataclass
    validate_action_envelope — pre-flight checks before touching the DB

Async functions (require DB session):
    check_idempotency        — look up a cached action receipt
    process_action           — full N-player action pipeline with optimistic locking
"""

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import MinigameSessionPhase as Phase
from app.modules.minigames.models import (
    MinigameActionReceipt,
    MinigameSession,
    MinigameSessionEvent,
)
from app.modules.minigames.plugin import GameTypePlugin
from app.modules.minigames.runtime_state import (
    is_parallel_selection_phase,
    resolve_state_timer_duration_ms,
    stamp_phase_deadlines,
)
from app.core.utils import now_riyadh_naive


# ── Constants ─────────────────────────────────────────────────────────────────

PLAYABLE_PHASES: frozenset[Phase] = frozenset({Phase.IN_PROGRESS, Phase.OVERTIME})


# ── Pure types ────────────────────────────────────────────────────────────────

@dataclass
class ActionError:
    """Structured validation error returned from pure validation functions."""
    code: str
    message_ar: str


# ── Pure validation ───────────────────────────────────────────────────────────

def validate_action_envelope(
    *,
    envelope: dict,
    session_phase: Phase | str,
    session_revision: int,
    current_turn_index: int | None,
    participants: list[dict],
    state: dict | None = None,
) -> ActionError | None:
    """Validate an incoming action envelope before any DB work.

    Checks are performed in order; the first failure is returned immediately.

    Args:
        envelope:            Raw action payload from the client. Expected keys:
                             state_revision, actor_membership_id, action.
        session_phase:       Current phase of the minigame session.
        session_revision:    Current authoritative revision stored in the DB.
        current_turn_index:  Which slot's turn it is, or None for solo games
                             (solo always allows).
        participants:        List of dicts with at least 'membership_id' and
                             'slot_index' keys, ordered by slot_index
                             (0, 1, 2, ..., N-1).

    Returns:
        None if the envelope is valid, ActionError otherwise.
    """

    # a. Session must be in a PLAYABLE phase
    if isinstance(session_phase, str):
        try:
            session_phase = Phase(session_phase)
        except ValueError:
            pass  # Will fail the next check anyway

    if session_phase not in PLAYABLE_PHASES:
        return ActionError(
            code="SESSION_ENDED",
            message_ar="الجلسة منتهية أو غير نشطة",
        )

    # b. state_revision from envelope must be >= session_revision (stale check)
    envelope_revision = envelope.get("state_revision")
    if envelope_revision is None or envelope_revision < session_revision:
        return ActionError(
            code="STALE_STATE",
            message_ar="حالة اللعبة قديمة — يرجى تحديث الشاشة",
        )

    # c. actor_membership_id must belong to a participant — resolve slot
    actor_id = envelope.get("actor_membership_id")
    actor_slot: int | None = None
    for p in participants:
        if p["membership_id"] == actor_id:
            actor_slot = p["slot_index"]
            break

    if actor_slot is None:
        return ActionError(
            code="NOT_PARTICIPANT",
            message_ar="أنت لست مشاركاً في هذه الجلسة",
        )

    # d. Turn check — skip for solo games (≤1 participant) or when
    #    current_turn_index is None (turn not yet established).
    if len(participants) <= 1 or current_turn_index is None:
        return None

    action = envelope.get("action", envelope.get("payload", {})) or {}
    action_type = action.get("type")
    if is_parallel_selection_phase(state) and action_type in {"select_words", "redraw"}:
        return None

    if actor_slot != current_turn_index:
        return ActionError(
            code="NOT_YOUR_TURN",
            message_ar="ليس دورك — انتظر دور الخصم",
        )

    return None


# ── Async — DB-backed helpers ─────────────────────────────────────────────────

async def check_idempotency(
    session: AsyncSession,
    action_id: uuid.UUID | None = None,
    *,
    session_id: uuid.UUID | None = None,
    actor_membership_id: uuid.UUID | None = None,
    client_seq: int | None = None,
) -> dict | None:
    """Return cached action response if this action was already processed.

    The primary idempotency key is ``action_id``. As a fallback, callers may
    supply ``session_id`` + ``actor_membership_id`` + ``client_seq`` to reuse
    the unique per-player sequence constraint when ``action_id`` is unavailable.
    """
    receipt = None

    if action_id is not None:
        result = await session.execute(
            select(MinigameActionReceipt).where(
                MinigameActionReceipt.action_id == action_id
            )
        )
        receipt = result.scalar_one_or_none()

    if (
        receipt is None
        and session_id is not None
        and actor_membership_id is not None
        and client_seq is not None
    ):
        result = await session.execute(
            select(MinigameActionReceipt).where(
                MinigameActionReceipt.session_id == session_id,
                MinigameActionReceipt.actor_membership_id == actor_membership_id,
                MinigameActionReceipt.client_seq == client_seq,
            )
        )
        receipt = result.scalar_one_or_none()

    return receipt.response if receipt is not None else None


async def get_expected_client_seq(
    session: AsyncSession,
    *,
    session_id: uuid.UUID,
    actor_membership_id: uuid.UUID,
) -> int:
    """Return the next valid client_seq for a player in a session."""
    result = await session.execute(
        select(func.max(MinigameActionReceipt.client_seq)).where(
            MinigameActionReceipt.session_id == session_id,
            MinigameActionReceipt.actor_membership_id == actor_membership_id,
        )
    )
    max_seen = result.scalar_one_or_none()
    if max_seen is None:
        return 1
    return int(max_seen) + 1


async def process_action(
    session: AsyncSession,
    *,
    mg_session: MinigameSession,
    plugin: GameTypePlugin,
    envelope: dict,
    participants: list[dict],
) -> dict:
    """Execute a validated action through the full N-player pipeline.

    Caller must have already validated the envelope via validate_action_envelope.

    Steps:
        1. plugin.validate_action   — raises ValueError on rule violation
        2. plugin.apply_action      — returns (new_state, side_effects)
        3. Advance turn             — (current_turn_index + 1) % num_players
        4. Optimistic lock UPDATE   — WHERE revision = current
        5. Log MinigameSessionEvent
        6. Log MinigameActionReceipt (idempotency)
        7. plugin.evaluate_terminal — check for game end

    Args:
        session:       Active async DB session.
        mg_session:    The MinigameSession ORM instance to mutate.
        plugin:        Game type plugin implementing validate/apply/evaluate.
        envelope:      Validated action envelope from the client.
        participants:  List of dicts with 'membership_id', 'slot_index',
                       'reconnect_token' keys, ordered by slot_index.

    Returns:
        Dict with the public action result fields plus ``_state`` for the
        caller's internal follow-up broadcast.

    Raises:
        ValueError   — if the plugin rejects the action.
        RuntimeError — if the optimistic lock fails (concurrent modification).
    """
    # 1. Call plugin to validate and apply the action
    action = envelope.get("action", envelope.get("payload", {}))
    actor_membership_id = envelope.get("actor_membership_id")
    client_seq = envelope.get("client_seq")
    action_id = envelope.get("action_id") or uuid.uuid4()

    if not isinstance(actor_membership_id, uuid.UUID):
        raise ValueError("معرف اللاعب غير صالح")
    if not isinstance(client_seq, int):
        raise ValueError("تسلسل الإجراء غير صالح")
    if not isinstance(action_id, uuid.UUID):
        raise ValueError("معرف الإجراء غير صالح")

    validation_err = plugin.validate_action(action, mg_session.game_state)
    if validation_err:
        raise ValueError(validation_err)

    new_state, side_effects = plugin.apply_action(action, mg_session.game_state)
    terminal_result = plugin.evaluate_terminal(new_state)
    previous_game_phase = (mg_session.game_state or {}).get("game_phase")
    next_game_phase = (new_state or {}).get("game_phase")

    # 2. Advance turn and turn counter using the authoritative participant count.
    num_players = max(len(participants), int(getattr(mg_session, "num_players", 0) or 0), 1)
    current_idx = (
        mg_session.current_turn_index
        if mg_session.current_turn_index is not None
        else 0
    )
    if previous_game_phase == "word_selection":
        if next_game_phase == "word_selection":
            next_turn_index = None
        else:
            next_turn_index = 0
    elif num_players <= 1:
        next_turn_index = current_idx
    else:
        next_turn_index = (current_idx + 1) % num_players
    new_revision = mg_session.revision + 1
    turn_increment = 0 if previous_game_phase == "word_selection" else 1
    new_turn_number = (getattr(mg_session, "turn_number", 0) or 0) + turn_increment
    now = now_riyadh_naive()
    if previous_game_phase == "word_selection" and next_game_phase == "word_selection":
        timer_started_at = getattr(mg_session, "turn_started_at", None) or now
        new_turn_duration_ms = getattr(mg_session, "turn_duration_ms", None)
    else:
        timer_started_at = now
        new_turn_duration_ms = resolve_state_timer_duration_ms(
            new_state,
            fallback_ms=getattr(mg_session, "turn_duration_ms", None),
        )
    new_state = stamp_phase_deadlines(
        new_state,
        started_at=timer_started_at,
        duration_ms=new_turn_duration_ms,
    )

    # 3. Optimistic lock UPDATE
    update_stmt = (
        update(MinigameSession)
        .where(
            MinigameSession.id == mg_session.id,
            MinigameSession.revision == mg_session.revision,
        )
        .values(
            game_state=new_state,
            current_turn_index=next_turn_index,
            turn_number=new_turn_number,
            turn_started_at=timer_started_at,
            turn_duration_ms=new_turn_duration_ms,
            revision=new_revision,
            updated_at=now,
        )
        .returning(MinigameSession.revision)
    )
    update_result = await session.execute(update_stmt)
    if update_result.fetchone() is None:
        raise RuntimeError(
            "Optimistic lock failed — session was modified concurrently"
        )

    result_payload: dict[str, Any] = {
        "success": True,
        "revision": new_revision,
        "side_effects": side_effects,
        "terminal_result": terminal_result,
        "next_turn_index": next_turn_index,
        "turn_number": new_turn_number,
    }

    # Keep the in-memory ORM object aligned with the committed update so any
    # same-request follow-up logic does not read stale fields.
    mg_session.game_state = new_state
    mg_session.current_turn_index = next_turn_index
    mg_session.turn_number = new_turn_number
    mg_session.turn_started_at = timer_started_at
    mg_session.turn_duration_ms = new_turn_duration_ms
    mg_session.revision = new_revision
    mg_session.updated_at = now

    # 4. Log event
    event = MinigameSessionEvent(
        session_id=mg_session.id,
        revision=new_revision,
        event_type="action",
        actor_type="participant",
        actor_membership_id=actor_membership_id,
        action_type=action.get("type"),
        payload=action,
        result={
            "side_effects": side_effects,
            "next_turn_index": next_turn_index,
            "turn_number": new_turn_number,
            "terminal_result": terminal_result,
        },
        correlation_id=mg_session.correlation_id,
    )
    session.add(event)

    # 5. Log receipt for idempotency
    receipt = MinigameActionReceipt(
        action_id=action_id,
        session_id=mg_session.id,
        actor_membership_id=actor_membership_id,
        client_seq=client_seq,
        response=dict(result_payload),
    )
    session.add(receipt)

    return {
        **result_payload,
        "_state": new_state,
    }
