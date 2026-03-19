"""Notification service — create notifications for game events."""

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import NotificationPriority, NotificationType
from app.modules.notifications.models import Notification


async def create_notification(
    session: AsyncSession,
    *,
    recipient_id: uuid.UUID,
    notification_type: NotificationType,
    title: str,
    message: str,
    membership_id: uuid.UUID | None = None,
    priority: NotificationPriority = NotificationPriority.NORMAL,
    reference_type: str | None = None,
    reference_id: uuid.UUID | None = None,
    deep_link: str | None = None,
) -> Notification:
    """Create and add a notification to the session (caller must commit)."""
    notif = Notification(
        recipient_id=recipient_id,
        membership_id=membership_id,
        notification_type=notification_type,
        title=title,
        message=message,
        priority=priority,
        reference_type=reference_type,
        reference_id=reference_id,
        deep_link=deep_link,
    )
    session.add(notif)
    return notif
