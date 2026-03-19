"""Store endpoints — list items, purchase, view inventory."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select

from app.core.auth import get_current_account
from app.core.database import async_session
from app.core.enums import (
    LedgerDirection,
    LedgerEntryType,
    ListingStatus,
    MembershipStatus,
    NotificationType,
    OwnedItemStatus,
)
from app.modules.auth.models import Account
from app.modules.competitions.models import Membership
from app.modules.scoring.models import LedgerEntry
from app.modules.notifications.service import create_notification
from app.modules.store.models import ItemDefinition, OwnedItem, StoreListing

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

    listings = []
    for listing, item in rows:
        stock_remaining = None
        if listing.total_stock is not None:
            stock_remaining = listing.total_stock - listing.sold_count

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
            return {"success": True, "data": []}

        # Get owned items with item details
        result = await session.execute(
            select(OwnedItem, ItemDefinition)
            .join(ItemDefinition, OwnedItem.item_definition_id == ItemDefinition.id)
            .where(
                OwnedItem.membership_id == membership.id,
                OwnedItem.status.in_([
                    OwnedItemStatus.AVAILABLE,
                    OwnedItemStatus.ACTIVATED,
                ]),
            )
            .order_by(OwnedItem.acquired_at.desc())
        )
        rows = result.all()

    items = []
    for owned, item_def in rows:
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
            "acquired_at": owned.acquired_at.isoformat() if owned.acquired_at else None,
            "expires_at": owned.expires_at.isoformat() if owned.expires_at else None,
        })

    return {"success": True, "data": items}
