"""Announcement models — rich broadcast system with scoping, timing, and CTA support."""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base, pg_enum


class AnnouncementScope(StrEnum):
    GLOBAL = "global"
    COMPETITION = "competition"
    SEASON = "season"
    CYCLE = "cycle"


class AnnouncementStyle(StrEnum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    DANGER = "danger"
    CELEBRATION = "celebration"


class Announcement(Base):
    __tablename__ = "announcements"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    subtitle: Mapped[str | None] = mapped_column(String(300))
    body: Mapped[str | None] = mapped_column(Text)
    style: Mapped[AnnouncementStyle] = mapped_column(
        pg_enum(AnnouncementStyle, name="announcement_style"),
        nullable=False,
        default=AnnouncementStyle.INFO,
    )

    # Scope
    scope: Mapped[AnnouncementScope] = mapped_column(
        pg_enum(AnnouncementScope, name="announcement_scope"),
        nullable=False,
        default=AnnouncementScope.GLOBAL,
    )
    competition_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("competitions.id", ondelete="CASCADE")
    )
    season_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("seasons.id", ondelete="CASCADE")
    )
    cycle_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cycles.id", ondelete="CASCADE")
    )

    # CTA
    cta_label: Mapped[str | None] = mapped_column(String(100))
    cta_url: Mapped[str | None] = mapped_column(String(500))

    # Timing & visibility
    is_active: Mapped[bool] = mapped_column(default=True)
    is_dismissible: Mapped[bool] = mapped_column(default=True)
    starts_at: Mapped[datetime | None] = mapped_column()
    ends_at: Mapped[datetime | None] = mapped_column()

    # Metadata
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="SET NULL"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
