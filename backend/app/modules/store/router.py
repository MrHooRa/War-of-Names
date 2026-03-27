"""Store endpoints — list items, purchase, view inventory, use items."""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select

from app.core.auth import get_current_account
from app.core.database import async_session
from app.core.utils import jsonb_safe
from app.core.enums import (
    AuditActorType,
    CycleStatus,
    LedgerDirection,
    LedgerEntryType,
    ListingStatus,
    MembershipStatus,
    NotificationType,
    OwnedItemStatus,
    SeasonStatus,
)
from pydantic import BaseModel
from app.modules.auth.models import Account
from app.modules.competitions.models import AliasRecord, Competition, Cycle, Membership, Season
from app.modules.scoring.models import LedgerEntry
from app.modules.notifications.service import create_notification
from app.modules.audit.service import write_audit
from app.modules.store.models import ItemActivation, ItemDefinition, ItemEffect, OwnedItem, StoreListing
from app.modules.store.service import execute_item_effects, build_pending_effect_entry, PENDING_TRIGGERS
from app.modules.store.effect_config import generate_effect_summary
from app.modules.settings.service import get_setting

router = APIRouter(tags=["store"])
CurrentAccount = Annotated[Account, Depends(get_current_account)]


# ── Shared membership resolution ─────────────────────────────────────────

async def _get_membership(session, account_id, competition_id):
    """Resolve membership for a known competition_id (used by path-param endpoints)."""
    result = await session.execute(
        select(Membership).where(
            Membership.account_id == account_id,
            Membership.competition_id == competition_id,
            Membership.status == MembershipStatus.ACTIVE,
        )
    )
    return result.scalars().first()


async def _resolve_membership(session, account_id, competition_id: str | None = None):
    """
    Resolve the player's active membership, scoped to a specific competition
    when provided.  Joins Competition to ensure it is active.

    Returns (membership, competition) or (None, None).
    """
    query = (
        select(Membership, Competition)
        .join(Competition, Membership.competition_id == Competition.id)
        .where(
            Membership.account_id == account_id,
            Membership.status == MembershipStatus.ACTIVE,
            Competition.status == "active",
        )
    )
    if competition_id:
        try:
            cid = uuid.UUID(competition_id)
            query = query.where(Competition.id == cid)
        except ValueError:
            pass
    query = query.limit(1)
    result = await session.execute(query)
    row = result.first()
    if not row:
        return None, None
    return row[0], row[1]


async def _resolve_season_cycle(session, competition_id):
    """Resolve the active season and cycle for a competition."""
    season = (await session.execute(
        select(Season).where(
            Season.competition_id == competition_id,
            Season.status == SeasonStatus.ACTIVE,
        ).limit(1)
    )).scalars().first()
    cycle = None
    if season:
        cycle = (await session.execute(
            select(Cycle).where(
                Cycle.season_id == season.id,
                Cycle.status == CycleStatus.ACTIVE,
            ).limit(1)
        )).scalars().first()
    return season, cycle


# ── Store catalog (already competition-scoped via path param) ─────────────

@router.get("/api/competitions/{competition_id}/store")
async def list_store(competition_id: uuid.UUID, account: CurrentAccount):
    """List all active store listings with their item details, enforcing time windows."""
    now = datetime.utcnow()
    async with async_session() as session:
        result = await session.execute(
            select(StoreListing, ItemDefinition)
            .join(ItemDefinition, StoreListing.item_definition_id == ItemDefinition.id)
            .where(
                StoreListing.competition_id == competition_id,
                StoreListing.status == ListingStatus.ACTIVE,
            )
            .order_by(StoreListing.price.asc())
        )
        all_rows = result.all()

    # Filter by time window: exclude listings not yet available or already expired
    rows = []
    for listing, item in all_rows:
        if listing.available_from and now < listing.available_from:
            continue
        if listing.available_until and now > listing.available_until:
            continue
        rows.append((listing, item))

        # Collect item IDs to fetch effects
        item_ids = [item.id for _, item in rows]
        effects_by_item = {}
        if item_ids:
            effects_result = await session.execute(
                select(ItemEffect)
                .where(ItemEffect.item_definition_id.in_(item_ids))
                .order_by(ItemEffect.order_index)
            )
            for eff in effects_result.scalars().all():
                effects_by_item.setdefault(eff.item_definition_id, []).append(eff)

    listings = []
    for listing, item in rows:
        stock_remaining = None
        if listing.total_stock is not None:
            stock_remaining = listing.total_stock - listing.sold_count

        # Generate effect summaries for this item
        item_effects = effects_by_item.get(item.id, [])
        effect_summaries = [
            generate_effect_summary(
                eff.effect_type, eff.parameters or {}, eff.duration_minutes,
                eff.target_scope or "self", eff.trigger_on or "activation",
            )
            for eff in item_effects
        ]

        listings.append({
            "listing_id": str(listing.id),
            "item_id": str(item.id),
            "name": item.name,
            "description": item.description,
            "rarity": item.rarity,
            "category": item.category,
            "usage_type": item.usage_type,
            "price": listing.price,
            "max_per_participant": listing.max_per_participant,
            "stock_remaining": stock_remaining,
            "icon": item.category or "lucide:package",
            "effects": effect_summaries,
        })

    return {"success": True, "data": listings}


# ── Purchase (already competition-scoped via path param) ──────────────────

@router.post("/api/competitions/{competition_id}/store/{listing_id}/buy")
async def buy_item(
    competition_id: uuid.UUID,
    listing_id: uuid.UUID,
    account: CurrentAccount,
):
    """Purchase an item from the store."""
    async with async_session() as session:
        # Get membership with row lock to prevent concurrent balance races
        membership_result = await session.execute(
            select(Membership).where(
                Membership.account_id == account.id,
                Membership.competition_id == competition_id,
                Membership.status == MembershipStatus.ACTIVE,
            ).with_for_update()
        )
        membership = membership_result.scalars().first()
        if not membership:
            raise HTTPException(status_code=403, detail="أنت لست عضواً في هذه المنافسة")

        if membership.is_bankrupt:
            raise HTTPException(status_code=400, detail="لا يمكن الشراء وأنت في حالة إفلاس")

        # Check inventory capacity
        max_capacity = await get_setting(
            session, "store_max_inventory",
            competition_id=competition_id,
        ) or 10
        current_count_result = await session.execute(
            select(func.count()).select_from(OwnedItem).where(
                OwnedItem.membership_id == membership.id,
                OwnedItem.status.in_([OwnedItemStatus.AVAILABLE, OwnedItemStatus.ACTIVATED, OwnedItemStatus.PENDING]),
            )
        )
        current_count = current_count_result.scalar() or 0
        if current_count >= max_capacity:
            raise HTTPException(
                status_code=400,
                detail=f"المخزون ممتلئ ({current_count}/{max_capacity}). استخدم أو تخلص من عنصر أولاً",
            )

        # Get listing with row lock to prevent stock oversell
        listing_result = await session.execute(
            select(StoreListing).where(StoreListing.id == listing_id).with_for_update()
        )
        listing = listing_result.scalars().first()
        if not listing or str(listing.competition_id) != str(competition_id):
            raise HTTPException(status_code=404, detail="العنصر غير متوفر")

        if listing.status != ListingStatus.ACTIVE:
            raise HTTPException(status_code=400, detail="هذا العنصر لم يعد متاحاً للشراء")

        # Enforce listing time window
        now = datetime.utcnow()
        if listing.available_from and now < listing.available_from:
            raise HTTPException(status_code=400, detail="هذا العنصر لم يتوفر بعد للشراء")
        if listing.available_until and now > listing.available_until:
            raise HTTPException(status_code=400, detail="انتهت فترة توفر هذا العنصر")

        # Check stock
        if listing.total_stock is not None and listing.sold_count >= listing.total_stock:
            raise HTTPException(status_code=400, detail="نفد المخزون من هذا العنصر")

        # Check max per participant
        if listing.max_per_participant is not None:
            owned_count_result = await session.execute(
                select(func.count()).select_from(OwnedItem).where(
                    OwnedItem.membership_id == membership.id,
                    OwnedItem.item_definition_id == listing.item_definition_id,
                    OwnedItem.source_type == "purchase",
                )
            )
            owned_count = owned_count_result.scalar() or 0
            if owned_count >= listing.max_per_participant:
                raise HTTPException(
                    status_code=400,
                    detail=f"لقد بلغت الحد الأقصى للشراء ({listing.max_per_participant})",
                )

        # Check balance (safe: membership row is locked)
        if membership.current_balance < listing.price:
            raise HTTPException(
                status_code=400,
                detail=f"رصيدك ({membership.current_balance}) لا يكفي. السعر: {listing.price}",
            )

        # Resolve season/cycle for ledger traceability
        season, cycle = await _resolve_season_cycle(session, competition_id)

        # Debit balance via ledger
        balance_before = membership.current_balance
        balance_after = balance_before - listing.price

        ledger = LedgerEntry(
            membership_id=membership.id,
            competition_id=competition_id,
            season_id=season.id if season else None,
            cycle_id=cycle.id if cycle else None,
            entry_type=LedgerEntryType.ITEM_PURCHASE,
            amount=listing.price,
            direction=LedgerDirection.DEBIT,
            balance_before=balance_before,
            balance_after=balance_after,
            source_type="store_listing",
            source_id=listing.id,
            reason=f"شراء عنصر من المتجر",
        )
        session.add(ledger)
        membership.current_balance = balance_after

        # Create owned item
        item_def = await session.get(ItemDefinition, listing.item_definition_id)
        owned = OwnedItem(
            membership_id=membership.id,
            item_definition_id=listing.item_definition_id,
            source_type="purchase",
            source_id=listing.id,
            quantity=1,
            uses_remaining=item_def.max_uses if item_def else None,
            status=OwnedItemStatus.AVAILABLE,
        )
        session.add(owned)

        # Increment sold count
        listing.sold_count += 1

        # Notification
        await create_notification(
            session,
            recipient_id=account.id,
            notification_type=NotificationType.ITEM_PURCHASED,
            title="تم الشراء بنجاح",
            message=f"اشتريت {item_def.name} مقابل {listing.price} نقطة",
            membership_id=membership.id,
            reference_type="owned_item",
            deep_link="/store",
        )

        await session.commit()
        await session.refresh(owned)

    return {
        "success": True,
        "data": {
            "owned_item_id": str(owned.id),
            "item_name": item_def.name if item_def else "عنصر",
            "balance_after": balance_after,
        },
        "message": f"تم شراء {item_def.name if item_def else 'العنصر'} بنجاح!",
    }


# ── Inventory (now competition-scoped) ────────────────────────────────────

@router.get("/api/me/inventory")
async def get_inventory(account: CurrentAccount, competition_id: str | None = None):
    """Get current user's inventory for their selected competition."""
    async with async_session() as session:
        membership, competition = await _resolve_membership(
            session, account.id, competition_id,
        )
        if not membership:
            return {"success": True, "data": {"items": [], "max_capacity": 10}}

        # Resolve inventory capacity setting
        max_capacity = await get_setting(
            session, "store_max_inventory",
            competition_id=membership.competition_id,
        ) or 10

        # Get owned items with item details
        result = await session.execute(
            select(OwnedItem, ItemDefinition)
            .join(ItemDefinition, OwnedItem.item_definition_id == ItemDefinition.id)
            .where(
                OwnedItem.membership_id == membership.id,
                OwnedItem.status.in_([
                    OwnedItemStatus.AVAILABLE,
                    OwnedItemStatus.ACTIVATED,
                    OwnedItemStatus.PENDING,
                ]),
            )
            .order_by(OwnedItem.acquired_at.desc())
        )
        all_rows = result.all()

        # Enforce expiry: auto-transition expired items to EXPIRED status
        now = datetime.utcnow()
        rows = []
        for owned, item_def in all_rows:
            if owned.expires_at and now > owned.expires_at:
                owned.status = OwnedItemStatus.EXPIRED
                # Don't include in active inventory
            else:
                rows.append((owned, item_def))

        # Commit any expiry transitions
        await session.commit()

        # Fetch effects for all items in inventory
        item_def_ids = [item_def.id for _, item_def in rows]
        effects_by_item = {}
        if item_def_ids:
            effects_result = await session.execute(
                select(ItemEffect)
                .where(ItemEffect.item_definition_id.in_(item_def_ids))
                .order_by(ItemEffect.order_index)
            )
            for eff in effects_result.scalars().all():
                effects_by_item.setdefault(eff.item_definition_id, []).append(eff)

    items = []
    for owned, item_def in rows:
        item_effects = effects_by_item.get(item_def.id, [])
        effect_summaries = [
            generate_effect_summary(
                eff.effect_type, eff.parameters or {}, eff.duration_minutes,
                eff.target_scope or "self", eff.trigger_on or "activation",
            )
            for eff in item_effects
        ]

        # Derive usability with explicit denial reason
        can_use = False
        denial_reason = None
        if owned.status != OwnedItemStatus.AVAILABLE:
            denial_reason = "العنصر ليس في حالة متاحة"
        elif membership.is_bankrupt:
            denial_reason = "لا يمكن استخدام العناصر أثناء الإفلاس"
        else:
            can_use = True

        items.append({
            "owned_item_id": str(owned.id),
            "item_id": str(item_def.id),
            "name": item_def.name,
            "description": item_def.description,
            "rarity": item_def.rarity,
            "category": item_def.category,
            "quantity": owned.quantity,
            "status": owned.status,
            "uses_remaining": owned.uses_remaining,
            "can_use": can_use,
            "denial_reason": denial_reason,
            "effects": effect_summaries,
            "acquired_at": owned.acquired_at.isoformat() if owned.acquired_at else None,
            "expires_at": owned.expires_at.isoformat() if owned.expires_at else None,
        })

    return {"success": True, "data": {"items": items, "max_capacity": max_capacity}}


# ── Item use (now competition-scoped + audited) ──────────────────────────

@router.post("/api/me/inventory/{owned_item_id}/use")
async def use_item(
    owned_item_id: uuid.UUID,
    account: CurrentAccount,
    competition_id: str | None = None,
):
    """
    Use/activate an item from inventory.

    Effect trigger modes:
      - activation  → instant effects run NOW, timed effects become ACTIVATED
      - next_success / next_failure / next_defense → stored as PENDING,
        applied later by the attack engine when the trigger fires
    """
    from datetime import datetime, timedelta

    async with async_session() as session:
        # Resolve membership scoped to the selected competition
        membership, competition = await _resolve_membership(
            session, account.id, competition_id,
        )
        if not membership:
            raise HTTPException(status_code=403, detail="أنت لست عضواً في أي منافسة نشطة")

        # Get owned item and verify it belongs to this membership
        owned = await session.get(OwnedItem, owned_item_id)
        if not owned or str(owned.membership_id) != str(membership.id):
            raise HTTPException(status_code=404, detail="العنصر غير موجود في مخزونك")

        if owned.status != OwnedItemStatus.AVAILABLE:
            raise HTTPException(status_code=400, detail="هذا العنصر غير متاح للاستخدام")

        # Enforce expiry before allowing use
        if owned.expires_at and datetime.utcnow() > owned.expires_at:
            owned.status = OwnedItemStatus.EXPIRED
            await session.commit()
            raise HTTPException(status_code=400, detail="انتهت صلاحية هذا العنصر")

        if membership.is_bankrupt:
            raise HTTPException(status_code=400, detail="لا يمكن استخدام العناصر أثناء الإفلاس")

        # Get item definition and its effects
        item_def = await session.get(ItemDefinition, owned.item_definition_id)
        if not item_def:
            raise HTTPException(status_code=404, detail="تعريف العنصر غير موجود")

        effects_result = await session.execute(
            select(ItemEffect)
            .where(ItemEffect.item_definition_id == item_def.id)
            .order_by(ItemEffect.order_index)
        )
        all_effects = effects_result.scalars().all()

        # ── Capture before-state for audit ────────────────────────
        before_state = {
            "owned_item_id": str(owned.id),
            "item_name": item_def.name,
            "status": owned.status,
            "uses_remaining": owned.uses_remaining,
            "membership_balance": membership.current_balance,
            "membership_protection": membership.protection,
            "membership_is_bankrupt": membership.is_bankrupt,
        }

        # Resolve season/cycle for ledger context
        season, cycle = await _resolve_season_cycle(session, membership.competition_id)
        effect_context = {
            "season_id": season.id if season else None,
            "cycle_id": cycle.id if cycle else None,
        }

        # ── Separate instant vs pending effects ──────────────────────
        instant_effects = [e for e in all_effects if (e.trigger_on or "activation") == "activation"]
        pending_effects = [e for e in all_effects if (e.trigger_on or "activation") in PENDING_TRIGGERS]

        # Execute instant effects via the effect engine
        instant_results = []
        if instant_effects:
            instant_results = await execute_item_effects(
                session, owned, membership, instant_effects,
                context=effect_context,
            )

        # Build metadata for pending effects (NOT executed — stored for later)
        pending_summaries = [build_pending_effect_entry(e) for e in pending_effects]

        # Build effect summary for the activation record
        effect_summary = {
            "item_name": item_def.name,
            "effects_applied": instant_results,
        }
        if pending_summaries:
            effect_summary["pending_effects"] = pending_summaries

        # ── Determine item status ────────────────────────────────────
        now = datetime.utcnow()
        owned.activated_at = now

        has_pending = len(pending_effects) > 0

        if has_pending:
            # Pending takes priority: item waits for the trigger action
            owned.status = OwnedItemStatus.PENDING
            # Optional expiry on pending items (if admin configures one)
            max_pending_duration = max(
                (e.duration_minutes for e in pending_effects if e.duration_minutes),
                default=None,
            )
            if max_pending_duration:
                owned.expires_at = now + timedelta(minutes=max_pending_duration)
        elif item_def.usage_type in ("time_limited",):
            # Timed active: ACTIVATED with expiry
            owned.status = OwnedItemStatus.ACTIVATED
            max_effect_duration = max(
                (e.duration_minutes for e in instant_effects if e.duration_minutes),
                default=None,
            )
            effective_expiry_minutes = max_effect_duration or item_def.expires_after_minutes
            if effective_expiry_minutes:
                owned.expires_at = now + timedelta(minutes=effective_expiry_minutes)
        elif item_def.usage_type in ("consumable",):
            # Consumable: decrement uses or consume fully
            if owned.uses_remaining is not None and owned.uses_remaining > 1:
                owned.uses_remaining -= 1
            else:
                owned.status = OwnedItemStatus.CONSUMED
                owned.consumed_at = now
        else:
            # Non-consumable / persistent: just activate
            owned.status = OwnedItemStatus.ACTIVATED

        # Record activation
        activation = ItemActivation(
            owned_item_id=owned.id,
            membership_id=membership.id,
            result_state="success",
            effect_summary=jsonb_safe(effect_summary),
        )
        session.add(activation)

        # Build player-facing message
        if has_pending:
            trigger_labels = {
                "next_success": "هجومك الناجح التالي",
                "next_failure": "هجومك الفاشل التالي",
                "next_defense": "تلقيك للهجوم التالي",
            }
            trigger_names = list({e.trigger_on for e in pending_effects})
            trigger_text = trigger_labels.get(trigger_names[0], "الإجراء التالي")
            notif_message = f"تم تفعيل {item_def.name} — ينتظر {trigger_text}"
        else:
            notif_message = f"تم استخدام {item_def.name} بنجاح"

        # Send notification
        await create_notification(
            session,
            recipient_id=account.id,
            notification_type=NotificationType.ITEM_RECEIVED,
            title="تم تفعيل العنصر",
            message=notif_message,
            membership_id=membership.id,
            reference_type="item_activation",
            deep_link="/dashboard",
        )

        # ── Capture after-state and write audit ───────────────────
        after_state = {
            "owned_item_id": str(owned.id),
            "item_name": item_def.name,
            "status": owned.status,
            "uses_remaining": owned.uses_remaining,
            "membership_balance": membership.current_balance,
            "membership_protection": membership.protection,
            "membership_is_bankrupt": membership.is_bankrupt,
            "effects_applied": [r.get("type", "unknown") for r in instant_results],
            "pending_effects": [p.get("type", "unknown") for p in pending_summaries],
        }

        await session.flush()  # get activation.id

        await write_audit(
            session,
            actor_id=account.id,
            actor_type=AuditActorType.PARTICIPANT,
            subject_type="owned_item",
            subject_id=owned.id,
            event_type="item_used",
            summary=f"استخدام عنصر: {item_def.name}",
            before_state=before_state,
            after_state=after_state,
            related_type="competition",
            related_id=membership.competition_id,
        )

        await session.commit()

    return {
        "success": True,
        "data": {
            "owned_item_id": str(owned.id),
            "item_name": item_def.name,
            "new_status": owned.status,
            "effects": effect_summary,
        },
        "message": notif_message,
    }


# ── Alias change (powered by ALLOW_ALIAS_CHANGE effect) ─────────────────

@router.get("/api/me/can-change-alias")
async def check_alias_change_permission(
    account: CurrentAccount,
    competition_id: str | None = None,
):
    """Check if the player has an unredeemed alias change permission."""
    async with async_session() as session:
        membership, competition = await _resolve_membership(
            session, account.id, competition_id,
        )
        if not membership:
            return {"success": True, "data": {"can_change": False}}

        # Find an unredeemed allow_alias_change activation
        result = await session.execute(
            select(ItemActivation)
            .where(
                ItemActivation.membership_id == membership.id,
                ItemActivation.result_state == "success",
            )
            .order_by(ItemActivation.activated_at.desc())
        )
        for activation in result.scalars().all():
            summary = activation.effect_summary or {}
            for eff in summary.get("effects_applied", []):
                if eff.get("type") == "allow_alias_change" and not eff.get("redeemed"):
                    return {"success": True, "data": {"can_change": True, "activation_id": str(activation.id)}}

    return {"success": True, "data": {"can_change": False}}


class ChangeAliasRequest(BaseModel):
    new_alias: str
    activation_id: str


@router.post("/api/me/change-alias")
async def change_alias(
    body: ChangeAliasRequest,
    account: CurrentAccount,
    competition_id: str | None = None,
):
    """Change the player's alias using an ALLOW_ALIAS_CHANGE activation."""
    from datetime import datetime

    if not body.new_alias or len(body.new_alias.strip()) < 2:
        raise HTTPException(status_code=400, detail="اللقب يجب أن يكون حرفين على الأقل")

    async with async_session() as session:
        membership, competition = await _resolve_membership(
            session, account.id, competition_id,
        )
        if not membership:
            raise HTTPException(status_code=403, detail="أنت لست عضواً في أي منافسة نشطة")

        # Verify activation exists and has unredeemed permission
        activation = await session.get(ItemActivation, uuid.UUID(body.activation_id))
        if not activation or str(activation.membership_id) != str(membership.id):
            raise HTTPException(status_code=400, detail="صلاحية تغيير اللقب غير موجودة")

        summary = activation.effect_summary or {}
        alias_effect = None
        for eff in summary.get("effects_applied", []):
            if eff.get("type") == "allow_alias_change" and not eff.get("redeemed"):
                alias_effect = eff
                break

        if not alias_effect:
            raise HTTPException(status_code=400, detail="صلاحية تغيير اللقب مستخدمة أو غير موجودة")

        # Check alias uniqueness
        conflict = await session.execute(
            select(Membership).where(
                Membership.competition_id == membership.competition_id,
                Membership.current_alias == body.new_alias.strip(),
                Membership.id != membership.id,
            )
        )
        if conflict.scalars().first():
            raise HTTPException(status_code=400, detail="هذا اللقب مستخدم بالفعل في المنافسة")

        old_alias = membership.current_alias
        new_alias = body.new_alias.strip()

        # Update membership alias
        membership.current_alias = new_alias

        # Create alias record
        alias_record = AliasRecord(
            membership_id=membership.id,
            alias_value=new_alias,
            is_active=True,
        )
        session.add(alias_record)

        # Mark the permission as redeemed in the activation's effect_summary
        alias_effect["redeemed"] = True
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(activation, "effect_summary")

        # Audit trail
        await write_audit(
            session,
            actor_id=account.id,
            actor_type=AuditActorType.PARTICIPANT,
            subject_type="membership",
            subject_id=membership.id,
            event_type="alias_changed",
            summary=f"تغيير اللقب من «{old_alias}» إلى «{new_alias}»",
            before_state={"alias": old_alias},
            after_state={"alias": new_alias},
            related_type="competition",
            related_id=membership.competition_id,
        )

        await session.commit()

    return {
        "success": True,
        "data": {"old_alias": old_alias, "new_alias": new_alias},
        "message": f"تم تغيير لقبك من «{old_alias}» إلى «{new_alias}»",
    }
