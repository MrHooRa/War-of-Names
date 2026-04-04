"""
Minigame Leaderboard Service.

Responsibilities:
  - Compute updated player stats after each match (wins, losses, streaks, averages)
  - Upsert MinigameLeaderboard rows after settlement
  - Query ranked leaderboard for a given game type + competition

Public surface:
  compute_updated_stats()  — pure, synchronous, fully testable
  update_leaderboard()     — async, requires SQLAlchemy AsyncSession
  get_leaderboard()        — async, requires SQLAlchemy AsyncSession
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession


# ─── Pure logic ──────────────────────────────────────────────────────────────

def compute_updated_stats(
    *,
    current: dict,
    is_win: bool | None = None,
    placement: int | None = None,
    num_players: int = 2,
    tools_used: int = 0,
    duration_sec: float = 0.0,
) -> dict:
    """Compute updated leaderboard stats after a single match result.

    Args:
        current:      Existing stat dict. Missing keys default to 0 / 0.0.
        is_win:       Legacy 2-player binary (True=win, False=loss). Used if placement is None.
        placement:    1-based rank (1=first, 2=second, etc.). Takes priority over is_win.
                      For N-player games, only placement=1 counts as a "win".
        num_players:  Total players in the match (reserved for future weighted scoring).
        tools_used:   Number of tools used during the match.
        duration_sec: Match duration in seconds.

    Returns:
        New stat dict with all fields updated.
    """
    # Resolve win/loss from placement (if provided) or is_win
    if placement is not None:
        is_win_resolved = (placement == 1)
    elif is_win is not None:
        is_win_resolved = is_win
    else:
        raise ValueError("Either is_win or placement must be provided")

    wins = current.get("wins", 0)
    losses = current.get("losses", 0)
    current_streak = current.get("current_streak", 0)
    best_streak = current.get("best_streak", 0)
    total_matches = current.get("total_matches", 0)
    avg_tools_used = current.get("avg_tools_used", 0.0)
    avg_match_duration_sec = current.get("avg_match_duration_sec", 0.0)

    prev_count = total_matches  # count before this match
    total_matches += 1

    if is_win_resolved:
        wins += 1
        current_streak += 1
        best_streak = max(best_streak, current_streak)
    else:
        losses += 1
        current_streak = 0
        # best_streak is unchanged on a loss

    # Running averages: new_avg = (old_avg * prev_count + new_value) / total_matches
    new_avg_tools = (avg_tools_used * prev_count + tools_used) / total_matches
    new_avg_duration = (avg_match_duration_sec * prev_count + duration_sec) / total_matches

    return {
        "wins": wins,
        "losses": losses,
        "current_streak": current_streak,
        "best_streak": best_streak,
        "total_matches": total_matches,
        "avg_tools_used": round(new_avg_tools, 2),
        "avg_match_duration_sec": round(new_avg_duration, 2),
    }


# ─── Async DB functions ───────────────────────────────────────────────────────

async def update_leaderboard(
    session: AsyncSession,
    *,
    game_type: str,
    competition_id: uuid.UUID,
    membership_id: uuid.UUID,
    is_win: bool,
    tools_used: int = 0,
    duration_sec: float = 0.0,
) -> None:
    """Upsert a MinigameLeaderboard row with the latest match result.

    If no row exists for (game_type, competition_id, membership_id), a new
    one is created starting from an empty stat baseline.
    """
    from sqlalchemy import select

    from app.modules.minigames.models import MinigameLeaderboard

    stmt = select(MinigameLeaderboard).where(
        MinigameLeaderboard.game_type == game_type,
        MinigameLeaderboard.competition_id == competition_id,
        MinigameLeaderboard.membership_id == membership_id,
    )
    result = await session.execute(stmt)
    entry = result.scalar_one_or_none()

    if entry is None:
        current: dict = {}
        updated = compute_updated_stats(
            current=current,
            is_win=is_win,
            tools_used=tools_used,
            duration_sec=duration_sec,
        )
        entry = MinigameLeaderboard(
            game_type=game_type,
            competition_id=competition_id,
            membership_id=membership_id,
            **updated,
        )
        session.add(entry)
    else:
        current = {
            "wins": entry.wins,
            "losses": entry.losses,
            "current_streak": entry.current_streak,
            "best_streak": entry.best_streak,
            "total_matches": entry.total_matches,
            "avg_tools_used": entry.avg_tools_used,
            "avg_match_duration_sec": entry.avg_match_duration_sec,
        }
        updated = compute_updated_stats(
            current=current,
            is_win=is_win,
            tools_used=tools_used,
            duration_sec=duration_sec,
        )
        for field, value in updated.items():
            setattr(entry, field, value)


async def get_leaderboard(
    session: AsyncSession,
    *,
    game_type: str,
    competition_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
) -> list:
    """Return ranked leaderboard entries for a game type + competition.

    Ordering: wins DESC, best_streak DESC, avg_tools_used ASC.

    Args:
        session:        Async SQLAlchemy session.
        game_type:      Minigame type identifier.
        competition_id: Competition UUID.
        limit:          Max rows to return (default 50).
        offset:         Pagination offset (default 0).

    Returns:
        List of MinigameLeaderboard ORM instances.
    """
    from sqlalchemy import select

    from app.modules.minigames.models import MinigameLeaderboard

    stmt = (
        select(MinigameLeaderboard)
        .where(
            MinigameLeaderboard.game_type == game_type,
            MinigameLeaderboard.competition_id == competition_id,
        )
        .order_by(
            MinigameLeaderboard.wins.desc(),
            MinigameLeaderboard.best_streak.desc(),
            MinigameLeaderboard.avg_tools_used.asc(),
        )
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())
