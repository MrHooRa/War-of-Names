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
) -> dict[str, Any]:
    """Load all minigame settings via cascade, with fallback defaults."""
    from app.modules.settings.service import get_settings_batch

    raw = await get_settings_batch(
        session,
        MINIGAME_SETTING_KEYS,
        competition_id=competition_id,
        season_id=season_id,
        cycle_id=cycle_id,
    )

    result = {}
    for key in MINIGAME_SETTING_KEYS:
        value = raw.get(key)
        if value is None:
            value = MINIGAME_DEFAULTS[key]
        result[key] = value

    return result
