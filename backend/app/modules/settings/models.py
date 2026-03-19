"""Settings & configuration engine models."""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import SettingDataType, SettingScope
from app.core.models import Base, pg_enum


class SettingDefinition(Base):
    __tablename__ = "setting_definitions"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    data_type: Mapped[SettingDataType] = mapped_column(
        pg_enum(SettingDataType, name="setting_data_type"), nullable=False
    )
    default_value: Mapped[dict] = mapped_column(JSONB, nullable=False)
    allowed_values: Mapped[dict | None] = mapped_column(JSONB)
    description: Mapped[str | None] = mapped_column(Text)
    is_per_competition: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)


class SettingValue(Base):
    __tablename__ = "setting_values"
    __table_args__ = (
        UniqueConstraint("setting_definition_id", "scope", "scope_id", name="uq_setting_value"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    setting_definition_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("setting_definitions.id", ondelete="CASCADE"), nullable=False
    )
    scope: Mapped[SettingScope] = mapped_column(pg_enum(SettingScope, name="setting_scope"), nullable=False)
    scope_id: Mapped[uuid.UUID | None] = mapped_column(UUID)
    value: Mapped[dict] = mapped_column(JSONB, nullable=False)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
