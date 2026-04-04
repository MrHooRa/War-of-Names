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

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import MinigameSessionPhase as Phase
from app.modules.minigames.models import (
    MinigameActionReceipt,
    MinigameSession,
    MinigameSessionEvent,
)
from app.modules.minigames.plugin import GameTypePlugin
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

    if actor_slot != current_turn_index:
        return ActionError(
            code="NOT_YOUR_TURN",
            message_ar="ليس دورك — انتظر دور الخصم",
        )

    return None


# ── Async — DB-backed helpers ─────────────────────────────────────────────────

async def check_idempotency(
    session: AsyncSession,
    action_id: uuid.UUID,
) -> dict | None:
    """Return cached action response if action_id was already processed, else None."""
    result = await session.execute(
        select(MinigameActionReceipt).where(
            MinigameActionReceipt.action_id == action_id
        )
    )
    receipt = result.scalar_one_or_none()
    return receipt.response if receipt is not None else None


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
        Dict with: success, revision, new_state, side_effects, terminal_result,
        next_turn_index.

    Raises:
        ValueError   — if the plugin rejects the action.
        RuntimeError — if the optimistic lock fails (concurrent modification).
    """
    del participants  # Currently unused beyond envelope validation; reserved for future

    # 1. Call plugin to validate and apply the action
    action = envelope.get("action", envelope.get("payload", {}))

    validation_err = plugin.validate_action(action, mg_session.game_state)
    if validation_err:
        raise ValueError(validation_err)

    new_state, side_effects = plugin.apply_action(action, mg_session.game_state)

    # 2. Advance turn: next_index = (current + 1) % num_players
    current_idx = mg_session.current_turn_index or 0
    next_turn_index = (current_idx + 1) % mg_session.num_players
    new_revision = mg_session.revision + 1
    now = now_riyadh_naive()

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
            turn_started_at=now,
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

    # 4. Log event
    event = MinigameSessionEvent(
        session_id=mg_session.id,
        revision=new_revision,
        event_type="action",
        actor_type="participant",
        actor_membership_id=envelope.get("actor_membership_id"),
        action_type=action.get("type"),
        payload=action,
        result={"side_effects": side_effects, "next_turn_index": next_turn_index},
        correlation_id=mg_session.correlation_id,
    )
    session.add(event)

    # 5. Log receipt for idempotency
    receipt = MinigameActionReceipt(
        action_id=envelope.get("action_id") or uuid.uuid4(),
        session_id=mg_session.id,
        revision=new_revision,
        response={
            "success": True,
            "new_state": new_state,
            "side_effects": side_effects,
        },
    )
    session.add(receipt)

    # 6. Check terminal condition
    terminal_result = plugin.evaluate_terminal(new_state)

    return {
        "success": True,
        "revision": new_revision,
        "new_state": new_state,
        "side_effects": side_effects,
        "terminal_result": terminal_result,
        "next_turn_index": next_turn_index,
    }
