"""Scoring & financial trace models — ledger entries."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import LedgerDirection, LedgerEntryType
from app.core.models import Base, pg_enum


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="chk_ledger_amount"),
        # chk_ledger_balance lives in the migration SQL only — asyncpg cannot
        # handle enum literal casts ('credit'::ledger_direction) inside DDL.
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    membership_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=False)
    competition_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("competitions.id", ondelete="RESTRICT"), nullable=False)
    season_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("seasons.id", ondelete="SET NULL"))
    cycle_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("cycles.id", ondelete="SET NULL"))
    entry_type: Mapped[LedgerEntryType] = mapped_column(
        pg_enum(LedgerEntryType, name="ledger_entry_type"), nullable=False
    )
    amount: Mapped[int] = mapped_column(nullable=False)
    direction: Mapped[LedgerDirection] = mapped_column(
        pg_enum(LedgerDirection, name="ledger_direction"), nullable=False
    )
    balance_before: Mapped[int] = mapped_column(nullable=False)
    balance_after: Mapped[int] = mapped_column(nullable=False)
    source_type: Mapped[str | None] = mapped_column(String(50))
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID)
    reason: Mapped[str | None] = mapped_column(Text)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
