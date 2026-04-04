"""Verify catalog enums exist and have expected members."""

from app.core.enums import (
    MinigameHeroVariant,
    MinigameCardVariant,
    MinigameCatalogAvailability,
)


def test_hero_variants():
    values = {v.value for v in MinigameHeroVariant}
    assert values == {"duel", "arena", "solo", "party", "tournament"}


def test_card_variants():
    values = {v.value for v in MinigameCardVariant}
    assert values == {"standard", "featured", "compact", "coming_soon_teaser"}


def test_availability_modes():
    values = {v.value for v in MinigameCatalogAvailability}
    assert values == {"active", "coming_soon", "hidden", "maintenance"}


def test_hero_variant_specific_members():
    assert MinigameHeroVariant.DUEL.value == "duel"
    assert MinigameHeroVariant.ARENA.value == "arena"
    assert MinigameHeroVariant.SOLO.value == "solo"
    assert MinigameHeroVariant.PARTY.value == "party"
    assert MinigameHeroVariant.TOURNAMENT.value == "tournament"


def test_card_variant_specific_members():
    assert MinigameCardVariant.STANDARD.value == "standard"
    assert MinigameCardVariant.FEATURED.value == "featured"
    assert MinigameCardVariant.COMPACT.value == "compact"
    assert MinigameCardVariant.COMING_SOON_TEASER.value == "coming_soon_teaser"


def test_availability_specific_members():
    assert MinigameCatalogAvailability.ACTIVE.value == "active"
    assert MinigameCatalogAvailability.COMING_SOON.value == "coming_soon"
    assert MinigameCatalogAvailability.HIDDEN.value == "hidden"
    assert MinigameCatalogAvailability.MAINTENANCE.value == "maintenance"
