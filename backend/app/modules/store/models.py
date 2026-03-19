"""Store / item / reward engine models."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import (
    DistributionStatus,
    DistributionTarget,
    DistributionType,
    EffectType,
    ItemAcquisitionType,
    ItemRarity,
    ItemStatus,
    ItemUsageType,
    ListingStatus,
    OwnedItemStatus,
    RewardGrantStatus,
    RewardType,
)
from app.core.models import Base, pg_enum


class ItemDefinition(Base):
    __tablename__ = "item_definitions"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    rarity: Mapped[ItemRarity] = mapped_column(
        pg_enum(ItemRarity, name="item_rarity"), nullable=False, default=ItemRarity.COMMON
    )
    status: Mapped[ItemStatus] = mapped_column(
        pg_enum(ItemStatus, name="item_status"), nullable=False, default=ItemStatus.DRAFT
    )
    category: Mapped[str | None] = mapped_column(String(50))
    acquisition_type: Mapped[ItemAcquisitionType] = mapped_column(
        pg_enum(ItemAcquisitionType, name="item_acquisition_type"), nullable=False, default=ItemAcquisitionType.PURCHASE
    )
    usage_type: Mapped[ItemUsageType] = mapped_column(
        pg_enum(ItemUsageType, name="item_usage_type"), nullable=False, default=ItemUsageType.CONSUMABLE
    )
    max_uses: Mapped[int | None] = mapped_column()
    is_stackable: Mapped[bool] = mapped_column(default=False)
    expires_after_minutes: Mapped[int | None] = mapped_column()
    scope_competition_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("competitions.id", ondelete="SET NULL"))
    visibility: Mapped[str] = mapped_column(String(20), nullable=False, default="visible")
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    effects = relationship("ItemEffect", back_populates="item_definition", lazy="selectin")


class ItemEffect(Base):
    __tablename__ = "item_effects"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    item_definition_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("item_definitions.id", ondelete="CASCADE"), nullable=False
    )
    effect_type: Mapped[EffectType] = mapped_column(pg_enum(EffectType, name="effect_type"), nullable=False)
    parameters: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    target_scope: Mapped[str] = mapped_column(String(20), nullable=False, default="self")
    duration_minutes: Mapped[int | None] = mapped_column()
    is_stackable: Mapped[bool] = mapped_column(default=False)
    trigger_on: Mapped[str] = mapped_column(String(20), nullable=False, default="activation")
    order_index: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    item_definition = relationship("ItemDefinition", back_populates="effects")


class StoreListing(Base):
    __tablename__ = "store_listings"
    __table_args__ = (
        CheckConstraint("price > 0", name="chk_listing_price"),
        CheckConstraint("total_stock IS NULL OR sold_count <= total_stock", name="chk_listing_stock"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    item_definition_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("item_definitions.id", ondelete="CASCADE"), nullable=False
    )
    competition_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("competitions.id", ondelete="CASCADE"), nullable=False)
    season_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("seasons.id", ondelete="SET NULL"))
    cycle_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("cycles.id", ondelete="SET NULL"))
    status: Mapped[ListingStatus] = mapped_column(
        pg_enum(ListingStatus, name="listing_status"), nullable=False, default=ListingStatus.ACTIVE
    )
    price: Mapped[int] = mapped_column(nullable=False)
    max_per_participant: Mapped[int | None] = mapped_column()
    total_stock: Mapped[int | None] = mapped_column()
    sold_count: Mapped[int] = mapped_column(default=0)
    available_from: Mapped[datetime | None] = mapped_column()
    available_until: Mapped[datetime | None] = mapped_column()
    eligibility_rules: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)


class OwnedItem(Base):
    __tablename__ = "owned_items"
    __table_args__ = (CheckConstraint("quantity > 0", name="chk_owned_quantity"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    membership_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=False)
    item_definition_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("item_definitions.id", ondelete="RESTRICT"), nullable=False
    )
    source_type: Mapped[str] = mapped_column(String(30), nullable=False)
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID)
    quantity: Mapped[int] = mapped_column(default=1)
    uses_remaining: Mapped[int | None] = mapped_column()
    status: Mapped[OwnedItemStatus] = mapped_column(
        pg_enum(OwnedItemStatus, name="owned_item_status"), nullable=False, default=OwnedItemStatus.AVAILABLE
    )
    acquired_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    activated_at: Mapped[datetime | None] = mapped_column()
    expires_at: Mapped[datetime | None] = mapped_column()
    consumed_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class ItemActivation(Base):
    __tablename__ = "item_activations"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    owned_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("owned_items.id", ondelete="RESTRICT"), nullable=False
    )
    membership_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=False)
    target_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("memberships.id", ondelete="SET NULL")
    )
    result_state: Mapped[str] = mapped_column(String(20), nullable=False, default="success")
    effect_summary: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    denial_reason: Mapped[str | None] = mapped_column(Text)
    activated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class RewardDefinition(Base):
    __tablename__ = "reward_definitions"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    reward_type: Mapped[RewardType] = mapped_column(pg_enum(RewardType, name="reward_type"), nullable=False)
    content: Mapped[dict] = mapped_column(JSONB, nullable=False)
    rules: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    competition_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("competitions.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)


class RewardGrant(Base):
    __tablename__ = "reward_grants"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    membership_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=False)
    reward_definition_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("reward_definitions.id", ondelete="SET NULL")
    )
    source_type: Mapped[str] = mapped_column(String(30), nullable=False)
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID)
    status: Mapped[RewardGrantStatus] = mapped_column(
        pg_enum(RewardGrantStatus, name="reward_grant_status"), nullable=False, default=RewardGrantStatus.PENDING
    )
    granted_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    claimed_at: Mapped[datetime | None] = mapped_column()
    expires_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class BoxOutcome(Base):
    __tablename__ = "box_outcomes"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    reward_grant_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("reward_grants.id", ondelete="SET NULL"))
    owned_item_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("owned_items.id", ondelete="SET NULL"))
    membership_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=False)
    outcome_type: Mapped[str] = mapped_column(String(20), nullable=False)
    outcome_content: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    ledger_entry_id: Mapped[uuid.UUID | None] = mapped_column(UUID)
    granted_item_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("owned_items.id", ondelete="SET NULL"))
    opened_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class Distribution(Base):
    __tablename__ = "distributions"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    competition_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("competitions.id", ondelete="CASCADE"), nullable=False)
    season_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("seasons.id", ondelete="SET NULL"))
    cycle_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("cycles.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    dist_type: Mapped[DistributionType] = mapped_column(
        pg_enum(DistributionType, name="distribution_type"), nullable=False
    )
    target_type: Mapped[DistributionTarget] = mapped_column(
        pg_enum(DistributionTarget, name="distribution_target"), nullable=False
    )
    target_rules: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    content: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[DistributionStatus] = mapped_column(
        pg_enum(DistributionStatus, name="distribution_status"), nullable=False, default=DistributionStatus.DRAFT
    )
    scheduled_at: Mapped[datetime | None] = mapped_column()
    executed_at: Mapped[datetime | None] = mapped_column()
    result_summary: Mapped[dict | None] = mapped_column(JSONB)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
