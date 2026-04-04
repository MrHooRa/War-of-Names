"""Minigame policy service — pre-game eligibility checks.

Pure functions (sync, no DB) are defined first for easy unit testing.
Async functions that touch the database follow.

Import strategy: only ``dataclasses`` and stdlib are imported at module level.
Everything that pulls in SQLAlchemy or app internals is deferred to the
function body so that pure-function tests can import this module without a
running application environment.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


# ---------------------------------------------------------------------------
# Policy result dataclass
# ---------------------------------------------------------------------------


@dataclass
class PolicyBlock:
    """Represents a failed policy check that blocks a player from entering a match."""

    code: str
    message_ar: str


# ---------------------------------------------------------------------------
# Pure check functions (sync, no DB, no app imports)
# ---------------------------------------------------------------------------


def check_daily_limit(*, matches_today: int, daily_cap: int) -> PolicyBlock | None:
    """Block if the player has reached or exceeded their daily match cap.

    Returns a :class:`PolicyBlock` when the limit is hit, otherwise ``None``.
    """
    if matches_today >= daily_cap:
        return PolicyBlock(
            code="DAILY_LIMIT",
            message_ar=f"وصلت للحد اليومي ({daily_cap} مباريات)",
        )
    return None


def check_opponent_cooldown(
    *,
    matches_with_opponent_this_cycle: int,
    same_opponent_limit: int,
    is_solo: bool = False,
) -> PolicyBlock | None:
    """Block if the player has already reached the per-cycle cap against this opponent.

    Skipped entirely for solo (practice) sessions where there is no second
    player — pass ``is_solo=True`` to bypass.
    """
    if is_solo:
        return None
    if matches_with_opponent_this_cycle >= same_opponent_limit:
        return PolicyBlock(
            code="OPPONENT_COOLDOWN",
            message_ar="لا يمكن مبارزة نفس الخصم مرة أخرى في هذه الدورة",
        )
    return None


def check_balance_gate(*, player_balance: int, buy_in_amount: int) -> PolicyBlock | None:
    """Block if the player cannot afford the match buy-in.

    Returns ``None`` when the balance is exactly equal to the buy-in — the
    player has enough to cover the cost.
    """
    if player_balance < buy_in_amount:
        return PolicyBlock(
            code="INSUFFICIENT_BALANCE",
            message_ar=f"رصيد غير كافٍ — تحتاج {buy_in_amount} نقطة",
        )
    return None


def check_bankruptcy(*, is_bankrupt: bool) -> PolicyBlock | None:
    """Block a bankrupt player from entering any match."""
    if is_bankrupt:
        return PolicyBlock(
            code="BANKRUPT",
            message_ar="لا يمكنك الدخول في مبارزة وأنت مفلس",
        )
    return None


def run_all_checks(
    *,
    matches_today: int,
    daily_cap: int,
    matches_with_opponent_this_cycle: int,
    same_opponent_limit: int,
    player_balance: int,
    buy_in_amount: int,
    is_bankrupt: bool,
    is_solo: bool = False,
) -> list[PolicyBlock]:
    """Run all four policy checks and return every block that fires.

    The returned list is empty when all checks pass. Callers should treat
    a non-empty list as a rejection and surface the ``message_ar`` values to
    the player.

    Check order:
    1. Daily match limit
    2. Per-cycle opponent cooldown (skipped for solo)
    3. Balance gate
    4. Bankruptcy
    """
    blocks: list[PolicyBlock] = []

    result = check_daily_limit(matches_today=matches_today, daily_cap=daily_cap)
    if result is not None:
        blocks.append(result)

    result = check_opponent_cooldown(
        matches_with_opponent_this_cycle=matches_with_opponent_this_cycle,
        same_opponent_limit=same_opponent_limit,
        is_solo=is_solo,
    )
    if result is not None:
        blocks.append(result)

    result = check_balance_gate(player_balance=player_balance, buy_in_amount=buy_in_amount)
    if result is not None:
        blocks.append(result)

    result = check_bankruptcy(is_bankrupt=is_bankrupt)
    if result is not None:
        blocks.append(result)

    return blocks


# ---------------------------------------------------------------------------
# Async DB helpers (all SQLAlchemy imports deferred to function body)
# ---------------------------------------------------------------------------
#
# These helpers support N-player minigames (2-8 participants per session).
# Participants live in the ``minigame_session_participants`` table, so both
# queries join through ``MinigameSessionParticipant`` and use
# SELECT COUNT(DISTINCT session.id) to avoid double-counting sessions where
# a player appears in multiple rows of the join.


async def count_player_matches_today(
    session: AsyncSession,
    membership_id: uuid.UUID,
    game_type: str,
    competition_id: uuid.UUID,
) -> int:
    """Return how many matches the player has started or joined today.

    "Today" is defined as midnight (00:00:00) in Asia/Riyadh time up to the
    current moment. Counts any session where the player appears as a participant
    regardless of slot index.
    """
    from sqlalchemy import func, select  # noqa: PLC0415

    from app.core.utils import now_riyadh_naive  # noqa: PLC0415
    from app.modules.minigames.models import (  # noqa: PLC0415
        MinigameSession,
        MinigameSessionParticipant,
    )

    now = now_riyadh_naive()
    today_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)

    stmt = (
        select(func.count(func.distinct(MinigameSession.id)))
        .select_from(MinigameSession)
        .join(
            MinigameSessionParticipant,
            MinigameSessionParticipant.session_id == MinigameSession.id,
        )
        .where(
            MinigameSession.game_type == game_type,
            MinigameSession.competition_id == competition_id,
            MinigameSession.created_at >= today_midnight,
            MinigameSessionParticipant.membership_id == membership_id,
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one()


async def count_opponent_matches_this_cycle(
    session: AsyncSession,
    membership_id: uuid.UUID,
    opponent_membership_id: uuid.UUID,
    game_type: str,
    competition_id: uuid.UUID,
    cycle_id: uuid.UUID,
) -> int:
    """Return the number of times these two players have faced each other in the cycle.

    Counts sessions where both players are participants, regardless of their slot
    assignments. Works for any num_players (2-8) — if both players are in the same
    session, it counts once.
    """
    from sqlalchemy import func, select  # noqa: PLC0415
    from sqlalchemy.orm import aliased  # noqa: PLC0415

    from app.modules.minigames.models import (  # noqa: PLC0415
        MinigameSession,
        MinigameSessionParticipant,
    )

    # Self-join the participants table: one alias for "me", one for "opponent"
    me = aliased(MinigameSessionParticipant)
    opponent = aliased(MinigameSessionParticipant)

    stmt = (
        select(func.count(func.distinct(MinigameSession.id)))
        .select_from(MinigameSession)
        .join(me, me.session_id == MinigameSession.id)
        .join(opponent, opponent.session_id == MinigameSession.id)
        .where(
            MinigameSession.game_type == game_type,
            MinigameSession.competition_id == competition_id,
            MinigameSession.cycle_id == cycle_id,
            me.membership_id == membership_id,
            opponent.membership_id == opponent_membership_id,
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one()
