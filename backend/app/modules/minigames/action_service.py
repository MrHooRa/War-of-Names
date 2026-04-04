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

from app.core.enums import MinigameSessionPhase as Phase

# TODO(sprint-b): N-player refactor — MinigameTurnSide enum removed.
# Turn tracking now uses MinigameSession.current_turn_index (int) + the
# MinigameSessionParticipant table. The service functions below still hold
# the old 1v1 shape and will be rewritten in Sprint B.
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


def _resolve_actor_slot(
    *,
    actor_membership_id,
    player_1_membership_id,
    player_2_membership_id,
) -> str | None:
    if actor_membership_id == player_1_membership_id:
        return "player_1"
    if actor_membership_id == player_2_membership_id:
        return "player_2"
    return None


# ── Pure validation ───────────────────────────────────────────────────────────

def validate_action_envelope(
    *,
    envelope: dict,
    session_phase: Phase | str,
    session_revision: int,
    current_turn: str | None,  # TODO(sprint-b): switch to current_turn_index + participants list
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
    # TODO(sprint-b): Replace with N-player turn check using current_turn_index
    # and the MinigameSessionParticipant table. Current shape accepts raw string
    # turn markers ("player_1" / "player_2") for legacy 1v1 callers only.
    if player_2_membership_id is not None:
        # 1v1 game — enforce turn order (legacy string compare)
        turn_str = current_turn if isinstance(current_turn, str) else None

        expected_actor = (
            player_1_membership_id
            if turn_str == "player_1"
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

    # TODO(sprint-b): N-player refactor — process_action needs to be rewritten
    # to resolve the actor's slot via MinigameSessionParticipant lookup and
    # advance current_turn_index modulo num_players. The full async pipeline
    # (optimistic lock, event log, receipt) will be re-implemented in Sprint B.
    del session, mg_session, plugin, envelope  # silence unused-arg warnings
    raise NotImplementedError(
        "process_action is awaiting N-player rewrite in Sprint B"
    )
