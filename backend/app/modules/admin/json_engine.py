"""
JSON config engine — export/import competition configurations.

Enables LLM-generated content and rapid season setup by allowing complete
competition configurations (items, store listings, settings) to be serialized
as JSON and re-imported into any competition.

Export format version: 1.0
"""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import (
    EffectType,
    ItemAcquisitionType,
    ItemRarity,
    ItemStatus,
    ItemUsageType,
    ListingStatus,
    SettingScope,
)
from app.core.utils import jsonb_safe, now_riyadh
from app.modules.audit.service import write_audit
from app.modules.competitions.models import Competition
from app.modules.settings.models import SettingDefinition, SettingValue
from app.modules.store.models import ItemDefinition, ItemEffect, StoreListing

CONFIG_VERSION = "1.0"


# ═══════════════════════════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════════════════════════


async def export_competition_config(
    session: AsyncSession,
    competition_id: uuid.UUID,
) -> dict:
    """
    Export a complete competition configuration as a JSON-serializable dict.

    Includes:
      - Competition metadata (name, description)
      - All ItemDefinitions scoped to the competition (or global)
      - Each item's ItemEffects
      - All active StoreListings for the competition
      - All Settings with competition-level overrides

    Returns a dict ready for ``json.dumps()``.
    """
    # ── Competition ──────────────────────────────────────────────────────
    comp = await session.get(Competition, competition_id)
    if not comp:
        raise ValueError(f"Competition {competition_id} not found")

    # ── Items + Effects ──────────────────────────────────────────────────
    items_result = await session.execute(
        select(ItemDefinition)
        .options(selectinload(ItemDefinition.effects))
        .where(
            (ItemDefinition.scope_competition_id == competition_id)
            | (ItemDefinition.scope_competition_id.is_(None))
        )
        .order_by(ItemDefinition.created_at)
    )
    items = items_result.scalars().all()

    items_data = []
    for item in items:
        effects_data = [
            {
                "effect_type": jsonb_safe(eff.effect_type),
                "parameters": jsonb_safe(eff.parameters),
                "target_scope": eff.target_scope,
                "duration_minutes": eff.duration_minutes,
                "is_stackable": eff.is_stackable,
                "trigger_on": eff.trigger_on,
                "order_index": eff.order_index,
            }
            for eff in sorted(item.effects, key=lambda e: e.order_index)
        ]

        items_data.append({
            "name": item.name,
            "description": item.description,
            "rarity": jsonb_safe(item.rarity),
            "category": item.category,
            "acquisition_type": jsonb_safe(item.acquisition_type),
            "usage_type": jsonb_safe(item.usage_type),
            "max_uses": item.max_uses,
            "is_stackable": item.is_stackable,
            "expires_after_minutes": item.expires_after_minutes,
            "visibility": item.visibility,
            "status": jsonb_safe(item.status),
            "effects": effects_data,
        })

    # ── Store Listings ───────────────────────────────────────────────────
    listings_result = await session.execute(
        select(StoreListing)
        .where(
            StoreListing.competition_id == competition_id,
            StoreListing.status == ListingStatus.ACTIVE,
        )
        .order_by(StoreListing.created_at)
    )
    listings = listings_result.scalars().all()

    # Build item ID → name lookup for listing references
    item_id_to_name: dict[uuid.UUID, str] = {item.id: item.name for item in items}

    listings_data = []
    for listing in listings:
        item_name = item_id_to_name.get(listing.item_definition_id)
        if not item_name:
            # Item might not be in our export set; fetch its name directly
            item_obj = await session.get(ItemDefinition, listing.item_definition_id)
            item_name = item_obj.name if item_obj else f"unknown:{listing.item_definition_id}"

        listings_data.append({
            "item_name": item_name,
            "price": listing.price,
            "max_per_participant": listing.max_per_participant,
            "total_stock": listing.total_stock,
            "status": jsonb_safe(listing.status),
        })

    # ── Settings ─────────────────────────────────────────────────────────
    # Collect all setting definitions, then resolve competition-level values
    defns_result = await session.execute(
        select(SettingDefinition).order_by(SettingDefinition.category, SettingDefinition.key)
    )
    definitions = defns_result.scalars().all()

    settings_data: dict[str, Any] = {}
    for defn in definitions:
        # Competition-level override
        comp_val_result = await session.execute(
            select(SettingValue).where(
                SettingValue.setting_definition_id == defn.id,
                SettingValue.scope == SettingScope.COMPETITION,
                SettingValue.scope_id == competition_id,
            )
        )
        comp_sv = comp_val_result.scalars().first()

        # Global value fallback
        global_val_result = await session.execute(
            select(SettingValue).where(
                SettingValue.setting_definition_id == defn.id,
                SettingValue.scope == SettingScope.GLOBAL,
                SettingValue.scope_id.is_(None),
            )
        )
        global_sv = global_val_result.scalars().first()

        # Resolve: competition → global → definition default
        if comp_sv:
            raw = comp_sv.value
        elif global_sv:
            raw = global_sv.value
        else:
            raw = defn.default_value

        settings_data[defn.key] = raw.get("v") if isinstance(raw, dict) else raw

    # ── Assemble ─────────────────────────────────────────────────────────
    return {
        "version": CONFIG_VERSION,
        "exported_at": now_riyadh().isoformat(),
        "competition": {
            "name": comp.name,
            "description": comp.description,
        },
        "items": items_data,
        "store_listings": listings_data,
        "settings": settings_data,
    }


# ═══════════════════════════════════════════════════════════════════════════
# IMPORT
# ═══════════════════════════════════════════════════════════════════════════

# Valid enum values for input validation
_VALID_RARITIES = {r.value for r in ItemRarity}
_VALID_USAGE_TYPES = {u.value for u in ItemUsageType}
_VALID_ACQUISITION_TYPES = {a.value for a in ItemAcquisitionType}
_VALID_EFFECT_TYPES = {e.value for e in EffectType}
_VALID_ITEM_STATUSES = {s.value for s in ItemStatus}
_VALID_LISTING_STATUSES = {s.value for s in ListingStatus}


def _validate_config(config: dict) -> list[str]:
    """Validate the JSON config structure. Returns a list of error messages (empty = valid)."""
    errors: list[str] = []

    if not isinstance(config, dict):
        return ["Config must be a JSON object"]

    if config.get("version") != CONFIG_VERSION:
        errors.append(f"Unsupported config version: {config.get('version')} (expected {CONFIG_VERSION})")

    if "items" in config and not isinstance(config["items"], list):
        errors.append("'items' must be a list")

    if "store_listings" in config and not isinstance(config["store_listings"], list):
        errors.append("'store_listings' must be a list")

    if "settings" in config and not isinstance(config["settings"], dict):
        errors.append("'settings' must be a dict")

    # Validate individual items
    for i, item in enumerate(config.get("items", [])):
        prefix = f"items[{i}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix}: must be an object")
            continue
        if not item.get("name"):
            errors.append(f"{prefix}: 'name' is required")
        if item.get("rarity") and item["rarity"] not in _VALID_RARITIES:
            errors.append(f"{prefix}: invalid rarity '{item['rarity']}'")
        if item.get("usage_type") and item["usage_type"] not in _VALID_USAGE_TYPES:
            errors.append(f"{prefix}: invalid usage_type '{item['usage_type']}'")
        if item.get("acquisition_type") and item["acquisition_type"] not in _VALID_ACQUISITION_TYPES:
            errors.append(f"{prefix}: invalid acquisition_type '{item['acquisition_type']}'")
        if item.get("status") and item["status"] not in _VALID_ITEM_STATUSES:
            errors.append(f"{prefix}: invalid status '{item['status']}'")

        # Validate effects within item
        for j, eff in enumerate(item.get("effects", [])):
            eff_prefix = f"{prefix}.effects[{j}]"
            if not isinstance(eff, dict):
                errors.append(f"{eff_prefix}: must be an object")
                continue
            if not eff.get("effect_type"):
                errors.append(f"{eff_prefix}: 'effect_type' is required")
            elif eff["effect_type"] not in _VALID_EFFECT_TYPES:
                errors.append(f"{eff_prefix}: invalid effect_type '{eff['effect_type']}'")

    # Validate store listings
    for i, listing in enumerate(config.get("store_listings", [])):
        prefix = f"store_listings[{i}]"
        if not isinstance(listing, dict):
            errors.append(f"{prefix}: must be an object")
            continue
        if not listing.get("item_name"):
            errors.append(f"{prefix}: 'item_name' is required")
        if not listing.get("price") or not isinstance(listing["price"], (int, float)) or listing["price"] <= 0:
            errors.append(f"{prefix}: 'price' must be a positive number")

    return errors


async def import_competition_config(
    session: AsyncSession,
    competition_id: uuid.UUID,
    config: dict,
    admin_id: uuid.UUID,
) -> dict:
    """
    Import a competition configuration from a JSON dict.

    Creates:
      - ItemDefinitions with their ItemEffects (scoped to the competition)
      - StoreListings linked to the created items
      - Settings overrides at competition scope

    Returns a summary: ``{"items_created": N, "listings_created": N, "settings_updated": N, "errors": [...]}``
    """
    # ── Validate ─────────────────────────────────────────────────────────
    errors = _validate_config(config)
    if errors:
        return {
            "items_created": 0,
            "listings_created": 0,
            "settings_updated": 0,
            "errors": errors,
        }

    # Verify competition exists
    comp = await session.get(Competition, competition_id)
    if not comp:
        return {
            "items_created": 0,
            "listings_created": 0,
            "settings_updated": 0,
            "errors": [f"Competition {competition_id} not found"],
        }

    items_created = 0
    listings_created = 0
    settings_updated = 0
    import_errors: list[str] = []

    # Track created items by name for listing linkage
    created_items: dict[str, ItemDefinition] = {}

    # ── Items + Effects ──────────────────────────────────────────────────
    for i, item_data in enumerate(config.get("items", [])):
        try:
            item = ItemDefinition(
                name=item_data["name"],
                description=item_data.get("description"),
                rarity=item_data.get("rarity", ItemRarity.COMMON),
                category=item_data.get("category"),
                acquisition_type=item_data.get("acquisition_type", ItemAcquisitionType.PURCHASE),
                usage_type=item_data.get("usage_type", ItemUsageType.CONSUMABLE),
                max_uses=item_data.get("max_uses"),
                is_stackable=item_data.get("is_stackable", False),
                expires_after_minutes=item_data.get("expires_after_minutes"),
                visibility=item_data.get("visibility", "visible"),
                status=item_data.get("status", ItemStatus.ACTIVE),
                scope_competition_id=competition_id,
            )
            session.add(item)
            await session.flush()

            # Create effects for this item
            for j, eff_data in enumerate(item_data.get("effects", [])):
                try:
                    effect = ItemEffect(
                        item_definition_id=item.id,
                        effect_type=eff_data["effect_type"],
                        parameters=eff_data.get("parameters", {}),
                        target_scope=eff_data.get("target_scope", "self"),
                        duration_minutes=eff_data.get("duration_minutes"),
                        is_stackable=eff_data.get("is_stackable", False),
                        trigger_on=eff_data.get("trigger_on", "activation"),
                        order_index=eff_data.get("order_index", j),
                    )
                    session.add(effect)
                except Exception as e:
                    import_errors.append(f"items[{i}].effects[{j}]: {str(e)}")

            created_items[item_data["name"]] = item
            items_created += 1

        except Exception as e:
            import_errors.append(f"items[{i}] ({item_data.get('name', '?')}): {str(e)}")

    # Flush all effects
    await session.flush()

    # ── Store Listings ───────────────────────────────────────────────────
    for i, listing_data in enumerate(config.get("store_listings", [])):
        try:
            item_name = listing_data["item_name"]
            item = created_items.get(item_name)

            if not item:
                # Try to find an existing item by name in the competition scope
                existing_result = await session.execute(
                    select(ItemDefinition).where(
                        ItemDefinition.name == item_name,
                        (
                            (ItemDefinition.scope_competition_id == competition_id)
                            | (ItemDefinition.scope_competition_id.is_(None))
                        ),
                    ).limit(1)
                )
                item = existing_result.scalars().first()

            if not item:
                import_errors.append(
                    f"store_listings[{i}]: item '{item_name}' not found "
                    f"(not created in this import and not in competition)"
                )
                continue

            listing = StoreListing(
                item_definition_id=item.id,
                competition_id=competition_id,
                price=int(listing_data["price"]),
                max_per_participant=listing_data.get("max_per_participant"),
                total_stock=listing_data.get("total_stock"),
                status=listing_data.get("status", ListingStatus.ACTIVE),
            )
            session.add(listing)
            listings_created += 1

        except Exception as e:
            import_errors.append(f"store_listings[{i}]: {str(e)}")

    # ── Settings ─────────────────────────────────────────────────────────
    for key, value in config.get("settings", {}).items():
        try:
            # Find the setting definition
            defn_result = await session.execute(
                select(SettingDefinition).where(SettingDefinition.key == key)
            )
            defn = defn_result.scalars().first()
            if not defn:
                import_errors.append(f"settings[{key}]: unknown setting key")
                continue

            # Upsert competition-scoped value
            sv_result = await session.execute(
                select(SettingValue).where(
                    SettingValue.setting_definition_id == defn.id,
                    SettingValue.scope == SettingScope.COMPETITION,
                    SettingValue.scope_id == competition_id,
                )
            )
            sv = sv_result.scalars().first()

            wrapped_value = {"v": value}

            if sv:
                sv.value = wrapped_value
                sv.updated_by = admin_id
            else:
                sv = SettingValue(
                    setting_definition_id=defn.id,
                    scope=SettingScope.COMPETITION,
                    scope_id=competition_id,
                    value=wrapped_value,
                    updated_by=admin_id,
                )
                session.add(sv)

            settings_updated += 1

        except Exception as e:
            import_errors.append(f"settings[{key}]: {str(e)}")

    # ── Audit Trail ──────────────────────────────────────────────────────
    await write_audit(
        session,
        actor_id=admin_id,
        subject_type="competition",
        subject_id=competition_id,
        event_type="config_imported",
        summary=(
            f"استيراد إعدادات المنافسة: "
            f"{items_created} عناصر، "
            f"{listings_created} عروض متجر، "
            f"{settings_updated} إعدادات"
        ),
        after_state=jsonb_safe({
            "items_created": items_created,
            "listings_created": listings_created,
            "settings_updated": settings_updated,
            "errors": import_errors,
        }),
    )

    await session.flush()

    return {
        "items_created": items_created,
        "listings_created": listings_created,
        "settings_updated": settings_updated,
        "errors": import_errors,
    }
