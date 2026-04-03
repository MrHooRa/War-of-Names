"""
Tests for compute_updated_stats() — pure, no DB required.

Covers:
  1. First win — wins=1, streak=1, best=1, total=1
  2. Streak continues — streak and best_streak both increment
  3. Loss resets streak — current_streak=0, best_streak unchanged
  4. Running average calculation — (old * prev + new) / total
  5. Best streak not overwritten by a lower value after loss
"""

import pytest

from app.modules.minigames.leaderboard_service import compute_updated_stats


# ─── Test helpers ─────────────────────────────────────────────────────────────

def _empty() -> dict:
    """Return a baseline empty-stats dict (mirrors a brand-new leaderboard row)."""
    return {
        "wins": 0,
        "losses": 0,
        "current_streak": 0,
        "best_streak": 0,
        "total_matches": 0,
        "avg_tools_used": 0.0,
        "avg_match_duration_sec": 0.0,
    }


# ─── Tests ────────────────────────────────────────────────────────────────────

def test_first_win():
    """After a single win from an empty baseline all counters are 1."""
    result = compute_updated_stats(current=_empty(), is_win=True, tools_used=2, duration_sec=30.0)

    assert result["wins"] == 1
    assert result["losses"] == 0
    assert result["current_streak"] == 1
    assert result["best_streak"] == 1
    assert result["total_matches"] == 1
    assert result["avg_tools_used"] == 2.0
    assert result["avg_match_duration_sec"] == 30.0


def test_streak_continues():
    """Consecutive wins increment both current_streak and best_streak."""
    state = _empty()

    # Match 1 — win
    state = compute_updated_stats(current=state, is_win=True)
    # Match 2 — win
    state = compute_updated_stats(current=state, is_win=True)
    # Match 3 — win
    state = compute_updated_stats(current=state, is_win=True)

    assert state["wins"] == 3
    assert state["current_streak"] == 3
    assert state["best_streak"] == 3
    assert state["total_matches"] == 3


def test_loss_resets_streak():
    """A loss sets current_streak to 0 but does not touch best_streak."""
    state = _empty()

    # Build a streak of 3
    for _ in range(3):
        state = compute_updated_stats(current=state, is_win=True)

    assert state["best_streak"] == 3

    # One loss
    state = compute_updated_stats(current=state, is_win=False)

    assert state["current_streak"] == 0
    assert state["best_streak"] == 3          # unchanged
    assert state["losses"] == 1
    assert state["wins"] == 3
    assert state["total_matches"] == 4


def test_running_average_calculation():
    """Running averages obey: new_avg = (old_avg * prev_count + new_value) / total."""
    state = _empty()

    # Match 1: tools=4, duration=20s  → avg = (0*0 + 4)/1 = 4.0, (0*0 + 20)/1 = 20.0
    state = compute_updated_stats(current=state, is_win=True, tools_used=4, duration_sec=20.0)
    assert state["avg_tools_used"] == 4.0
    assert state["avg_match_duration_sec"] == 20.0

    # Match 2: tools=2, duration=40s  → avg = (4*1 + 2)/2 = 3.0, (20*1 + 40)/2 = 30.0
    state = compute_updated_stats(current=state, is_win=True, tools_used=2, duration_sec=40.0)
    assert state["avg_tools_used"] == 3.0
    assert state["avg_match_duration_sec"] == 30.0

    # Match 3: tools=6, duration=30s  → avg = (3*2 + 6)/3 = 4.0, (30*2 + 30)/3 = 30.0
    state = compute_updated_stats(current=state, is_win=False, tools_used=6, duration_sec=30.0)
    assert state["avg_tools_used"] == 4.0
    assert state["avg_match_duration_sec"] == 30.0


def test_best_streak_not_overwritten_by_lower_value():
    """After losing the streak, a short new win-run must not overwrite the old best."""
    state = _empty()

    # Build streak of 5
    for _ in range(5):
        state = compute_updated_stats(current=state, is_win=True)

    assert state["best_streak"] == 5

    # One loss → streak reset
    state = compute_updated_stats(current=state, is_win=False)

    # Two wins → new streak of 2, which is less than best of 5
    for _ in range(2):
        state = compute_updated_stats(current=state, is_win=True)

    assert state["current_streak"] == 2
    assert state["best_streak"] == 5          # must remain 5
