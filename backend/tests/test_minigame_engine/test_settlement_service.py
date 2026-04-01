"""
Tests for minigame settlement_service — pure compute_settlement_type() only.

All tests in this module are synchronous and require no database connection.
The async execute_settlement() function is covered by integration tests elsewhere.
"""

import uuid

import pytest

from app.modules.minigames.settlement_service import (
    SettlementType,
    compute_settlement_type,
)

# ─── Constants ────────────────────────────────────────────────────────────────

WINNER_ID = uuid.uuid4()

# Terminal phases (as string values matching MinigameSessionPhase)
PHASE_COMPLETED = "completed"
PHASE_CANCELLED = "cancelled"
PHASE_ABANDONED = "abandoned"

# Non-terminal phases
PHASE_IN_PROGRESS = "in_progress"
PHASE_WAITING = "waiting"
PHASE_CREATED = "created"
PHASE_PAUSED = "paused"
PHASE_READY = "ready"


# ─── compute_settlement_type tests ───────────────────────────────────────────

class TestComputeSettlementType:
    """Pure-function tests — no DB, no async."""

    # ── NORMAL ────────────────────────────────────────────────────────────────

    def test_completed_with_winner_is_normal(self):
        result = compute_settlement_type(
            phase=PHASE_COMPLETED,
            terminal_reason=None,
            winner_membership_id=WINNER_ID,
            is_solo=False,
        )
        assert result == SettlementType.NORMAL

    def test_completed_without_winner_is_normal(self):
        """COMPLETED + no winner + not solo → NORMAL (draw scenario)."""
        result = compute_settlement_type(
            phase=PHASE_COMPLETED,
            terminal_reason=None,
            winner_membership_id=None,
            is_solo=False,
        )
        assert result == SettlementType.NORMAL

    # ── FORFEIT ───────────────────────────────────────────────────────────────

    def test_abandoned_with_winner_is_forfeit(self):
        result = compute_settlement_type(
            phase=PHASE_ABANDONED,
            terminal_reason="grace_timeout",
            winner_membership_id=WINNER_ID,
            is_solo=False,
        )
        assert result == SettlementType.FORFEIT

    # ── CANCEL ────────────────────────────────────────────────────────────────

    def test_cancelled_is_cancel(self):
        result = compute_settlement_type(
            phase=PHASE_CANCELLED,
            terminal_reason=None,
            winner_membership_id=None,
            is_solo=False,
        )
        assert result == SettlementType.CANCEL

    def test_cancelled_with_winner_is_still_cancel(self):
        """CANCELLED always maps to CANCEL, even when a winner is recorded."""
        result = compute_settlement_type(
            phase=PHASE_CANCELLED,
            terminal_reason=None,
            winner_membership_id=WINNER_ID,
            is_solo=False,
        )
        assert result == SettlementType.CANCEL

    def test_abandoned_no_winner_is_cancel(self):
        """Both players disconnected → no winner → CANCEL (refund both)."""
        result = compute_settlement_type(
            phase=PHASE_ABANDONED,
            terminal_reason="both_disconnected",
            winner_membership_id=None,
            is_solo=False,
        )
        assert result == SettlementType.CANCEL

    # ── SOLO ──────────────────────────────────────────────────────────────────

    def test_completed_solo_is_solo(self):
        result = compute_settlement_type(
            phase=PHASE_COMPLETED,
            terminal_reason=None,
            winner_membership_id=None,
            is_solo=True,
        )
        assert result == SettlementType.SOLO

    def test_completed_not_solo_is_normal(self):
        result = compute_settlement_type(
            phase=PHASE_COMPLETED,
            terminal_reason=None,
            winner_membership_id=WINNER_ID,
            is_solo=False,
        )
        assert result == SettlementType.NORMAL

    # ── Non-terminal raises ValueError ────────────────────────────────────────

    @pytest.mark.parametrize("phase", [
        PHASE_IN_PROGRESS,
        PHASE_WAITING,
        PHASE_CREATED,
        PHASE_PAUSED,
        PHASE_READY,
    ])
    def test_non_terminal_phase_raises(self, phase: str):
        with pytest.raises(ValueError, match="لا يمكن تسوية جلسة غير نهائية"):
            compute_settlement_type(
                phase=phase,
                terminal_reason=None,
                winner_membership_id=None,
                is_solo=False,
            )

    # ── Return type is always SettlementType ──────────────────────────────────

    @pytest.mark.parametrize("phase,winner,is_solo,expected", [
        (PHASE_COMPLETED, WINNER_ID, False, SettlementType.NORMAL),
        (PHASE_COMPLETED, None,      False, SettlementType.NORMAL),
        (PHASE_COMPLETED, None,      True,  SettlementType.SOLO),
        (PHASE_ABANDONED, WINNER_ID, False, SettlementType.FORFEIT),
        (PHASE_ABANDONED, None,      False, SettlementType.CANCEL),
        (PHASE_CANCELLED, None,      False, SettlementType.CANCEL),
        (PHASE_CANCELLED, WINNER_ID, False, SettlementType.CANCEL),
    ])
    def test_return_is_settlement_type_enum(
        self, phase, winner, is_solo, expected
    ):
        result = compute_settlement_type(
            phase=phase,
            terminal_reason=None,
            winner_membership_id=winner,
            is_solo=is_solo,
        )
        assert isinstance(result, SettlementType)
        assert result == expected
