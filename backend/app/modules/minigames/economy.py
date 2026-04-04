"""
Minigame Economy Bridge — pure ledger-entry factories.

All functions return LedgerEntry instances without touching the DB session.
The caller is responsible for session.add() and flushing.

Balance rules:
  DEBIT  → balance_after = balance_before - amount  (amount clamped to balance_before)
  CREDIT → balance_after = balance_before + amount
"""

import uuid
from typing import Optional

from app.core.enums import LedgerDirection, LedgerEntryType
from app.modules.scoring.models import LedgerEntry


# ─── Private helper ──────────────────────────────────────────────────────────

def _make_entry(
    *,
    membership_id: uuid.UUID,
    competition_id: uuid.UUID,
    session_id: uuid.UUID,
    entry_type: LedgerEntryType,
    direction: LedgerDirection,
    amount: int,
    balance_before: int,
    reason: str,
    season_id: Optional[uuid.UUID] = None,
    cycle_id: Optional[uuid.UUID] = None,
) -> LedgerEntry:
    """Construct a single LedgerEntry with correct balance_after."""
    if direction == LedgerDirection.DEBIT:
        balance_after = balance_before - amount
    else:
        balance_after = balance_before + amount

    return LedgerEntry(
        membership_id=membership_id,
        competition_id=competition_id,
        season_id=season_id,
        cycle_id=cycle_id,
        entry_type=entry_type,
        amount=amount,
        direction=direction,
        balance_before=balance_before,
        balance_after=balance_after,
        source_type="minigame_session",
        source_id=session_id,
        reason=reason,
    )


# ─── Public factory functions ─────────────────────────────────────────────────

def create_buy_in_entry(
    *,
    membership_id: uuid.UUID,
    competition_id: uuid.UUID,
    session_id: uuid.UUID,
    amount: int,
    balance_before: int,
    season_id: Optional[uuid.UUID] = None,
    cycle_id: Optional[uuid.UUID] = None,
) -> LedgerEntry:
    """
    Debit buy-in from player balance.
    Clamped: if balance_before < amount, debit only what is available.
    """
    effective_amount = min(amount, balance_before)
    return _make_entry(
        membership_id=membership_id,
        competition_id=competition_id,
        session_id=session_id,
        entry_type=LedgerEntryType.MINIGAME_BUY_IN,
        direction=LedgerDirection.DEBIT,
        amount=effective_amount,
        balance_before=balance_before,
        reason="رسوم دخول اللعبة المصغرة",
        season_id=season_id,
        cycle_id=cycle_id,
    )


def create_payout_entry(
    *,
    membership_id: uuid.UUID,
    competition_id: uuid.UUID,
    session_id: uuid.UUID,
    amount: int,
    balance_before: int,
    season_id: Optional[uuid.UUID] = None,
    cycle_id: Optional[uuid.UUID] = None,
) -> LedgerEntry:
    """Credit winnings to player balance."""
    return _make_entry(
        membership_id=membership_id,
        competition_id=competition_id,
        session_id=session_id,
        entry_type=LedgerEntryType.MINIGAME_PAYOUT,
        direction=LedgerDirection.CREDIT,
        amount=amount,
        balance_before=balance_before,
        reason="مكافأة الفوز في اللعبة المصغرة",
        season_id=season_id,
        cycle_id=cycle_id,
    )


def create_refund_entry(
    *,
    membership_id: uuid.UUID,
    competition_id: uuid.UUID,
    session_id: uuid.UUID,
    amount: int,
    balance_before: int,
    season_id: Optional[uuid.UUID] = None,
    cycle_id: Optional[uuid.UUID] = None,
) -> LedgerEntry:
    """Credit buy-in refund when session is cancelled."""
    return _make_entry(
        membership_id=membership_id,
        competition_id=competition_id,
        session_id=session_id,
        entry_type=LedgerEntryType.MINIGAME_REFUND,
        direction=LedgerDirection.CREDIT,
        amount=amount,
        balance_before=balance_before,
        reason="استرداد رسوم الدخول — إلغاء الجلسة",
        season_id=season_id,
        cycle_id=cycle_id,
    )


# ─── Settlement helpers ───────────────────────────────────────────────────────

def create_normal_settlement_entries(
    *,
    winner_membership_id: uuid.UUID,
    loser_membership_id: uuid.UUID,  # kept for signature clarity; not used here
    competition_id: uuid.UUID,
    session_id: uuid.UUID,
    buy_in_amount: int,
    winner_balance: int,
    season_id: Optional[uuid.UUID] = None,
    cycle_id: Optional[uuid.UUID] = None,
) -> list[LedgerEntry]:
    """
    Normal (non-forfeit) two-player settlement.
    Both players paid buy_in_amount at session start.
    Winner receives buy_in_amount * 2 (zero-sum pot).
    Returns [payout_entry].
    """
    payout = create_payout_entry(
        membership_id=winner_membership_id,
        competition_id=competition_id,
        session_id=session_id,
        amount=buy_in_amount * 2,
        balance_before=winner_balance,
        season_id=season_id,
        cycle_id=cycle_id,
    )
    return [payout]


def create_forfeit_settlement_entries(
    *,
    winner_membership_id: uuid.UUID,
    competition_id: uuid.UUID,
    session_id: uuid.UUID,
    buy_in_amount: int,
    winner_balance: int,
    season_id: Optional[uuid.UUID] = None,
    cycle_id: Optional[uuid.UUID] = None,
) -> list[LedgerEntry]:
    """
    Forfeit settlement — forfeiting player already paid buy-in at session start.
    Winner still receives buy_in_amount * 2 (same as normal settlement).
    Returns [payout_entry].
    """
    payout = create_payout_entry(
        membership_id=winner_membership_id,
        competition_id=competition_id,
        session_id=session_id,
        amount=buy_in_amount * 2,
        balance_before=winner_balance,
        season_id=season_id,
        cycle_id=cycle_id,
    )
    return [payout]


def create_cancel_settlement_entries(
    *,
    player_1_membership_id: uuid.UUID,
    player_2_membership_id: Optional[uuid.UUID],
    competition_id: uuid.UUID,
    session_id: uuid.UUID,
    buy_in_amount: int,
    player_1_balance: int,
    player_2_balance: int,
    season_id: Optional[uuid.UUID] = None,
    cycle_id: Optional[uuid.UUID] = None,
) -> list[LedgerEntry]:
    """
    Cancel settlement — refund buy-in to all participants.
    If player_2_membership_id is None (solo game cancelled), only refund player_1.
    Returns [refund_p1] or [refund_p1, refund_p2].
    """
    entries: list[LedgerEntry] = []

    entries.append(
        create_refund_entry(
            membership_id=player_1_membership_id,
            competition_id=competition_id,
            session_id=session_id,
            amount=buy_in_amount,
            balance_before=player_1_balance,
            season_id=season_id,
            cycle_id=cycle_id,
        )
    )

    if player_2_membership_id is not None:
        entries.append(
            create_refund_entry(
                membership_id=player_2_membership_id,
                competition_id=competition_id,
                session_id=session_id,
                amount=buy_in_amount,
                balance_before=player_2_balance,
                season_id=season_id,
                cycle_id=cycle_id,
            )
        )

    return entries


def create_solo_settlement_entries(
    *,
    player_membership_id: uuid.UUID,
    competition_id: uuid.UUID,
    session_id: uuid.UUID,
    reward_amount: int,
    player_balance: int,
    season_id: Optional[uuid.UUID] = None,
    cycle_id: Optional[uuid.UUID] = None,
) -> list[LedgerEntry]:
    """
    Solo game completion — credit reward_amount to player.
    Returns [] if reward_amount is 0 (no ledger entry needed).
    reason overrides the default payout reason for solo context.
    """
    if reward_amount == 0:
        return []

    entry = _make_entry(
        membership_id=player_membership_id,
        competition_id=competition_id,
        session_id=session_id,
        entry_type=LedgerEntryType.MINIGAME_PAYOUT,
        direction=LedgerDirection.CREDIT,
        amount=reward_amount,
        balance_before=player_balance,
        reason="مكافأة إتمام اللعبة المصغرة",
        season_id=season_id,
        cycle_id=cycle_id,
    )
    return [entry]


# ─── N-player settlement helpers ─────────────────────────────────────────────

def create_ranked_settlement_entries(
    *,
    results: list[dict],
    competition_id: uuid.UUID,
    session_id: uuid.UUID,
    season_id: Optional[uuid.UUID] = None,
    cycle_id: Optional[uuid.UUID] = None,
) -> list[LedgerEntry]:
    """Create ledger entries for N-player ranked settlement.

    Args:
        results: list of {"membership_id": UUID, "rank": int, "payout": int, "balance_before": int}
                 Only players with payout > 0 get a CREDIT entry.

    Returns:
        List of LedgerEntry instances (one per player with payout > 0, in rank order)
    """
    return [
        create_payout_entry(
            membership_id=r["membership_id"],
            competition_id=competition_id,
            session_id=session_id,
            amount=r["payout"],
            balance_before=r.get("balance_before", 0),
            season_id=season_id,
            cycle_id=cycle_id,
        )
        for r in results
        if r["payout"] > 0
    ]


def create_refund_all_entries(
    *,
    player_membership_ids: list[uuid.UUID],
    player_balances: list[int],
    competition_id: uuid.UUID,
    session_id: uuid.UUID,
    buy_in_amount: int,
    season_id: Optional[uuid.UUID] = None,
    cycle_id: Optional[uuid.UUID] = None,
) -> list[LedgerEntry]:
    """Refund buy-in to all participants (for cancellations).

    player_membership_ids and player_balances must be the same length
    (each player's starting balance).
    """
    return [
        create_refund_entry(
            membership_id=mid,
            competition_id=competition_id,
            session_id=session_id,
            amount=buy_in_amount,
            balance_before=balance,
            season_id=season_id,
            cycle_id=cycle_id,
        )
        for mid, balance in zip(player_membership_ids, player_balances)
    ]
