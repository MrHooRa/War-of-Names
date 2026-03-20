"""Store endpoints — list items, purchase, view inventory."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select

from app.core.auth import get_current_account
from app.core.database import async_session
from app.core.utils import jsonb_safe
from app.core.enums import (
    LedgerDirection,
    LedgerEntryType,
    ListingStatus,
    MembershipStatus,
    NotificationType,
    OwnedItemStatus,
)
from pydantic import BaseModel
from app.modules.auth.models import Account
from app.modules.competitions.models import AliasRecord, Membership
from app.modules.scoring.models import LedgerEntry
from app.modules.notifications.service import create_notification
from app.modules.store.models import ItemActivation, ItemDefinition, ItemEffect, OwnedItem, StoreListing
from app.modules.store.service import execute_item_effects, build_pending_effect_entry, PENDING_TRIGGERS
from app.modules.store.effect_config import generate_effect_summary
from app.modules.settings.service import get_setting

router = APIRouter(tags=["store"])
CurrentAccount = Annotated[Account, Depends(get_current_account)]


async def _get_membership(session, account_id, competition_id):
    result = await session.execute(
        select(Membership).where(
            Membership.account_id == account_id,
            Membership.competition_id == competition_id,
            Membership.status == MembershipStatus.ACTIVE,
        )
    )
    return result.scalars().first()


@router.get("/api/competitions/{competition_id}/store")
async def list_store(competition_id: uuid.UUID, account: CurrentAccount):
    """List all active store listings with their item details."""
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
        rows = result.all()

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


@router.post("/api/competitions/{competition_id}/store/{listing_id}/buy")
async def buy_item(
    competition_id: uuid.UUID,
    listing_id: uuid.UUID,
    account: CurrentAccount,
):
    """Purchase an item from the store."""
    async with async_session() as session:
        # Get membership
        membership = await _get_membership(session, account.id, competition_id)
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

        # Get listing
        listing = await session.get(StoreListing, listing_id)
        if not listing or str(listing.competition_id) != str(competition_id):
            raise HTTPException(status_code=404, detail="العنصر غير متوفر")

        if listing.status != ListingStatus.ACTIVE:
            raise HTTPException(status_code=400, detail="هذا العنصر لم يعد متاحاً للشراء")

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

        # Check balance
        if membership.current_balance < listing.price:
            raise HTTPException(
                status_code=400,
                detail=f"رصيدك ({membership.current_balance}) لا يكفي. السعر: {listing.price}",
            )

        # Debit balance via ledger
        balance_before = membership.current_balance
        balance_after = balance_before - listing.price

        ledger = LedgerEntry(
            membership_id=membership.id,
            competition_id=competition_id,
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


@router.get("/api/me/inventory")
async def get_inventory(account: CurrentAccount):
    """Get current user's inventory for their active competition."""
    async with async_session() as session:
        # Find user's active membership
        mem_result = await session.execute(
            select(Membership).where(
                Membership.account_id == account.id,
                Membership.status == MembershipStatus.ACTIVE,
            ).limit(1)
        )
        membership = mem_result.scalars().first()
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
        rows = result.all()

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
            "can_use": owned.status == OwnedItemStatus.AVAILABLE,
            "effects": effect_summaries,
            "acquired_at": owned.acquired_at.isoformat() if owned.acquired_at else None,
            "expires_at": owned.expires_at.isoformat() if owned.expires_at else None,
        })

    return {"success": True, "data": {"items": items, "max_capacity": max_capacity}}


@router.post("/api/me/inventory/{owned_item_id}/use")
async def use_item(owned_item_id: uuid.UUID, account: CurrentAccount):
    """
    Use/activate an item from inventory.

    Effect trigger modes:
      - activation  → instant effects run NOW, timed effects become ACTIVATED
      - next_success / next_failure / next_defense → stored as PENDING,
        applied later by the attack engine when the trigger fires
    """
    from datetime import datetime, timedelta

    async with async_session() as session:
        # Get membership
        mem_result = await session.execute(
            select(Membership).where(
                Membership.account_id == account.id,
                Membership.status == MembershipStatus.ACTIVE,
            ).limit(1)
        )
        membership = mem_result.scalars().first()
        if not membership:
            raise HTTPException(status_code=403, detail="أنت لست عضواً في أي منافسة")

        # Get owned item
        owned = await session.get(OwnedItem, owned_item_id)
        if not owned or str(owned.membership_id) != str(membership.id):
            raise HTTPException(status_code=404, detail="العنصر غير موجود في مخزونك")

        if owned.status != OwnedItemStatus.AVAILABLE:
            raise HTTPException(status_code=400, detail="هذا العنصر غير متاح للاستخدام")

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

        # ── Separate instant vs pending effects ──────────────────────
        instant_effects = [e for e in all_effects if (e.trigger_on or "activation") == "activation"]
        pending_effects = [e for e in all_effects if (e.trigger_on or "activation") in PENDING_TRIGGERS]

        # Execute instant effects via the effect engine
        instant_results = []
        if instant_effects:
            instant_results = await execute_item_effects(
                session, owned, membership, instant_effects,
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
async def check_alias_change_permission(account: CurrentAccount):
    """Check if the player has an unredeemed alias change permission."""
    async with async_session() as session:
        mem_result = await session.execute(
            select(Membership).where(
                Membership.account_id == account.id,
                Membership.status == MembershipStatus.ACTIVE,
            ).limit(1)
        )
        membership = mem_result.scalars().first()
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
async def change_alias(body: ChangeAliasRequest, account: CurrentAccount):
    """Change the player's alias using an ALLOW_ALIAS_CHANGE activation."""
    from datetime import datetime

    if not body.new_alias or len(body.new_alias.strip()) < 2:
        raise HTTPException(status_code=400, detail="اللقب يجب أن يكون حرفين على الأقل")

    async with async_session() as session:
        mem_result = await session.execute(
            select(Membership).where(
                Membership.account_id == account.id,
                Membership.status == MembershipStatus.ACTIVE,
            ).limit(1)
        )
        membership = mem_result.scalars().first()
        if not membership:
            raise HTTPException(status_code=403, detail="أنت لست عضواً في أي منافسة")

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

        await session.commit()

    return {
        "success": True,
        "data": {"old_alias": old_alias, "new_alias": new_alias},
        "message": f"تم تغيير لقبك من «{old_alias}» إلى «{new_alias}»",
    }
