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
# TODO(sprint-b): N-player refactor — count_player_matches_today and
# count_opponent_matches_this_cycle still filter on the removed
# MinigameSession.player_1_membership_id / player_2_membership_id columns.
# Sprint B will rewrite these queries to join through
# MinigameSessionParticipant so they work for any num_players. Pure check_*
# helpers above are unaffected.


async def count_player_matches_today(
    session: AsyncSession,
    membership_id: uuid.UUID,
    game_type: str,
    competition_id: uuid.UUID,
) -> int:
    """Return how many matches the player has started or joined today.

    "Today" is defined as midnight (00:00:00) in Asia/Riyadh time up to the
    current moment.  The query counts any session where the player appears as
    either ``player_1_membership_id`` or ``player_2_membership_id``.
    """
    from sqlalchemy import func, or_, select  # noqa: PLC0415

    from app.core.utils import now_riyadh_naive  # noqa: PLC0415
    from app.modules.minigames.models import MinigameSession  # noqa: PLC0415

    now = now_riyadh_naive()
    today_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)

    stmt = (
        select(func.count())
        .select_from(MinigameSession)
        .where(
            MinigameSession.game_type == game_type,
            MinigameSession.competition_id == competition_id,
            MinigameSession.created_at >= today_midnight,
            or_(
                MinigameSession.player_1_membership_id == membership_id,
                MinigameSession.player_2_membership_id == membership_id,
            ),
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

    The check is symmetric: it does not matter which player was player_1 and
    which was player_2.
    """
    from sqlalchemy import func, or_, select  # noqa: PLC0415
    from sqlalchemy import and_  # noqa: PLC0415

    from app.modules.minigames.models import MinigameSession  # noqa: PLC0415

    mg = MinigameSession

    # Match where (p1=membership AND p2=opponent) OR (p1=opponent AND p2=membership)
    pair_condition = or_(
        and_(
            mg.player_1_membership_id == membership_id,
            mg.player_2_membership_id == opponent_membership_id,
        ),
        and_(
            mg.player_1_membership_id == opponent_membership_id,
            mg.player_2_membership_id == membership_id,
        ),
    )

    stmt = (
        select(func.count())
        .select_from(mg)
        .where(
            mg.game_type == game_type,
            mg.competition_id == competition_id,
            mg.cycle_id == cycle_id,
            pair_condition,
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one()
