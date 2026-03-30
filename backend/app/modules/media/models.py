"""Media, import, and export models."""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import (
    ExportStatus,
    ImportStatus,
    ImportType,
    MediaContentType,
    MediaStorageType,
)
from app.core.models import Base, pg_enum
from app.core.utils import now_riyadh_naive


class MediaAsset(Base):
    __tablename__ = "media_assets"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    storage_type: Mapped[MediaStorageType] = mapped_column(
        pg_enum(MediaStorageType, name="media_storage_type"), nullable=False
    )
    storage_path: Mapped[str | None] = mapped_column(Text)
    external_url: Mapped[str | None] = mapped_column(Text)
    media_type: Mapped[MediaContentType] = mapped_column(
        pg_enum(MediaContentType, name="media_content_type"), nullable=False
    )
    original_filename: Mapped[str | None] = mapped_column(String(255))
    file_size_bytes: Mapped[int | None] = mapped_column()
    mime_type: Mapped[str | None] = mapped_column(String(100))
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(default=now_riyadh_naive)


class ImportJob(Base):
    __tablename__ = "import_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    import_type: Mapped[ImportType] = mapped_column(pg_enum(ImportType, name="import_type"), nullable=False)
    file_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("media_assets.id", ondelete="SET NULL"))
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[ImportStatus] = mapped_column(
        pg_enum(ImportStatus, name="import_status"), nullable=False, default=ImportStatus.PENDING
    )
    validation_summary: Mapped[dict | None] = mapped_column(JSONB)
    result_summary: Mapped[dict | None] = mapped_column(JSONB)
    target_group_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("question_groups.id", ondelete="SET NULL")
    )
    started_at: Mapped[datetime | None] = mapped_column()
    completed_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(default=now_riyadh_naive)


class ExportArtifact(Base):
    __tablename__ = "export_artifacts"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    export_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_scope: Mapped[str | None] = mapped_column(String(50))
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID)
    file_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("media_assets.id", ondelete="SET NULL"))
    generated_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[ExportStatus] = mapped_column(
        pg_enum(ExportStatus, name="export_status"), nullable=False, default=ExportStatus.GENERATING
    )
    generated_at: Mapped[datetime | None] = mapped_column()
    expires_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(default=now_riyadh_naive)
