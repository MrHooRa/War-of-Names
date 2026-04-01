"""
Tests for minigame economy bridge functions.

All functions are pure (no DB session required) — they produce LedgerEntry
instances with correct types, directions, amounts, and balance calculations.
"""

import uuid

import pytest

# Import app.core.models first so all model modules are fully initialized
# before economy.py attempts to import LedgerEntry — this resolves the
# circular import that arises from core/models.py importing scoring/models.py.
import app.core.models  # noqa: F401

from app.core.enums import LedgerDirection, LedgerEntryType
from app.modules.minigames.economy import (
    create_buy_in_entry,
    create_cancel_settlement_entries,
    create_forfeit_settlement_entries,
    create_normal_settlement_entries,
    create_payout_entry,
    create_refund_entry,
    create_solo_settlement_entries,
)

# ─── Shared fixtures ──────────────────────────────────────────────────────────

MEMBERSHIP_ID = uuid.uuid4()
COMPETITION_ID = uuid.uuid4()
SESSION_ID = uuid.uuid4()

MEMBERSHIP_2_ID = uuid.uuid4()


# ─── create_buy_in_entry ──────────────────────────────────────────────────────

class TestCreateBuyInEntry:
    def test_is_debit(self):
        entry = create_buy_in_entry(
            membership_id=MEMBERSHIP_ID,
            competition_id=COMPETITION_ID,
            session_id=SESSION_ID,
            amount=100,
            balance_before=500,
        )
        assert entry.direction == LedgerDirection.DEBIT

    def test_correct_entry_type(self):
        entry = create_buy_in_entry(
            membership_id=MEMBERSHIP_ID,
            competition_id=COMPETITION_ID,
            session_id=SESSION_ID,
            amount=100,
            balance_before=500,
        )
        assert entry.entry_type == LedgerEntryType.MINIGAME_BUY_IN

    def test_balance_after_deducted(self):
        entry = create_buy_in_entry(
            membership_id=MEMBERSHIP_ID,
            competition_id=COMPETITION_ID,
            session_id=SESSION_ID,
            amount=100,
            balance_before=500,
        )
        assert entry.balance_before == 500
        assert entry.amount == 100
        assert entry.balance_after == 400

    def test_clamped_when_balance_less_than_amount(self):
        """If balance < amount, debit only what is available."""
        entry = create_buy_in_entry(
            membership_id=MEMBERSHIP_ID,
            competition_id=COMPETITION_ID,
            session_id=SESSION_ID,
            amount=200,
            balance_before=50,
        )
        assert entry.amount == 50          # clamped to available balance
        assert entry.balance_after == 0    # balance drained to zero

    def test_clamped_exact_balance(self):
        """When amount equals balance, clamp produces same amount."""
        entry = create_buy_in_entry(
            membership_id=MEMBERSHIP_ID,
            competition_id=COMPETITION_ID,
            session_id=SESSION_ID,
            amount=300,
            balance_before=300,
        )
        assert entry.amount == 300
        assert entry.balance_after == 0

    def test_source_fields(self):
        entry = create_buy_in_entry(
            membership_id=MEMBERSHIP_ID,
            competition_id=COMPETITION_ID,
            session_id=SESSION_ID,
            amount=50,
            balance_before=200,
        )
        assert entry.source_type == "minigame_session"
        assert entry.source_id == SESSION_ID

    def test_arabic_reason(self):
        entry = create_buy_in_entry(
            membership_id=MEMBERSHIP_ID,
            competition_id=COMPETITION_ID,
            session_id=SESSION_ID,
            amount=50,
            balance_before=200,
        )
        assert entry.reason == "رسوم دخول اللعبة المصغرة"

    def test_optional_season_cycle(self):
        season_id = uuid.uuid4()
        cycle_id = uuid.uuid4()
        entry = create_buy_in_entry(
            membership_id=MEMBERSHIP_ID,
            competition_id=COMPETITION_ID,
            session_id=SESSION_ID,
            amount=50,
            balance_before=200,
            season_id=season_id,
            cycle_id=cycle_id,
        )
        assert entry.season_id == season_id
        assert entry.cycle_id == cycle_id

    def test_no_session_add_called(self):
        """Function must be pure — no SQLAlchemy session interaction."""
        # If function tried session.add() it would raise; just verify it returns
        entry = create_buy_in_entry(
            membership_id=MEMBERSHIP_ID,
            competition_id=COMPETITION_ID,
            session_id=SESSION_ID,
            amount=10,
            balance_before=100,
        )
        assert entry is not None


# ─── create_payout_entry ─────────────────────────────────────────────────────

class TestCreatePayoutEntry:
    def test_is_credit(self):
        entry = create_payout_entry(
            membership_id=MEMBERSHIP_ID,
            competition_id=COMPETITION_ID,
            session_id=SESSION_ID,
            amount=200,
            balance_before=400,
        )
        assert entry.direction == LedgerDirection.CREDIT

    def test_correct_entry_type(self):
        entry = create_payout_entry(
            membership_id=MEMBERSHIP_ID,
            competition_id=COMPETITION_ID,
            session_id=SESSION_ID,
            amount=200,
            balance_before=400,
        )
        assert entry.entry_type == LedgerEntryType.MINIGAME_PAYOUT

    def test_balance_after_increased(self):
        entry = create_payout_entry(
            membership_id=MEMBERSHIP_ID,
            competition_id=COMPETITION_ID,
            session_id=SESSION_ID,
            amount=200,
            balance_before=400,
        )
        assert entry.balance_after == 600

    def test_arabic_reason(self):
        entry = create_payout_entry(
            membership_id=MEMBERSHIP_ID,
            competition_id=COMPETITION_ID,
            session_id=SESSION_ID,
            amount=100,
            balance_before=300,
        )
        assert entry.reason == "مكافأة الفوز في اللعبة المصغرة"


# ─── create_refund_entry ─────────────────────────────────────────────────────

class TestCreateRefundEntry:
    def test_is_credit(self):
        entry = create_refund_entry(
            membership_id=MEMBERSHIP_ID,
            competition_id=COMPETITION_ID,
            session_id=SESSION_ID,
            amount=100,
            balance_before=50,
        )
        assert entry.direction == LedgerDirection.CREDIT

    def test_correct_entry_type(self):
        entry = create_refund_entry(
            membership_id=MEMBERSHIP_ID,
            competition_id=COMPETITION_ID,
            session_id=SESSION_ID,
            amount=100,
            balance_before=50,
        )
        assert entry.entry_type == LedgerEntryType.MINIGAME_REFUND

    def test_balance_after_restored(self):
        entry = create_refund_entry(
            membership_id=MEMBERSHIP_ID,
            competition_id=COMPETITION_ID,
            session_id=SESSION_ID,
            amount=100,
            balance_before=50,
        )
        assert entry.balance_after == 150

    def test_arabic_reason(self):
        entry = create_refund_entry(
            membership_id=MEMBERSHIP_ID,
            competition_id=COMPETITION_ID,
            session_id=SESSION_ID,
            amount=100,
            balance_before=50,
        )
        assert "إلغاء" in entry.reason


# ─── create_normal_settlement_entries ────────────────────────────────────────

class TestCreateNormalSettlementEntries:
    def test_returns_one_entry(self):
        entries = create_normal_settlement_entries(
            winner_membership_id=MEMBERSHIP_ID,
            loser_membership_id=MEMBERSHIP_2_ID,
            competition_id=COMPETITION_ID,
            session_id=SESSION_ID,
            buy_in_amount=100,
            winner_balance=300,
        )
        assert len(entries) == 1

    def test_payout_is_double_buy_in(self):
        entries = create_normal_settlement_entries(
            winner_membership_id=MEMBERSHIP_ID,
            loser_membership_id=MEMBERSHIP_2_ID,
            competition_id=COMPETITION_ID,
            session_id=SESSION_ID,
            buy_in_amount=100,
            winner_balance=300,
        )
        payout = entries[0]
        assert payout.amount == 200  # 100 * 2

    def test_payout_is_credit(self):
        entries = create_normal_settlement_entries(
            winner_membership_id=MEMBERSHIP_ID,
            loser_membership_id=MEMBERSHIP_2_ID,
            competition_id=COMPETITION_ID,
            session_id=SESSION_ID,
            buy_in_amount=100,
            winner_balance=300,
        )
        assert entries[0].direction == LedgerDirection.CREDIT

    def test_payout_type(self):
        entries = create_normal_settlement_entries(
            winner_membership_id=MEMBERSHIP_ID,
            loser_membership_id=MEMBERSHIP_2_ID,
            competition_id=COMPETITION_ID,
            session_id=SESSION_ID,
            buy_in_amount=100,
            winner_balance=300,
        )
        assert entries[0].entry_type == LedgerEntryType.MINIGAME_PAYOUT

    def test_winner_balance_after(self):
        entries = create_normal_settlement_entries(
            winner_membership_id=MEMBERSHIP_ID,
            loser_membership_id=MEMBERSHIP_2_ID,
            competition_id=COMPETITION_ID,
            session_id=SESSION_ID,
            buy_in_amount=100,
            winner_balance=300,
        )
        assert entries[0].balance_before == 300
        assert entries[0].balance_after == 500  # 300 + 200


# ─── create_forfeit_settlement_entries ───────────────────────────────────────

class TestCreateForfeitSettlementEntries:
    def test_returns_one_entry(self):
        entries = create_forfeit_settlement_entries(
            winner_membership_id=MEMBERSHIP_ID,
            competition_id=COMPETITION_ID,
            session_id=SESSION_ID,
            buy_in_amount=100,
            winner_balance=200,
        )
        assert len(entries) == 1

    def test_payout_is_double_buy_in(self):
        entries = create_forfeit_settlement_entries(
            winner_membership_id=MEMBERSHIP_ID,
            competition_id=COMPETITION_ID,
            session_id=SESSION_ID,
            buy_in_amount=150,
            winner_balance=200,
        )
        assert entries[0].amount == 300  # 150 * 2

    def test_payout_is_credit(self):
        entries = create_forfeit_settlement_entries(
            winner_membership_id=MEMBERSHIP_ID,
            competition_id=COMPETITION_ID,
            session_id=SESSION_ID,
            buy_in_amount=100,
            winner_balance=200,
        )
        assert entries[0].direction == LedgerDirection.CREDIT

    def test_payout_type(self):
        entries = create_forfeit_settlement_entries(
            winner_membership_id=MEMBERSHIP_ID,
            competition_id=COMPETITION_ID,
            session_id=SESSION_ID,
            buy_in_amount=100,
            winner_balance=200,
        )
        assert entries[0].entry_type == LedgerEntryType.MINIGAME_PAYOUT


# ─── create_cancel_settlement_entries ────────────────────────────────────────

class TestCreateCancelSettlementEntries:
    def test_two_players_returns_two_entries(self):
        entries = create_cancel_settlement_entries(
            player_1_membership_id=MEMBERSHIP_ID,
            player_2_membership_id=MEMBERSHIP_2_ID,
            competition_id=COMPETITION_ID,
            session_id=SESSION_ID,
            buy_in_amount=100,
            player_1_balance=50,
            player_2_balance=80,
        )
        assert len(entries) == 2

    def test_both_entries_are_refunds(self):
        entries = create_cancel_settlement_entries(
            player_1_membership_id=MEMBERSHIP_ID,
            player_2_membership_id=MEMBERSHIP_2_ID,
            competition_id=COMPETITION_ID,
            session_id=SESSION_ID,
            buy_in_amount=100,
            player_1_balance=50,
            player_2_balance=80,
        )
        assert entries[0].entry_type == LedgerEntryType.MINIGAME_REFUND
        assert entries[0].direction == LedgerDirection.CREDIT
        assert entries[1].entry_type == LedgerEntryType.MINIGAME_REFUND
        assert entries[1].direction == LedgerDirection.CREDIT

    def test_player_1_refund_balance(self):
        entries = create_cancel_settlement_entries(
            player_1_membership_id=MEMBERSHIP_ID,
            player_2_membership_id=MEMBERSHIP_2_ID,
            competition_id=COMPETITION_ID,
            session_id=SESSION_ID,
            buy_in_amount=100,
            player_1_balance=50,
            player_2_balance=80,
        )
        p1_entry = entries[0]
        assert p1_entry.membership_id == MEMBERSHIP_ID
        assert p1_entry.balance_before == 50
        assert p1_entry.balance_after == 150

    def test_player_2_refund_balance(self):
        entries = create_cancel_settlement_entries(
            player_1_membership_id=MEMBERSHIP_ID,
            player_2_membership_id=MEMBERSHIP_2_ID,
            competition_id=COMPETITION_ID,
            session_id=SESSION_ID,
            buy_in_amount=100,
            player_1_balance=50,
            player_2_balance=80,
        )
        p2_entry = entries[1]
        assert p2_entry.membership_id == MEMBERSHIP_2_ID
        assert p2_entry.balance_before == 80
        assert p2_entry.balance_after == 180

    def test_solo_cancel_returns_one_entry(self):
        """If player_2 is None (solo game cancelled), only refund player_1."""
        entries = create_cancel_settlement_entries(
            player_1_membership_id=MEMBERSHIP_ID,
            player_2_membership_id=None,
            competition_id=COMPETITION_ID,
            session_id=SESSION_ID,
            buy_in_amount=100,
            player_1_balance=50,
            player_2_balance=0,  # ignored
        )
        assert len(entries) == 1
        assert entries[0].membership_id == MEMBERSHIP_ID
        assert entries[0].entry_type == LedgerEntryType.MINIGAME_REFUND


# ─── create_solo_settlement_entries ──────────────────────────────────────────

class TestCreateSoloSettlementEntries:
    def test_nonzero_reward_creates_one_entry(self):
        entries = create_solo_settlement_entries(
            player_membership_id=MEMBERSHIP_ID,
            competition_id=COMPETITION_ID,
            session_id=SESSION_ID,
            reward_amount=250,
            player_balance=100,
        )
        assert len(entries) == 1

    def test_entry_is_credit_payout(self):
        entries = create_solo_settlement_entries(
            player_membership_id=MEMBERSHIP_ID,
            competition_id=COMPETITION_ID,
            session_id=SESSION_ID,
            reward_amount=250,
            player_balance=100,
        )
        entry = entries[0]
        assert entry.direction == LedgerDirection.CREDIT
        assert entry.entry_type == LedgerEntryType.MINIGAME_PAYOUT

    def test_balance_after_correct(self):
        entries = create_solo_settlement_entries(
            player_membership_id=MEMBERSHIP_ID,
            competition_id=COMPETITION_ID,
            session_id=SESSION_ID,
            reward_amount=250,
            player_balance=100,
        )
        entry = entries[0]
        assert entry.balance_before == 100
        assert entry.amount == 250
        assert entry.balance_after == 350

    def test_arabic_reason(self):
        entries = create_solo_settlement_entries(
            player_membership_id=MEMBERSHIP_ID,
            competition_id=COMPETITION_ID,
            session_id=SESSION_ID,
            reward_amount=100,
            player_balance=0,
        )
        assert "إتمام" in entries[0].reason

    def test_zero_reward_returns_empty_list(self):
        entries = create_solo_settlement_entries(
            player_membership_id=MEMBERSHIP_ID,
            competition_id=COMPETITION_ID,
            session_id=SESSION_ID,
            reward_amount=0,
            player_balance=500,
        )
        assert entries == []

    def test_source_fields_set(self):
        entries = create_solo_settlement_entries(
            player_membership_id=MEMBERSHIP_ID,
            competition_id=COMPETITION_ID,
            session_id=SESSION_ID,
            reward_amount=50,
            player_balance=200,
        )
        entry = entries[0]
        assert entry.source_type == "minigame_session"
        assert entry.source_id == SESSION_ID
