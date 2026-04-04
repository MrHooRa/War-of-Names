"""Test the pure catalog config resolver.

Verifies fallback defaults from BRD §11.4.3 when a config row is missing,
and passthrough of real values when present.
"""

from types import SimpleNamespace

from app.modules.minigames.catalog_config_resolver import (
    FALLBACK_ACCENT_COLOR,
    FALLBACK_CARD_VARIANT,
    FALLBACK_HERO_VARIANT,
    FALLBACK_ICON_TOKEN,
    FALLBACK_SHORT_DESCRIPTION_EMPTY,
    resolve_catalog_config,
)


def _game_type(description: str | None = None):
    return SimpleNamespace(id="demo", name="Demo", description=description)


def _config(**overrides):
    # Use plain strings for enum values to keep the test DB-free.
    base = dict(
        game_type="demo",
        short_description="custom short",
        icon_token="lucide:custom",
        accent_color="#ABCDEF",
        hero_variant="duel",
        card_variant="featured",
        estimated_duration_sec=420,
        featured=True,
        sort_order=5,
        availability_mode="active",
        marketing_label="hot",
        expected_launch_at=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


# ── Config present — passthrough ─────────────────────────────

def test_real_config_returned_as_is():
    gt = _game_type(description="ignored description")
    cfg = _config()

    result, warning = resolve_catalog_config(gt, cfg)

    assert warning is False
    assert result["short_description"] == "custom short"
    assert result["icon_token"] == "lucide:custom"
    assert result["accent_color"] == "#ABCDEF"
    assert result["hero_variant"] == "duel"
    assert result["card_variant"] == "featured"
    assert result["estimated_duration_sec"] == 420
    assert result["featured"] is True
    assert result["sort_order"] == 5
    assert result["availability_mode"] == "active"
    assert result["marketing_label"] == "hot"
    assert result["expected_launch_at"] is None


def test_enum_passthrough_accepts_plain_strings():
    """Resolver must also handle dict-ish inputs with string enum values."""
    gt = _game_type()
    cfg = SimpleNamespace(
        game_type="demo",
        short_description="s",
        icon_token="lucide:x",
        accent_color="#000000",
        hero_variant="arena",
        card_variant="standard",
        estimated_duration_sec=None,
        featured=False,
        sort_order=50,
        availability_mode="active",
        marketing_label=None,
        expected_launch_at=None,
    )

    result, warning = resolve_catalog_config(gt, cfg)

    assert warning is False
    assert result["hero_variant"] == "arena"
    assert result["card_variant"] == "standard"


# ── Config missing — fallback ────────────────────────────────

def test_missing_config_returns_fallback_with_game_type_description():
    gt = _game_type(description="a game type description")

    result, warning = resolve_catalog_config(gt, None)

    assert warning is True
    assert result["short_description"] == "a game type description"
    assert result["icon_token"] == FALLBACK_ICON_TOKEN
    assert result["accent_color"] == FALLBACK_ACCENT_COLOR
    assert result["hero_variant"] == FALLBACK_HERO_VARIANT
    assert result["card_variant"] == FALLBACK_CARD_VARIANT
    assert result["availability_mode"] == "hidden"


def test_missing_config_with_null_description_uses_empty_string():
    gt = _game_type(description=None)

    result, warning = resolve_catalog_config(gt, None)

    assert warning is True
    assert result["short_description"] == FALLBACK_SHORT_DESCRIPTION_EMPTY


def test_fallback_sets_hidden_availability():
    """BRD §11.4.3 — missing config → hidden by default."""
    gt = _game_type()
    result, warning = resolve_catalog_config(gt, None)
    assert result["availability_mode"] == "hidden"
    assert warning is True


def test_fallback_sort_order_default():
    gt = _game_type()
    result, _ = resolve_catalog_config(gt, None)
    assert result["sort_order"] == 999  # pushed to end


def test_fallback_no_duration_no_featured():
    gt = _game_type()
    result, _ = resolve_catalog_config(gt, None)
    assert result["estimated_duration_sec"] is None
    assert result["featured"] is False
    assert result["marketing_label"] is None
    assert result["expected_launch_at"] is None
