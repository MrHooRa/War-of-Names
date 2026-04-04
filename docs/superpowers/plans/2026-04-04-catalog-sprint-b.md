# Catalog & Lobby — Sprint B: Aggregation Service

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the catalog aggregation service that transforms raw DB rows + in-memory lobby state into catalog card read models. The core deliverable is `get_catalog()` which executes exactly 6 SQL queries regardless of game count, meeting the p95 < 200ms target.

**Architecture:** Split into pure helpers (testable with zero deps) and async DB-backed services. Pure helpers handle all the business logic: label formatting, CTA resolution, duration source selection, and card assembly. The async layer is a thin adapter that loads raw data via a `CatalogDataLoader` (6 batched queries) and passes it to the pure `build_catalog_cards()` aggregator.

**Tech Stack:** Python 3.12, SQLAlchemy 2.x async, pytest. NO new dependencies.

**BRD Reference:** `docs/minigames/War of Names - Minigames Catalog & Lobby BRD - V1.0.md` — §7.1, §8.1-8.2, §9, §10.1.1, §14, §15 (entire section), §18.1

**Depends on:** Sprint A complete (catalog_config_model, catalog_config_resolver, enums)

---

## Sprint Scope

1. **Pure helpers** — 3 small modules with zero DB dependencies:
   - `build_player_count_label()` — BRD §9.1 rule
   - `resolve_card_status()` — BRD §15.4 priority chain
   - `resolve_estimated_duration()` — BRD §8.1.1 source resolution
2. **Read model dataclasses** — typed structures for card + lobby responses
3. **`CatalogDataLoader`** — async class with `load_all()` that issues exactly 6 SQL queries
4. **`build_catalog_cards()`** — pure aggregator that merges raw data into read models
5. **`get_catalog()`** — async orchestrator (loader + aggregator + lobby snapshot)
6. **`get_lobby_detail()`** — async service for single-game lobby page read model

**NOT in Sprint B:** REST endpoints (Sprint C), WebSocket broadcast (Sprint D), Frontend (Sprint E).

---

## File Structure

```
backend/app/modules/minigames/
├── catalog_helpers.py                     # CREATE: 3 pure functions
├── catalog_read_model.py                  # CREATE: dataclasses for read models
├── catalog_data_loader.py                 # CREATE: 6-query batched loader
├── catalog_aggregator.py                  # CREATE: pure build_catalog_cards
├── catalog_service.py                     # CREATE: get_catalog + get_lobby_detail
└── (existing files unchanged)

backend/tests/test_minigame_engine/
├── test_catalog_helpers.py                # CREATE
├── test_catalog_read_model.py             # CREATE
└── test_catalog_aggregator.py             # CREATE
```

**No files modified** — Sprint B is purely additive. Existing router/services are untouched.

---

## Task 1: Pure Helpers — Labels, Status, Duration

**Files:**
- Create: `backend/app/modules/minigames/catalog_helpers.py`
- Create: `backend/tests/test_minigame_engine/test_catalog_helpers.py`

Three pure functions that encapsulate the business rules from BRD §9.1, §15.4, and §8.1.1.

- [ ] **Step 1: Write tests**

Create `backend/tests/test_minigame_engine/test_catalog_helpers.py`:

```python
"""Tests for catalog helper pure functions.

All functions are stateless, no DB, no async. These tests cover every
branch of BRD §9.1, §15.4, and §8.1.1.
"""

import pytest

from app.modules.minigames.catalog_helpers import (
    build_player_count_label,
    resolve_card_status,
    resolve_estimated_duration,
)


# ── build_player_count_label (BRD §9.1) ────────────────────────────

class TestPlayerCountLabel:
    def test_1v1(self):
        assert build_player_count_label(2, 2) == "1v1"

    def test_solo(self):
        assert build_player_count_label(1, 1) == "منفرد"

    def test_fixed_four(self):
        assert build_player_count_label(4, 4) == "4 لاعبين"

    def test_fixed_six(self):
        assert build_player_count_label(6, 6) == "6 لاعبين"

    def test_range_2_to_4(self):
        assert build_player_count_label(2, 4) == "2-4 لاعبين"

    def test_range_3_to_8(self):
        assert build_player_count_label(3, 8) == "3-8 لاعبين"

    def test_invalid_min_greater_than_max_returns_empty(self):
        assert build_player_count_label(5, 2) == ""

    def test_invalid_zero_returns_empty(self):
        assert build_player_count_label(0, 0) == ""

    def test_invalid_negative_returns_empty(self):
        assert build_player_count_label(-1, 2) == ""


# ── resolve_card_status (BRD §15.4) ────────────────────────────────

class TestResolveCardStatus:
    def _base(self, **overrides):
        defaults = dict(
            availability_mode="active",
            kill_switch_level="off",
            my_active_session_id=None,
            in_queue=False,
            player_balance=1000,
            buy_in_amount=500,
            is_bankrupt=False,
        )
        defaults.update(overrides)
        return defaults

    def test_playable_default(self):
        status, reason = resolve_card_status(**self._base())
        assert status == "playable"
        assert reason is None

    def test_in_match_beats_everything(self):
        """BRD §15.4 priority 1 — in_match trumps all other statuses."""
        status, reason = resolve_card_status(
            **self._base(
                my_active_session_id="00000000-0000-0000-0000-000000000001",
                in_queue=True,
                player_balance=0,
                is_bankrupt=True,
            )
        )
        assert status == "in_match"
        assert reason is None

    def test_queued_beats_balance_and_availability(self):
        """BRD §15.4 priority 2 — queued trumps balance/maintenance/coming_soon."""
        status, reason = resolve_card_status(
            **self._base(in_queue=True, player_balance=0, is_bankrupt=True)
        )
        assert status == "queued"

    def test_insufficient_balance(self):
        status, reason = resolve_card_status(
            **self._base(player_balance=200, buy_in_amount=500)
        )
        assert status == "insufficient_balance"
        assert "500" in (reason or "")

    def test_bankrupt_treated_as_insufficient_balance(self):
        status, reason = resolve_card_status(**self._base(is_bankrupt=True))
        assert status == "insufficient_balance"

    def test_exact_balance_is_playable(self):
        status, _ = resolve_card_status(
            **self._base(player_balance=500, buy_in_amount=500)
        )
        assert status == "playable"

    def test_maintenance_availability(self):
        status, reason = resolve_card_status(
            **self._base(availability_mode="maintenance")
        )
        assert status == "maintenance"
        assert reason is not None

    def test_kill_switch_emergency_treated_as_maintenance(self):
        status, _ = resolve_card_status(**self._base(kill_switch_level="emergency"))
        assert status == "maintenance"

    def test_kill_switch_hard_treated_as_maintenance(self):
        status, _ = resolve_card_status(**self._base(kill_switch_level="hard"))
        assert status == "maintenance"

    def test_coming_soon_availability(self):
        status, _ = resolve_card_status(**self._base(availability_mode="coming_soon"))
        assert status == "coming_soon"

    def test_hidden_availability(self):
        status, _ = resolve_card_status(**self._base(availability_mode="hidden"))
        assert status == "hidden"


# ── resolve_estimated_duration (BRD §8.1.1) ─────────────────────────

class TestResolveEstimatedDuration:
    def test_stats_with_enough_matches(self):
        duration, source = resolve_estimated_duration(
            leaderboard_avg_sec=285.5,
            leaderboard_match_count=42,
            config_duration_sec=300,
        )
        assert duration == 285  # rounded down
        assert source == "stats"

    def test_stats_with_exactly_ten_matches_uses_stats(self):
        duration, source = resolve_estimated_duration(
            leaderboard_avg_sec=310.0,
            leaderboard_match_count=10,
            config_duration_sec=300,
        )
        assert duration == 310
        assert source == "stats"

    def test_stats_with_fewer_than_ten_matches_falls_back_to_config(self):
        duration, source = resolve_estimated_duration(
            leaderboard_avg_sec=100.0,
            leaderboard_match_count=9,
            config_duration_sec=300,
        )
        assert duration == 300
        assert source == "config"

    def test_null_stats_falls_back_to_config(self):
        duration, source = resolve_estimated_duration(
            leaderboard_avg_sec=None,
            leaderboard_match_count=0,
            config_duration_sec=300,
        )
        assert duration == 300
        assert source == "config"

    def test_null_both_returns_none(self):
        duration, source = resolve_estimated_duration(
            leaderboard_avg_sec=None,
            leaderboard_match_count=0,
            config_duration_sec=None,
        )
        assert duration is None
        assert source is None

    def test_zero_config_treated_as_missing(self):
        duration, source = resolve_estimated_duration(
            leaderboard_avg_sec=None,
            leaderboard_match_count=0,
            config_duration_sec=0,
        )
        assert duration is None
        assert source is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_minigame_engine/test_catalog_helpers.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.modules.minigames.catalog_helpers'`

- [ ] **Step 3: Implement the helpers**

Create `backend/app/modules/minigames/catalog_helpers.py`:

```python
"""Pure helper functions for catalog aggregation.

All functions in this module are stateless, synchronous, and have zero
database or async dependencies. They encode the business rules from
BRD §9.1, §15.4, and §8.1.1.
"""

from __future__ import annotations

# BRD §8.1.1 — leaderboard needs ≥10 matches before its average is trusted
LEADERBOARD_STATS_MIN_MATCHES = 10

# Kill-switch levels that block new session creation (BRD §16.3)
KILL_SWITCH_BLOCKING_LEVELS = frozenset({"hard", "emergency"})

# Availability modes that hide the card from players (BRD §10.1.1)
CARD_LOCKED_AVAILABILITY_MODES = frozenset({"maintenance", "coming_soon", "hidden"})


# ─── Player count label (BRD §9.1) ─────────────────────────────────

def build_player_count_label(min_players: int, max_players: int) -> str:
    """Return the human-readable player-count badge text.

    BRD §9.1 rules:
        min == max == 1                → "منفرد"
        min == max == 2                → "1v1"
        min == max (other)             → "{N} لاعبين"
        min != max                     → "{min}-{max} لاعبين"
        invalid (min>max or <=0)       → "" (caller must hide CTA)
    """
    if min_players <= 0 or max_players <= 0:
        return ""
    if min_players > max_players:
        return ""

    if min_players == max_players:
        if min_players == 1:
            return "منفرد"
        if min_players == 2:
            return "1v1"
        return f"{min_players} لاعبين"

    return f"{min_players}-{max_players} لاعبين"


# ─── Card status resolution (BRD §15.4) ────────────────────────────

def resolve_card_status(
    *,
    availability_mode: str,
    kill_switch_level: str,
    my_active_session_id: str | None,
    in_queue: bool,
    player_balance: int,
    buy_in_amount: int,
    is_bankrupt: bool,
) -> tuple[str, str | None]:
    """Determine the status and optional Arabic reason for a game card.

    Returns (status, availability_reason). BRD §15.4 priority order:
        1. in_match    → player has active session, always wins
        2. queued      → player in matchmaking queue
        3. insufficient_balance → bankrupt or balance < buy_in
        4. maintenance → hard/emergency kill switch OR availability_mode=maintenance
        5. coming_soon → availability_mode=coming_soon
        6. hidden      → availability_mode=hidden (caller filters out)
        7. playable    → default

    Note: insufficient_balance takes priority over maintenance/coming_soon
    because the kill switch doesn't help a player who can't afford anyway.
    """
    # Priority 1: active session
    if my_active_session_id is not None:
        return ("in_match", None)

    # Priority 2: queued
    if in_queue:
        return ("queued", None)

    # Priority 3: insufficient balance / bankrupt
    if is_bankrupt or player_balance < buy_in_amount:
        return (
            "insufficient_balance",
            f"رصيد غير كافٍ — تحتاج {buy_in_amount} نقطة للدخول",
        )

    # Priority 4: maintenance (kill switch or config)
    if kill_switch_level in KILL_SWITCH_BLOCKING_LEVELS:
        return ("maintenance", "صيانة مؤقتة — نرجع قريباً")
    if availability_mode == "maintenance":
        return ("maintenance", "صيانة مؤقتة — نرجع قريباً")

    # Priority 5: coming soon
    if availability_mode == "coming_soon":
        return ("coming_soon", None)

    # Priority 6: hidden (surface filters this out but we still return it)
    if availability_mode == "hidden":
        return ("hidden", None)

    # Default
    return ("playable", None)


# ─── Estimated duration resolution (BRD §8.1.1) ─────────────────────

def resolve_estimated_duration(
    *,
    leaderboard_avg_sec: float | None,
    leaderboard_match_count: int,
    config_duration_sec: int | None,
) -> tuple[int | None, str | None]:
    """Return (duration_sec, source) using the priority chain in BRD §8.1.1.

    Priority:
        1. leaderboard stats — if avg is set AND match_count >= 10
        2. catalog config    — if configured and positive
        3. null              — no estimate available

    Source strings: "stats", "config", or None.
    """
    if (
        leaderboard_avg_sec is not None
        and leaderboard_avg_sec > 0
        and leaderboard_match_count >= LEADERBOARD_STATS_MIN_MATCHES
    ):
        return (int(leaderboard_avg_sec), "stats")

    if config_duration_sec is not None and config_duration_sec > 0:
        return (config_duration_sec, "config")

    return (None, None)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_minigame_engine/test_catalog_helpers.py -v`
Expected: All ~26 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd "e:/Salman/مشاريع/War of Names" && git add backend/app/modules/minigames/catalog_helpers.py backend/tests/test_minigame_engine/test_catalog_helpers.py && git commit -m "feat(catalog): pure helpers — player count label, card status resolver, duration resolver

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Read Model Dataclasses

**Files:**
- Create: `backend/app/modules/minigames/catalog_read_model.py`
- Create: `backend/tests/test_minigame_engine/test_catalog_read_model.py`

Typed Python dataclasses matching the JSON read models in BRD §8.1 and §8.2.
These are plain stdlib dataclasses — no Pydantic (not needed for internal
responses, and we want to keep pure tests dependency-free).

- [ ] **Step 1: Write tests**

Create `backend/tests/test_minigame_engine/test_catalog_read_model.py`:

```python
"""Tests for catalog read model dataclasses.

Verifies shape, defaults, and serialization helpers.
"""

import uuid
from datetime import datetime

from app.modules.minigames.catalog_read_model import (
    CatalogCard,
    CatalogMyState,
    CatalogMyStats,
    CatalogResponse,
    LobbyPageResponse,
    catalog_card_to_dict,
    catalog_response_to_dict,
)


def _sample_card(**overrides):
    base = dict(
        game_type="mutaraha",
        name="مطارحة",
        short_description="مبارزة كلمات 1v1",
        description="خمّن كلمات خصمك قبل ما يخمّن كلماتك",
        icon="lucide:swords",
        accent_color="#D84315",
        hero_variant="duel",
        card_variant="standard",
        min_players=2,
        max_players=2,
        player_count_label="1v1",
        estimated_duration_sec=300,
        estimated_duration_source="stats",
        buy_in_amount=500,
        status="playable",
        availability_reason=None,
        expected_launch_at=None,
        presence_count=3,
        queue_count=1,
        active_matches_count=1,
        recent_results_count=5,
        supports_overtime=True,
        supports_spectators=False,
        supports_ranked=False,
        supports_team_mode=False,
        featured=True,
        sort_order=10,
        correlation_id=str(uuid.uuid4()),
        my_state=CatalogMyState(
            queued=False,
            in_active_match=False,
            active_session_id=None,
            active_session_phase=None,
        ),
        my_stats=CatalogMyStats(
            wins=5,
            losses=2,
            current_streak=3,
            best_streak=4,
            total_matches=7,
            win_rate=0.714,
            has_history=True,
        ),
    )
    base.update(overrides)
    return CatalogCard(**base)


class TestCatalogCard:
    def test_construction_with_all_fields(self):
        card = _sample_card()
        assert card.game_type == "mutaraha"
        assert card.player_count_label == "1v1"
        assert card.my_stats.has_history is True

    def test_my_state_defaults(self):
        state = CatalogMyState()
        assert state.queued is False
        assert state.in_active_match is False
        assert state.active_session_id is None
        assert state.active_session_phase is None

    def test_my_stats_empty_player_defaults(self):
        stats = CatalogMyStats()
        assert stats.wins == 0
        assert stats.losses == 0
        assert stats.total_matches == 0
        assert stats.win_rate == 0.0
        assert stats.has_history is False


class TestSerializationHelpers:
    def test_catalog_card_to_dict_includes_all_fields(self):
        card = _sample_card()
        d = catalog_card_to_dict(card)
        assert d["game_type"] == "mutaraha"
        assert d["player_count_label"] == "1v1"
        assert d["my_state"]["queued"] is False
        assert d["my_stats"]["wins"] == 5
        assert d["my_stats"]["has_history"] is True

    def test_catalog_card_to_dict_with_active_session_phase(self):
        card = _sample_card(
            my_state=CatalogMyState(
                queued=False,
                in_active_match=True,
                active_session_id="00000000-0000-0000-0000-000000000001",
                active_session_phase="in_progress",
            )
        )
        d = catalog_card_to_dict(card)
        assert d["my_state"]["in_active_match"] is True
        assert d["my_state"]["active_session_phase"] == "in_progress"

    def test_catalog_card_to_dict_with_expected_launch_at(self):
        when = datetime(2026, 6, 1, 0, 0, 0)
        card = _sample_card(expected_launch_at=when, status="coming_soon")
        d = catalog_card_to_dict(card)
        assert d["expected_launch_at"] == "2026-06-01T00:00:00"

    def test_catalog_card_to_dict_expected_launch_at_null(self):
        card = _sample_card()
        d = catalog_card_to_dict(card)
        assert d["expected_launch_at"] is None

    def test_catalog_response_to_dict(self):
        card = _sample_card()
        cid = str(uuid.uuid4())
        resp = CatalogResponse(correlation_id=cid, games=[card])
        d = catalog_response_to_dict(resp)
        assert d["correlation_id"] == cid
        assert len(d["games"]) == 1
        assert d["games"][0]["game_type"] == "mutaraha"


class TestLobbyPageResponse:
    def test_construction(self):
        resp = LobbyPageResponse(
            correlation_id="test-id",
            game={"game_type": "mutaraha", "name": "مطارحة"},
            my_state={"queued": False, "in_active_match": False},
            my_stats={"wins": 0, "losses": 0, "has_history": False},
            lobby={"players": [], "queue_size": 0, "active_matches": [], "recent_results": []},
            leaderboard_preview=[],
            how_to_play={"summary_steps": []},
        )
        assert resp.correlation_id == "test-id"
        assert resp.game["game_type"] == "mutaraha"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_minigame_engine/test_catalog_read_model.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement read models**

Create `backend/app/modules/minigames/catalog_read_model.py`:

```python
"""Read model dataclasses for catalog and lobby endpoints.

Plain stdlib dataclasses — no Pydantic, no SQLAlchemy. These structures
mirror the JSON contracts in BRD §8.1 and §8.2 so every field has a
named Python home with type annotations.

Use the ``catalog_*_to_dict`` helpers for JSON serialization at the
API boundary. Keeping serialization in helpers (instead of custom
__dict__ logic) means the dataclasses stay pure for unit testing.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


# ─── Player-facing substructures ───────────────────────────────────

@dataclass
class CatalogMyState:
    """The current player's state for one game card (BRD §8.1 my_state)."""

    queued: bool = False
    in_active_match: bool = False
    active_session_id: str | None = None
    active_session_phase: str | None = None  # in_progress | overtime | paused | None


@dataclass
class CatalogMyStats:
    """The current player's stats for one game card (BRD §8.1 my_stats).

    When ``has_history`` is False the other fields are zero — the UI
    should hide the stats row and show an onboarding label instead.
    """

    wins: int = 0
    losses: int = 0
    current_streak: int = 0
    best_streak: int = 0
    total_matches: int = 0
    win_rate: float = 0.0
    has_history: bool = False


# ─── Catalog card ──────────────────────────────────────────────────

@dataclass
class CatalogCard:
    """One minigame card in the catalog response (BRD §8.1)."""

    game_type: str
    name: str
    short_description: str
    description: str | None
    icon: str
    accent_color: str
    hero_variant: str
    card_variant: str
    min_players: int
    max_players: int
    player_count_label: str
    estimated_duration_sec: int | None
    estimated_duration_source: str | None  # stats | config | None
    buy_in_amount: int
    status: str
    availability_reason: str | None
    expected_launch_at: datetime | None
    presence_count: int
    queue_count: int
    active_matches_count: int
    recent_results_count: int
    supports_overtime: bool
    supports_spectators: bool
    supports_ranked: bool
    supports_team_mode: bool
    featured: bool
    sort_order: int
    correlation_id: str
    my_state: CatalogMyState
    my_stats: CatalogMyStats


@dataclass
class CatalogResponse:
    """Top-level response for GET /catalog."""

    correlation_id: str
    games: list[CatalogCard] = field(default_factory=list)


# ─── Lobby page response ───────────────────────────────────────────

@dataclass
class LobbyPageResponse:
    """Response payload for GET /{game_type}/lobby (BRD §8.2).

    We keep the nested fields as plain dicts here because the lobby
    endpoint has a lot of nested optional data (recent_results,
    leaderboard_preview, how_to_play steps) that doesn't benefit from
    strict typing at this layer. Typed aggregation happens in Sprint C.
    """

    correlation_id: str
    game: dict[str, Any]
    my_state: dict[str, Any]
    my_stats: dict[str, Any]
    lobby: dict[str, Any]
    leaderboard_preview: list[dict[str, Any]]
    how_to_play: dict[str, Any]


# ─── Serialization helpers ─────────────────────────────────────────

def catalog_card_to_dict(card: CatalogCard) -> dict[str, Any]:
    """Convert a CatalogCard dataclass to a JSON-ready dict.

    Handles datetime → ISO string for expected_launch_at.
    """
    data = asdict(card)
    if card.expected_launch_at is not None:
        data["expected_launch_at"] = card.expected_launch_at.isoformat()
    return data


def catalog_response_to_dict(response: CatalogResponse) -> dict[str, Any]:
    """Convert a CatalogResponse dataclass to a JSON-ready dict."""
    return {
        "correlation_id": response.correlation_id,
        "games": [catalog_card_to_dict(card) for card in response.games],
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_minigame_engine/test_catalog_read_model.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
cd "e:/Salman/مشاريع/War of Names" && git add backend/app/modules/minigames/catalog_read_model.py backend/tests/test_minigame_engine/test_catalog_read_model.py && git commit -m "feat(catalog): read model dataclasses + serialization helpers

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: `CatalogDataLoader` — 6-Query Batched Loader

**Files:**
- Create: `backend/app/modules/minigames/catalog_data_loader.py`

**No tests in this task** — the loader is a thin SQL-to-dataclass adapter
that requires a live DB to exercise. It will be covered by the
integration tests in Sprint C and by the end-to-end aggregator tests
in Task 4 (which uses a fake loader output).

- [ ] **Step 1: Implement the loader**

Create `backend/app/modules/minigames/catalog_data_loader.py`:

```python
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
```

- [ ] **Step 2: Syntax check**

```bash
cd backend && python -c "import ast; ast.parse(open('app/modules/minigames/catalog_data_loader.py').read()); print('loader syntax ok')"
```

- [ ] **Step 3: Commit**

```bash
cd "e:/Salman/مشاريع/War of Names" && git add backend/app/modules/minigames/catalog_data_loader.py && git commit -m "feat(catalog): CatalogDataLoader — 6 batched SQL queries for aggregation

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: `build_catalog_cards` — Pure Aggregator

**Files:**
- Create: `backend/app/modules/minigames/catalog_aggregator.py`
- Create: `backend/tests/test_minigame_engine/test_catalog_aggregator.py`

The aggregator takes `CatalogRawData` + in-memory lobby snapshots and
produces the final list of `CatalogCard` dataclasses. It's a pure
function — all the edge cases (hidden games, empty stats, fallback
configs) can be tested with SimpleNamespace stubs.

- [ ] **Step 1: Write tests**

Create `backend/tests/test_minigame_engine/test_catalog_aggregator.py`:

```python
"""Tests for the pure catalog aggregator.

Uses SimpleNamespace stubs for all DB-backed objects so the tests run
without SQLAlchemy. This is the core unit test surface for
BRD §8.1.1 (every field) and §10.1.1 (visibility rules).
"""

import uuid
from dataclasses import dataclass
from datetime import datetime
from types import SimpleNamespace

import pytest

from app.modules.minigames.catalog_aggregator import (
    LobbyPresenceSnapshot,
    build_catalog_cards,
)


# ─── Stub builders ─────────────────────────────────────────────────

def _game_type(game_id="mutaraha", **overrides):
    base = dict(
        id=game_id,
        name="مطارحة",
        description="duel game",
        min_players=2,
        max_players=2,
        supports_overtime=True,
        supports_spectators=False,
        supports_ranked=False,
        supports_team_mode=False,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _config(**overrides):
    base = dict(
        game_type="mutaraha",
        short_description="مبارزة كلمات 1v1",
        icon_token="lucide:swords",
        accent_color="#D84315",
        hero_variant="duel",
        card_variant="standard",
        estimated_duration_sec=300,
        featured=True,
        sort_order=10,
        availability_mode="active",
        marketing_label=None,
        expected_launch_at=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _leaderboard(**overrides):
    base = dict(
        game_type="mutaraha",
        wins=5,
        losses=2,
        current_streak=3,
        best_streak=4,
        total_matches=7,
        avg_match_duration_sec=285.0,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _raw(
    game_types=None,
    configs_by_game_type=None,
    settings=None,
    counts_by_game_type=None,
    my_active_session_by_game_type=None,
    leaderboard_by_game_type=None,
):
    return SimpleNamespace(
        game_types=game_types or [_game_type()],
        configs_by_game_type=configs_by_game_type or {"mutaraha": _config()},
        settings=settings
        or {
            "minigame_buy_in": 500,
            "minigame_kill_switch": "off",
        },
        counts_by_game_type=counts_by_game_type or {"mutaraha": (1, 5)},
        my_active_session_by_game_type=my_active_session_by_game_type or {},
        leaderboard_by_game_type=leaderboard_by_game_type or {},
    )


def _presence(**overrides):
    base = dict(
        mutaraha=LobbyPresenceSnapshot(presence_count=3, queue_count=1, in_queue=False)
    )
    base.update(overrides)
    return base


# ─── Happy path ────────────────────────────────────────────────────

class TestHappyPath:
    def test_single_playable_card(self):
        cards = build_catalog_cards(
            raw=_raw(),
            lobby_presence=_presence(),
            player_balance=1000,
            is_bankrupt=False,
            membership_id=uuid.uuid4(),
            correlation_id="cid-1",
        )
        assert len(cards) == 1
        card = cards[0]
        assert card.game_type == "mutaraha"
        assert card.name == "مطارحة"
        assert card.player_count_label == "1v1"
        assert card.status == "playable"
        assert card.buy_in_amount == 500
        assert card.presence_count == 3
        assert card.queue_count == 1
        assert card.active_matches_count == 1
        assert card.recent_results_count == 5
        assert card.correlation_id == "cid-1"
        assert card.my_stats.has_history is False  # no leaderboard row
        assert card.my_stats.wins == 0


# ─── Visibility rules (BRD §10.1.1) ────────────────────────────────

class TestVisibility:
    def test_hidden_config_is_filtered_out(self):
        cards = build_catalog_cards(
            raw=_raw(configs_by_game_type={"mutaraha": _config(availability_mode="hidden")}),
            lobby_presence=_presence(),
            player_balance=1000,
            is_bankrupt=False,
            membership_id=uuid.uuid4(),
            correlation_id="cid",
        )
        assert cards == []

    def test_maintenance_card_is_visible_as_locked(self):
        cards = build_catalog_cards(
            raw=_raw(
                configs_by_game_type={
                    "mutaraha": _config(availability_mode="maintenance")
                }
            ),
            lobby_presence=_presence(),
            player_balance=1000,
            is_bankrupt=False,
            membership_id=uuid.uuid4(),
            correlation_id="cid",
        )
        assert len(cards) == 1
        assert cards[0].status == "maintenance"
        assert cards[0].availability_reason is not None

    def test_coming_soon_card_is_visible(self):
        cards = build_catalog_cards(
            raw=_raw(
                configs_by_game_type={
                    "mutaraha": _config(availability_mode="coming_soon")
                }
            ),
            lobby_presence=_presence(),
            player_balance=1000,
            is_bankrupt=False,
            membership_id=uuid.uuid4(),
            correlation_id="cid",
        )
        assert len(cards) == 1
        assert cards[0].status == "coming_soon"

    def test_missing_config_falls_back_to_hidden(self):
        """BRD §11.4.3 — missing config → hidden by default (filtered out)."""
        cards = build_catalog_cards(
            raw=_raw(configs_by_game_type={}),
            lobby_presence=_presence(),
            player_balance=1000,
            is_bankrupt=False,
            membership_id=uuid.uuid4(),
            correlation_id="cid",
        )
        assert cards == []

    def test_kill_switch_emergency_forces_maintenance(self):
        cards = build_catalog_cards(
            raw=_raw(settings={"minigame_buy_in": 500, "minigame_kill_switch": "emergency"}),
            lobby_presence=_presence(),
            player_balance=1000,
            is_bankrupt=False,
            membership_id=uuid.uuid4(),
            correlation_id="cid",
        )
        assert len(cards) == 1
        assert cards[0].status == "maintenance"


# ─── My state / my stats ───────────────────────────────────────────

class TestMyStateAndStats:
    def test_active_session_overrides_status(self):
        session_id = uuid.uuid4()
        cards = build_catalog_cards(
            raw=_raw(
                my_active_session_by_game_type={
                    "mutaraha": (session_id, "in_progress")
                }
            ),
            lobby_presence=_presence(),
            player_balance=0,  # would be insufficient
            is_bankrupt=True,  # would normally block
            membership_id=uuid.uuid4(),
            correlation_id="cid",
        )
        assert cards[0].status == "in_match"
        assert cards[0].my_state.active_session_id == str(session_id)
        assert cards[0].my_state.active_session_phase == "in_progress"
        assert cards[0].my_state.in_active_match is True

    def test_in_queue_overrides_balance(self):
        cards = build_catalog_cards(
            raw=_raw(),
            lobby_presence={
                "mutaraha": LobbyPresenceSnapshot(
                    presence_count=3, queue_count=1, in_queue=True
                )
            },
            player_balance=0,
            is_bankrupt=True,
            membership_id=uuid.uuid4(),
            correlation_id="cid",
        )
        assert cards[0].status == "queued"
        assert cards[0].my_state.queued is True

    def test_insufficient_balance(self):
        cards = build_catalog_cards(
            raw=_raw(),
            lobby_presence=_presence(),
            player_balance=100,
            is_bankrupt=False,
            membership_id=uuid.uuid4(),
            correlation_id="cid",
        )
        assert cards[0].status == "insufficient_balance"
        assert "500" in (cards[0].availability_reason or "")

    def test_leaderboard_present_fills_stats(self):
        cards = build_catalog_cards(
            raw=_raw(leaderboard_by_game_type={"mutaraha": _leaderboard()}),
            lobby_presence=_presence(),
            player_balance=1000,
            is_bankrupt=False,
            membership_id=uuid.uuid4(),
            correlation_id="cid",
        )
        stats = cards[0].my_stats
        assert stats.wins == 5
        assert stats.losses == 2
        assert stats.total_matches == 7
        assert stats.has_history is True
        assert stats.win_rate == pytest.approx(5 / 7, rel=1e-3)

    def test_zero_matches_win_rate_safe(self):
        lb = _leaderboard(wins=0, losses=0, total_matches=0)
        cards = build_catalog_cards(
            raw=_raw(leaderboard_by_game_type={"mutaraha": lb}),
            lobby_presence=_presence(),
            player_balance=1000,
            is_bankrupt=False,
            membership_id=uuid.uuid4(),
            correlation_id="cid",
        )
        stats = cards[0].my_stats
        assert stats.total_matches == 0
        assert stats.win_rate == 0.0
        assert stats.has_history is False


# ─── Duration source resolution ────────────────────────────────────

class TestDurationSource:
    def test_stats_source_when_enough_matches(self):
        lb = _leaderboard(total_matches=42, avg_match_duration_sec=275.5)
        cards = build_catalog_cards(
            raw=_raw(leaderboard_by_game_type={"mutaraha": lb}),
            lobby_presence=_presence(),
            player_balance=1000,
            is_bankrupt=False,
            membership_id=uuid.uuid4(),
            correlation_id="cid",
        )
        assert cards[0].estimated_duration_sec == 275
        assert cards[0].estimated_duration_source == "stats"

    def test_config_source_when_not_enough_matches(self):
        lb = _leaderboard(total_matches=5, avg_match_duration_sec=275.5)
        cards = build_catalog_cards(
            raw=_raw(leaderboard_by_game_type={"mutaraha": lb}),
            lobby_presence=_presence(),
            player_balance=1000,
            is_bankrupt=False,
            membership_id=uuid.uuid4(),
            correlation_id="cid",
        )
        # Config says 300
        assert cards[0].estimated_duration_sec == 300
        assert cards[0].estimated_duration_source == "config"


# ─── Sort order ────────────────────────────────────────────────────

class TestSortOrder:
    def test_cards_sorted_by_sort_order_ascending(self):
        raw = _raw(
            game_types=[
                _game_type(game_id="game_a"),
                _game_type(game_id="game_b"),
                _game_type(game_id="game_c"),
            ],
            configs_by_game_type={
                "game_a": _config(game_type="game_a", sort_order=30),
                "game_b": _config(game_type="game_b", sort_order=10),
                "game_c": _config(game_type="game_c", sort_order=20),
            },
            counts_by_game_type={"game_a": (0, 0), "game_b": (0, 0), "game_c": (0, 0)},
        )
        cards = build_catalog_cards(
            raw=raw,
            lobby_presence={
                "game_a": LobbyPresenceSnapshot(0, 0, False),
                "game_b": LobbyPresenceSnapshot(0, 0, False),
                "game_c": LobbyPresenceSnapshot(0, 0, False),
            },
            player_balance=1000,
            is_bankrupt=False,
            membership_id=uuid.uuid4(),
            correlation_id="cid",
        )
        assert [c.game_type for c in cards] == ["game_b", "game_c", "game_a"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_minigame_engine/test_catalog_aggregator.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement the aggregator**

Create `backend/app/modules/minigames/catalog_aggregator.py`:

```python
"""Pure catalog aggregator.

Combines raw DB data (from ``CatalogDataLoader``) with in-memory lobby
presence snapshots to produce the final list of ``CatalogCard``
dataclasses. This module is a pure function module — no DB access,
no async, no app.core.utils import.

The aggregator applies all the rules from:
    BRD §8.1.1 — field computation
    BRD §10.1.1 — visibility (hidden/disabled filtered out)
    BRD §15.4 — CTA priority chain (via catalog_helpers)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from app.modules.minigames.catalog_config_resolver import resolve_catalog_config
from app.modules.minigames.catalog_helpers import (
    build_player_count_label,
    resolve_card_status,
    resolve_estimated_duration,
)
from app.modules.minigames.catalog_read_model import (
    CatalogCard,
    CatalogMyState,
    CatalogMyStats,
)


# ─── Presence snapshot (injected from lobby_manager in Task 5) ─────

@dataclass
class LobbyPresenceSnapshot:
    """In-memory lobby data for a single game type.

    ``presence_count`` = how many players are in the lobby right now
    ``queue_count``    = how many of them are in the matchmaking queue
    ``in_queue``       = whether the current player is in that queue
    """

    presence_count: int = 0
    queue_count: int = 0
    in_queue: bool = False


# ─── Visibility rule ───────────────────────────────────────────────

def _is_card_visible(availability_mode: str) -> bool:
    """BRD §10.1.1 — hidden cards are filtered out entirely.

    Maintenance, coming_soon, and active cards all remain visible.
    """
    return availability_mode != "hidden"


# ─── Stats computation ─────────────────────────────────────────────

def _build_my_stats(leaderboard_row: Any | None) -> CatalogMyStats:
    """Build CatalogMyStats from an optional leaderboard row.

    BRD §8.1.1 — when the row is missing or total_matches is zero,
    returns an empty stats object with has_history=False.
    """
    if leaderboard_row is None:
        return CatalogMyStats()

    wins = int(getattr(leaderboard_row, "wins", 0) or 0)
    losses = int(getattr(leaderboard_row, "losses", 0) or 0)
    total = int(getattr(leaderboard_row, "total_matches", 0) or 0)

    if total <= 0:
        return CatalogMyStats()

    win_rate = wins / total if total > 0 else 0.0

    return CatalogMyStats(
        wins=wins,
        losses=losses,
        current_streak=int(getattr(leaderboard_row, "current_streak", 0) or 0),
        best_streak=int(getattr(leaderboard_row, "best_streak", 0) or 0),
        total_matches=total,
        win_rate=round(win_rate, 3),
        has_history=True,
    )


# ─── My state computation ─────────────────────────────────────────

def _build_my_state(
    *,
    active_session: tuple[uuid.UUID, str] | None,
    in_queue: bool,
) -> CatalogMyState:
    """Build CatalogMyState from active session lookup and queue flag."""
    if active_session is not None:
        session_id, phase = active_session
        return CatalogMyState(
            queued=False,
            in_active_match=True,
            active_session_id=str(session_id),
            active_session_phase=phase,
        )
    return CatalogMyState(
        queued=in_queue,
        in_active_match=False,
        active_session_id=None,
        active_session_phase=None,
    )


# ─── Main entry point ──────────────────────────────────────────────

def build_catalog_cards(
    *,
    raw: Any,  # CatalogRawData (SimpleNamespace-compatible for testing)
    lobby_presence: dict[str, LobbyPresenceSnapshot],
    player_balance: int,
    is_bankrupt: bool,
    membership_id: uuid.UUID,
    correlation_id: str,
) -> list[CatalogCard]:
    """Transform raw data + lobby state into a sorted list of catalog cards.

    Args:
        raw: CatalogRawData from CatalogDataLoader (or SimpleNamespace in tests)
        lobby_presence: per-game presence/queue data from lobby_manager
        player_balance: caller's current balance for eligibility check
        is_bankrupt: caller's bankruptcy flag
        membership_id: caller's membership ID (for future per-player logic)
        correlation_id: request-scoped correlation ID, stamped on every card

    Returns:
        List of CatalogCard ordered by sort_order ASC, then game_type ASC.
        Cards with availability_mode='hidden' are excluded entirely.
    """
    settings = raw.settings or {}
    default_buy_in = int(settings.get("minigame_buy_in", 500))
    kill_switch = str(settings.get("minigame_kill_switch", "off"))

    cards: list[CatalogCard] = []

    for game_type in raw.game_types:
        game_id = game_type.id
        config = raw.configs_by_game_type.get(game_id)

        # Resolve config with fallback (BRD §11.4.3)
        resolved_config, _is_fallback = resolve_catalog_config(game_type, config)

        # BRD §10.1.1 — hidden cards are filtered before any other work
        if not _is_card_visible(resolved_config["availability_mode"]):
            continue

        presence = lobby_presence.get(game_id) or LobbyPresenceSnapshot()
        counts = raw.counts_by_game_type.get(game_id, (0, 0))
        active_matches_count, recent_results_count = counts
        active_session = raw.my_active_session_by_game_type.get(game_id)
        leaderboard_row = raw.leaderboard_by_game_type.get(game_id)

        # Build the substructures
        my_stats = _build_my_stats(leaderboard_row)
        my_state = _build_my_state(
            active_session=active_session,
            in_queue=presence.in_queue,
        )

        # Resolve status (BRD §15.4)
        status, reason = resolve_card_status(
            availability_mode=resolved_config["availability_mode"],
            kill_switch_level=kill_switch,
            my_active_session_id=my_state.active_session_id,
            in_queue=my_state.queued,
            player_balance=player_balance,
            buy_in_amount=default_buy_in,
            is_bankrupt=is_bankrupt,
        )

        # Resolve duration (BRD §8.1.1)
        leaderboard_avg = (
            float(getattr(leaderboard_row, "avg_match_duration_sec", 0) or 0)
            if leaderboard_row is not None
            else None
        )
        leaderboard_match_count = (
            int(getattr(leaderboard_row, "total_matches", 0) or 0)
            if leaderboard_row is not None
            else 0
        )
        duration_sec, duration_source = resolve_estimated_duration(
            leaderboard_avg_sec=leaderboard_avg,
            leaderboard_match_count=leaderboard_match_count,
            config_duration_sec=resolved_config["estimated_duration_sec"],
        )

        # Assemble the card
        card = CatalogCard(
            game_type=game_id,
            name=game_type.name,
            short_description=resolved_config["short_description"],
            description=getattr(game_type, "description", None),
            icon=resolved_config["icon_token"],
            accent_color=resolved_config["accent_color"],
            hero_variant=resolved_config["hero_variant"],
            card_variant=resolved_config["card_variant"],
            min_players=int(game_type.min_players),
            max_players=int(game_type.max_players),
            player_count_label=build_player_count_label(
                int(game_type.min_players), int(game_type.max_players)
            ),
            estimated_duration_sec=duration_sec,
            estimated_duration_source=duration_source,
            buy_in_amount=default_buy_in,
            status=status,
            availability_reason=reason,
            expected_launch_at=resolved_config["expected_launch_at"],
            presence_count=presence.presence_count,
            queue_count=presence.queue_count,
            active_matches_count=active_matches_count,
            recent_results_count=recent_results_count,
            supports_overtime=bool(getattr(game_type, "supports_overtime", False)),
            supports_spectators=bool(getattr(game_type, "supports_spectators", False)),
            supports_ranked=bool(getattr(game_type, "supports_ranked", False)),
            supports_team_mode=bool(getattr(game_type, "supports_team_mode", False)),
            featured=bool(resolved_config["featured"]),
            sort_order=int(resolved_config["sort_order"]),
            correlation_id=correlation_id,
            my_state=my_state,
            my_stats=my_stats,
        )
        cards.append(card)

    # BRD §14 default ordering — sort_order ASC, game_type ASC for stability
    cards.sort(key=lambda c: (c.sort_order, c.game_type))
    return cards
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_minigame_engine/test_catalog_aggregator.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
cd "e:/Salman/مشاريع/War of Names" && git add backend/app/modules/minigames/catalog_aggregator.py backend/tests/test_minigame_engine/test_catalog_aggregator.py && git commit -m "feat(catalog): pure aggregator — build_catalog_cards with visibility, stats, duration resolution

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: `get_catalog` Orchestrator + `get_lobby_detail`

**Files:**
- Create: `backend/app/modules/minigames/catalog_service.py`

This task wires everything together. No new tests here — the pure
helpers, dataclasses, and aggregator are already tested. Sprint C will
add integration tests against real Docker Postgres.

- [ ] **Step 1: Implement the service**

Create `backend/app/modules/minigames/catalog_service.py`:

```python
"""Catalog aggregation service — public entry points.

Two async functions for the REST layer in Sprint C:

    get_catalog       — full catalog for a player in a competition
    get_lobby_detail  — single-game lobby page read model

Both produce the read models defined in BRD §8.1 and §8.2.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.minigames.catalog_aggregator import (
    LobbyPresenceSnapshot,
    build_catalog_cards,
)
from app.modules.minigames.catalog_data_loader import CatalogDataLoader
from app.modules.minigames.catalog_read_model import (
    CatalogResponse,
    LobbyPageResponse,
    catalog_card_to_dict,
)
from app.modules.minigames.lobby_manager import lobby_mgr


# ─── Lobby presence extraction ─────────────────────────────────────

def _presence_snapshot_for_player(
    *,
    game_type: str,
    competition_id: uuid.UUID,
    membership_id: uuid.UUID,
) -> LobbyPresenceSnapshot:
    """Read the in-memory lobby snapshot for one (game_type, competition_id).

    Returns an empty snapshot if the lobby has never been opened.
    """
    lobby_key = f"{game_type}:{competition_id}"

    # Use LobbyManager public API — get_player_count + get_queue_size + is_queued
    try:
        presence = lobby_mgr.get_player_count(lobby_key)
        queue = lobby_mgr.get_queue_size(lobby_key)
        in_queue = lobby_mgr.is_queued(lobby_key, membership_id)
    except Exception:
        return LobbyPresenceSnapshot(presence_count=0, queue_count=0, in_queue=False)

    return LobbyPresenceSnapshot(
        presence_count=int(presence),
        queue_count=int(queue),
        in_queue=bool(in_queue),
    )


def _build_presence_map(
    *,
    game_types: list,
    competition_id: uuid.UUID,
    membership_id: uuid.UUID,
) -> dict[str, LobbyPresenceSnapshot]:
    """Build per-game presence snapshots from the in-memory lobby manager."""
    return {
        gt.id: _presence_snapshot_for_player(
            game_type=gt.id,
            competition_id=competition_id,
            membership_id=membership_id,
        )
        for gt in game_types
    }


# ─── get_catalog ──────────────────────────────────────────────────

async def get_catalog(
    session: AsyncSession,
    *,
    competition_id: uuid.UUID,
    membership_id: uuid.UUID,
    player_balance: int,
    is_bankrupt: bool,
    season_id: uuid.UUID | None = None,
    cycle_id: uuid.UUID | None = None,
    correlation_id: str | None = None,
) -> CatalogResponse:
    """Produce the full catalog response for a player in a competition.

    Issues exactly 6 SQL queries (delegated to ``CatalogDataLoader``)
    plus a handful of in-memory lookups against ``lobby_mgr``. No
    N+1 anywhere.
    """
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())

    loader = CatalogDataLoader()
    raw = await loader.load_all(
        session,
        competition_id=competition_id,
        membership_id=membership_id,
        season_id=season_id,
        cycle_id=cycle_id,
    )

    presence_map = _build_presence_map(
        game_types=raw.game_types,
        competition_id=competition_id,
        membership_id=membership_id,
    )

    cards = build_catalog_cards(
        raw=raw,
        lobby_presence=presence_map,
        player_balance=player_balance,
        is_bankrupt=is_bankrupt,
        membership_id=membership_id,
        correlation_id=correlation_id,
    )

    return CatalogResponse(correlation_id=correlation_id, games=cards)


# ─── get_lobby_detail ─────────────────────────────────────────────

async def get_lobby_detail(
    session: AsyncSession,
    *,
    game_type: str,
    competition_id: uuid.UUID,
    membership_id: uuid.UUID,
    player_balance: int,
    is_bankrupt: bool,
    season_id: uuid.UUID | None = None,
    cycle_id: uuid.UUID | None = None,
    correlation_id: str | None = None,
) -> LobbyPageResponse:
    """Produce the full lobby page response for one game in a competition.

    Reuses the catalog loader (which fetches all game types) and then
    extracts the single matching card. This keeps the query count
    low and avoids a second code path for single-game aggregation.
    """
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())

    catalog = await get_catalog(
        session,
        competition_id=competition_id,
        membership_id=membership_id,
        player_balance=player_balance,
        is_bankrupt=is_bankrupt,
        season_id=season_id,
        cycle_id=cycle_id,
        correlation_id=correlation_id,
    )

    target_card = next((c for c in catalog.games if c.game_type == game_type), None)
    if target_card is None:
        # Game either doesn't exist or is hidden — return an empty shell
        # that the REST layer can convert to a 404.
        raise LookupError(f"game_type '{game_type}' not found in catalog")

    card_dict = catalog_card_to_dict(target_card)

    # Full lobby snapshot from in-memory manager
    lobby_key = f"{game_type}:{competition_id}"
    try:
        lobby_snapshot = lobby_mgr.get_lobby_state(lobby_key)
    except Exception:
        lobby_snapshot = {
            "players": [],
            "queue_size": 0,
            "active_matches": 0,
            "recent_results": [],
        }

    return LobbyPageResponse(
        correlation_id=correlation_id,
        game={
            "game_type": card_dict["game_type"],
            "name": card_dict["name"],
            "description": card_dict["description"],
            "icon": card_dict["icon"],
            "accent_color": card_dict["accent_color"],
            "hero_variant": card_dict["hero_variant"],
            "min_players": card_dict["min_players"],
            "max_players": card_dict["max_players"],
            "player_count_label": card_dict["player_count_label"],
            "buy_in_amount": card_dict["buy_in_amount"],
            "estimated_duration_sec": card_dict["estimated_duration_sec"],
            "estimated_duration_source": card_dict["estimated_duration_source"],
            "supports_overtime": card_dict["supports_overtime"],
            "supports_spectators": card_dict["supports_spectators"],
        },
        my_state=card_dict["my_state"],
        my_stats=card_dict["my_stats"],
        lobby=lobby_snapshot,
        leaderboard_preview=[],
        how_to_play={"summary_steps": []},
    )
```

- [ ] **Step 2: Syntax check**

```bash
cd backend && python -c "import ast; ast.parse(open('app/modules/minigames/catalog_service.py').read()); print('service syntax ok')"
```

- [ ] **Step 3: Commit**

```bash
cd "e:/Salman/مشاريع/War of Names" && git add backend/app/modules/minigames/catalog_service.py && git commit -m "feat(catalog): orchestrator — get_catalog + get_lobby_detail wiring loader, aggregator, lobby state

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: Final Verification

- [ ] **Step 1: Run the full pure-test suite**

```bash
cd backend && python -m pytest \
  tests/test_minigame_engine/test_catalog_helpers.py \
  tests/test_minigame_engine/test_catalog_read_model.py \
  tests/test_minigame_engine/test_catalog_aggregator.py \
  tests/test_minigame_engine/test_catalog_enums.py \
  tests/test_minigame_engine/test_catalog_config_resolver.py \
  tests/test_minigame_engine/test_enums.py \
  tests/test_minigame_engine/test_plugin_contract.py \
  tests/test_minigame_engine/test_registry.py \
  tests/test_minigame_engine/test_state_machine.py \
  tests/test_minigame_engine/test_session_service.py \
  tests/test_minigame_engine/test_settlement_service.py \
  tests/test_minigame_engine/test_policy_service.py \
  tests/test_minigame_engine/test_leaderboard_service.py \
  tests/test_minigame_engine/test_settings_helper.py \
  tests/test_minigame_engine/test_connection_manager.py \
  tests/test_minigame_engine/test_lobby_manager.py \
  tests/test_minigame_engine/test_mutaraha_tools.py \
  tests/test_minigame_engine/test_mutaraha_plugin.py \
  --tb=short 2>&1 | tail -10
```

Expected: All tests pass (Sprint A 233 + Sprint B new tests).

- [ ] **Step 2: Syntax check every modified file**

```bash
cd backend && python -c "
import ast
files = [
    'app/modules/minigames/catalog_helpers.py',
    'app/modules/minigames/catalog_read_model.py',
    'app/modules/minigames/catalog_data_loader.py',
    'app/modules/minigames/catalog_aggregator.py',
    'app/modules/minigames/catalog_service.py',
]
for f in files:
    ast.parse(open(f).read())
    print(f'{f}: OK')
"
```

- [ ] **Step 3: Commit plan document**

```bash
cd "e:/Salman/مشاريع/War of Names" && git add docs/superpowers/plans/2026-04-04-catalog-sprint-b.md && git commit -m "docs(catalog): Sprint B detailed task-by-task plan — aggregation service

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Sprint B Deliverables Summary

| Task | Component | Tests |
|---|---|---|
| 1 | Pure helpers (label + status + duration) | ~26 |
| 2 | Read model dataclasses + serializers | ~11 |
| 3 | `CatalogDataLoader` (6 batched queries) | via Sprint C integration |
| 4 | `build_catalog_cards` pure aggregator | ~18 |
| 5 | `get_catalog` + `get_lobby_detail` orchestrators | via Sprint C integration |
| 6 | Plan document + verification | — |
| **Total** | **5 files created** | **~55 new pure tests** |

## What Sprint C Will Build On This

Sprint C (REST Endpoints) will consume this sprint's public API:
- `GET /api/competitions/{id}/minigames/catalog` calls `catalog_service.get_catalog()` directly
- `GET /api/competitions/{id}/minigames/{game_type}/lobby` calls `catalog_service.get_lobby_detail()`
- Pydantic response models wrap the dataclasses (or Sprint C just dumps dicts directly)
- Integration tests against Docker verify the 6-query claim via actual query logging
- Arabic error responses handled at the endpoint layer (404 when `LookupError` raised)
