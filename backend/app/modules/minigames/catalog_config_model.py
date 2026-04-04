"""Presentation metadata for minigame catalog cards.

Separate from MinigameType (which holds operational metadata) so that
marketing/UX fields can evolve independently of the engine contract.

BRD reference: §11.3
"""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import (
    MinigameCardVariant,
    MinigameCatalogAvailability,
    MinigameHeroVariant,
)
from app.core.models import Base, pg_enum
from app.core.utils import now_riyadh_naive


class MinigameCatalogConfig(Base):
    __tablename__ = "minigame_catalog_configs"
    __table_args__ = (
        CheckConstraint("sort_order >= 0", name="chk_mg_catalog_sort_order"),
        CheckConstraint(
            "estimated_duration_sec IS NULL OR estimated_duration_sec > 0",
            name="chk_mg_catalog_duration_positive",
        ),
    )

    # Primary key — 1:1 with minigame_types.id
    game_type: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("minigame_types.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Presentation content
    short_description: Mapped[str] = mapped_column(String(200), nullable=False)
    icon_token: Mapped[str] = mapped_column(String(100), nullable=False)
    accent_color: Mapped[str] = mapped_column(String(7), nullable=False)  # #RRGGBB

    # Layout variants (enums)
    hero_variant: Mapped[MinigameHeroVariant] = mapped_column(
        pg_enum(MinigameHeroVariant, name="minigame_hero_variant"),
        nullable=False,
        default=MinigameHeroVariant.ARENA,
    )
    card_variant: Mapped[MinigameCardVariant] = mapped_column(
        pg_enum(MinigameCardVariant, name="minigame_card_variant"),
        nullable=False,
        default=MinigameCardVariant.STANDARD,
    )

    # Optional metadata
    estimated_duration_sec: Mapped[int | None] = mapped_column()
    featured: Mapped[bool] = mapped_column(nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(nullable=False, default=100)

    # Availability + marketing
    availability_mode: Mapped[MinigameCatalogAvailability] = mapped_column(
        pg_enum(MinigameCatalogAvailability, name="minigame_catalog_availability"),
        nullable=False,
        default=MinigameCatalogAvailability.ACTIVE,
    )
    marketing_label: Mapped[str | None] = mapped_column(String(100))
    expected_launch_at: Mapped[datetime | None] = mapped_column()

    # Audit timestamps
    created_at: Mapped[datetime] = mapped_column(default=now_riyadh_naive)
    updated_at: Mapped[datetime] = mapped_column(default=now_riyadh_naive, onupdate=now_riyadh_naive)
