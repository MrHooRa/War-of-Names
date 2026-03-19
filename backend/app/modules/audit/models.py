"""Audit & operational log models."""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import AuditActorType
from app.core.models import Base, pg_enum


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"))
    actor_type: Mapped[AuditActorType] = mapped_column(
        pg_enum(AuditActorType, name="audit_actor_type"), nullable=False
    )
    subject_type: Mapped[str] = mapped_column(String(50), nullable=False)
    subject_id: Mapped[uuid.UUID | None] = mapped_column(UUID)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    before_state: Mapped[dict | None] = mapped_column(JSONB)
    after_state: Mapped[dict | None] = mapped_column(JSONB)
    related_type: Mapped[str | None] = mapped_column(String(50))
    related_id: Mapped[uuid.UUID | None] = mapped_column(UUID)
    ip_address: Mapped[str | None] = mapped_column(INET)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
