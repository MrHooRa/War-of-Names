"""Minigame action service — envelope validation, idempotency, and action processing.

Pure functions (sync, no DB):
    ActionError              — structured error dataclass
    validate_action_envelope — pre-flight checks before touching the DB

Async functions (require DB session):
    check_idempotency        — look up a cached action receipt
    process_action           — full action pipeline with optimistic locking
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import MinigameSessionPhase as Phase, MinigameTurnSide
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
    current_turn: MinigameTurnSide | str | None,
    player_1_membership_id,
    player_2_membership_id,
) -> ActionError | None:
    """Validate an incoming action envelope before any DB work.

    Checks are performed in order; the first failure is returned immediately.

    Args:
        envelope:                 Raw action payload from the client.
                                  Expected keys: state_revision, actor_membership_id, action.
        session_phase:            Current phase of the minigame session.
        session_revision:         Current authoritative revision stored in the DB.
        current_turn:             Whose turn it is (PLAYER_1 / PLAYER_2), or None.
        player_1_membership_id:   Membership ID of player 1.
        player_2_membership_id:   Membership ID of player 2, or None for solo games.

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

    # c. actor_membership_id must be player_1 or player_2
    actor_id = envelope.get("actor_membership_id")
    valid_participants = {player_1_membership_id}
    if player_2_membership_id is not None:
        valid_participants.add(player_2_membership_id)

    if actor_id not in valid_participants:
        return ActionError(
            code="NOT_PARTICIPANT",
            message_ar="أنت لست مشاركاً في هذه الجلسة",
        )

    # d. Turn check — SKIP FOR SOLO GAMES (player_2_membership_id is None)
    if player_2_membership_id is not None:
        # 1v1 game — enforce turn order
        if isinstance(current_turn, str):
            try:
                current_turn = MinigameTurnSide(current_turn)
            except ValueError:
                current_turn = None

        expected_actor = (
            player_1_membership_id
            if current_turn == MinigameTurnSide.PLAYER_1
            else player_2_membership_id
        )

        if actor_id != expected_actor:
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
) -> dict:
    """Execute a validated action through the full pipeline.

    Steps:
        a. plugin.validate_action   — raises ValueError on rule violation
        b. plugin.apply_action      — returns (new_state, side_effects)
        c. Advance turn             — PLAYER_1 ↔ PLAYER_2 for 1v1; unchanged for solo
        d. Optimistic lock UPDATE   — WHERE revision = current
        e. Log MinigameSessionEvent
        f. Log MinigameActionReceipt (idempotency)
        g. plugin.evaluate_terminal — check for game end

    Returns a result dict with: success, revision, side_effects, terminal_result.

    Raises:
        ValueError   — if the plugin rejects the action or the optimistic lock fails
        RuntimeError — if a race condition prevents the update (stale lock)
    """

    action = envelope.get("action", {})
    actor_id = envelope.get("actor_membership_id")
    action_id = envelope.get("action_id")
    client_seq = envelope.get("client_seq", 0)

    current_state = mg_session.game_state
    current_revision = mg_session.revision

    # a. Plugin-level action validation
    error_msg = plugin.validate_action(action, current_state)
    if error_msg is not None:
        raise ValueError(error_msg)

    # b. Apply the action
    new_state, side_effects = plugin.apply_action(action, current_state)

    # c. Advance turn
    if mg_session.player_2_membership_id is None:
        # Solo game — keep PLAYER_1 always
        next_turn = MinigameTurnSide.PLAYER_1
    else:
        # 1v1 — alternate turns
        if mg_session.current_turn == MinigameTurnSide.PLAYER_1:
            next_turn = MinigameTurnSide.PLAYER_2
        else:
            next_turn = MinigameTurnSide.PLAYER_1

    new_revision = current_revision + 1
    new_turn_number = mg_session.turn_number + 1
    now = now_riyadh_naive()

    # d. Optimistic lock UPDATE (WHERE revision = current)
    update_result = await session.execute(
        update(MinigameSession)
        .where(
            MinigameSession.id == mg_session.id,
            MinigameSession.revision == current_revision,
        )
        .values(
            game_state=new_state,
            revision=new_revision,
            current_turn=next_turn,
            turn_number=new_turn_number,
            turn_started_at=now,
            updated_at=now,
        )
        .returning(MinigameSession.id)
    )

    updated_row = update_result.scalar_one_or_none()
    if updated_row is None:
        raise RuntimeError("تعديل متزامن — يرجى إعادة المحاولة")

    # e. Log MinigameSessionEvent
    event = MinigameSessionEvent(
        id=uuid.uuid4(),
        session_id=mg_session.id,
        revision=new_revision,
        event_type="action",
        actor_type="player",
        actor_membership_id=actor_id,
        action_type=action.get("type"),
        payload=action,
        result={"side_effects": side_effects},
        from_phase=mg_session.phase.value if isinstance(mg_session.phase, Phase) else str(mg_session.phase),
        to_phase=mg_session.phase.value if isinstance(mg_session.phase, Phase) else str(mg_session.phase),
        correlation_id=mg_session.correlation_id,
        created_at=now,
    )
    session.add(event)

    # f. Log MinigameActionReceipt (idempotency)
    result_dict: dict = {
        "success": True,
        "revision": new_revision,
        "side_effects": side_effects,
    }

    if action_id is not None:
        receipt = MinigameActionReceipt(
            action_id=action_id if isinstance(action_id, uuid.UUID) else uuid.UUID(str(action_id)),
            session_id=mg_session.id,
            actor_membership_id=actor_id,
            client_seq=client_seq,
            response=result_dict,
            created_at=now,
        )
        session.add(receipt)

    # g. Check terminal state via plugin
    terminal_result = plugin.evaluate_terminal(new_state)
    result_dict["terminal_result"] = terminal_result

    await session.flush()

    return result_dict
