"""Unit tests for minigame policy_service pure functions.

All tests exercise sync-only code (no database, no SQLAlchemy).  The module
can be imported without a running application environment because all
SQLAlchemy imports are deferred inside async function bodies.

16 tests in total — grouped by check type plus one class for run_all_checks.
"""

from __future__ import annotations

import pytest

from app.modules.minigames.policy_service import (
    PolicyBlock,
    check_balance_gate,
    check_bankruptcy,
    check_daily_limit,
    check_opponent_cooldown,
    run_all_checks,
)


# ---------------------------------------------------------------------------
# check_daily_limit  (3 tests)
# ---------------------------------------------------------------------------


class TestCheckDailyLimit:
    def test_under_cap_returns_none(self):
        result = check_daily_limit(matches_today=2, daily_cap=5)
        assert result is None

    def test_at_cap_returns_block(self):
        block = check_daily_limit(matches_today=5, daily_cap=5)
        assert isinstance(block, PolicyBlock)
        assert block.code == "DAILY_LIMIT"
        assert "5" in block.message_ar
        assert "اليومي" in block.message_ar

    def test_over_cap_returns_block(self):
        block = check_daily_limit(matches_today=10, daily_cap=5)
        assert isinstance(block, PolicyBlock)
        assert block.code == "DAILY_LIMIT"


# ---------------------------------------------------------------------------
# check_opponent_cooldown  (3 tests)
# ---------------------------------------------------------------------------


class TestCheckOpponentCooldown:
    def test_no_history_returns_none(self):
        result = check_opponent_cooldown(
            matches_with_opponent_this_cycle=0,
            same_opponent_limit=2,
        )
        assert result is None

    def test_at_limit_returns_block(self):
        block = check_opponent_cooldown(
            matches_with_opponent_this_cycle=2,
            same_opponent_limit=2,
        )
        assert isinstance(block, PolicyBlock)
        assert block.code == "OPPONENT_COOLDOWN"
        assert "الخصم" in block.message_ar

    def test_solo_skips_check(self):
        """Even if already over limit, solo sessions must not be blocked."""
        result = check_opponent_cooldown(
            matches_with_opponent_this_cycle=999,
            same_opponent_limit=1,
            is_solo=True,
        )
        assert result is None


# ---------------------------------------------------------------------------
# check_balance_gate  (3 tests)
# ---------------------------------------------------------------------------


class TestCheckBalanceGate:
    def test_sufficient_balance_returns_none(self):
        result = check_balance_gate(player_balance=200, buy_in_amount=100)
        assert result is None

    def test_insufficient_balance_returns_block(self):
        block = check_balance_gate(player_balance=50, buy_in_amount=100)
        assert isinstance(block, PolicyBlock)
        assert block.code == "INSUFFICIENT_BALANCE"
        assert "100" in block.message_ar
        assert "رصيد" in block.message_ar

    def test_exact_balance_equals_buy_in_returns_none(self):
        """Edge case: balance exactly equal to buy-in must pass."""
        result = check_balance_gate(player_balance=100, buy_in_amount=100)
        assert result is None


# ---------------------------------------------------------------------------
# check_bankruptcy  (2 tests)
# ---------------------------------------------------------------------------


class TestCheckBankruptcy:
    def test_not_bankrupt_returns_none(self):
        result = check_bankruptcy(is_bankrupt=False)
        assert result is None

    def test_bankrupt_returns_block(self):
        block = check_bankruptcy(is_bankrupt=True)
        assert isinstance(block, PolicyBlock)
        assert block.code == "BANKRUPT"
        assert "مفلس" in block.message_ar


# ---------------------------------------------------------------------------
# run_all_checks  (5 tests)
# ---------------------------------------------------------------------------


class TestRunAllChecks:
    """Tests for the aggregator that runs all four checks."""

    def _base_kwargs(self, **overrides):
        base = dict(
            matches_today=0,
            daily_cap=5,
            matches_with_opponent_this_cycle=0,
            same_opponent_limit=2,
            player_balance=200,
            buy_in_amount=100,
            is_bankrupt=False,
            is_solo=False,
        )
        base.update(overrides)
        return base

    def test_all_pass_returns_empty_list(self):
        blocks = run_all_checks(**self._base_kwargs())
        assert blocks == []

    def test_single_failure_returns_one_block(self):
        blocks = run_all_checks(**self._base_kwargs(matches_today=5, daily_cap=5))
        assert len(blocks) == 1
        assert blocks[0].code == "DAILY_LIMIT"

    def test_multiple_failures_all_collected(self):
        """Daily limit + insufficient balance should both appear."""
        blocks = run_all_checks(**self._base_kwargs(
            matches_today=10,
            daily_cap=5,
            player_balance=0,
            buy_in_amount=100,
        ))
        codes = [b.code for b in blocks]
        assert "DAILY_LIMIT" in codes
        assert "INSUFFICIENT_BALANCE" in codes

    def test_solo_skips_opponent_check(self):
        """With is_solo=True the opponent cooldown block must not appear."""
        blocks = run_all_checks(**self._base_kwargs(
            matches_with_opponent_this_cycle=999,
            same_opponent_limit=1,
            is_solo=True,
        ))
        codes = [b.code for b in blocks]
        assert "OPPONENT_COOLDOWN" not in codes

    def test_all_checks_can_fire_simultaneously(self):
        """All four checks triggered at once should return four blocks."""
        blocks = run_all_checks(
            matches_today=10,
            daily_cap=5,
            matches_with_opponent_this_cycle=5,
            same_opponent_limit=2,
            player_balance=0,
            buy_in_amount=100,
            is_bankrupt=True,
            is_solo=False,
        )
        codes = [b.code for b in blocks]
        assert "DAILY_LIMIT" in codes
        assert "OPPONENT_COOLDOWN" in codes
        assert "INSUFFICIENT_BALANCE" in codes
        assert "BANKRUPT" in codes
        assert len(blocks) == 4
