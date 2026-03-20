"""
Audit trail writer — records admin and system mutations.

Every admin action that changes state should call write_audit() to create
a traceable record with before/after snapshots.
"""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import AuditActorType
from app.core.utils import jsonb_safe
from app.modules.audit.models import AuditEvent


async def write_audit(
    session: AsyncSession,
    *,
    actor_id: uuid.UUID,
    actor_type: AuditActorType = AuditActorType.ADMIN,
    subject_type: str,
    subject_id: uuid.UUID | None = None,
    event_type: str,
    summary: str,
    reason: str | None = None,
    before_state: dict[str, Any] | None = None,
    after_state: dict[str, Any] | None = None,
    related_type: str | None = None,
    related_id: uuid.UUID | None = None,
    ip_address: str | None = None,
) -> AuditEvent:
    """
    Write an audit event to the database.

    Args:
        actor_id: The account ID of the person/system performing the action.
        actor_type: ADMIN, SYSTEM, or PARTICIPANT.
        subject_type: What was acted upon (e.g. "membership", "competition", "setting").
        subject_id: UUID of the subject record.
        event_type: Verb-noun key (e.g. "balance_adjusted", "status_changed", "setting_updated").
        summary: Human-readable description of what happened.
        reason: Optional reason provided by the admin.
        before_state: JSON snapshot of state before the change.
        after_state: JSON snapshot of state after the change.
        related_type: Optional related entity type (e.g. "competition").
        related_id: Optional related entity UUID.
        ip_address: Optional IP address of the actor.
    """
    event = AuditEvent(
        actor_id=actor_id,
        actor_type=actor_type,
        subject_type=subject_type,
        subject_id=subject_id,
        event_type=event_type,
        summary=summary,
        reason=reason,
        before_state=jsonb_safe(before_state),
        after_state=jsonb_safe(after_state),
        related_type=related_type,
        related_id=related_id,
        ip_address=ip_address,
    )
    session.add(event)
    return event
