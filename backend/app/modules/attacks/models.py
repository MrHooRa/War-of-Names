"""Attack & protection engine models."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import AttackOutcome, BankruptcyState, ProtectionType
from app.core.models import Base, pg_enum


class AttackAttempt(Base):
    __tablename__ = "attack_attempts"
    __table_args__ = (
        CheckConstraint("attacker_id <> target_id", name="chk_attack_self"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    attacker_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=False)
    competition_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("competitions.id", ondelete="RESTRICT"), nullable=False)
    season_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("seasons.id", ondelete="RESTRICT"), nullable=False)
    cycle_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cycles.id", ondelete="RESTRICT"), nullable=False)
    guessed_account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False)
    outcome: Mapped[AttackOutcome] = mapped_column(
        pg_enum(AttackOutcome, name="attack_outcome"), nullable=False
    )
    reward_amount: Mapped[int] = mapped_column(default=0)
    penalty_amount: Mapped[int] = mapped_column(default=0)
    modifiers_applied: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    blocking_reason: Mapped[str | None] = mapped_column(Text)
    executed_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class ProtectionRecord(Base):
    __tablename__ = "protection_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    membership_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("memberships.id", ondelete="CASCADE"), nullable=False)
    protection_type: Mapped[ProtectionType] = mapped_column(
        pg_enum(ProtectionType, name="protection_type"), nullable=False
    )
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID)
    season_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("seasons.id", ondelete="SET NULL"))
    cycle_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("cycles.id", ondelete="SET NULL"))
    reason: Mapped[str | None] = mapped_column(Text)
    starts_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    ends_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class AttackExposure(Base):
    __tablename__ = "attack_exposure"
    __table_args__ = (
        UniqueConstraint("membership_id", "cycle_id", name="uq_attack_exposure"),
        CheckConstraint("successful_attack_count >= 0", name="chk_exposure_count"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    membership_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=False)
    season_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("seasons.id", ondelete="RESTRICT"), nullable=False)
    cycle_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cycles.id", ondelete="RESTRICT"), nullable=False)
    successful_attack_count: Mapped[int] = mapped_column(default=0)
    current_reward_stage: Mapped[int] = mapped_column(default=0)
    max_attacks_reached: Mapped[bool] = mapped_column(default=False)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)


class BankruptcyRecord(Base):
    __tablename__ = "bankruptcy_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    membership_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("memberships.id", ondelete="CASCADE"), nullable=False)
    cycle_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cycles.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[BankruptcyState] = mapped_column(
        pg_enum(BankruptcyState, name="bankruptcy_state"), nullable=False, default=BankruptcyState.ACTIVE
    )
    trigger_reason: Mapped[str | None] = mapped_column(Text)
    trigger_source_id: Mapped[uuid.UUID | None] = mapped_column(UUID)
    triggered_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    active_until: Mapped[datetime | None] = mapped_column()
    resolved_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
