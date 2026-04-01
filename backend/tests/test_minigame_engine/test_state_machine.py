"""Test session state machine transitions."""

import pytest
from app.core.enums import MinigameSessionPhase as Phase
from app.modules.minigames.state_machine import (
    TERMINAL_PHASES,
    can_transition,
    validate_transition,
    is_terminal,
)


# ── Valid transitions ─────────────────────────────────────────────

def test_created_to_waiting():
    assert can_transition(Phase.CREATED, Phase.WAITING) is True


def test_created_to_cancelled():
    assert can_transition(Phase.CREATED, Phase.CANCELLED) is True


def test_waiting_to_ready():
    assert can_transition(Phase.WAITING, Phase.READY) is True


def test_waiting_to_cancelled():
    assert can_transition(Phase.WAITING, Phase.CANCELLED) is True


def test_ready_to_in_progress():
    assert can_transition(Phase.READY, Phase.IN_PROGRESS) is True


def test_ready_to_cancelled():
    assert can_transition(Phase.READY, Phase.CANCELLED) is True


def test_in_progress_to_completed():
    assert can_transition(Phase.IN_PROGRESS, Phase.COMPLETED) is True


def test_in_progress_to_overtime():
    assert can_transition(Phase.IN_PROGRESS, Phase.OVERTIME) is True


def test_in_progress_to_paused():
    assert can_transition(Phase.IN_PROGRESS, Phase.PAUSED) is True


def test_in_progress_to_abandoned():
    assert can_transition(Phase.IN_PROGRESS, Phase.ABANDONED) is True


def test_in_progress_to_cancelled():
    assert can_transition(Phase.IN_PROGRESS, Phase.CANCELLED) is True


def test_overtime_to_completed():
    assert can_transition(Phase.OVERTIME, Phase.COMPLETED) is True


def test_overtime_to_abandoned():
    assert can_transition(Phase.OVERTIME, Phase.ABANDONED) is True


def test_paused_to_in_progress():
    assert can_transition(Phase.PAUSED, Phase.IN_PROGRESS) is True


def test_paused_to_abandoned():
    assert can_transition(Phase.PAUSED, Phase.ABANDONED) is True


# ── Invalid transitions ──────────────────────────────────────────

def test_created_to_in_progress_invalid():
    assert can_transition(Phase.CREATED, Phase.IN_PROGRESS) is False


def test_waiting_to_in_progress_invalid():
    assert can_transition(Phase.WAITING, Phase.IN_PROGRESS) is False


def test_completed_to_anything_invalid():
    for target in Phase:
        assert can_transition(Phase.COMPLETED, target) is False


def test_cancelled_to_anything_invalid():
    for target in Phase:
        assert can_transition(Phase.CANCELLED, target) is False


def test_abandoned_to_anything_invalid():
    for target in Phase:
        assert can_transition(Phase.ABANDONED, target) is False


def test_same_state_transition_invalid():
    for phase in Phase:
        assert can_transition(phase, phase) is False


# ── Terminal states ───────────────────────────────────────────────

def test_terminal_phases():
    assert is_terminal(Phase.COMPLETED) is True
    assert is_terminal(Phase.CANCELLED) is True
    assert is_terminal(Phase.ABANDONED) is True


def test_non_terminal_phases():
    assert is_terminal(Phase.CREATED) is False
    assert is_terminal(Phase.WAITING) is False
    assert is_terminal(Phase.IN_PROGRESS) is False
    assert is_terminal(Phase.OVERTIME) is False
    assert is_terminal(Phase.PAUSED) is False


# ── validate_transition raises on invalid ─────────────────────────

def test_validate_transition_raises_on_invalid():
    with pytest.raises(ValueError, match="انتقال غير صالح"):
        validate_transition(Phase.COMPLETED, Phase.IN_PROGRESS)


def test_validate_transition_passes_on_valid():
    validate_transition(Phase.CREATED, Phase.WAITING)  # Should not raise
