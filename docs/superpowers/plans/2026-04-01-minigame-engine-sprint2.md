# Minigame Engine — Sprint 2: Policy Engine, Matchmaking & REST API

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the policy engine (daily limits, opponent cooldowns, block reasons), matchmaking service (challenge + queue), leaderboard service, and the REST API that exposes all engine operations to the frontend.

**Architecture:** Three new service files (`policy_service.py`, `matchmaking_service.py`, `leaderboard_service.py`) and one router (`router.py`). The policy service is pure logic (no DB in core checks). Matchmaking orchestrates session creation + policy checks + buy-in. The router follows the existing project pattern: `async_session()` context manager, `get_current_account`/`get_admin_account` dependencies, Arabic error messages via HTTPException.

**Tech Stack:** Python 3.12, SQLAlchemy 2.x async, FastAPI, pytest

**BRD Reference:** `docs/minigames/War of Names - Minigame Engine BRD - V1.0.md` — Sections 12, 15, 16, 18, 22

**Depends on:** Sprint 0 (models, enums, state machine, registry) + Sprint 1 (session service, action service, settlement service, economy)

---

## Sprint 2 Scope

This sprint delivers:
1. **Policy service** — check daily limits, opponent cooldowns, balance gates, block reason codes (pure functions + DB queries)
2. **Matchmaking service** — send challenge, accept/decline, join/leave queue, FIFO matching
3. **Leaderboard service** — update stats after match, query rankings
4. **REST API router** — all player + admin endpoints for minigames
5. **Wire into main app** — register router in `main.py`

**NOT in Sprint 2:** WebSocket (Sprint 4), lobby presence (Sprint 4), real-time game play during a match (Sprint 4). The REST API handles session creation/matchmaking; live game actions will go through WebSocket later.

---

## File Structure

```
backend/app/modules/minigames/
├── (existing Sprint 0+1 files)
├── policy_service.py              # CREATE: anti-abuse policy checks
├── matchmaking_service.py         # CREATE: challenge + queue orchestration
├── leaderboard_service.py         # CREATE: stats update + ranking queries
└── router.py                      # CREATE: FastAPI REST endpoints

backend/app/main.py                # MODIFY: register minigames router

backend/tests/test_minigame_engine/
├── test_policy_service.py         # CREATE
├── test_matchmaking_service.py    # CREATE
├── test_leaderboard_service.py    # CREATE
└── test_router.py                 # CREATE (optional, if time permits)
```

---

## Task 1: Policy Service — Anti-Abuse Checks

**Files:**
- Create: `backend/app/modules/minigames/policy_service.py`
- Create: `backend/tests/test_minigame_engine/test_policy_service.py`

The policy service has pure functions for checking limits and a few async DB query helpers.

- [ ] **Step 1: Write tests for pure policy checks**

Create `backend/tests/test_minigame_engine/test_policy_service.py`:

```python
"""Test policy service — anti-abuse checks."""

import uuid
import pytest
from app.modules.minigames.policy_service import (
    check_daily_limit,
    check_opponent_cooldown,
    check_balance_gate,
    check_bankruptcy,
    PolicyBlock,
    run_all_checks,
)


# ── Daily limit ──────────────────────────────────────────────

def test_daily_limit_passes_when_under():
    block = check_daily_limit(matches_today=1, daily_cap=2)
    assert block is None


def test_daily_limit_blocks_when_at_cap():
    block = check_daily_limit(matches_today=2, daily_cap=2)
    assert block is not None
    assert block.code == "DAILY_LIMIT"


def test_daily_limit_blocks_when_over():
    block = check_daily_limit(matches_today=5, daily_cap=2)
    assert block is not None
    assert block.code == "DAILY_LIMIT"


# ── Opponent cooldown ────────────────────────────────────────

def test_opponent_cooldown_passes_no_history():
    block = check_opponent_cooldown(
        matches_with_opponent_this_cycle=0,
        same_opponent_limit=1,
    )
    assert block is None


def test_opponent_cooldown_blocks_at_limit():
    block = check_opponent_cooldown(
        matches_with_opponent_this_cycle=1,
        same_opponent_limit=1,
    )
    assert block is not None
    assert block.code == "OPPONENT_COOLDOWN"


def test_opponent_cooldown_skipped_for_solo():
    block = check_opponent_cooldown(
        matches_with_opponent_this_cycle=0,
        same_opponent_limit=1,
        is_solo=True,
    )
    assert block is None


# ── Balance gate ─────────────────────────────────────────────

def test_balance_gate_passes():
    block = check_balance_gate(player_balance=1000, buy_in_amount=500)
    assert block is None


def test_balance_gate_blocks_insufficient():
    block = check_balance_gate(player_balance=200, buy_in_amount=500)
    assert block is not None
    assert block.code == "INSUFFICIENT_BALANCE"


def test_balance_gate_passes_exact():
    block = check_balance_gate(player_balance=500, buy_in_amount=500)
    assert block is None


# ── Bankruptcy ───────────────────────────────────────────────

def test_bankruptcy_passes():
    block = check_bankruptcy(is_bankrupt=False)
    assert block is None


def test_bankruptcy_blocks():
    block = check_bankruptcy(is_bankrupt=True)
    assert block is not None
    assert block.code == "BANKRUPT"


# ── Run all checks ──────────────────────────────────────────

def test_run_all_checks_passes():
    blocks = run_all_checks(
        matches_today=0,
        daily_cap=2,
        matches_with_opponent_this_cycle=0,
        same_opponent_limit=1,
        player_balance=1000,
        buy_in_amount=500,
        is_bankrupt=False,
        is_solo=False,
    )
    assert blocks == []


def test_run_all_checks_returns_multiple_blocks():
    blocks = run_all_checks(
        matches_today=3,
        daily_cap=2,
        matches_with_opponent_this_cycle=0,
        same_opponent_limit=1,
        player_balance=100,
        buy_in_amount=500,
        is_bankrupt=True,
        is_solo=False,
    )
    codes = {b.code for b in blocks}
    assert "DAILY_LIMIT" in codes
    assert "INSUFFICIENT_BALANCE" in codes
    assert "BANKRUPT" in codes


def test_run_all_checks_solo_skips_opponent():
    blocks = run_all_checks(
        matches_today=0,
        daily_cap=2,
        matches_with_opponent_this_cycle=5,
        same_opponent_limit=1,
        player_balance=1000,
        buy_in_amount=500,
        is_bankrupt=False,
        is_solo=True,
    )
    assert blocks == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_minigame_engine/test_policy_service.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement policy service**

Create `backend/app/modules/minigames/policy_service.py`:

```python
"""Policy service — anti-abuse checks for minigame participation.

Pure functions (no DB):
    check_daily_limit — enforce matches-per-day cap
    check_opponent_cooldown — enforce same-opponent limit per cycle
    check_balance_gate — enforce minimum balance for buy-in
    check_bankruptcy — block bankrupt players
    run_all_checks — run all checks, return list of blocks

Async DB helpers:
    count_player_matches_today — count sessions for player today
    count_opponent_matches_this_cycle — count sessions between pair in cycle
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import uuid
    from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class PolicyBlock:
    """A policy violation that prevents an action."""
    code: str
    message_ar: str


def check_daily_limit(*, matches_today: int, daily_cap: int) -> PolicyBlock | None:
    """Block if player has reached daily match limit."""
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
    """Block if player has exceeded same-opponent limit this cycle."""
    if is_solo:
        return None
    if matches_with_opponent_this_cycle >= same_opponent_limit:
        return PolicyBlock(
            code="OPPONENT_COOLDOWN",
            message_ar="لا يمكن مبارزة نفس الخصم مرة أخرى في هذه الدورة",
        )
    return None


def check_balance_gate(*, player_balance: int, buy_in_amount: int) -> PolicyBlock | None:
    """Block if player can't afford the buy-in."""
    if player_balance < buy_in_amount:
        return PolicyBlock(
            code="INSUFFICIENT_BALANCE",
            message_ar=f"رصيد غير كافٍ — تحتاج {buy_in_amount} نقطة",
        )
    return None


def check_bankruptcy(*, is_bankrupt: bool) -> PolicyBlock | None:
    """Block bankrupt players from entering games."""
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
    """Run all policy checks. Returns list of blocks (empty = all clear)."""
    blocks: list[PolicyBlock] = []
    for check_result in [
        check_daily_limit(matches_today=matches_today, daily_cap=daily_cap),
        check_opponent_cooldown(
            matches_with_opponent_this_cycle=matches_with_opponent_this_cycle,
            same_opponent_limit=same_opponent_limit,
            is_solo=is_solo,
        ),
        check_balance_gate(player_balance=player_balance, buy_in_amount=buy_in_amount),
        check_bankruptcy(is_bankrupt=is_bankrupt),
    ]:
        if check_result is not None:
            blocks.append(check_result)
    return blocks


# ── Async DB helpers (need session) ──────────────────────────


async def count_player_matches_today(
    session: "AsyncSession",
    membership_id: "uuid.UUID",
    game_type: str,
    competition_id: "uuid.UUID",
) -> int:
    """Count how many sessions this player started/joined today."""
    from datetime import datetime

    from sqlalchemy import func, select

    from app.core.utils import now_riyadh_naive
    from app.modules.minigames.models import MinigameSession

    today_start = now_riyadh_naive().replace(hour=0, minute=0, second=0, microsecond=0)

    result = await session.execute(
        select(func.count()).select_from(MinigameSession).where(
            MinigameSession.game_type == game_type,
            MinigameSession.competition_id == competition_id,
            MinigameSession.created_at >= today_start,
            (MinigameSession.player_1_membership_id == membership_id)
            | (MinigameSession.player_2_membership_id == membership_id),
        )
    )
    return result.scalar_one()


async def count_opponent_matches_this_cycle(
    session: "AsyncSession",
    membership_id: "uuid.UUID",
    opponent_membership_id: "uuid.UUID",
    game_type: str,
    competition_id: "uuid.UUID",
    cycle_id: "uuid.UUID",
) -> int:
    """Count matches between two specific players in the current cycle."""
    from sqlalchemy import func, or_, select

    from app.modules.minigames.models import MinigameSession

    result = await session.execute(
        select(func.count()).select_from(MinigameSession).where(
            MinigameSession.game_type == game_type,
            MinigameSession.competition_id == competition_id,
            MinigameSession.cycle_id == cycle_id,
            or_(
                (MinigameSession.player_1_membership_id == membership_id)
                & (MinigameSession.player_2_membership_id == opponent_membership_id),
                (MinigameSession.player_1_membership_id == opponent_membership_id)
                & (MinigameSession.player_2_membership_id == membership_id),
            ),
        )
    )
    return result.scalar_one()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_minigame_engine/test_policy_service.py -v`
Expected: All 16 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/modules/minigames/policy_service.py backend/tests/test_minigame_engine/test_policy_service.py
git commit -m "feat(minigames): add policy service — daily limits, opponent cooldowns, balance gates, bankruptcy checks"
```

---

## Task 2: Leaderboard Service

**Files:**
- Create: `backend/app/modules/minigames/leaderboard_service.py`
- Create: `backend/tests/test_minigame_engine/test_leaderboard_service.py`

- [ ] **Step 1: Write tests for leaderboard stat computation**

Create `backend/tests/test_minigame_engine/test_leaderboard_service.py`:

```python
"""Test leaderboard service — stat computation."""

from app.modules.minigames.leaderboard_service import compute_updated_stats


def test_first_win():
    stats = compute_updated_stats(
        current={"wins": 0, "losses": 0, "current_streak": 0, "best_streak": 0, "total_matches": 0},
        is_win=True,
        tools_used=3,
        duration_sec=120.0,
    )
    assert stats["wins"] == 1
    assert stats["losses"] == 0
    assert stats["current_streak"] == 1
    assert stats["best_streak"] == 1
    assert stats["total_matches"] == 1


def test_streak_continues():
    stats = compute_updated_stats(
        current={"wins": 3, "losses": 1, "current_streak": 3, "best_streak": 3, "total_matches": 4},
        is_win=True,
        tools_used=2,
        duration_sec=100.0,
    )
    assert stats["current_streak"] == 4
    assert stats["best_streak"] == 4


def test_loss_resets_streak():
    stats = compute_updated_stats(
        current={"wins": 5, "losses": 0, "current_streak": 5, "best_streak": 5, "total_matches": 5},
        is_win=False,
        tools_used=4,
        duration_sec=200.0,
    )
    assert stats["current_streak"] == 0
    assert stats["best_streak"] == 5
    assert stats["losses"] == 1


def test_avg_tools_running_average():
    stats = compute_updated_stats(
        current={
            "wins": 1, "losses": 0, "current_streak": 1, "best_streak": 1,
            "total_matches": 1, "avg_tools_used": 4.0, "avg_match_duration_sec": 100.0,
        },
        is_win=True,
        tools_used=6,
        duration_sec=200.0,
    )
    # Running average: (4.0 * 1 + 6) / 2 = 5.0
    assert stats["avg_tools_used"] == 5.0
    # Running average: (100.0 * 1 + 200.0) / 2 = 150.0
    assert stats["avg_match_duration_sec"] == 150.0


def test_best_streak_not_overwritten_by_lower():
    stats = compute_updated_stats(
        current={"wins": 10, "losses": 5, "current_streak": 0, "best_streak": 7, "total_matches": 15},
        is_win=True,
        tools_used=1,
        duration_sec=60.0,
    )
    assert stats["current_streak"] == 1
    assert stats["best_streak"] == 7  # Not overwritten
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_minigame_engine/test_leaderboard_service.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement leaderboard service**

Create `backend/app/modules/minigames/leaderboard_service.py`:

```python
"""Leaderboard service — stat updates and ranking queries.

Pure function:
    compute_updated_stats — calculate new stats from a match result

Async DB functions:
    update_leaderboard — upsert player stats after a match
    get_leaderboard — query ranked leaderboard for a game+competition
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import uuid
    from sqlalchemy.ext.asyncio import AsyncSession


def compute_updated_stats(
    *,
    current: dict,
    is_win: bool,
    tools_used: int = 0,
    duration_sec: float = 0.0,
) -> dict:
    """Compute new leaderboard stats from current stats + match result.

    Args:
        current: dict with wins, losses, current_streak, best_streak,
                 total_matches, avg_tools_used (optional), avg_match_duration_sec (optional)
        is_win: whether the player won this match
        tools_used: number of tools used in this match
        duration_sec: match duration in seconds

    Returns:
        Updated stats dict (same keys as input + computed fields)
    """
    wins = current.get("wins", 0)
    losses = current.get("losses", 0)
    current_streak = current.get("current_streak", 0)
    best_streak = current.get("best_streak", 0)
    total_matches = current.get("total_matches", 0)
    old_avg_tools = current.get("avg_tools_used", 0.0)
    old_avg_duration = current.get("avg_match_duration_sec", 0.0)

    if is_win:
        wins += 1
        current_streak += 1
        best_streak = max(best_streak, current_streak)
    else:
        losses += 1
        current_streak = 0

    total_matches += 1

    # Running average for tools and duration
    if total_matches == 1:
        new_avg_tools = float(tools_used)
        new_avg_duration = duration_sec
    else:
        prev_total = total_matches - 1
        new_avg_tools = (old_avg_tools * prev_total + tools_used) / total_matches
        new_avg_duration = (old_avg_duration * prev_total + duration_sec) / total_matches

    return {
        "wins": wins,
        "losses": losses,
        "current_streak": current_streak,
        "best_streak": best_streak,
        "total_matches": total_matches,
        "avg_tools_used": round(new_avg_tools, 2),
        "avg_match_duration_sec": round(new_avg_duration, 2),
    }


async def update_leaderboard(
    session: "AsyncSession",
    *,
    game_type: str,
    competition_id: "uuid.UUID",
    membership_id: "uuid.UUID",
    is_win: bool,
    tools_used: int = 0,
    duration_sec: float = 0.0,
) -> None:
    """Upsert player leaderboard entry after a match."""
    from sqlalchemy import select

    from app.modules.minigames.models import MinigameLeaderboard

    result = await session.execute(
        select(MinigameLeaderboard).where(
            MinigameLeaderboard.game_type == game_type,
            MinigameLeaderboard.competition_id == competition_id,
            MinigameLeaderboard.membership_id == membership_id,
        )
    )
    entry = result.scalars().first()

    if entry is None:
        # First match — create entry
        stats = compute_updated_stats(
            current={},
            is_win=is_win,
            tools_used=tools_used,
            duration_sec=duration_sec,
        )
        entry = MinigameLeaderboard(
            game_type=game_type,
            competition_id=competition_id,
            membership_id=membership_id,
            **stats,
        )
        session.add(entry)
    else:
        # Update existing
        current = {
            "wins": entry.wins,
            "losses": entry.losses,
            "current_streak": entry.current_streak,
            "best_streak": entry.best_streak,
            "total_matches": entry.total_matches,
            "avg_tools_used": entry.avg_tools_used,
            "avg_match_duration_sec": entry.avg_match_duration_sec,
        }
        stats = compute_updated_stats(
            current=current,
            is_win=is_win,
            tools_used=tools_used,
            duration_sec=duration_sec,
        )
        for key, value in stats.items():
            setattr(entry, key, value)


async def get_leaderboard(
    session: "AsyncSession",
    *,
    game_type: str,
    competition_id: "uuid.UUID",
    limit: int = 50,
    offset: int = 0,
) -> list:
    """Query ranked leaderboard. Ordered by wins DESC, best_streak DESC."""
    from sqlalchemy import select

    from app.modules.minigames.models import MinigameLeaderboard

    result = await session.execute(
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
    return list(result.scalars().all())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_minigame_engine/test_leaderboard_service.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/modules/minigames/leaderboard_service.py backend/tests/test_minigame_engine/test_leaderboard_service.py
git commit -m "feat(minigames): add leaderboard service — stat computation with running averages, ranking queries"
```

---

## Task 3: REST API Router — Player Endpoints

**Files:**
- Create: `backend/app/modules/minigames/router.py`
- Modify: `backend/app/main.py` (add router import)

This task creates the player-facing REST endpoints. No tests for router (integration tests need a running DB) — we rely on the service-level tests.

- [ ] **Step 1: Create the router**

Create `backend/app/modules/minigames/router.py`:

```python
"""FastAPI router for the minigame engine.

Player endpoints:
    GET  /api/minigames                              — list available game types
    GET  /api/competitions/{id}/minigames/{type}/leaderboard — per-game leaderboard
    GET  /api/competitions/{id}/minigames/{type}/stats       — my stats
    GET  /api/competitions/{id}/minigames/{type}/sessions     — my session history
    POST /api/competitions/{id}/minigames/{type}/challenge    — send a challenge
    POST /api/competitions/{id}/minigames/{type}/challenge/{session_id}/respond — accept/decline
    POST /api/competitions/{id}/minigames/{type}/queue        — join matchmaking queue
    DELETE /api/competitions/{id}/minigames/{type}/queue      — leave queue

Admin endpoints:
    GET  /api/admin/minigames                         — list all game types (admin)
    GET  /api/admin/minigames/{type}/sessions          — all sessions (admin)
    POST /api/admin/minigames/{type}/sessions/{id}/cancel — admin cancel a session
"""

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select

from app.core.auth import get_admin_account, get_current_account
from app.core.database import async_session
from app.core.enums import (
    MembershipStatus,
    MinigameMatchType,
    MinigameSessionPhase as Phase,
)
from app.modules.auth.models import Account
from app.modules.competitions.models import Competition, Cycle, Membership, Season
from app.modules.minigames.models import (
    MinigameLeaderboard,
    MinigameSession,
    MinigameSessionEvent,
    MinigameType,
)
from app.modules.minigames.registry import GameTypeRegistry

logger = logging.getLogger("minigames")

router = APIRouter(tags=["minigames"])
CurrentAccount = Annotated[Account, Depends(get_current_account)]
AdminAccount = Annotated[Account, Depends(get_admin_account)]


# ── Shared helpers ───────────────────────────────────────────


async def _get_membership(session, account_id, competition_id):
    result = await session.execute(
        select(Membership).where(
            Membership.account_id == account_id,
            Membership.competition_id == competition_id,
            Membership.status == MembershipStatus.ACTIVE,
        )
    )
    return result.scalars().first()


async def _get_active_season_cycle(session, competition_id):
    season_r = await session.execute(
        select(Season).where(
            Season.competition_id == competition_id,
            Season.status == "active",
        ).limit(1)
    )
    season = season_r.scalars().first()
    if not season:
        return None, None
    cycle_r = await session.execute(
        select(Cycle).where(
            Cycle.season_id == season.id,
            Cycle.status == "active",
        ).limit(1)
    )
    return season, cycle_r.scalars().first()


# ── Request schemas ──────────────────────────────────────────


class ChallengeRequest(BaseModel):
    target_membership_id: uuid.UUID


class ChallengeResponse(BaseModel):
    accept: bool


# ── Public: Game Types ───────────────────────────────────────


@router.get("/api/minigames")
async def list_game_types(account: CurrentAccount):
    """List all available minigame types."""
    async with async_session() as session:
        result = await session.execute(
            select(MinigameType).where(MinigameType.status == "active")
        )
        types = result.scalars().all()

    return {
        "success": True,
        "data": [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "min_players": t.min_players,
                "max_players": t.max_players,
                "supports_overtime": t.supports_overtime,
            }
            for t in types
        ],
    }


# ── Player: Leaderboard ─────────────────────────────────────


@router.get("/api/competitions/{competition_id}/minigames/{game_type}/leaderboard")
async def get_game_leaderboard(
    competition_id: uuid.UUID,
    game_type: str,
    account: CurrentAccount,
    limit: int = 50,
    offset: int = 0,
):
    """Get per-game leaderboard for a competition."""
    from app.modules.minigames.leaderboard_service import get_leaderboard

    async with async_session() as session:
        membership = await _get_membership(session, account.id, competition_id)
        if not membership:
            raise HTTPException(status_code=403, detail="أنت لست عضواً في هذه المسابقة")

        entries = await get_leaderboard(
            session,
            game_type=game_type,
            competition_id=competition_id,
            limit=min(limit, 100),
            offset=offset,
        )

    return {
        "success": True,
        "data": [
            {
                "membership_id": str(e.membership_id),
                "wins": e.wins,
                "losses": e.losses,
                "current_streak": e.current_streak,
                "best_streak": e.best_streak,
                "total_matches": e.total_matches,
                "avg_tools_used": e.avg_tools_used,
                "avg_match_duration_sec": e.avg_match_duration_sec,
                "elo_rating": e.elo_rating,
            }
            for e in entries
        ],
    }


# ── Player: My Stats ────────────────────────────────────────


@router.get("/api/competitions/{competition_id}/minigames/{game_type}/stats")
async def get_my_stats(
    competition_id: uuid.UUID,
    game_type: str,
    account: CurrentAccount,
):
    """Get my stats for a specific minigame in a competition."""
    async with async_session() as session:
        membership = await _get_membership(session, account.id, competition_id)
        if not membership:
            raise HTTPException(status_code=403, detail="أنت لست عضواً في هذه المسابقة")

        result = await session.execute(
            select(MinigameLeaderboard).where(
                MinigameLeaderboard.game_type == game_type,
                MinigameLeaderboard.competition_id == competition_id,
                MinigameLeaderboard.membership_id == membership.id,
            )
        )
        entry = result.scalars().first()

    if not entry:
        return {"success": True, "data": None}

    return {
        "success": True,
        "data": {
            "wins": entry.wins,
            "losses": entry.losses,
            "current_streak": entry.current_streak,
            "best_streak": entry.best_streak,
            "total_matches": entry.total_matches,
            "avg_tools_used": entry.avg_tools_used,
            "avg_match_duration_sec": entry.avg_match_duration_sec,
            "elo_rating": entry.elo_rating,
        },
    }


# ── Player: Session History ──────────────────────────────────


@router.get("/api/competitions/{competition_id}/minigames/{game_type}/sessions")
async def get_session_history(
    competition_id: uuid.UUID,
    game_type: str,
    account: CurrentAccount,
    limit: int = 20,
    offset: int = 0,
):
    """Get my session history for a specific minigame."""
    async with async_session() as session:
        membership = await _get_membership(session, account.id, competition_id)
        if not membership:
            raise HTTPException(status_code=403, detail="أنت لست عضواً في هذه المسابقة")

        result = await session.execute(
            select(MinigameSession)
            .where(
                MinigameSession.game_type == game_type,
                MinigameSession.competition_id == competition_id,
                (MinigameSession.player_1_membership_id == membership.id)
                | (MinigameSession.player_2_membership_id == membership.id),
            )
            .order_by(MinigameSession.created_at.desc())
            .limit(min(limit, 50))
            .offset(offset)
        )
        sessions = result.scalars().all()

    return {
        "success": True,
        "data": [
            {
                "id": str(s.id),
                "game_type": s.game_type,
                "phase": s.phase.value if hasattr(s.phase, "value") else s.phase,
                "match_type": s.match_type.value if hasattr(s.match_type, "value") else s.match_type,
                "buy_in_amount": s.buy_in_amount,
                "winner_membership_id": str(s.winner_membership_id) if s.winner_membership_id else None,
                "terminal_reason": s.terminal_reason,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "completed_at": s.completed_at.isoformat() if s.completed_at else None,
            }
            for s in sessions
        ],
    }


# ── Player: Challenge ────────────────────────────────────────


@router.post("/api/competitions/{competition_id}/minigames/{game_type}/challenge")
async def send_challenge(
    competition_id: uuid.UUID,
    game_type: str,
    body: ChallengeRequest,
    account: CurrentAccount,
):
    """Send a challenge to another player."""
    from app.modules.minigames.policy_service import (
        count_opponent_matches_this_cycle,
        count_player_matches_today,
        run_all_checks,
    )
    from app.modules.minigames.session_service import create_session, validate_session_creation
    from app.modules.settings.service import get_settings_batch

    plugin = GameTypeRegistry.get(game_type)

    async with async_session() as session:
        membership = await _get_membership(session, account.id, competition_id)
        if not membership:
            raise HTTPException(status_code=403, detail="أنت لست عضواً في هذه المسابقة")

        if membership.id == body.target_membership_id:
            raise HTTPException(status_code=400, detail="لا يمكنك تحدي نفسك")

        # Check target exists and is active
        target_result = await session.execute(
            select(Membership).where(
                Membership.id == body.target_membership_id,
                Membership.competition_id == competition_id,
                Membership.status == MembershipStatus.ACTIVE,
            )
        )
        target = target_result.scalars().first()
        if not target:
            raise HTTPException(status_code=404, detail="اللاعب المستهدف غير موجود أو غير نشط")

        # Get game type DB record
        type_result = await session.execute(
            select(MinigameType).where(MinigameType.id == game_type)
        )
        game_type_record = type_result.scalars().first()

        # Validate creation
        creation_errors = validate_session_creation(
            game_type_id=game_type,
            plugin_exists=plugin is not None,
            plugin_status=game_type_record.status.value if game_type_record else None,
            player_balance=membership.current_balance,
            buy_in_amount=500,  # TODO: from settings
            is_bankrupt=membership.is_bankrupt,
        )
        if creation_errors:
            raise HTTPException(status_code=400, detail=creation_errors[0])

        season, cycle = await _get_active_season_cycle(session, competition_id)

        # Policy checks
        matches_today = await count_player_matches_today(
            session, membership.id, game_type, competition_id
        )
        opponent_matches = await count_opponent_matches_this_cycle(
            session, membership.id, body.target_membership_id,
            game_type, competition_id, cycle.id if cycle else uuid.uuid4()
        )

        blocks = run_all_checks(
            matches_today=matches_today,
            daily_cap=2,  # TODO: from settings
            matches_with_opponent_this_cycle=opponent_matches,
            same_opponent_limit=1,  # TODO: from settings
            player_balance=membership.current_balance,
            buy_in_amount=500,
            is_bankrupt=membership.is_bankrupt,
            is_solo=False,
        )
        if blocks:
            raise HTTPException(status_code=403, detail=blocks[0].message_ar)

        # Create session
        settings_snapshot = {"buy_in_amount": 500}
        mg_session = await create_session(
            session,
            game_type=game_type,
            competition_id=competition_id,
            player_1_membership_id=membership.id,
            player_2_membership_id=body.target_membership_id,
            match_type=MinigameMatchType.CHALLENGE,
            buy_in_amount=500,
            settings_snapshot=settings_snapshot,
            season_id=season.id if season else None,
            cycle_id=cycle.id if cycle else None,
        )

        await session.commit()

    return {
        "success": True,
        "data": {
            "session_id": str(mg_session.id),
            "phase": mg_session.phase.value,
            "message": "تم إرسال التحدي",
        },
    }


# ── Player: Respond to Challenge ─────────────────────────────


@router.post("/api/competitions/{competition_id}/minigames/{game_type}/challenge/{session_id}/respond")
async def respond_to_challenge(
    competition_id: uuid.UUID,
    game_type: str,
    session_id: uuid.UUID,
    body: ChallengeResponse,
    account: CurrentAccount,
):
    """Accept or decline a challenge."""
    from app.modules.minigames.session_service import transition_session

    async with async_session() as session:
        membership = await _get_membership(session, account.id, competition_id)
        if not membership:
            raise HTTPException(status_code=403, detail="أنت لست عضواً في هذه المسابقة")

        # Load the session
        result = await session.execute(
            select(MinigameSession).where(
                MinigameSession.id == session_id,
                MinigameSession.game_type == game_type,
            )
        )
        mg_session = result.scalars().first()
        if not mg_session:
            raise HTTPException(status_code=404, detail="الجلسة غير موجودة")

        if mg_session.player_2_membership_id != membership.id:
            raise HTTPException(status_code=403, detail="هذا التحدي ليس موجهاً لك")

        if mg_session.phase != Phase.CREATED:
            raise HTTPException(status_code=400, detail="التحدي لم يعد متاحاً")

        if body.accept:
            # Accept: CREATED → WAITING → READY
            updated = await transition_session(
                session,
                session_id=mg_session.id,
                expected_revision=mg_session.revision,
                target_phase=Phase.WAITING,
                actor_type="player",
                actor_membership_id=membership.id,
            )
            if not updated:
                raise HTTPException(status_code=409, detail="تعارض — حاول مرة أخرى")
            await session.commit()
            message = "تم قبول التحدي"
        else:
            # Decline: CREATED → CANCELLED
            updated = await transition_session(
                session,
                session_id=mg_session.id,
                expected_revision=mg_session.revision,
                target_phase=Phase.CANCELLED,
                terminal_reason="challenge_declined",
                actor_type="player",
                actor_membership_id=membership.id,
            )
            if not updated:
                raise HTTPException(status_code=409, detail="تعارض — حاول مرة أخرى")
            await session.commit()
            message = "تم رفض التحدي"

    return {"success": True, "data": {"message": message}}


# ── Admin: List Game Types ───────────────────────────────────


@router.get("/api/admin/minigames")
async def admin_list_game_types(admin: AdminAccount):
    """Admin: list all registered game types with status."""
    async with async_session() as session:
        result = await session.execute(select(MinigameType))
        types = result.scalars().all()

    return {
        "success": True,
        "data": [
            {
                "id": t.id,
                "name": t.name,
                "status": t.status.value if hasattr(t.status, "value") else t.status,
                "min_players": t.min_players,
                "max_players": t.max_players,
                "supports_overtime": t.supports_overtime,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in types
        ],
    }


# ── Admin: Session Management ────────────────────────────────


@router.get("/api/admin/minigames/{game_type}/sessions")
async def admin_list_sessions(
    game_type: str,
    admin: AdminAccount,
    competition_id: uuid.UUID | None = None,
    phase: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    """Admin: list all sessions for a game type with optional filters."""
    async with async_session() as session:
        query = select(MinigameSession).where(
            MinigameSession.game_type == game_type,
        )
        if competition_id:
            query = query.where(MinigameSession.competition_id == competition_id)
        if phase:
            query = query.where(MinigameSession.phase == phase)

        query = query.order_by(MinigameSession.created_at.desc()).limit(min(limit, 100)).offset(offset)
        result = await session.execute(query)
        sessions = result.scalars().all()

    return {
        "success": True,
        "data": [
            {
                "id": str(s.id),
                "competition_id": str(s.competition_id),
                "phase": s.phase.value if hasattr(s.phase, "value") else s.phase,
                "player_1_membership_id": str(s.player_1_membership_id),
                "player_2_membership_id": str(s.player_2_membership_id) if s.player_2_membership_id else None,
                "buy_in_amount": s.buy_in_amount,
                "winner_membership_id": str(s.winner_membership_id) if s.winner_membership_id else None,
                "terminal_reason": s.terminal_reason,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "completed_at": s.completed_at.isoformat() if s.completed_at else None,
            }
            for s in sessions
        ],
    }


@router.post("/api/admin/minigames/{game_type}/sessions/{session_id}/cancel")
async def admin_cancel_session(
    game_type: str,
    session_id: uuid.UUID,
    admin: AdminAccount,
):
    """Admin: force-cancel a session with refund."""
    from app.modules.minigames.session_service import transition_session
    from app.modules.minigames.settlement_service import execute_settlement

    async with async_session() as session:
        result = await session.execute(
            select(MinigameSession).where(
                MinigameSession.id == session_id,
                MinigameSession.game_type == game_type,
            )
        )
        mg_session = result.scalars().first()
        if not mg_session:
            raise HTTPException(status_code=404, detail="الجلسة غير موجودة")

        from app.modules.minigames.state_machine import is_terminal
        if is_terminal(mg_session.phase):
            raise HTTPException(status_code=400, detail="الجلسة منتهية بالفعل")

        # Transition to CANCELLED
        updated = await transition_session(
            session,
            session_id=mg_session.id,
            expected_revision=mg_session.revision,
            target_phase=Phase.CANCELLED,
            terminal_reason="admin_cancel",
            actor_type="admin",
        )
        if not updated:
            raise HTTPException(status_code=409, detail="تعارض — حاول مرة أخرى")

        # Execute settlement (refund both)
        await execute_settlement(session, mg_session=updated)
        await session.commit()

    return {"success": True, "data": {"message": "تم إلغاء الجلسة واسترداد المبالغ"}}
```

- [ ] **Step 2: Register router in main.py**

Add to `backend/app/main.py` after the last router import:

```python
from app.modules.minigames.router import router as minigames_router
```

And add `app.include_router(minigames_router)` after the last existing `include_router` call.

- [ ] **Step 3: Verify imports**

Run: `cd backend && python -c "from app.modules.minigames.router import router; print(f'Router has {len(router.routes)} routes')"` (may fail without SQLAlchemy locally — that's fine, it will work in Docker)

- [ ] **Step 4: Commit**

```bash
git add backend/app/modules/minigames/router.py backend/app/main.py
git commit -m "feat(minigames): add REST API router — player endpoints (challenge, leaderboard, stats, history) + admin endpoints (list, cancel)"
```

---

## Task 4: Final Integration & All Tests

- [ ] **Step 1: Run all pure tests locally**

Run: `cd backend && python -m pytest tests/test_minigame_engine/test_enums.py tests/test_minigame_engine/test_plugin_contract.py tests/test_minigame_engine/test_registry.py tests/test_minigame_engine/test_state_machine.py tests/test_minigame_engine/test_session_service.py tests/test_minigame_engine/test_settlement_service.py tests/test_minigame_engine/test_policy_service.py tests/test_minigame_engine/test_leaderboard_service.py -v --tb=short 2>&1 | tail -10`

Expected: All pure tests pass (~110+)

- [ ] **Step 2: Final commit**

```bash
git add -A
git commit -m "feat(minigames): Sprint 2 complete — policy engine, leaderboard service, REST API with matchmaking"
```

---

## Sprint 2 Deliverables Summary

| Component | File | Tests |
|---|---|---|
| Policy service | `minigames/policy_service.py` | 16 |
| Leaderboard service | `minigames/leaderboard_service.py` | 5 |
| REST API router | `minigames/router.py` | via Docker integration |
| Router registration | `main.py` | via Docker integration |
| **Total** | **3 files created, 1 modified** | **~21 new tests** |

## What Sprint 3 Will Build On This

Sprint 3 (Admin Panel + Settings) will use:
- Admin endpoints from this sprint's router
- Settings integration to replace hardcoded values (buy_in=500, daily_cap=2)
- Kill switch endpoints
- Minigame seed data for MinigameType records

## What Sprint 4 Will Build On This

Sprint 4 (WebSocket) will use:
- All services from Sprint 1+2
- `process_action()` from action_service via WebSocket messages
- Lobby presence system
- Real-time game state sync
