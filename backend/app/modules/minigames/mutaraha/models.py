"""مطارحة word bank model."""

import uuid
from datetime import datetime

from sqlalchemy import String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base
from app.core.utils import now_riyadh_naive


class MutarahaWord(Base):
    __tablename__ = "mutaraha_word_bank"
    __table_args__ = (
        UniqueConstraint("word", "category", name="uq_mutaraha_word"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    word: Mapped[str] = mapped_column(String(50), nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    letter_count: Mapped[int] = mapped_column(nullable=False)
    first_letter: Mapped[str] = mapped_column(String(1), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(10), nullable=False, default="easy")
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(default=now_riyadh_naive)
    updated_at: Mapped[datetime] = mapped_column(default=now_riyadh_naive, onupdate=now_riyadh_naive)
