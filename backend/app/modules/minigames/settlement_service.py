"""
Minigame Settlement Service.

Responsibilities:
  - Classify finished sessions into settlement types (NORMAL, FORFEIT, CANCEL, SOLO)
  - Execute the financial settlement by building ledger entries and persisting a
    MinigameSessionSettlement record.

Public surface:
  SettlementType              — StrEnum of the four settlement categories
  compute_settlement_type()   — pure, synchronous, fully testable
  execute_settlement()        — async, requires SQLAlchemy AsyncSession
  _get_loser_id()             — private helper; exposed for testing convenience
"""

from __future__ import annotations

import uuid
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.modules.minigames.models import MinigameSession, MinigameSessionSettlement


# ─── Settlement type enum ────────────────────────────────────────────────────

class SettlementType(StrEnum):
    NORMAL = "normal"
    FORFEIT = "forfeit"
    CANCEL = "cancel"
    SOLO = "solo"


# ─── Pure logic ──────────────────────────────────────────────────────────────

def compute_settlement_type(
    *,
    phase: str,
    terminal_reason: str | None,
    winner_membership_id: uuid.UUID | None,
    is_solo: bool,
) -> SettlementType:
    """
    Determine the SettlementType for a session that has reached a terminal phase.

    Rules (evaluated in order):
      1. Phase must be terminal — raises ValueError otherwise.
      2. CANCELLED → CANCEL (always, regardless of winner or is_solo).
      3. ABANDONED + winner exists → FORFEIT.
      4. ABANDONED + no winner → CANCEL (both sides disconnected).
      5. COMPLETED + is_solo → SOLO.
      6. COMPLETED + not is_solo → NORMAL.

    Parameters
    ----------
    phase:
        The session's current phase value (string or MinigameSessionPhase).
    terminal_reason:
        Optional string stored on the session explaining why it ended.
    winner_membership_id:
        UUID of the winning player, or None if there is no winner.
    is_solo:
        True when the session has no second player (player_2_membership_id is None).
    """
    # Import here to keep this function importable without a full app context.
    from app.modules.minigames.state_machine import is_terminal
    from app.core.enums import MinigameSessionPhase

    if not is_terminal(phase):
        raise ValueError("لا يمكن تسوية جلسة غير نهائية")

    # Normalise to the enum value for comparison
    try:
        phase_enum = MinigameSessionPhase(phase)
    except ValueError:
        phase_enum = phase  # type: ignore[assignment]

    if phase_enum == MinigameSessionPhase.CANCELLED:
        return SettlementType.CANCEL

    if phase_enum == MinigameSessionPhase.ABANDONED:
        if winner_membership_id is not None:
            return SettlementType.FORFEIT
        return SettlementType.CANCEL

    # COMPLETED
    if is_solo:
        return SettlementType.SOLO
    return SettlementType.NORMAL


# ─── Private helper ──────────────────────────────────────────────────────────

def _get_loser_id(mg_session: "MinigameSession") -> uuid.UUID | None:
    """
    Derive the loser's membership_id from the session.

    The loser is whichever player is *not* the winner.
    Returns None when there is no winner or the session is solo.
    """
    winner = mg_session.winner_membership_id
    if winner is None:
        return None

    p1 = mg_session.player_1_membership_id
    p2 = mg_session.player_2_membership_id

    if p2 is None:
        # Solo session — no loser
        return None

    return p2 if winner == p1 else p1


# ─── Async settlement executor ───────────────────────────────────────────────

async def execute_settlement(
    session: "AsyncSession",
    *,
    mg_session: "MinigameSession",
    winner_balance: int = 0,
    loser_balance: int = 0,
    player_1_balance: int = 0,
    player_2_balance: int = 0,
) -> "MinigameSessionSettlement":
    """
    Execute the financial settlement for a terminal minigame session.

    Idempotent: if a MinigameSessionSettlement already exists for this
    session_id, it is returned immediately without any additional work.

    Parameters
    ----------
    session:
        The SQLAlchemy async session to use for DB operations.
    mg_session:
        The MinigameSession ORM instance to settle.
    winner_balance:
        Current ledger balance of the winning player (used for NORMAL/FORFEIT).
    loser_balance:
        Current ledger balance of the losing player (informational; not consumed
        by any economy function at present, kept for API symmetry).
    player_1_balance:
        Current ledger balance of player 1 (used for CANCEL refunds).
    player_2_balance:
        Current ledger balance of player 2 (used for CANCEL refunds).
    """
    from sqlalchemy import select

    from app.core.enums import MinigameSettlementState
    from app.core.utils import now_riyadh_naive
    from app.modules.minigames.models import MinigameSessionSettlement
    from app.modules.minigames import economy

    # ── Idempotency check ────────────────────────────────────────────────────
    existing = await session.scalar(
        select(MinigameSessionSettlement).where(
            MinigameSessionSettlement.session_id == mg_session.id
        )
    )
    if existing is not None:
        return existing

    # ── Determine settlement type ────────────────────────────────────────────
    is_solo = mg_session.player_2_membership_id is None

    settlement_type = compute_settlement_type(
        phase=mg_session.phase,
        terminal_reason=mg_session.terminal_reason,
        winner_membership_id=mg_session.winner_membership_id,
        is_solo=is_solo,
    )

    loser_id = _get_loser_id(mg_session)

    # ── Build ledger entries ─────────────────────────────────────────────────
    entries = []

    if settlement_type == SettlementType.NORMAL:
        entries = economy.create_normal_settlement_entries(
            winner_membership_id=mg_session.winner_membership_id,
            loser_membership_id=loser_id,
            competition_id=mg_session.competition_id,
            session_id=mg_session.id,
            buy_in_amount=mg_session.buy_in_amount,
            winner_balance=winner_balance,
            season_id=mg_session.season_id,
            cycle_id=mg_session.cycle_id,
        )

    elif settlement_type == SettlementType.FORFEIT:
        entries = economy.create_forfeit_settlement_entries(
            winner_membership_id=mg_session.winner_membership_id,
            competition_id=mg_session.competition_id,
            session_id=mg_session.id,
            buy_in_amount=mg_session.buy_in_amount,
            winner_balance=winner_balance,
            season_id=mg_session.season_id,
            cycle_id=mg_session.cycle_id,
        )

    elif settlement_type == SettlementType.CANCEL:
        entries = economy.create_cancel_settlement_entries(
            player_1_membership_id=mg_session.player_1_membership_id,
            player_2_membership_id=mg_session.player_2_membership_id,
            competition_id=mg_session.competition_id,
            session_id=mg_session.id,
            buy_in_amount=mg_session.buy_in_amount,
            player_1_balance=player_1_balance,
            player_2_balance=player_2_balance,
            season_id=mg_session.season_id,
            cycle_id=mg_session.cycle_id,
        )

    elif settlement_type == SettlementType.SOLO:
        # Reward the solo player buy_in_amount * 2 for a completed run.
        reward = mg_session.buy_in_amount * 2
        entries = economy.create_solo_settlement_entries(
            player_membership_id=mg_session.player_1_membership_id,
            competition_id=mg_session.competition_id,
            session_id=mg_session.id,
            reward_amount=reward,
            player_balance=player_1_balance,
            season_id=mg_session.season_id,
            cycle_id=mg_session.cycle_id,
        )

    # ── Persist ledger entries ───────────────────────────────────────────────
    for entry in entries:
        session.add(entry)

    # Flush so every entry gets a database-assigned id.
    await session.flush()

    ledger_ids = [entry.id for entry in entries]

    # ── Create settlement record ─────────────────────────────────────────────
    settlement = MinigameSessionSettlement(
        session_id=mg_session.id,
        winner_membership_id=mg_session.winner_membership_id,
        loser_membership_id=loser_id,
        winner_payout=mg_session.buy_in_amount * 2 if settlement_type in (
            SettlementType.NORMAL,
            SettlementType.FORFEIT,
            SettlementType.SOLO,
        ) else 0,
        loser_penalty=0,
        settlement_state=MinigameSettlementState.SETTLED,
        ledger_entry_ids=ledger_ids if ledger_ids else None,
        correlation_id=mg_session.correlation_id,
        settled_at=now_riyadh_naive(),
    )
    session.add(settlement)
    await session.flush()

    return settlement
