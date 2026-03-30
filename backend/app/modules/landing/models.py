"""Landing link model — lightweight tracked share links."""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base
from app.core.utils import now_riyadh_naive


class LandingLink(Base):
    __tablename__ = "landing_links"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    token: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    label: Mapped[str] = mapped_column(String(200))
    destination_path: Mapped[str] = mapped_column(String(500), default="/landing.html")
    competition_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("competitions.id", ondelete="SET NULL"), nullable=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(default=True)
    total_clicks: Mapped[int] = mapped_column(default=0)
    total_joins: Mapped[int] = mapped_column(default=0)
    last_clicked_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=now_riyadh_naive)
