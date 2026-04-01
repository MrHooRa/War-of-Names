"""Integration tests — full minigame lifecycle using pure (sync, no-DB) functions.

These tests exercise the complete flow through all four service modules:
  session_service  → validate_session_creation, compute_transition_update
  action_service   → validate_action_envelope, ActionError
  settlement_service → compute_settlement_type, SettlementType
  economy          → create_buy_in_entry, create_normal_settlement_entries,
                     create_solo_settlement_entries

No async, no database, no application startup required.

Import app.core.models first (project-established pattern) to avoid the
circular import that arises when economy.py pulls in scoring/models.py.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import patch

import pytest

# ── Circular-import guard — must be first app import ─────────────────────────
import app.core.models  # noqa: F401

# ── Enums ─────────────────────────────────────────────────────────────────────
from app.core.enums import (
    LedgerDirection,
    MinigameSessionPhase as Phase,
    MinigameTurnSide,
)

# ── Service imports ───────────────────────────────────────────────────────────
from app.modules.minigames.session_service import (
    compute_transition_update,
    validate_session_creation,
)
from app.modules.minigames.action_service import (
    ActionError,
    validate_action_envelope,
)
from app.modules.minigames.settlement_service import (
    SettlementType,
    compute_settlement_type,
)
from app.modules.minigames.economy import (
    create_buy_in_entry,
    create_normal_settlement_entries,
    create_solo_settlement_entries,
)

# ── Helpers ───────────────────────────────────────────────────────────────────

_FIXED_NOW = datetime(2026, 4, 1, 12, 0, 0)

_PATCH_NOW = patch(
    "app.modules.minigames.session_service._now",
    return_value=_FIXED_NOW,
)


def _transition(**kwargs):
    """Call compute_transition_update with _now patched to a fixed value."""
    with _PATCH_NOW:
        return compute_transition_update(**kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# Test 1 — Full 1v1 happy-path lifecycle
# ─────────────────────────────────────────────────────────────────────────────

class TestFull1v1LifecycleHappyPath:
    """End-to-end flow: creation → buy-in → transitions → action → settlement."""

    # Stable IDs used throughout every step.
    COMPETITION_ID = uuid.uuid4()
    SESSION_ID = uuid.uuid4()
    PLAYER_1 = uuid.uuid4()
    PLAYER_2 = uuid.uuid4()
    BUY_IN = 100

    def test_full_1v1_lifecycle_happy_path(self):
        # ── Step 1: Validate session creation ──────────────────────────────
        errors = validate_session_creation(
            game_type_id="mutaraha",
            plugin_exists=True,
            plugin_status="active",
            player_balance=500,
            buy_in_amount=self.BUY_IN,
            is_bankrupt=False,
        )
        assert errors == [], f"Creation validation failed: {errors}"

        # ── Step 2: Create buy-in entries for both players ─────────────────
        p1_balance_before = 500
        p2_balance_before = 300

        entry_p1 = create_buy_in_entry(
            membership_id=self.PLAYER_1,
            competition_id=self.COMPETITION_ID,
            session_id=self.SESSION_ID,
            amount=self.BUY_IN,
            balance_before=p1_balance_before,
        )
        entry_p2 = create_buy_in_entry(
            membership_id=self.PLAYER_2,
            competition_id=self.COMPETITION_ID,
            session_id=self.SESSION_ID,
            amount=self.BUY_IN,
            balance_before=p2_balance_before,
        )

        # Both entries must be DEBITs.
        assert entry_p1.direction == LedgerDirection.DEBIT
        assert entry_p2.direction == LedgerDirection.DEBIT

        # Balances are correctly deducted.
        assert entry_p1.balance_before == p1_balance_before
        assert entry_p1.balance_after == p1_balance_before - self.BUY_IN
        assert entry_p2.balance_before == p2_balance_before
        assert entry_p2.balance_after == p2_balance_before - self.BUY_IN

        # ── Step 3: Transitions CREATED → WAITING → READY → IN_PROGRESS ───
        revision = 0

        upd1 = _transition(
            current_phase=Phase.CREATED,
            target_phase=Phase.WAITING,
            current_revision=revision,
        )
        assert upd1["phase"] == Phase.WAITING
        revision = upd1["revision"]
        assert revision == 1

        upd2 = _transition(
            current_phase=Phase.WAITING,
            target_phase=Phase.READY,
            current_revision=revision,
        )
        assert upd2["phase"] == Phase.READY
        revision = upd2["revision"]
        assert revision == 2

        upd3 = _transition(
            current_phase=Phase.READY,
            target_phase=Phase.IN_PROGRESS,
            current_revision=revision,
        )
        assert upd3["phase"] == Phase.IN_PROGRESS
        revision = upd3["revision"]
        assert revision == 3

        # IN_PROGRESS transition must set turn fields.
        assert upd3["current_turn"] == MinigameTurnSide.PLAYER_1
        assert upd3["started_at"] == _FIXED_NOW

        # ── Step 4: Validate action envelope (player_1's turn) ─────────────
        envelope = {
            "state_revision": revision,
            "actor_membership_id": self.PLAYER_1,
            "action": {"type": "guess"},
        }
        action_err = validate_action_envelope(
            envelope=envelope,
            session_phase=Phase.IN_PROGRESS,
            session_revision=revision,
            current_turn=MinigameTurnSide.PLAYER_1,
            player_1_membership_id=self.PLAYER_1,
            player_2_membership_id=self.PLAYER_2,
        )
        assert action_err is None, f"Action validation failed: {action_err}"

        # ── Step 5: Transition IN_PROGRESS → COMPLETED with a winner ───────
        upd4 = _transition(
            current_phase=Phase.IN_PROGRESS,
            target_phase=Phase.COMPLETED,
            current_revision=revision,
            terminal_reason="player_won",
            winner_membership_id=self.PLAYER_1,
        )
        assert upd4["phase"] == Phase.COMPLETED
        assert upd4["winner_membership_id"] == self.PLAYER_1
        assert upd4["terminal_reason"] == "player_won"
        assert upd4["completed_at"] == _FIXED_NOW
        revision = upd4["revision"]
        assert revision == 4

        # ── Step 6: Compute settlement type ────────────────────────────────
        stype = compute_settlement_type(
            phase="completed",
            terminal_reason="player_won",
            winner_membership_id=self.PLAYER_1,
            is_solo=False,
        )
        assert stype == SettlementType.NORMAL

        # ── Step 7: Create normal settlement entries ────────────────────────
        # Winner's balance after the buy-in deduction.
        winner_balance_after_buy_in = entry_p1.balance_after

        entries = create_normal_settlement_entries(
            winner_membership_id=self.PLAYER_1,
            loser_membership_id=self.PLAYER_2,
            competition_id=self.COMPETITION_ID,
            session_id=self.SESSION_ID,
            buy_in_amount=self.BUY_IN,
            winner_balance=winner_balance_after_buy_in,
        )

        assert len(entries) == 1
        payout = entries[0]
        assert payout.direction == LedgerDirection.CREDIT
        assert payout.amount == self.BUY_IN * 2          # winner gets full pot
        assert payout.balance_before == winner_balance_after_buy_in
        assert payout.balance_after == winner_balance_after_buy_in + self.BUY_IN * 2


# ─────────────────────────────────────────────────────────────────────────────
# Test 2 — Solo game lifecycle
# ─────────────────────────────────────────────────────────────────────────────

class TestSoloLifecycle:
    """End-to-end solo flow — no player_2, no turn enforcement."""

    COMPETITION_ID = uuid.uuid4()
    SESSION_ID = uuid.uuid4()
    PLAYER_1 = uuid.uuid4()
    BUY_IN = 50

    def test_solo_lifecycle(self):
        # ── Step 1: Validate creation ───────────────────────────────────────
        errors = validate_session_creation(
            game_type_id="mutaraha",
            plugin_exists=True,
            plugin_status="active",
            player_balance=200,
            buy_in_amount=self.BUY_IN,
            is_bankrupt=False,
        )
        assert errors == []

        # ── Step 2: Buy-in for player_1 only ───────────────────────────────
        p1_balance_before = 200
        entry_p1 = create_buy_in_entry(
            membership_id=self.PLAYER_1,
            competition_id=self.COMPETITION_ID,
            session_id=self.SESSION_ID,
            amount=self.BUY_IN,
            balance_before=p1_balance_before,
        )
        assert entry_p1.direction == LedgerDirection.DEBIT
        assert entry_p1.balance_after == p1_balance_before - self.BUY_IN

        # ── Step 3: Transition to IN_PROGRESS ──────────────────────────────
        revision = 0

        upd1 = _transition(
            current_phase=Phase.CREATED,
            target_phase=Phase.WAITING,
            current_revision=revision,
        )
        revision = upd1["revision"]

        upd2 = _transition(
            current_phase=Phase.WAITING,
            target_phase=Phase.READY,
            current_revision=revision,
        )
        revision = upd2["revision"]

        upd3 = _transition(
            current_phase=Phase.READY,
            target_phase=Phase.IN_PROGRESS,
            current_revision=revision,
        )
        assert upd3["phase"] == Phase.IN_PROGRESS
        revision = upd3["revision"]

        # ── Step 4: Validate action — solo game skips turn check ───────────
        envelope = {
            "state_revision": revision,
            "actor_membership_id": self.PLAYER_1,
            "action": {"type": "answer"},
        }
        action_err = validate_action_envelope(
            envelope=envelope,
            session_phase=Phase.IN_PROGRESS,
            session_revision=revision,
            current_turn=MinigameTurnSide.PLAYER_1,
            player_1_membership_id=self.PLAYER_1,
            player_2_membership_id=None,   # solo — no turn enforcement
        )
        assert action_err is None, f"Solo action rejected unexpectedly: {action_err}"

        # ── Step 5: Transition to COMPLETED ────────────────────────────────
        upd4 = _transition(
            current_phase=Phase.IN_PROGRESS,
            target_phase=Phase.COMPLETED,
            current_revision=revision,
            terminal_reason="solo_complete",
            winner_membership_id=self.PLAYER_1,
        )
        assert upd4["phase"] == Phase.COMPLETED
        revision = upd4["revision"]

        # ── Step 6: Compute settlement type → SOLO ─────────────────────────
        stype = compute_settlement_type(
            phase="completed",
            terminal_reason="solo_complete",
            winner_membership_id=self.PLAYER_1,
            is_solo=True,
        )
        assert stype == SettlementType.SOLO

        # ── Step 7: Create solo settlement entries ─────────────────────────
        reward = self.BUY_IN * 2
        player_balance_after_buy_in = entry_p1.balance_after

        entries = create_solo_settlement_entries(
            player_membership_id=self.PLAYER_1,
            competition_id=self.COMPETITION_ID,
            session_id=self.SESSION_ID,
            reward_amount=reward,
            player_balance=player_balance_after_buy_in,
        )

        assert len(entries) == 1
        assert entries[0].direction == LedgerDirection.CREDIT
        assert entries[0].amount == reward
        assert entries[0].balance_after == player_balance_after_buy_in + reward


# ─────────────────────────────────────────────────────────────────────────────
# Test 3 — Cancel lifecycle
# ─────────────────────────────────────────────────────────────────────────────

class TestCancelLifecycle:
    """CANCELLED phase → SettlementType.CANCEL."""

    PLAYER_1 = uuid.uuid4()

    def test_cancel_lifecycle(self):
        stype = compute_settlement_type(
            phase="cancelled",
            terminal_reason="admin_cancelled",
            winner_membership_id=None,
            is_solo=False,
        )
        assert stype == SettlementType.CANCEL


# ─────────────────────────────────────────────────────────────────────────────
# Test 4 — Abandon with winner → FORFEIT
# ─────────────────────────────────────────────────────────────────────────────

class TestAbandonWithWinnerLifecycle:
    """ABANDONED phase with a declared winner → SettlementType.FORFEIT."""

    PLAYER_1 = uuid.uuid4()

    def test_abandon_with_winner_lifecycle(self):
        winner_id = uuid.uuid4()
        stype = compute_settlement_type(
            phase="abandoned",
            terminal_reason="player_disconnected",
            winner_membership_id=winner_id,
            is_solo=False,
        )
        assert stype == SettlementType.FORFEIT


# ─────────────────────────────────────────────────────────────────────────────
# Test 5 — Action rejected in terminal session
# ─────────────────────────────────────────────────────────────────────────────

class TestActionRejectedInTerminalSession:
    """validate_action_envelope must return SESSION_ENDED for terminal phases."""

    PLAYER_1 = uuid.uuid4()
    PLAYER_2 = uuid.uuid4()

    def test_action_rejected_in_terminal_session(self):
        envelope = {
            "state_revision": 5,
            "actor_membership_id": self.PLAYER_1,
            "action": {"type": "guess"},
        }
        error = validate_action_envelope(
            envelope=envelope,
            session_phase=Phase.COMPLETED,
            session_revision=5,
            current_turn=MinigameTurnSide.PLAYER_1,
            player_1_membership_id=self.PLAYER_1,
            player_2_membership_id=self.PLAYER_2,
        )

        assert isinstance(error, ActionError), "Expected an ActionError for COMPLETED phase"
        assert error.code == "SESSION_ENDED"
        assert "منتهية" in error.message_ar or "غير نشطة" in error.message_ar
