"""Minigame settings helper — loads settings via cascade with fallback defaults.

Pure functions:
    check_kill_switch — evaluate kill switch level and permissions

Async:
    get_minigame_settings — loads all minigame settings via cascade
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import uuid
    from sqlalchemy.ext.asyncio import AsyncSession

# All minigame setting keys
MINIGAME_SETTING_KEYS: list[str] = [
    "minigame_enabled",
    "minigame_buy_in",
    "minigame_daily_limit",
    "minigame_same_opponent_limit",
    "minigame_turn_duration_sec",
    "minigame_overtime_enabled",
    "minigame_grace_timer_sec",
    "minigame_kill_switch",
]

GAME_SPECIFIC_SETTING_KEYS: dict[str, list[str]] = {
    "mutaraha": [
        "mutaraha_enabled",
        "mutaraha_buy_in",
        "mutaraha_daily_limit",
        "mutaraha_same_opponent_limit",
        "mutaraha_turn_duration_sec",
        "mutaraha_selection_duration_sec",
        "mutaraha_overtime_enabled",
        "mutaraha_overtime_turns",
        "mutaraha_overtime_turn_sec",
        "mutaraha_overtime_cost_multiplier",
        "mutaraha_redraw_cost",
        "mutaraha_grace_timer_sec",
        "mutaraha_queue_timeout_sec",
        "mutaraha_challenge_timeout_sec",
        "mutaraha_cost_letter_check",
        "mutaraha_cost_word_length",
        "mutaraha_cost_letter_eliminate",
        "mutaraha_cost_first_letter",
        "mutaraha_cost_narrow_down",
        "mutaraha_cost_wrong_guess",
        "mutaraha_categories_enabled",
        "mutaraha_disabled_words",
        "mutaraha_words_per_draw",
        "mutaraha_words_to_select",
        "mutaraha_recent_match_word_limit",
    ],
}

# Fallback defaults (used when DB settings are missing)
MINIGAME_DEFAULTS: dict[str, Any] = {
    "minigame_enabled": False,
    "minigame_buy_in": 500,
    "minigame_daily_limit": 2,
    "minigame_same_opponent_limit": 1,
    "minigame_turn_duration_sec": 30,
    "minigame_overtime_enabled": True,
    "minigame_grace_timer_sec": 60,
    "minigame_kill_switch": "off",
}

GAME_SPECIFIC_DEFAULTS: dict[str, dict[str, Any]] = {
    "mutaraha": {
        "mutaraha_enabled": False,
        "mutaraha_buy_in": 500,
        "mutaraha_daily_limit": 2,
        "mutaraha_same_opponent_limit": 1,
        "mutaraha_turn_duration_sec": 30,
        "mutaraha_selection_duration_sec": 45,
        "mutaraha_overtime_enabled": True,
        "mutaraha_overtime_turns": 3,
        "mutaraha_overtime_turn_sec": 20,
        "mutaraha_overtime_cost_multiplier": 2,
        "mutaraha_redraw_cost": 20,
        "mutaraha_grace_timer_sec": 60,
        "mutaraha_queue_timeout_sec": 120,
        "mutaraha_challenge_timeout_sec": 60,
        "mutaraha_cost_letter_check": 20,
        "mutaraha_cost_word_length": 20,
        "mutaraha_cost_letter_eliminate": 40,
        "mutaraha_cost_first_letter": 50,
        "mutaraha_cost_narrow_down": 60,
        "mutaraha_cost_wrong_guess": 50,
        "mutaraha_categories_enabled": [],
        "mutaraha_disabled_words": [],
        "mutaraha_words_per_draw": 10,
        "mutaraha_words_to_select": 5,
        "mutaraha_recent_match_word_limit": 5,
    },
}


class KillSwitchLevel(StrEnum):
    OFF = "off"
    SOFT = "soft"
    HARD = "hard"
    EMERGENCY = "emergency"


@dataclass
class KillSwitchStatus:
    """Result of evaluating kill switch level."""
    level: KillSwitchLevel
    can_create_session: bool
    can_matchmake: bool
    cancel_active: bool = False
    message_ar: str = ""


def check_kill_switch(value: str | None) -> KillSwitchStatus:
    """Evaluate kill switch level and return permissions.

    BRD Section 16.3:
    - off: everything works
    - soft: no new matchmaking, active sessions continue
    - hard: no new sessions at all
    - emergency: cancel all active sessions + refund
    """
    if value is None or value not in {e.value for e in KillSwitchLevel}:
        return KillSwitchStatus(
            level=KillSwitchLevel.OFF,
            can_create_session=True,
            can_matchmake=True,
        )

    level = KillSwitchLevel(value)

    if level == KillSwitchLevel.OFF:
        return KillSwitchStatus(
            level=level,
            can_create_session=True,
            can_matchmake=True,
        )

    if level == KillSwitchLevel.SOFT:
        return KillSwitchStatus(
            level=level,
            can_create_session=True,
            can_matchmake=False,
            message_ar="التوفيق معطل مؤقتاً — المباريات الجارية مستمرة",
        )

    if level == KillSwitchLevel.HARD:
        return KillSwitchStatus(
            level=level,
            can_create_session=False,
            can_matchmake=False,
            message_ar="الألعاب المصغرة معطلة حالياً",
        )

    # EMERGENCY
    return KillSwitchStatus(
        level=level,
        can_create_session=False,
        can_matchmake=False,
        cancel_active=True,
        message_ar="إيقاف طارئ — جميع الجلسات ملغاة مع استرداد",
    )


async def get_minigame_settings(
    session: "AsyncSession",
    *,
    competition_id: "uuid.UUID",
    season_id: "uuid.UUID | None" = None,
    cycle_id: "uuid.UUID | None" = None,
    game_type: str | None = None,
) -> dict[str, Any]:
    """Load all minigame settings via cascade, with fallback defaults."""
    from app.modules.settings.service import get_settings_batch

    keys = list(MINIGAME_SETTING_KEYS)
    defaults = dict(MINIGAME_DEFAULTS)
    if game_type:
        keys.extend(GAME_SPECIFIC_SETTING_KEYS.get(game_type, []))
        defaults.update(GAME_SPECIFIC_DEFAULTS.get(game_type, {}))

    raw = await get_settings_batch(
        session,
        keys,
        competition_id=competition_id,
        season_id=season_id,
        cycle_id=cycle_id,
    )

    result = {}
    for key in keys:
        value = raw.get(key)
        if value is None:
            value = defaults[key]
        result[key] = value

    return result


def get_setting_keys_for_game(game_type: str | None = None) -> list[str]:
    """Return the generic minigame setting keys plus any game-specific keys."""
    keys = list(MINIGAME_SETTING_KEYS)
    if game_type:
        keys.extend(GAME_SPECIFIC_SETTING_KEYS.get(game_type, []))
    return keys


def get_setting_defaults_for_game(game_type: str | None = None) -> dict[str, Any]:
    """Return fallback defaults for the generic + game-specific settings set."""
    defaults = dict(MINIGAME_DEFAULTS)
    if game_type:
        defaults.update(GAME_SPECIFIC_DEFAULTS.get(game_type, {}))
    return defaults


def get_effective_setting(
    settings: dict[str, Any],
    *,
    generic_key: str,
    game_key: str | None = None,
    default: Any = None,
) -> Any:
    """Prefer a game-specific override and fall back to the generic engine setting."""
    if game_key and settings.get(game_key) is not None:
        return settings.get(game_key)
    if settings.get(generic_key) is not None:
        return settings.get(generic_key)
    return default
