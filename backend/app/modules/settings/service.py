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

from app.core.enums import SettingScope
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
