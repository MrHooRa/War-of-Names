"""Tests for catalog helper pure functions.

All functions are stateless, no DB, no async. These tests cover every
branch of BRD §9.1, §15.4, and §8.1.1.
"""

import pytest

from app.modules.minigames.catalog_helpers import (
    build_player_count_label,
    resolve_card_status,
    resolve_estimated_duration,
)


# ── build_player_count_label (BRD §9.1) ────────────────────────────

class TestPlayerCountLabel:
    def test_1v1(self):
        assert build_player_count_label(2, 2) == "1v1"

    def test_solo(self):
        assert build_player_count_label(1, 1) == "منفرد"

    def test_fixed_four(self):
        assert build_player_count_label(4, 4) == "4 لاعبين"

    def test_fixed_six(self):
        assert build_player_count_label(6, 6) == "6 لاعبين"

    def test_range_2_to_4(self):
        assert build_player_count_label(2, 4) == "2-4 لاعبين"

    def test_range_3_to_8(self):
        assert build_player_count_label(3, 8) == "3-8 لاعبين"

    def test_invalid_min_greater_than_max_returns_empty(self):
        assert build_player_count_label(5, 2) == ""

    def test_invalid_zero_returns_empty(self):
        assert build_player_count_label(0, 0) == ""

    def test_invalid_negative_returns_empty(self):
        assert build_player_count_label(-1, 2) == ""


# ── resolve_card_status (BRD §15.4) ────────────────────────────────

class TestResolveCardStatus:
    def _base(self, **overrides):
        defaults = dict(
            availability_mode="active",
            kill_switch_level="off",
            my_active_session_id=None,
            in_queue=False,
            player_balance=1000,
            buy_in_amount=500,
            is_bankrupt=False,
        )
        defaults.update(overrides)
        return defaults

    def test_playable_default(self):
        status, reason = resolve_card_status(**self._base())
        assert status == "playable"
        assert reason is None

    def test_in_match_beats_everything(self):
        """BRD §15.4 priority 1 — in_match trumps all other statuses."""
        status, reason = resolve_card_status(
            **self._base(
                my_active_session_id="00000000-0000-0000-0000-000000000001",
                in_queue=True,
                player_balance=0,
                is_bankrupt=True,
            )
        )
        assert status == "in_match"
        assert reason is None

    def test_queued_beats_balance_and_availability(self):
        """BRD §15.4 priority 2 — queued trumps balance/maintenance/coming_soon."""
        status, reason = resolve_card_status(
            **self._base(in_queue=True, player_balance=0, is_bankrupt=True)
        )
        assert status == "queued"

    def test_insufficient_balance(self):
        status, reason = resolve_card_status(
            **self._base(player_balance=200, buy_in_amount=500)
        )
        assert status == "insufficient_balance"
        assert "500" in (reason or "")

    def test_bankrupt_treated_as_insufficient_balance(self):
        status, reason = resolve_card_status(**self._base(is_bankrupt=True))
        assert status == "insufficient_balance"

    def test_exact_balance_is_playable(self):
        status, _ = resolve_card_status(
            **self._base(player_balance=500, buy_in_amount=500)
        )
        assert status == "playable"

    def test_maintenance_availability(self):
        status, reason = resolve_card_status(
            **self._base(availability_mode="maintenance")
        )
        assert status == "maintenance"
        assert reason is not None

    def test_kill_switch_emergency_treated_as_maintenance(self):
        status, _ = resolve_card_status(**self._base(kill_switch_level="emergency"))
        assert status == "maintenance"

    def test_kill_switch_hard_treated_as_maintenance(self):
        status, _ = resolve_card_status(**self._base(kill_switch_level="hard"))
        assert status == "maintenance"

    def test_coming_soon_availability(self):
        status, _ = resolve_card_status(**self._base(availability_mode="coming_soon"))
        assert status == "coming_soon"

    def test_hidden_availability(self):
        status, _ = resolve_card_status(**self._base(availability_mode="hidden"))
        assert status == "hidden"


# ── resolve_estimated_duration (BRD §8.1.1) ─────────────────────────

class TestResolveEstimatedDuration:
    def test_stats_with_enough_matches(self):
        duration, source = resolve_estimated_duration(
            leaderboard_avg_sec=285.5,
            leaderboard_match_count=42,
            config_duration_sec=300,
        )
        assert duration == 285  # rounded down
        assert source == "stats"

    def test_stats_with_exactly_ten_matches_uses_stats(self):
        duration, source = resolve_estimated_duration(
            leaderboard_avg_sec=310.0,
            leaderboard_match_count=10,
            config_duration_sec=300,
        )
        assert duration == 310
        assert source == "stats"

    def test_stats_with_fewer_than_ten_matches_falls_back_to_config(self):
        duration, source = resolve_estimated_duration(
            leaderboard_avg_sec=100.0,
            leaderboard_match_count=9,
            config_duration_sec=300,
        )
        assert duration == 300
        assert source == "config"

    def test_null_stats_falls_back_to_config(self):
        duration, source = resolve_estimated_duration(
            leaderboard_avg_sec=None,
            leaderboard_match_count=0,
            config_duration_sec=300,
        )
        assert duration == 300
        assert source == "config"

    def test_null_both_returns_none(self):
        duration, source = resolve_estimated_duration(
            leaderboard_avg_sec=None,
            leaderboard_match_count=0,
            config_duration_sec=None,
        )
        assert duration is None
        assert source is None

    def test_zero_config_treated_as_missing(self):
        duration, source = resolve_estimated_duration(
            leaderboard_avg_sec=None,
            leaderboard_match_count=0,
            config_duration_sec=0,
        )
        assert duration is None
        assert source is None
