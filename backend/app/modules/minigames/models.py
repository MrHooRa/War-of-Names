"""Minigame engine database models.

Tables:
    minigame_types           — registry of available game types
    minigame_sessions        — game sessions with state + revision
    minigame_session_events  — append-only event log
    minigame_action_receipts — idempotency table
    minigame_session_settlements — financial settlements
    minigame_leaderboards    — per-game rankings
    minigame_policy_rules    — anti-abuse policy rules
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import (
    MinigameMatchType,
    MinigameSessionPhase,
    MinigameSettlementState,
    MinigameTypeStatus,
)
from app.core.models import Base, pg_enum
from app.core.utils import now_riyadh_naive


class MinigameType(Base):
    __tablename__ = "minigame_types"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    plugin_api_version: Mapped[str] = mapped_column(String(10), nullable=False, default="1.0")
    settings_schema_version: Mapped[str] = mapped_column(String(10), nullable=False, default="1.0")
    min_players: Mapped[int] = mapped_column(nullable=False, default=2)
    max_players: Mapped[int] = mapped_column(nullable=False, default=2)
    supports_overtime: Mapped[bool] = mapped_column(default=False)
    supports_spectators: Mapped[bool] = mapped_column(default=False)
    supports_ranked: Mapped[bool] = mapped_column(default=False)
    supports_team_mode: Mapped[bool] = mapped_column(default=False)
    status: Mapped[MinigameTypeStatus] = mapped_column(
        pg_enum(MinigameTypeStatus, name="minigame_type_status"),
        nullable=False,
        default=MinigameTypeStatus.ACTIVE,
    )
    created_at: Mapped[datetime] = mapped_column(default=now_riyadh_naive)
    updated_at: Mapped[datetime] = mapped_column(default=now_riyadh_naive, onupdate=now_riyadh_naive)


class MinigameSession(Base):
    __tablename__ = "minigame_sessions"
    __table_args__ = (
        CheckConstraint("buy_in_amount >= 0", name="chk_mg_buy_in"),
        CheckConstraint("revision >= 0", name="chk_mg_revision"),
        CheckConstraint("turn_number >= 0", name="chk_mg_turn_number"),
        CheckConstraint("num_players >= 1 AND num_players <= 8", name="chk_mg_num_players"),
        Index(
            "idx_mg_sessions_active",
            "game_type", "competition_id",
            postgresql_where="phase NOT IN ('completed', 'cancelled', 'abandoned')",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    game_type: Mapped[str] = mapped_column(
        ForeignKey("minigame_types.id", ondelete="RESTRICT"), nullable=False
    )
    competition_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("competitions.id", ondelete="RESTRICT"), nullable=False
    )
    season_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("seasons.id", ondelete="SET NULL")
    )
    cycle_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cycles.id", ondelete="SET NULL")
    )
    phase: Mapped[MinigameSessionPhase] = mapped_column(
        pg_enum(MinigameSessionPhase, name="minigame_session_phase"),
        nullable=False,
        default=MinigameSessionPhase.CREATED,
    )
    revision: Mapped[int] = mapped_column(nullable=False, default=0)
    num_players: Mapped[int] = mapped_column(nullable=False, default=2)
    min_players: Mapped[int] = mapped_column(nullable=False, default=2)
    max_players: Mapped[int] = mapped_column(nullable=False, default=2)
    match_type: Mapped[MinigameMatchType] = mapped_column(
        pg_enum(MinigameMatchType, name="minigame_match_type"), nullable=False
    )
    current_turn_index: Mapped[int | None] = mapped_column()  # 0-based player slot
    turn_number: Mapped[int] = mapped_column(nullable=False, default=0)
    game_state: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    settings_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    buy_in_amount: Mapped[int] = mapped_column(nullable=False, default=0)
    terminal_reason: Mapped[str | None] = mapped_column(String(100))
    winner_slot_index: Mapped[int | None] = mapped_column()  # winning player's slot
    turn_started_at: Mapped[datetime | None] = mapped_column()
    turn_duration_ms: Mapped[int] = mapped_column(nullable=False, default=30000)
    grace_timer_ms: Mapped[int] = mapped_column(nullable=False, default=60000)
    correlation_id: Mapped[uuid.UUID] = mapped_column(UUID, nullable=False, default=uuid.uuid4)
    started_at: Mapped[datetime | None] = mapped_column()
    completed_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(default=now_riyadh_naive)
    updated_at: Mapped[datetime] = mapped_column(default=now_riyadh_naive, onupdate=now_riyadh_naive)


class MinigameSessionParticipant(Base):
    __tablename__ = "minigame_session_participants"
    __table_args__ = (
        UniqueConstraint("session_id", "membership_id", name="uq_mg_participant"),
        UniqueConstraint("session_id", "slot_index", name="uq_mg_participant_slot"),
        CheckConstraint("slot_index >= 0 AND slot_index <= 7", name="chk_mg_slot_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("minigame_sessions.id", ondelete="CASCADE"), nullable=False
    )
    membership_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=False
    )
    slot_index: Mapped[int] = mapped_column(nullable=False)  # 0-7
    reconnect_token: Mapped[str | None] = mapped_column(String(128))
    joined_at: Mapped[datetime] = mapped_column(default=now_riyadh_naive)


class MinigameSessionEvent(Base):
    __tablename__ = "minigame_session_events"
    __table_args__ = (
        Index("idx_mg_events_session", "session_id", "revision"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("minigame_sessions.id", ondelete="CASCADE"), nullable=False
    )
    revision: Mapped[int] = mapped_column(nullable=False)
    event_type: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_membership_id: Mapped[uuid.UUID | None] = mapped_column(UUID)
    action_type: Mapped[str | None] = mapped_column(String(50))
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    result: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    from_phase: Mapped[str | None] = mapped_column(String(20))
    to_phase: Mapped[str | None] = mapped_column(String(20))
    correlation_id: Mapped[uuid.UUID] = mapped_column(UUID, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=now_riyadh_naive)


class MinigameActionReceipt(Base):
    __tablename__ = "minigame_action_receipts"
    __table_args__ = (
        UniqueConstraint("session_id", "actor_membership_id", "client_seq", name="uq_mg_action_seq"),
    )

    action_id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("minigame_sessions.id", ondelete="CASCADE"), nullable=False
    )
    actor_membership_id: Mapped[uuid.UUID] = mapped_column(UUID, nullable=False)
    client_seq: Mapped[int] = mapped_column(nullable=False)
    response: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=now_riyadh_naive)


class MinigameSessionSettlement(Base):
    __tablename__ = "minigame_session_settlements"
    __table_args__ = (
        UniqueConstraint("session_id", name="uq_mg_settlement_session"),
        CheckConstraint("retry_count >= 0 AND retry_count <= 3", name="chk_mg_retry_count"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("minigame_sessions.id", ondelete="RESTRICT"), nullable=False
    )
    participant_results: Mapped[list | None] = mapped_column(JSONB)
    # Format: [{"membership_id": "uuid", "slot_index": 0, "rank": 1, "payout": 1000}, ...]
    total_pool: Mapped[int] = mapped_column(nullable=False, default=0)
    settlement_state: Mapped[MinigameSettlementState] = mapped_column(
        pg_enum(MinigameSettlementState, name="minigame_settlement_state"),
        nullable=False,
        default=MinigameSettlementState.PENDING,
    )
    ledger_entry_ids: Mapped[list | None] = mapped_column(ARRAY(UUID))
    correlation_id: Mapped[uuid.UUID] = mapped_column(UUID, nullable=False)
    settled_at: Mapped[datetime | None] = mapped_column()
    failure_reason: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(default=now_riyadh_naive)
    updated_at: Mapped[datetime] = mapped_column(default=now_riyadh_naive, onupdate=now_riyadh_naive)


class MinigameLeaderboard(Base):
    __tablename__ = "minigame_leaderboards"
    __table_args__ = (
        UniqueConstraint("game_type", "competition_id", "membership_id", name="uq_mg_leaderboard"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    game_type: Mapped[str] = mapped_column(
        ForeignKey("minigame_types.id", ondelete="CASCADE"), nullable=False
    )
    competition_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("competitions.id", ondelete="CASCADE"), nullable=False
    )
    membership_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("memberships.id", ondelete="CASCADE"), nullable=False
    )
    wins: Mapped[int] = mapped_column(nullable=False, default=0)
    losses: Mapped[int] = mapped_column(nullable=False, default=0)
    current_streak: Mapped[int] = mapped_column(nullable=False, default=0)
    best_streak: Mapped[int] = mapped_column(nullable=False, default=0)
    total_matches: Mapped[int] = mapped_column(nullable=False, default=0)
    avg_tools_used: Mapped[float] = mapped_column(nullable=False, default=0.0)
    avg_match_duration_sec: Mapped[float] = mapped_column(nullable=False, default=0.0)
    elo_rating: Mapped[int | None] = mapped_column()
    updated_at: Mapped[datetime] = mapped_column(default=now_riyadh_naive, onupdate=now_riyadh_naive)


class MinigamePolicyRule(Base):
    __tablename__ = "minigame_policy_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    game_type: Mapped[str | None] = mapped_column(String(64))
    competition_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("competitions.id", ondelete="CASCADE")
    )
    scope: Mapped[str] = mapped_column(String(30), nullable=False)
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    limit_value: Mapped[int] = mapped_column(nullable=False)
    window: Mapped[str] = mapped_column(String(20), nullable=False)
    enabled: Mapped[bool] = mapped_column(nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(default=now_riyadh_naive)
    updated_at: Mapped[datetime] = mapped_column(default=now_riyadh_naive, onupdate=now_riyadh_naive)
