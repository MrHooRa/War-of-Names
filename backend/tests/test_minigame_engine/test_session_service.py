"""Unit tests for minigame session_service pure functions.

Only ``validate_session_creation`` and ``compute_transition_update`` are
tested here — they are sync functions with no database dependency.

``_now()`` is patched to a fixed datetime so tests remain deterministic and
do not require the application's settings/config stack (pydantic_settings,
asyncpg, etc.) to be installed.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import patch

import pytest

from app.core.enums import MinigameSessionPhase as Phase, MinigameTurnSide
from app.modules.minigames.session_service import (
    compute_transition_update,
    validate_session_creation,
)

# Fixed timestamp used wherever _now() would be called during tests.
_FIXED_NOW = datetime(2026, 4, 1, 12, 0, 0)


def _transition(**kwargs):
    """Helper: call compute_transition_update with _now patched."""
    with patch("app.modules.minigames.session_service._now", return_value=_FIXED_NOW):
        return compute_transition_update(**kwargs)


# ---------------------------------------------------------------------------
# validate_session_creation
# ---------------------------------------------------------------------------


class TestValidateSessionCreation:
    """Tests for the creation-time validation helper."""

    def _valid_kwargs(self, **overrides):
        base = dict(
            game_type_id="mutaraha",
            plugin_exists=True,
            plugin_status="active",
            player_balance=200,
            buy_in_amount=100,
            is_bankrupt=False,
        )
        base.update(overrides)
        return base

    def test_valid_inputs_returns_empty_list(self):
        errors = validate_session_creation(**self._valid_kwargs())
        assert errors == []

    def test_unknown_game_type_returns_error(self):
        errors = validate_session_creation(**self._valid_kwargs(
            game_type_id="ghost_game",
            plugin_exists=False,
        ))
        assert len(errors) == 1
        assert "ghost_game" in errors[0]
        assert "غير موجود" in errors[0]

    def test_unknown_game_type_short_circuits_other_checks(self):
        """When plugin is missing, disabled / balance checks must be skipped."""
        errors = validate_session_creation(**self._valid_kwargs(
            game_type_id="ghost_game",
            plugin_exists=False,
            plugin_status="disabled",
            is_bankrupt=True,
            player_balance=0,
            buy_in_amount=500,
        ))
        # Only the "not found" error should appear.
        assert len(errors) == 1

    def test_disabled_plugin_returns_error(self):
        errors = validate_session_creation(**self._valid_kwargs(
            plugin_status="disabled",
        ))
        assert any("معطلة" in e for e in errors)

    def test_insufficient_balance_returns_error(self):
        errors = validate_session_creation(**self._valid_kwargs(
            player_balance=50,
            buy_in_amount=100,
        ))
        assert any("100" in e and "رصيد" in e for e in errors)

    def test_bankrupt_player_returns_error(self):
        errors = validate_session_creation(**self._valid_kwargs(is_bankrupt=True))
        assert any("مفلس" in e for e in errors)

    def test_exact_balance_equals_buy_in_is_valid(self):
        """Edge case: balance exactly equal to buy-in should pass."""
        errors = validate_session_creation(**self._valid_kwargs(
            player_balance=100,
            buy_in_amount=100,
        ))
        assert errors == []

    def test_multiple_errors_accumulate(self):
        """Disabled plugin, bankrupt, and insufficient balance should all appear."""
        errors = validate_session_creation(**self._valid_kwargs(
            plugin_status="disabled",
            is_bankrupt=True,
            player_balance=0,
            buy_in_amount=100,
        ))
        assert len(errors) == 3


# ---------------------------------------------------------------------------
# compute_transition_update
# ---------------------------------------------------------------------------


class TestComputeTransitionUpdate:
    """Tests for the transition-field computation helper."""

    def test_valid_transition_created_to_waiting(self):
        result = _transition(
            current_phase=Phase.CREATED,
            target_phase=Phase.WAITING,
            current_revision=0,
        )
        assert result["phase"] == Phase.WAITING
        assert result["revision"] == 1
        assert result["updated_at"] == _FIXED_NOW
        # Non-terminal: no completed_at / terminal_reason / winner
        assert "completed_at" not in result
        assert "terminal_reason" not in result
        assert "winner_membership_id" not in result

    def test_terminal_transition_sets_completion_fields(self):
        winner_id = uuid.uuid4()
        result = _transition(
            current_phase=Phase.IN_PROGRESS,
            target_phase=Phase.COMPLETED,
            current_revision=3,
            terminal_reason="player_won",
            winner_membership_id=winner_id,
        )
        assert result["phase"] == Phase.COMPLETED
        assert result["revision"] == 4
        assert result["completed_at"] == _FIXED_NOW
        assert result["terminal_reason"] == "player_won"
        assert result["winner_membership_id"] == winner_id

    def test_invalid_transition_raises_value_error(self):
        with pytest.raises(ValueError, match="انتقال غير صالح"):
            _transition(
                current_phase=Phase.COMPLETED,
                target_phase=Phase.WAITING,
                current_revision=5,
            )

    def test_transition_to_in_progress_sets_turn_fields(self):
        result = _transition(
            current_phase=Phase.READY,
            target_phase=Phase.IN_PROGRESS,
            current_revision=2,
        )
        assert result["phase"] == Phase.IN_PROGRESS
        assert result["started_at"] == _FIXED_NOW
        assert result["turn_started_at"] == _FIXED_NOW
        assert result["current_turn"] == MinigameTurnSide.PLAYER_1

    def test_revision_increments_by_one(self):
        result = _transition(
            current_phase=Phase.WAITING,
            target_phase=Phase.READY,
            current_revision=7,
        )
        assert result["revision"] == 8

    def test_string_phase_values_accepted(self):
        """Phase inputs may arrive as raw strings from DB rows."""
        result = _transition(
            current_phase="created",
            target_phase="waiting",
            current_revision=0,
        )
        assert result["phase"] == Phase.WAITING
        assert result["revision"] == 1

    def test_cancelled_terminal_has_no_winner(self):
        result = _transition(
            current_phase=Phase.CREATED,
            target_phase=Phase.CANCELLED,
            current_revision=0,
            terminal_reason="admin_cancelled",
        )
        assert result["phase"] == Phase.CANCELLED
        assert result["completed_at"] == _FIXED_NOW
        assert result["terminal_reason"] == "admin_cancelled"
        assert result["winner_membership_id"] is None
