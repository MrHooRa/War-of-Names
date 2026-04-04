"""Pure helpers for minigame runtime state and phase timers."""

from __future__ import annotations

from datetime import datetime, timedelta


def is_parallel_selection_phase(state: dict | None) -> bool:
    """Return True when the current in-game phase allows parallel input."""
    if not isinstance(state, dict):
        return False
    return state.get("game_phase") == "word_selection"


def resolve_state_timer_duration_ms(
    state: dict | None,
    *,
    fallback_ms: int | None = None,
) -> int | None:
    """Resolve the active timer duration from normalized session state settings."""
    if not isinstance(state, dict):
        return fallback_ms

    settings = state.get("settings", {}) or {}
    game_phase = state.get("game_phase")

    seconds = None
    if game_phase == "word_selection":
        seconds = settings.get("selection_duration_sec")
    elif state.get("overtime_active") or game_phase == "overtime":
        seconds = settings.get("overtime_turn_duration_sec")
    else:
        seconds = settings.get("turn_duration_sec")

    if isinstance(seconds, (int, float)) and seconds > 0:
        return int(seconds * 1000)
    return fallback_ms


def stamp_phase_deadlines(
    state: dict | None,
    *,
    started_at: datetime,
    duration_ms: int | None,
) -> dict:
    """Return a shallow-copied state with the active phase deadline fields updated."""
    new_state = dict(state or {})
    if duration_ms is None or duration_ms <= 0:
        new_state.pop("word_selection_deadline", None)
        new_state.pop("current_turn_deadline", None)
        return new_state

    deadline = started_at + timedelta(milliseconds=int(duration_ms))
    if new_state.get("game_phase") == "word_selection":
        new_state["word_selection_deadline"] = deadline.isoformat()
        new_state.pop("current_turn_deadline", None)
    else:
        new_state["current_turn_deadline"] = deadline.isoformat()
        new_state.pop("word_selection_deadline", None)
    return new_state
