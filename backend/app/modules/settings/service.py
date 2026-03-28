"""
Settings resolver — reads game settings with cascade logic.

Cascade order (most specific wins):
  CYCLE → SEASON → COMPETITION → GLOBAL → SettingDefinition.default_value

Usage:
    value = await get_setting(session, "attack_base_reward", competition_id=comp_id)
"""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import SettingDataType, SettingScope
from app.modules.settings.models import SettingDefinition, SettingValue


async def get_setting(
    session: AsyncSession,
    key: str,
    *,
    competition_id: uuid.UUID | None = None,
    season_id: uuid.UUID | None = None,
    cycle_id: uuid.UUID | None = None,
) -> Any:
    """
    Resolve a single setting value using the cascade.

    Returns the unwrapped value (the "v" key from the JSONB column),
    or None if the setting key doesn't exist at all.
    """
    # Load definition first (needed for default_value fallback)
    defn_result = await session.execute(
        select(SettingDefinition).where(SettingDefinition.key == key)
    )
    defn = defn_result.scalars().first()
    if not defn:
        return None

    # Build candidate scopes from most specific to least
    scopes: list[tuple[SettingScope, uuid.UUID | None]] = []
    if cycle_id:
        scopes.append((SettingScope.CYCLE, cycle_id))
    if season_id:
        scopes.append((SettingScope.SEASON, season_id))
    if competition_id:
        scopes.append((SettingScope.COMPETITION, competition_id))
    scopes.append((SettingScope.GLOBAL, None))

    for scope, scope_id in scopes:
        query = select(SettingValue).where(
            SettingValue.setting_definition_id == defn.id,
            SettingValue.scope == scope,
        )
        if scope_id is not None:
            query = query.where(SettingValue.scope_id == scope_id)
        else:
            query = query.where(SettingValue.scope_id.is_(None))

        result = await session.execute(query)
        sv = result.scalars().first()
        if sv is not None:
            return sv.value.get("v") if isinstance(sv.value, dict) else sv.value

    # Fallback to definition default
    default = defn.default_value
    return default.get("v") if isinstance(default, dict) else default


async def get_settings_batch(
    session: AsyncSession,
    keys: list[str],
    *,
    competition_id: uuid.UUID | None = None,
    season_id: uuid.UUID | None = None,
    cycle_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Resolve multiple settings at once. Returns {key: value} dict."""
    result = {}
    for key in keys:
        result[key] = await get_setting(
            session, key,
            competition_id=competition_id,
            season_id=season_id,
            cycle_id=cycle_id,
        )
    return result


def validate_setting_value(defn: SettingDefinition, value: dict) -> str | None:
    """Validate a setting value against its definition.

    Args:
        defn: The SettingDefinition row.
        value: The JSONB value dict (e.g. {"v": 42}).

    Returns:
        None if valid, or an Arabic error message string if invalid.
    """
    if not isinstance(value, dict) or "v" not in value:
        return "القيمة يجب أن تكون بصيغة {\"v\": ...}"

    v = value["v"]

    # ── Type check ──
    if defn.data_type == SettingDataType.INTEGER:
        if not isinstance(v, int) or isinstance(v, bool):
            return f"الإعداد {defn.key} يتطلب قيمة عددية صحيحة"
    elif defn.data_type == SettingDataType.DECIMAL:
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            return f"الإعداد {defn.key} يتطلب قيمة رقمية"
    elif defn.data_type == SettingDataType.BOOLEAN:
        if not isinstance(v, bool):
            return f"الإعداد {defn.key} يتطلب قيمة منطقية (true/false)"
    elif defn.data_type == SettingDataType.STRING:
        if not isinstance(v, str):
            return f"الإعداد {defn.key} يتطلب قيمة نصية"
    elif defn.data_type == SettingDataType.JSON:
        pass  # Any JSON-serializable value is fine

    # ── allowed_values check ──
    if defn.allowed_values:
        av = defn.allowed_values

        # Range check: {"min": X, "max": Y}
        if "min" in av and isinstance(v, (int, float)):
            if v < av["min"]:
                return f"القيمة يجب أن تكون {av['min']} على الأقل"
        if "max" in av and isinstance(v, (int, float)):
            if v > av["max"]:
                return f"القيمة يجب ألا تتجاوز {av['max']}"

        # Options check: {"options": ["a", "b", "c"]}
        if "options" in av:
            if v not in av["options"]:
                options_str = "، ".join(str(o) for o in av["options"])
                return f"القيمة يجب أن تكون إحدى: {options_str}"

    return None
