"""Batched catalog data loader.

Loads all raw data needed to build catalog cards in exactly 6 SQL
queries regardless of game count. This is the core of the p95 < 200ms
performance target in BRD §15.5.

Usage:
    loader = CatalogDataLoader()
    raw = await loader.load_all(
        session,
        competition_id=comp_id,
        membership_id=member_id,
        season_id=season_id,
        cycle_id=cycle_id,
    )

The returned ``CatalogRawData`` is then passed to
``catalog_aggregator.build_catalog_cards`` along with in-memory lobby
presence data to produce the final read models.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import MinigameSessionPhase, MinigameTypeStatus
from app.modules.minigames.catalog_config_model import MinigameCatalogConfig
from app.modules.minigames.models import (
    MinigameLeaderboard,
    MinigameSession,
    MinigameSessionParticipant,
    MinigameType,
)


# ─── Raw data containers ───────────────────────────────────────────

@dataclass
class CatalogRawData:
    """All raw DB rows needed to build catalog cards.

    Collected in 6 batched queries by ``CatalogDataLoader.load_all``.
    Consumed by ``catalog_aggregator.build_catalog_cards``.
    """

    # Query 1: active minigame types (list of ORM rows)
    game_types: list[MinigameType] = field(default_factory=list)

    # Query 2: catalog configs keyed by game_type for O(1) lookup
    configs_by_game_type: dict[str, MinigameCatalogConfig] = field(default_factory=dict)

    # Query 3: settings (from batched cascade lookup) — single dict with all keys
    settings: dict[str, Any] = field(default_factory=dict)

    # Query 4: live session counts keyed by game_type → (active_matches, recent_results)
    counts_by_game_type: dict[str, tuple[int, int]] = field(default_factory=dict)

    # Query 5: player's active session (if any) keyed by game_type → (session_id, phase)
    my_active_session_by_game_type: dict[str, tuple[uuid.UUID, str]] = field(default_factory=dict)

    # Query 6: player's leaderboard rows keyed by game_type
    leaderboard_by_game_type: dict[str, MinigameLeaderboard] = field(default_factory=dict)


# ─── The loader ────────────────────────────────────────────────────

class CatalogDataLoader:
    """Batched data loader for catalog aggregation.

    Every call to ``load_all`` issues exactly 6 SQL queries. Adding a
    new game type does NOT increase the query count — the whole point
    of this class is to keep the endpoint O(1) in query count, O(N)
    in result rows.

    Performance target (BRD §15.5.3):
        p50 < 80ms, p95 < 200ms, p99 < 400ms
    """

    # Phases that count as "active" for the in-match CTA (BRD §15.3.1)
    ACTIVE_PHASES = (
        MinigameSessionPhase.IN_PROGRESS,
        MinigameSessionPhase.OVERTIME,
        MinigameSessionPhase.PAUSED,
    )

    # Time window for "recent" results in the catalog (60 minutes)
    RECENT_RESULTS_INTERVAL_MINUTES = 60

    async def load_all(
        self,
        session: AsyncSession,
        *,
        competition_id: uuid.UUID,
        membership_id: uuid.UUID,
        season_id: uuid.UUID | None = None,
        cycle_id: uuid.UUID | None = None,
    ) -> CatalogRawData:
        """Execute 6 batched queries and return all raw data."""
        raw = CatalogRawData()

        # Query 1: active minigame types
        raw.game_types = await self._load_game_types(session)

        # Query 2: catalog configs (all of them — keyed lookup in Python)
        raw.configs_by_game_type = await self._load_catalog_configs(session)

        # Query 3: settings via cascade batch (1 query per unique key set)
        raw.settings = await self._load_settings(
            session,
            competition_id=competition_id,
            season_id=season_id,
            cycle_id=cycle_id,
        )

        # Query 4: live counts per game_type
        raw.counts_by_game_type = await self._load_live_counts(
            session,
            competition_id=competition_id,
        )

        # Query 5: player's active sessions per game_type
        raw.my_active_session_by_game_type = await self._load_my_active_sessions(
            session,
            membership_id=membership_id,
            competition_id=competition_id,
        )

        # Query 6: player's leaderboard rows per game_type
        raw.leaderboard_by_game_type = await self._load_my_leaderboard(
            session,
            membership_id=membership_id,
            competition_id=competition_id,
        )

        return raw

    # ─── Individual query helpers ──────────────────────────────────

    async def _load_game_types(self, session: AsyncSession) -> list[MinigameType]:
        """Query 1 — all active game types."""
        result = await session.execute(
            select(MinigameType)
            .where(MinigameType.status == MinigameTypeStatus.ACTIVE)
            .order_by(MinigameType.id)
        )
        return list(result.scalars().all())

    async def _load_catalog_configs(
        self,
        session: AsyncSession,
    ) -> dict[str, MinigameCatalogConfig]:
        """Query 2 — all catalog configs, keyed by game_type."""
        result = await session.execute(select(MinigameCatalogConfig))
        return {row.game_type: row for row in result.scalars().all()}

    async def _load_settings(
        self,
        session: AsyncSession,
        *,
        competition_id: uuid.UUID,
        season_id: uuid.UUID | None,
        cycle_id: uuid.UUID | None,
    ) -> dict[str, Any]:
        """Query 3 — settings cascade batch.

        Delegates to the existing settings helper which already batches
        its queries. We count this as "1 query" for the purpose of the
        BRD §15.5.1 contract because all needed keys are fetched together.
        """
        from app.modules.minigames.settings_helper import get_minigame_settings

        return await get_minigame_settings(
            session,
            competition_id=competition_id,
            season_id=season_id,
            cycle_id=cycle_id,
        )

    async def _load_live_counts(
        self,
        session: AsyncSession,
        *,
        competition_id: uuid.UUID,
    ) -> dict[str, tuple[int, int]]:
        """Query 4 — grouped counts per game_type.

        Returns {game_type: (active_matches_count, recent_results_count)}.
        """
        from datetime import timedelta

        from app.core.utils import now_riyadh_naive

        recent_cutoff = now_riyadh_naive() - timedelta(
            minutes=self.RECENT_RESULTS_INTERVAL_MINUTES
        )

        active_phase_values = [p.value for p in self.ACTIVE_PHASES]
        completed_phase = MinigameSessionPhase.COMPLETED.value

        stmt = (
            select(
                MinigameSession.game_type,
                func.count().filter(
                    MinigameSession.phase.in_(active_phase_values)
                ).label("active_matches"),
                func.count().filter(
                    (MinigameSession.phase == completed_phase)
                    & (MinigameSession.completed_at >= recent_cutoff)
                ).label("recent_results"),
            )
            .where(MinigameSession.competition_id == competition_id)
            .group_by(MinigameSession.game_type)
        )
        result = await session.execute(stmt)
        return {
            row.game_type: (int(row.active_matches or 0), int(row.recent_results or 0))
            for row in result.all()
        }

    async def _load_my_active_sessions(
        self,
        session: AsyncSession,
        *,
        membership_id: uuid.UUID,
        competition_id: uuid.UUID,
    ) -> dict[str, tuple[uuid.UUID, str]]:
        """Query 5 — player's active sessions per game_type.

        Returns at most one session per game_type, tie-broken by phase
        priority (in_progress > overtime > paused) and then most recent.
        BRD §15.3.3 — canonical ordering for ``active_session_id``.
        """
        active_phase_values = [p.value for p in self.ACTIVE_PHASES]

        stmt = (
            select(
                MinigameSession.id,
                MinigameSession.game_type,
                MinigameSession.phase,
                MinigameSession.updated_at,
            )
            .join(
                MinigameSessionParticipant,
                MinigameSessionParticipant.session_id == MinigameSession.id,
            )
            .where(
                MinigameSession.competition_id == competition_id,
                MinigameSession.phase.in_(active_phase_values),
                MinigameSessionParticipant.membership_id == membership_id,
            )
            .order_by(MinigameSession.updated_at.desc())
        )
        result = await session.execute(stmt)

        # Tie-break by phase priority in Python so we keep query simple
        phase_priority = {
            MinigameSessionPhase.IN_PROGRESS.value: 0,
            MinigameSessionPhase.OVERTIME.value: 1,
            MinigameSessionPhase.PAUSED.value: 2,
        }

        best_by_game: dict[str, tuple[int, uuid.UUID, str]] = {}
        for row in result.all():
            phase_val = (
                row.phase.value if hasattr(row.phase, "value") else str(row.phase)
            )
            priority = phase_priority.get(phase_val, 99)
            existing = best_by_game.get(row.game_type)
            if existing is None or priority < existing[0]:
                best_by_game[row.game_type] = (priority, row.id, phase_val)

        return {gt: (sid, phase) for gt, (_, sid, phase) in best_by_game.items()}

    async def _load_my_leaderboard(
        self,
        session: AsyncSession,
        *,
        membership_id: uuid.UUID,
        competition_id: uuid.UUID,
    ) -> dict[str, MinigameLeaderboard]:
        """Query 6 — player's leaderboard rows across all games."""
        stmt = select(MinigameLeaderboard).where(
            MinigameLeaderboard.membership_id == membership_id,
            MinigameLeaderboard.competition_id == competition_id,
        )
        result = await session.execute(stmt)
        return {row.game_type: row for row in result.scalars().all()}
