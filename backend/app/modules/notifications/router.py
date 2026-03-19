"""Notification endpoints — list and mark as read."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update

from app.core.auth import get_current_account
from app.core.database import async_session
from app.modules.auth.models import Account
from app.modules.notifications.models import Notification

router = APIRouter(tags=["notifications"])
CurrentAccount = Annotated[Account, Depends(get_current_account)]


@router.get("/api/me/notifications")
async def list_notifications(account: CurrentAccount):
    """List all notifications for the current user, newest first."""
    async with async_session() as session:
        result = await session.execute(
            select(Notification)
            .where(Notification.recipient_id == account.id)
            .order_by(Notification.created_at.desc())
            .limit(50)
        )
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

    return {"success": True, "data": notifications}


@router.post("/api/me/notifications/{notification_id}/read")
async def mark_read(notification_id: uuid.UUID, account: CurrentAccount):
    """Mark a single notification as read."""
    async with async_session() as session:
        notif = await session.get(Notification, notification_id)
        if not notif or str(notif.recipient_id) != str(account.id):
            raise HTTPException(status_code=404, detail="الإشعار غير موجود")

        notif.is_read = True
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
            .values(is_read=True)
        )
        await session.commit()

    return {"success": True, "message": "تم تحديد جميع الإشعارات كمقروءة"}
