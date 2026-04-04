"""Pure resolver that produces effective catalog metadata for a game type.

When a MinigameCatalogConfig row exists, its values are returned as-is
(normalized to dict). When it is missing, a fallback dict is returned
per BRD §11.4.3 and a warning flag is set so the caller can emit a
`catalog_config_missing` telemetry event.

This module is a pure function module — no DB, no async, fully testable.
"""

from __future__ import annotations

from typing import Any


# BRD §11.4.3 fallback constants
FALLBACK_ICON_TOKEN = "lucide:gamepad-2"
FALLBACK_ACCENT_COLOR = "#64748B"  # brand-slate
FALLBACK_HERO_VARIANT = "arena"
FALLBACK_CARD_VARIANT = "standard"
FALLBACK_AVAILABILITY_MODE = "hidden"
FALLBACK_SORT_ORDER = 999
FALLBACK_SHORT_DESCRIPTION_EMPTY = ""


def _enum_value(value: Any) -> str:
    """Coerce a StrEnum member or raw string to its string value."""
    if value is None:
        return ""
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)


def resolve_catalog_config(
    game_type_row: Any,
    config_row: Any | None,
) -> tuple[dict[str, Any], bool]:
    """Return (resolved_config_dict, is_fallback).

    Args:
        game_type_row: A MinigameType-like object with `id`, `name`, `description`.
        config_row: A MinigameCatalogConfig instance, or None when missing.

    Returns:
        A tuple of:
          - resolved dict with all presentation fields populated
          - is_fallback flag (True when config_row was None)

    Fallback rules (BRD §11.4.3):
        short_description → game_type.description or "" when missing
        icon_token        → "lucide:gamepad-2"
        accent_color      → "#64748B" (brand-slate)
        hero_variant      → "arena"
        card_variant      → "standard"
        availability_mode → "hidden"
        sort_order        → 999 (pushed to end)
    """
    if config_row is None:
        return (
            {
                "short_description": (
                    getattr(game_type_row, "description", None)
                    or FALLBACK_SHORT_DESCRIPTION_EMPTY
                ),
                "icon_token": FALLBACK_ICON_TOKEN,
                "accent_color": FALLBACK_ACCENT_COLOR,
                "hero_variant": FALLBACK_HERO_VARIANT,
                "card_variant": FALLBACK_CARD_VARIANT,
                "estimated_duration_sec": None,
                "featured": False,
                "sort_order": FALLBACK_SORT_ORDER,
                "availability_mode": FALLBACK_AVAILABILITY_MODE,
                "marketing_label": None,
                "expected_launch_at": None,
            },
            True,
        )

    return (
        {
            "short_description": config_row.short_description,
            "icon_token": config_row.icon_token,
            "accent_color": config_row.accent_color,
            "hero_variant": _enum_value(config_row.hero_variant),
            "card_variant": _enum_value(config_row.card_variant),
            "estimated_duration_sec": config_row.estimated_duration_sec,
            "featured": config_row.featured,
            "sort_order": config_row.sort_order,
            "availability_mode": _enum_value(config_row.availability_mode),
            "marketing_label": config_row.marketing_label,
            "expected_launch_at": config_row.expected_launch_at,
        },
        False,
    )
