"""Competition structure + membership models."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import (
    CompetitionStatus,
    CycleStatus,
    InviteStatus,
    InviteType,
    MembershipStatus,
    ProtectionType,
    SeasonStatus,
)
from app.core.models import Base, pg_enum
from app.core.utils import now_riyadh_naive


# ── Competition Structure ─────────────────────────────────────────────────


class Competition(Base):
    __tablename__ = "competitions"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[CompetitionStatus] = mapped_column(
        pg_enum(CompetitionStatus, name="competition_status"), nullable=False, default=CompetitionStatus.DRAFT
    )
    registration_open: Mapped[bool] = mapped_column(default=False)
    visibility: Mapped[str] = mapped_column(String(20), nullable=False, default="private")
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=now_riyadh_naive)
    updated_at: Mapped[datetime] = mapped_column(default=now_riyadh_naive, onupdate=now_riyadh_naive)

    seasons = relationship("Season", back_populates="competition", lazy="selectin")
    memberships = relationship("Membership", back_populates="competition", lazy="selectin")
    invites = relationship("CompetitionInvite", back_populates="competition", lazy="selectin")


class CompetitionInvite(Base):
    __tablename__ = "competition_invites"
    __table_args__ = (
        CheckConstraint("max_uses IS NULL OR use_count <= max_uses", name="chk_invite_uses"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    competition_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("competitions.id", ondelete="CASCADE"), nullable=False)
    invite_type: Mapped[InviteType] = mapped_column(pg_enum(InviteType, name="invite_type"), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    status: Mapped[InviteStatus] = mapped_column(
        pg_enum(InviteStatus, name="invite_status"), nullable=False, default=InviteStatus.ACTIVE
    )
    max_uses: Mapped[int | None] = mapped_column()
    use_count: Mapped[int] = mapped_column(default=0)
    expires_at: Mapped[datetime | None] = mapped_column()
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(default=now_riyadh_naive)

    competition = relationship("Competition", back_populates="invites")


class Season(Base):
    __tablename__ = "seasons"
    __table_args__ = (
        CheckConstraint("ends_at IS NULL OR ends_at > starts_at", name="chk_season_dates"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    competition_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("competitions.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    order_index: Mapped[int] = mapped_column(default=1)
    status: Mapped[SeasonStatus] = mapped_column(
        pg_enum(SeasonStatus, name="season_status"), nullable=False, default=SeasonStatus.DRAFT
    )
    starts_at: Mapped[datetime | None] = mapped_column()
    ends_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(default=now_riyadh_naive)
    updated_at: Mapped[datetime] = mapped_column(default=now_riyadh_naive, onupdate=now_riyadh_naive)

    competition = relationship("Competition", back_populates="seasons")
    cycles = relationship("Cycle", back_populates="season", lazy="selectin")


class Cycle(Base):
    __tablename__ = "cycles"
    __table_args__ = (
        CheckConstraint("ends_at IS NULL OR ends_at > starts_at", name="chk_cycle_dates"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    season_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("seasons.id", ondelete="CASCADE"), nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    order_index: Mapped[int] = mapped_column(default=1)
    status: Mapped[CycleStatus] = mapped_column(
        pg_enum(CycleStatus, name="cycle_status"), nullable=False, default=CycleStatus.DRAFT
    )
    starts_at: Mapped[datetime | None] = mapped_column()
    ends_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(default=now_riyadh_naive)
    updated_at: Mapped[datetime] = mapped_column(default=now_riyadh_naive, onupdate=now_riyadh_naive)

    season = relationship("Season", back_populates="cycles")


# ── Membership & Gameplay Identity ────────────────────────────────────────


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("account_id", "competition_id", name="uq_membership"),
        CheckConstraint("current_balance >= 0", name="chk_balance_non_negative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False)
    competition_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("competitions.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[MembershipStatus] = mapped_column(
        pg_enum(MembershipStatus, name="membership_status"), nullable=False, default=MembershipStatus.PENDING
    )
    current_alias: Mapped[str | None] = mapped_column(String(100))
    current_balance: Mapped[int] = mapped_column(default=0)
    is_bankrupt: Mapped[bool] = mapped_column(default=False)
    protection: Mapped[ProtectionType] = mapped_column(
        pg_enum(ProtectionType, name="protection_type"), nullable=False, default=ProtectionType.NONE
    )
    joined_at: Mapped[datetime] = mapped_column(default=now_riyadh_naive)
    updated_at: Mapped[datetime] = mapped_column(default=now_riyadh_naive, onupdate=now_riyadh_naive)

    account = relationship("Account", back_populates="memberships")
    competition = relationship("Competition", back_populates="memberships")
    alias_records = relationship("AliasRecord", back_populates="membership", lazy="selectin")


class AliasRecord(Base):
    __tablename__ = "alias_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    membership_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("memberships.id", ondelete="CASCADE"), nullable=False)
    alias_value: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    reason: Mapped[str | None] = mapped_column(String(200))
    season_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("seasons.id", ondelete="SET NULL"))
    cycle_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("cycles.id", ondelete="SET NULL"))
    starts_at: Mapped[datetime] = mapped_column(default=now_riyadh_naive)
    ends_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(default=now_riyadh_naive)

    membership = relationship("Membership", back_populates="alias_records")
