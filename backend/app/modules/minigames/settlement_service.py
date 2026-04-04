"""
Minigame Settlement Service.

Responsibilities:
  - Classify finished sessions into settlement types (NORMAL, FORFEIT, CANCEL, SOLO)
  - Execute the financial settlement by building ledger entries and persisting a
    MinigameSessionSettlement record using the N-player participant_results model.

Public surface:
  SettlementType                — StrEnum of the four settlement categories
  compute_settlement_type()     — pure, synchronous, fully testable
  execute_settlement()          — async, N-player settlement driven by plugin output
  execute_cancel_settlement()   — async, refund-all settlement for cancellations
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


async def _apply_entries_and_membership_balances(
    session: "AsyncSession",
    *,
    entries: list,
) -> list[uuid.UUID]:
    """Persist ledger entries and update membership.current_balance in-place."""
    if not entries:
        return []

    from sqlalchemy import select

    from app.modules.competitions.models import Membership

    membership_ids = [entry.membership_id for entry in entries]
    result = await session.execute(
        select(Membership).where(Membership.id.in_(membership_ids))
    )
    memberships = {
        membership.id: membership
        for membership in result.scalars().all()
    }

    for entry in entries:
        session.add(entry)
        membership = memberships.get(entry.membership_id)
        if membership is not None:
            membership.current_balance = entry.balance_after

    await session.flush()
    return [entry.id for entry in entries]


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


# ─── Async settlement executor ───────────────────────────────────────────────

async def execute_settlement(
    session: "AsyncSession",
    *,
    mg_session: "MinigameSession",
    participants: list[dict],
    plugin_settlement: dict,
) -> "MinigameSessionSettlement":
    """Execute financial settlement for a terminal minigame session.

    Idempotent: returns existing settlement if one exists for this session_id.

    Args:
        session: SQLAlchemy async session
        mg_session: The terminal MinigameSession to settle
        participants: List of participants with their current balances, used for
                      ledger balance_before calculations. Ordered by slot_index.
                      Each dict: {"membership_id": UUID, "slot_index": int, "balance": int}
        plugin_settlement: Output of plugin.compute_settlement(terminal_result).
                           Contains "participant_results" list and "total_pool".

    Returns:
        The created (or existing) MinigameSessionSettlement record.
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

    # Build a balance lookup by membership_id
    balance_by_mid = {p["membership_id"]: p.get("balance", 0) for p in participants}

    # Extract participant_results from plugin output
    participant_results = plugin_settlement.get("participant_results", [])
    total_pool = plugin_settlement.get("total_pool", 0)

    # Enrich each result with balance_before for the economy helper
    enriched_results = []
    for r in participant_results:
        mid = r["membership_id"]
        # Convert string UUIDs back to UUID objects if needed
        if isinstance(mid, str):
            mid = uuid.UUID(mid)
        enriched_results.append({
            "membership_id": mid,
            "rank": r.get("rank", 0),
            "payout": r.get("payout", 0),
            "balance_before": balance_by_mid.get(mid, 0),
        })

    # Create ledger entries for players with payout > 0
    entries = economy.create_ranked_settlement_entries(
        results=enriched_results,
        competition_id=mg_session.competition_id,
        session_id=mg_session.id,
        season_id=mg_session.season_id,
        cycle_id=mg_session.cycle_id,
    )

    # Persist ledger entries
    ledger_ids = await _apply_entries_and_membership_balances(
        session,
        entries=entries,
    )

    # Build JSONB payload — convert UUIDs to strings for storage
    jsonb_results = [
        {
            "membership_id": str(r["membership_id"]) if not isinstance(r["membership_id"], str) else r["membership_id"],
            "slot_index": r.get("slot_index", 0),
            "rank": r.get("rank", 0),
            "payout": r.get("payout", 0),
        }
        for r in participant_results
    ]

    settlement = MinigameSessionSettlement(
        session_id=mg_session.id,
        participant_results=jsonb_results,
        total_pool=total_pool,
        settlement_state=MinigameSettlementState.SETTLED,
        ledger_entry_ids=ledger_ids if ledger_ids else None,
        correlation_id=mg_session.correlation_id,
        settled_at=now_riyadh_naive(),
    )
    session.add(settlement)
    await session.flush()

    return settlement


async def execute_cancel_settlement(
    session: "AsyncSession",
    *,
    mg_session: "MinigameSession",
    participants: list[dict],
) -> "MinigameSessionSettlement":
    """Execute a cancellation settlement — refund all participants.

    Used when a session is cancelled (admin cancel, all players disconnect, etc.).
    Each participant gets their buy_in refunded.

    Idempotent: returns existing settlement if one exists for this session_id.

    Args:
        session: SQLAlchemy async session
        mg_session: The cancelled MinigameSession to settle
        participants: List of participants with balances, ordered by slot_index.
                      Each dict: {"membership_id": UUID, "slot_index": int, "balance": int}

    Returns:
        The created (or existing) MinigameSessionSettlement record.
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

    membership_ids = [p["membership_id"] for p in participants]
    balances = [p.get("balance", 0) for p in participants]

    entries = economy.create_refund_all_entries(
        player_membership_ids=membership_ids,
        player_balances=balances,
        competition_id=mg_session.competition_id,
        session_id=mg_session.id,
        buy_in_amount=mg_session.buy_in_amount,
        season_id=mg_session.season_id,
        cycle_id=mg_session.cycle_id,
    )

    ledger_ids = await _apply_entries_and_membership_balances(
        session,
        entries=entries,
    )

    # Build participant_results showing everyone got their buy_in refunded
    jsonb_results = [
        {
            "membership_id": str(p["membership_id"]),
            "slot_index": p.get("slot_index", 0),
            "rank": 0,  # 0 indicates no winner
            "payout": mg_session.buy_in_amount,
        }
        for p in participants
    ]

    settlement = MinigameSessionSettlement(
        session_id=mg_session.id,
        participant_results=jsonb_results,
        total_pool=mg_session.buy_in_amount * len(participants),
        settlement_state=MinigameSettlementState.SETTLED,
        ledger_entry_ids=ledger_ids if ledger_ids else None,
        correlation_id=mg_session.correlation_id,
        settled_at=now_riyadh_naive(),
    )
    session.add(settlement)
    await session.flush()

    return settlement
