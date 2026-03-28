"""Notification endpoints — list and mark as read."""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select, update

from app.core.auth import get_current_account
from app.core.database import async_session
from app.core.enums import MembershipStatus
from app.modules.auth.models import Account
from app.modules.competitions.models import Membership
from app.modules.notifications.models import Notification

router = APIRouter(tags=["notifications"])
CurrentAccount = Annotated[Account, Depends(get_current_account)]


@router.get("/api/me/notifications")
async def list_notifications(
    account: CurrentAccount,
    competition_id: str | None = None,
    limit: int = 20,
    offset: int = 0,
):
    """List notifications for the current user, newest first.
    When competition_id is provided, returns only notifications for that
    competition's membership (plus any account-global notifications).
    """
    async with async_session() as session:
        query = (
            select(Notification)
            .where(Notification.recipient_id == account.id)
        )

        # If competition_id provided, filter to that competition's membership
        if competition_id:
            try:
                cid = uuid.UUID(competition_id)
                mem_result = await session.execute(
                    select(Membership.id).where(
                        Membership.account_id == account.id,
                        Membership.competition_id == cid,
                        Membership.status == MembershipStatus.ACTIVE,
                    ).limit(1)
                )
                membership_id = mem_result.scalar()
                if membership_id:
                    # Show notifications for this membership + global (no membership)
                    query = query.where(
                        (Notification.membership_id == membership_id)
                        | (Notification.membership_id == None)  # noqa: E711
                    )
            except ValueError:
                pass

        # Count total matching notifications (reuse the same filters from query)
        count_query = query.with_only_columns(func.count()).order_by(None)
        total_count = await session.execute(count_query)
        total = total_count.scalar()

        query = query.order_by(Notification.created_at.desc()).limit(limit).offset(offset)
        result = await session.execute(query)
        rows = result.scalars().all()

    notifications = []
    for n in rows:
        notifications.append({
            "id": str(n.id),
            "type": n.notification_type,
            "title": n.title,
            "message": n.message,
            "is_read": n.is_read,
            "priority": n.priority,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        })

    return {
        "success": True,
        "data": notifications,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("/api/me/notifications/{notification_id}/read")
async def mark_read(notification_id: uuid.UUID, account: CurrentAccount):
    """Mark a single notification as read."""
    async with async_session() as session:
        notif = await session.get(Notification, notification_id)
        if not notif or str(notif.recipient_id) != str(account.id):
            raise HTTPException(status_code=404, detail="الإشعار غير موجود")

        notif.is_read = True
        notif.read_at = datetime.utcnow()
        await session.commit()

    return {"success": True, "message": "تم تحديد الإشعار كمقروء"}


@router.post("/api/me/notifications/read-all")
async def mark_all_read(account: CurrentAccount):
    """Mark all notifications as read for current user."""
    async with async_session() as session:
        await session.execute(
            update(Notification)
            .where(
                Notification.recipient_id == account.id,
                Notification.is_read == False,
            )
            .values(is_read=True, read_at=datetime.utcnow())
        )
        await session.commit()

    return {"success": True, "message": "تم تحديد جميع الإشعارات كمقروءة"}
