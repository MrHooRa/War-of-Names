# Minigame Engine — Sprint 0: Foundation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the minigame engine foundation — enums, database models, SQL migration, plugin contract interface, game type registry, and session state machine with transition validation.

**Architecture:** A new `backend/app/modules/minigames/` module following the existing module pattern (models, service, router). Enums added to the centralized `enums.py`. Models registered in `core/models.py`. Plugin contract defined as an abstract base class. State machine enforced via a transition map with pure functions.

**Tech Stack:** Python 3.12, SQLAlchemy 2.x async (Mapped annotations), PostgreSQL 16 (native ENUMs, JSONB, UUID), FastAPI, pytest

**BRD Reference:** `docs/minigames/War of Names - Minigame Engine BRD - V1.0.md` — Sections 4-9

---

## Sprint 0 Scope

This sprint delivers:
1. All minigame-related enums (session phase, match type, settlement state, turn side)
2. All 7 core database models (types, sessions, events, receipts, settlements, leaderboards, policy rules)
3. SQL migration for all tables and enum types
4. Plugin contract (abstract base class with 8 lifecycle hooks)
5. Game type registry (register/lookup/list plugins)
6. Session state machine (valid transitions, guards, terminal state enforcement)
7. Unit tests for state machine transitions and plugin registry

**NOT in Sprint 0:** Session service (create/advance), economy bridge, matchmaking, REST API, WebSocket, admin endpoints. Those are Sprint 1+.

---

## File Structure

```
backend/
├── app/
│   ├── core/
│   │   ├── enums.py                          # MODIFY: add 5 new enums
│   │   └── models.py                         # MODIFY: register minigame models
│   └── modules/
│       └── minigames/
│           ├── __init__.py                   # CREATE: empty
│           ├── models.py                     # CREATE: 7 SQLAlchemy models
│           ├── plugin.py                     # CREATE: abstract plugin contract
│           ├── registry.py                   # CREATE: game type registry
│           └── state_machine.py              # CREATE: session state transitions
├── migrations/
│   └── 002_minigame_engine.sql               # CREATE: all tables + enums
└── tests/
    └── test_minigame_engine/
        ├── __init__.py                       # CREATE: empty
        ├── test_state_machine.py             # CREATE: state machine tests
        ├── test_registry.py                  # CREATE: registry tests
        └── test_plugin_contract.py           # CREATE: plugin contract tests
```

---

## Task 1: Minigame Enums

**Files:**
- Modify: `backend/app/core/enums.py`

- [ ] **Step 1: Write tests for new enums**

Create `backend/tests/test_minigame_engine/__init__.py` (empty) and `backend/tests/test_minigame_engine/test_enums.py`:

```python
"""Verify minigame enums exist and have expected members."""

from app.core.enums import (
    MinigameSessionPhase,
    MinigameMatchType,
    MinigameSettlementState,
    MinigameTurnSide,
    MinigameTypeStatus,
)


def test_session_phase_has_all_states():
    phases = {p.value for p in MinigameSessionPhase}
    expected = {"created", "waiting", "ready", "in_progress", "overtime", "paused", "completed", "cancelled", "abandoned"}
    assert phases == expected


def test_session_phase_terminal_states():
    terminal = {"completed", "cancelled", "abandoned"}
    for phase in MinigameSessionPhase:
        if phase.value in terminal:
            assert phase in (
                MinigameSessionPhase.COMPLETED,
                MinigameSessionPhase.CANCELLED,
                MinigameSessionPhase.ABANDONED,
            )


def test_match_type_values():
    assert MinigameMatchType.CHALLENGE.value == "challenge"
    assert MinigameMatchType.QUEUE.value == "queue"


def test_settlement_state_values():
    states = {s.value for s in MinigameSettlementState}
    assert states == {"pending", "settled", "failed", "reconciled"}


def test_turn_side_values():
    assert MinigameTurnSide.PLAYER_1.value == "player_1"
    assert MinigameTurnSide.PLAYER_2.value == "player_2"


def test_type_status_values():
    statuses = {s.value for s in MinigameTypeStatus}
    assert statuses == {"active", "disabled", "deprecated"}


def test_ledger_entry_type_has_minigame_values():
    from app.core.enums import LedgerEntryType
    minigame_types = {
        "minigame_buy_in",
        "minigame_payout",
        "minigame_forfeit",
        "minigame_refund",
        "minigame_cancel_penalty",
    }
    existing = {t.value for t in LedgerEntryType}
    assert minigame_types.issubset(existing)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_minigame_engine/test_enums.py -v`
Expected: FAIL — `ImportError: cannot import name 'MinigameSessionPhase'`

- [ ] **Step 3: Add minigame enums to enums.py**

Add at the end of `backend/app/core/enums.py` (before the final blank line):

```python
# ── Minigame Engine ──────────────────────────────────────────────────────

class MinigameSessionPhase(StrEnum):
    CREATED = "created"
    WAITING = "waiting"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    OVERTIME = "overtime"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ABANDONED = "abandoned"


class MinigameMatchType(StrEnum):
    CHALLENGE = "challenge"
    QUEUE = "queue"


class MinigameSettlementState(StrEnum):
    PENDING = "pending"
    SETTLED = "settled"
    FAILED = "failed"
    RECONCILED = "reconciled"


class MinigameTurnSide(StrEnum):
    PLAYER_1 = "player_1"
    PLAYER_2 = "player_2"


class MinigameTypeStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"
    DEPRECATED = "deprecated"
```

Also add the 5 new ledger entry types to the existing `LedgerEntryType` class:

```python
class LedgerEntryType(StrEnum):
    # ... existing values ...
    BOX_RESULT = "box_result"
    # ── Minigame entries ──
    MINIGAME_BUY_IN = "minigame_buy_in"
    MINIGAME_PAYOUT = "minigame_payout"
    MINIGAME_FORFEIT = "minigame_forfeit"
    MINIGAME_REFUND = "minigame_refund"
    MINIGAME_CANCEL_PENALTY = "minigame_cancel_penalty"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_minigame_engine/test_enums.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/enums.py backend/tests/test_minigame_engine/
git commit -m "feat(minigames): add minigame engine enums — session phases, match types, settlement states, ledger types"
```

---

## Task 2: Plugin Contract (Abstract Base Class)

**Files:**
- Create: `backend/app/modules/minigames/__init__.py`
- Create: `backend/app/modules/minigames/plugin.py`
- Create: `backend/tests/test_minigame_engine/test_plugin_contract.py`

- [ ] **Step 1: Write tests for plugin contract**

Create `backend/tests/test_minigame_engine/test_plugin_contract.py`:

```python
"""Verify plugin contract interface and a dummy implementation."""

import pytest
from app.modules.minigames.plugin import GameTypePlugin


class DummyPlugin(GameTypePlugin):
    """Minimal valid plugin for testing the contract."""

    id = "test_dummy"
    name = "لعبة تجريبية"
    description = "لعبة للاختبار فقط"
    plugin_api_version = "1.0"
    settings_schema_version = "1.0"
    supports_overtime = False
    supports_spectators = False
    supports_ranked = False
    supports_team_mode = False
    min_players = 2
    max_players = 2

    def validate_settings(self, settings: dict) -> list[str]:
        return []

    def init_session_state(self, config: dict) -> dict:
        return {"turn": 0, "scores": [0, 0]}

    def validate_action(self, action: dict, state: dict) -> str | None:
        if action.get("type") not in ("move", "pass"):
            return "نوع الإجراء غير صالح"
        return None

    def apply_action(self, action: dict, state: dict) -> tuple[dict, list[dict]]:
        new_state = {**state, "turn": state["turn"] + 1}
        side_effects = [{"type": "sound", "name": "click"}]
        return new_state, side_effects

    def evaluate_terminal(self, state: dict) -> dict | None:
        if state["turn"] >= 10:
            return {"winner": "player_1", "reason": "turn_limit"}
        return None

    def evaluate_overtime(self, state: dict) -> dict | None:
        return None

    def compute_settlement(self, terminal_result: dict) -> dict:
        return {
            "winner_membership_id": None,
            "loser_membership_id": None,
            "winner_payout": 1000,
            "loser_penalty": 500,
        }

    def build_public_view(self, state: dict, viewer_membership_id) -> dict:
        return {"turn": state["turn"], "my_view": True}


def test_dummy_plugin_satisfies_contract():
    plugin = DummyPlugin()
    assert plugin.id == "test_dummy"
    assert plugin.min_players == 2
    assert plugin.max_players == 2


def test_validate_settings_returns_empty_for_valid():
    plugin = DummyPlugin()
    errors = plugin.validate_settings({"some": "config"})
    assert errors == []


def test_init_session_state_returns_dict():
    plugin = DummyPlugin()
    state = plugin.init_session_state({})
    assert isinstance(state, dict)
    assert state["turn"] == 0


def test_validate_action_returns_none_for_valid():
    plugin = DummyPlugin()
    error = plugin.validate_action({"type": "move"}, {"turn": 0})
    assert error is None


def test_validate_action_returns_error_for_invalid():
    plugin = DummyPlugin()
    error = plugin.validate_action({"type": "invalid"}, {"turn": 0})
    assert error == "نوع الإجراء غير صالح"


def test_apply_action_returns_new_state_and_effects():
    plugin = DummyPlugin()
    new_state, effects = plugin.apply_action({"type": "move"}, {"turn": 0, "scores": [0, 0]})
    assert new_state["turn"] == 1
    assert len(effects) == 1


def test_evaluate_terminal_returns_none_mid_game():
    plugin = DummyPlugin()
    result = plugin.evaluate_terminal({"turn": 5})
    assert result is None


def test_evaluate_terminal_returns_result_at_end():
    plugin = DummyPlugin()
    result = plugin.evaluate_terminal({"turn": 10})
    assert result is not None
    assert result["winner"] == "player_1"


def test_compute_settlement_returns_payout():
    plugin = DummyPlugin()
    settlement = plugin.compute_settlement({"winner": "player_1"})
    assert settlement["winner_payout"] == 1000
    assert settlement["loser_penalty"] == 500


def test_build_public_view_returns_filtered_state():
    plugin = DummyPlugin()
    view = plugin.build_public_view({"turn": 3, "secret": "hidden"}, viewer_membership_id=1)
    assert view["turn"] == 3
    assert "secret" not in view


def test_cannot_instantiate_abstract_directly():
    with pytest.raises(TypeError):
        GameTypePlugin()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_minigame_engine/test_plugin_contract.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.modules.minigames'`

- [ ] **Step 3: Create the plugin contract**

Create `backend/app/modules/minigames/__init__.py` (empty file).

Create `backend/app/modules/minigames/plugin.py`:

```python
"""Abstract base class defining the plugin contract for minigames.

Every minigame must subclass GameTypePlugin and implement all abstract
methods. The engine calls these hooks at specific lifecycle points —
see BRD Section 5.2 for when each hook fires.
"""

from abc import ABC, abstractmethod


class GameTypePlugin(ABC):
    """Contract that every minigame plugin must satisfy.

    Class attributes (set by subclass):
        id: Unique identifier, e.g. "mutaraha"
        name: Arabic display name, e.g. "مطارحة"
        description: Short Arabic description
        plugin_api_version: Engine API version this plugin targets
        settings_schema_version: Version of this plugin's settings schema
        supports_overtime: Whether evaluate_overtime is meaningful
        supports_spectators: Reserved for future use
        supports_ranked: Whether ELO matchmaking is supported
        supports_team_mode: Reserved for future use
        min_players: Minimum players required (typically 2)
        max_players: Maximum players allowed (typically 2)
    """

    id: str
    name: str
    description: str
    plugin_api_version: str
    settings_schema_version: str
    supports_overtime: bool
    supports_spectators: bool
    supports_ranked: bool
    supports_team_mode: bool
    min_players: int
    max_players: int

    @abstractmethod
    def validate_settings(self, settings: dict) -> list[str]:
        """Validate admin-provided settings. Return list of error messages (empty = valid)."""
        ...

    @abstractmethod
    def init_session_state(self, config: dict) -> dict:
        """Create initial game state when a session starts."""
        ...

    @abstractmethod
    def validate_action(self, action: dict, state: dict) -> str | None:
        """Check if an action is legal. Return None if valid, Arabic error string if not."""
        ...

    @abstractmethod
    def apply_action(self, action: dict, state: dict) -> tuple[dict, list[dict]]:
        """Execute a validated action. Return (new_state, side_effects)."""
        ...

    @abstractmethod
    def evaluate_terminal(self, state: dict) -> dict | None:
        """Check if game has ended. Return terminal result dict or None if still playing."""
        ...

    @abstractmethod
    def evaluate_overtime(self, state: dict) -> dict | None:
        """Handle tied state after regular turns. Return overtime config or None."""
        ...

    @abstractmethod
    def compute_settlement(self, terminal_result: dict) -> dict:
        """Calculate financial settlement from terminal result.

        Must return: {
            winner_membership_id, loser_membership_id,
            winner_payout, loser_penalty
        }
        """
        ...

    @abstractmethod
    def build_public_view(self, state: dict, viewer_membership_id) -> dict:
        """Return sanitized state safe to send to a specific player."""
        ...
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_minigame_engine/test_plugin_contract.py -v`
Expected: All 12 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/modules/minigames/
git add backend/tests/test_minigame_engine/test_plugin_contract.py
git commit -m "feat(minigames): add plugin contract — abstract base class with 8 lifecycle hooks"
```

---

## Task 3: Game Type Registry

**Files:**
- Create: `backend/app/modules/minigames/registry.py`
- Create: `backend/tests/test_minigame_engine/test_registry.py`

- [ ] **Step 1: Write tests for registry**

Create `backend/tests/test_minigame_engine/test_registry.py`:

```python
"""Test the in-memory game type registry."""

import pytest
from app.modules.minigames.registry import GameTypeRegistry
from app.modules.minigames.plugin import GameTypePlugin


class FakePlugin(GameTypePlugin):
    id = "fake_game"
    name = "لعبة وهمية"
    description = "لعبة للاختبار"
    plugin_api_version = "1.0"
    settings_schema_version = "1.0"
    supports_overtime = False
    supports_spectators = False
    supports_ranked = False
    supports_team_mode = False
    min_players = 2
    max_players = 2

    def validate_settings(self, settings): return []
    def init_session_state(self, config): return {}
    def validate_action(self, action, state): return None
    def apply_action(self, action, state): return state, []
    def evaluate_terminal(self, state): return None
    def evaluate_overtime(self, state): return None
    def compute_settlement(self, result): return {"winner_payout": 0, "loser_penalty": 0}
    def build_public_view(self, state, vid): return state


class AnotherFakePlugin(GameTypePlugin):
    id = "another_fake"
    name = "لعبة أخرى"
    description = "لعبة ثانية"
    plugin_api_version = "1.0"
    settings_schema_version = "1.0"
    supports_overtime = True
    supports_spectators = False
    supports_ranked = False
    supports_team_mode = False
    min_players = 2
    max_players = 4

    def validate_settings(self, settings): return []
    def init_session_state(self, config): return {}
    def validate_action(self, action, state): return None
    def apply_action(self, action, state): return state, []
    def evaluate_terminal(self, state): return None
    def evaluate_overtime(self, state): return None
    def compute_settlement(self, result): return {"winner_payout": 0, "loser_penalty": 0}
    def build_public_view(self, state, vid): return state


@pytest.fixture(autouse=True)
def clean_registry():
    """Reset the registry before each test."""
    GameTypeRegistry._plugins.clear()
    yield
    GameTypeRegistry._plugins.clear()


def test_register_and_get():
    plugin = FakePlugin()
    GameTypeRegistry.register(plugin)
    found = GameTypeRegistry.get("fake_game")
    assert found is plugin


def test_get_unknown_returns_none():
    assert GameTypeRegistry.get("nonexistent") is None


def test_register_duplicate_raises():
    GameTypeRegistry.register(FakePlugin())
    with pytest.raises(ValueError, match="مسجلة مسبقاً"):
        GameTypeRegistry.register(FakePlugin())


def test_list_all_returns_registered():
    GameTypeRegistry.register(FakePlugin())
    GameTypeRegistry.register(AnotherFakePlugin())
    all_plugins = GameTypeRegistry.list_all()
    assert len(all_plugins) == 2
    ids = {p.id for p in all_plugins}
    assert ids == {"fake_game", "another_fake"}


def test_list_all_empty():
    assert GameTypeRegistry.list_all() == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_minigame_engine/test_registry.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.modules.minigames.registry'`

- [ ] **Step 3: Implement the registry**

Create `backend/app/modules/minigames/registry.py`:

```python
"""In-memory game type registry.

Plugins register at import time. The engine looks up plugins by id
when creating sessions or resolving game-specific logic.
"""

from app.modules.minigames.plugin import GameTypePlugin


class GameTypeRegistry:
    """Singleton registry mapping game type IDs to plugin instances."""

    _plugins: dict[str, GameTypePlugin] = {}

    @classmethod
    def register(cls, plugin: GameTypePlugin) -> None:
        """Register a game type plugin. Raises ValueError on duplicate id."""
        if plugin.id in cls._plugins:
            raise ValueError(f"اللعبة '{plugin.id}' مسجلة مسبقاً")
        cls._plugins[plugin.id] = plugin

    @classmethod
    def get(cls, game_type_id: str) -> GameTypePlugin | None:
        """Look up a plugin by its id. Returns None if not found."""
        return cls._plugins.get(game_type_id)

    @classmethod
    def list_all(cls) -> list[GameTypePlugin]:
        """Return all registered plugins."""
        return list(cls._plugins.values())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_minigame_engine/test_registry.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/modules/minigames/registry.py
git add backend/tests/test_minigame_engine/test_registry.py
git commit -m "feat(minigames): add game type registry — register, lookup, and list plugins"
```

---

## Task 4: Session State Machine

**Files:**
- Create: `backend/app/modules/minigames/state_machine.py`
- Create: `backend/tests/test_minigame_engine/test_state_machine.py`

- [ ] **Step 1: Write tests for state machine transitions**

Create `backend/tests/test_minigame_engine/test_state_machine.py`:

```python
"""Test session state machine transitions."""

import pytest
from app.core.enums import MinigameSessionPhase as Phase
from app.modules.minigames.state_machine import (
    TERMINAL_PHASES,
    can_transition,
    validate_transition,
    is_terminal,
)


# ── Valid transitions ─────────────────────────────────────────────

def test_created_to_waiting():
    assert can_transition(Phase.CREATED, Phase.WAITING) is True


def test_created_to_cancelled():
    assert can_transition(Phase.CREATED, Phase.CANCELLED) is True


def test_waiting_to_ready():
    assert can_transition(Phase.WAITING, Phase.READY) is True


def test_waiting_to_cancelled():
    assert can_transition(Phase.WAITING, Phase.CANCELLED) is True


def test_ready_to_in_progress():
    assert can_transition(Phase.READY, Phase.IN_PROGRESS) is True


def test_ready_to_cancelled():
    assert can_transition(Phase.READY, Phase.CANCELLED) is True


def test_in_progress_to_completed():
    assert can_transition(Phase.IN_PROGRESS, Phase.COMPLETED) is True


def test_in_progress_to_overtime():
    assert can_transition(Phase.IN_PROGRESS, Phase.OVERTIME) is True


def test_in_progress_to_paused():
    assert can_transition(Phase.IN_PROGRESS, Phase.PAUSED) is True


def test_in_progress_to_abandoned():
    assert can_transition(Phase.IN_PROGRESS, Phase.ABANDONED) is True


def test_in_progress_to_cancelled():
    assert can_transition(Phase.IN_PROGRESS, Phase.CANCELLED) is True


def test_overtime_to_completed():
    assert can_transition(Phase.OVERTIME, Phase.COMPLETED) is True


def test_overtime_to_abandoned():
    assert can_transition(Phase.OVERTIME, Phase.ABANDONED) is True


def test_paused_to_in_progress():
    assert can_transition(Phase.PAUSED, Phase.IN_PROGRESS) is True


def test_paused_to_abandoned():
    assert can_transition(Phase.PAUSED, Phase.ABANDONED) is True


# ── Invalid transitions ──────────────────────────────────────────

def test_created_to_in_progress_invalid():
    assert can_transition(Phase.CREATED, Phase.IN_PROGRESS) is False


def test_waiting_to_in_progress_invalid():
    assert can_transition(Phase.WAITING, Phase.IN_PROGRESS) is False


def test_completed_to_anything_invalid():
    for target in Phase:
        assert can_transition(Phase.COMPLETED, target) is False


def test_cancelled_to_anything_invalid():
    for target in Phase:
        assert can_transition(Phase.CANCELLED, target) is False


def test_abandoned_to_anything_invalid():
    for target in Phase:
        assert can_transition(Phase.ABANDONED, target) is False


def test_same_state_transition_invalid():
    for phase in Phase:
        assert can_transition(phase, phase) is False


# ── Terminal states ───────────────────────────────────────────────

def test_terminal_phases():
    assert is_terminal(Phase.COMPLETED) is True
    assert is_terminal(Phase.CANCELLED) is True
    assert is_terminal(Phase.ABANDONED) is True


def test_non_terminal_phases():
    assert is_terminal(Phase.CREATED) is False
    assert is_terminal(Phase.WAITING) is False
    assert is_terminal(Phase.IN_PROGRESS) is False
    assert is_terminal(Phase.OVERTIME) is False
    assert is_terminal(Phase.PAUSED) is False


# ── validate_transition raises on invalid ─────────────────────────

def test_validate_transition_raises_on_invalid():
    with pytest.raises(ValueError, match="انتقال غير صالح"):
        validate_transition(Phase.COMPLETED, Phase.IN_PROGRESS)


def test_validate_transition_passes_on_valid():
    validate_transition(Phase.CREATED, Phase.WAITING)  # Should not raise
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_minigame_engine/test_state_machine.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement the state machine**

Create `backend/app/modules/minigames/state_machine.py`:

```python
"""Session state machine — defines valid phase transitions.

The transition map encodes BRD Section 6.3. Terminal states (COMPLETED,
CANCELLED, ABANDONED) have no outgoing transitions. Once reached, all
further actions are rejected.
"""

from app.core.enums import MinigameSessionPhase as Phase

# Valid transitions: from_phase → set of allowed to_phases
TRANSITION_MAP: dict[Phase, set[Phase]] = {
    Phase.CREATED: {Phase.WAITING, Phase.CANCELLED},
    Phase.WAITING: {Phase.READY, Phase.CANCELLED},
    Phase.READY: {Phase.IN_PROGRESS, Phase.CANCELLED},
    Phase.IN_PROGRESS: {
        Phase.COMPLETED,
        Phase.OVERTIME,
        Phase.PAUSED,
        Phase.ABANDONED,
        Phase.CANCELLED,
    },
    Phase.OVERTIME: {Phase.COMPLETED, Phase.ABANDONED},
    Phase.PAUSED: {Phase.IN_PROGRESS, Phase.ABANDONED},
    # Terminal states — no outgoing transitions
    Phase.COMPLETED: set(),
    Phase.CANCELLED: set(),
    Phase.ABANDONED: set(),
}

TERMINAL_PHASES: frozenset[Phase] = frozenset({
    Phase.COMPLETED,
    Phase.CANCELLED,
    Phase.ABANDONED,
})


def can_transition(from_phase: Phase, to_phase: Phase) -> bool:
    """Check whether a state transition is allowed."""
    return to_phase in TRANSITION_MAP.get(from_phase, set())


def validate_transition(from_phase: Phase, to_phase: Phase) -> None:
    """Raise ValueError if the transition is not allowed."""
    if not can_transition(from_phase, to_phase):
        raise ValueError(
            f"انتقال غير صالح: {from_phase.value} → {to_phase.value}"
        )


def is_terminal(phase: Phase) -> bool:
    """Check whether a phase is a terminal (final) state."""
    return phase in TERMINAL_PHASES
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_minigame_engine/test_state_machine.py -v`
Expected: All 24 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/modules/minigames/state_machine.py
git add backend/tests/test_minigame_engine/test_state_machine.py
git commit -m "feat(minigames): add session state machine — transition map with 15 valid paths and 3 terminal states"
```

---

## Task 5: Database Models

**Files:**
- Create: `backend/app/modules/minigames/models.py`

- [ ] **Step 1: Write the models**

Create `backend/app/modules/minigames/models.py`:

```python
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
    MinigameTurnSide,
    MinigameTypeStatus,
)
from app.core.models import Base, pg_enum
from app.core.utils import now_riyadh_naive


# ── Game Type Registry ────────────────────────────────────────────

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


# ── Game Session ──────────────────────────────────────────────────

class MinigameSession(Base):
    __tablename__ = "minigame_sessions"
    __table_args__ = (
        CheckConstraint("buy_in_amount >= 0", name="chk_mg_buy_in"),
        CheckConstraint("revision >= 0", name="chk_mg_revision"),
        CheckConstraint("turn_number >= 0", name="chk_mg_turn_number"),
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

    player_1_membership_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=False
    )
    player_2_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("memberships.id", ondelete="RESTRICT")
    )

    match_type: Mapped[MinigameMatchType] = mapped_column(
        pg_enum(MinigameMatchType, name="minigame_match_type"), nullable=False
    )
    current_turn: Mapped[MinigameTurnSide | None] = mapped_column(
        pg_enum(MinigameTurnSide, name="minigame_turn_side")
    )
    turn_number: Mapped[int] = mapped_column(nullable=False, default=0)

    game_state: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    settings_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    buy_in_amount: Mapped[int] = mapped_column(nullable=False, default=0)

    reconnect_token_p1: Mapped[str | None] = mapped_column(String(128))
    reconnect_token_p2: Mapped[str | None] = mapped_column(String(128))

    terminal_reason: Mapped[str | None] = mapped_column(String(100))
    winner_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("memberships.id", ondelete="SET NULL")
    )

    turn_started_at: Mapped[datetime | None] = mapped_column()
    turn_duration_ms: Mapped[int] = mapped_column(nullable=False, default=30000)
    grace_timer_ms: Mapped[int] = mapped_column(nullable=False, default=60000)

    correlation_id: Mapped[uuid.UUID] = mapped_column(UUID, nullable=False, default=uuid.uuid4)

    started_at: Mapped[datetime | None] = mapped_column()
    completed_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(default=now_riyadh_naive)
    updated_at: Mapped[datetime] = mapped_column(default=now_riyadh_naive, onupdate=now_riyadh_naive)


# ── Session Events (append-only) ─────────────────────────────────

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
    event_type: Mapped[str] = mapped_column(String(20), nullable=False)  # action | transition | system
    actor_type: Mapped[str] = mapped_column(String(20), nullable=False)  # player | system | admin
    actor_membership_id: Mapped[uuid.UUID | None] = mapped_column(UUID)

    action_type: Mapped[str | None] = mapped_column(String(50))
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    result: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    from_phase: Mapped[str | None] = mapped_column(String(20))
    to_phase: Mapped[str | None] = mapped_column(String(20))

    correlation_id: Mapped[uuid.UUID] = mapped_column(UUID, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=now_riyadh_naive)


# ── Action Receipts (idempotency) ────────────────────────────────

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


# ── Session Settlements ──────────────────────────────────────────

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
    winner_membership_id: Mapped[uuid.UUID | None] = mapped_column(UUID)
    loser_membership_id: Mapped[uuid.UUID | None] = mapped_column(UUID)
    winner_payout: Mapped[int] = mapped_column(nullable=False, default=0)
    loser_penalty: Mapped[int] = mapped_column(nullable=False, default=0)
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


# ── Leaderboard ──────────────────────────────────────────────────

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


# ── Policy Rules ─────────────────────────────────────────────────

class MinigamePolicyRule(Base):
    __tablename__ = "minigame_policy_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    game_type: Mapped[str | None] = mapped_column(String(64))  # null = all games
    competition_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("competitions.id", ondelete="CASCADE")
    )
    scope: Mapped[str] = mapped_column(String(30), nullable=False)  # per_player_daily, per_pair_cycle
    action: Mapped[str] = mapped_column(String(30), nullable=False)  # duel, challenge, queue
    limit_value: Mapped[int] = mapped_column(nullable=False)
    window: Mapped[str] = mapped_column(String(20), nullable=False)  # 24h, cycle, season
    enabled: Mapped[bool] = mapped_column(nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(default=now_riyadh_naive)
    updated_at: Mapped[datetime] = mapped_column(default=now_riyadh_naive, onupdate=now_riyadh_naive)
```

- [ ] **Step 2: Register models in core/models.py**

Add to the end of `backend/app/core/models.py` (after the last import block):

```python
from app.modules.minigames.models import (  # noqa: E402, F401
    MinigameActionReceipt,
    MinigameLeaderboard,
    MinigamePolicyRule,
    MinigameSession,
    MinigameSessionEvent,
    MinigameSessionSettlement,
    MinigameType,
)
```

- [ ] **Step 3: Verify models are importable**

Run: `cd backend && python -c "from app.core.models import Base; tables = [t for t in Base.metadata.tables if t.startswith('minigame')]; print(f'{len(tables)} minigame tables found:', tables)"`

Expected output: `7 minigame tables found: ['minigame_types', 'minigame_sessions', 'minigame_session_events', 'minigame_action_receipts', 'minigame_session_settlements', 'minigame_leaderboards', 'minigame_policy_rules']`

- [ ] **Step 4: Commit**

```bash
git add backend/app/modules/minigames/models.py backend/app/core/models.py
git commit -m "feat(minigames): add 7 database models — types, sessions, events, receipts, settlements, leaderboards, policy rules"
```

---

## Task 6: SQL Migration

**Files:**
- Create: `backend/migrations/002_minigame_engine.sql`

- [ ] **Step 1: Write the migration**

Create `backend/migrations/002_minigame_engine.sql`:

```sql
-- ============================================================
-- Migration 002: Minigame Engine tables
-- BRD: docs/minigames/War of Names - Minigame Engine BRD - V1.0.md
-- ============================================================

BEGIN;

-- ── New ENUM types ───────────────────────────────────────────

CREATE TYPE minigame_type_status AS ENUM ('active', 'disabled', 'deprecated');
CREATE TYPE minigame_session_phase AS ENUM ('created', 'waiting', 'ready', 'in_progress', 'overtime', 'paused', 'completed', 'cancelled', 'abandoned');
CREATE TYPE minigame_match_type AS ENUM ('challenge', 'queue');
CREATE TYPE minigame_settlement_state AS ENUM ('pending', 'settled', 'failed', 'reconciled');
CREATE TYPE minigame_turn_side AS ENUM ('player_1', 'player_2');

-- ── Extend existing ledger_entry_type ────────────────────────

ALTER TYPE ledger_entry_type ADD VALUE IF NOT EXISTS 'minigame_buy_in';
ALTER TYPE ledger_entry_type ADD VALUE IF NOT EXISTS 'minigame_payout';
ALTER TYPE ledger_entry_type ADD VALUE IF NOT EXISTS 'minigame_forfeit';
ALTER TYPE ledger_entry_type ADD VALUE IF NOT EXISTS 'minigame_refund';
ALTER TYPE ledger_entry_type ADD VALUE IF NOT EXISTS 'minigame_cancel_penalty';

-- ── minigame_types ───────────────────────────────────────────

CREATE TABLE minigame_types (
    id              VARCHAR(64) PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    description     TEXT,
    plugin_api_version      VARCHAR(10) NOT NULL DEFAULT '1.0',
    settings_schema_version VARCHAR(10) NOT NULL DEFAULT '1.0',
    min_players     INTEGER NOT NULL DEFAULT 2,
    max_players     INTEGER NOT NULL DEFAULT 2,
    supports_overtime   BOOLEAN NOT NULL DEFAULT FALSE,
    supports_spectators BOOLEAN NOT NULL DEFAULT FALSE,
    supports_ranked     BOOLEAN NOT NULL DEFAULT FALSE,
    supports_team_mode  BOOLEAN NOT NULL DEFAULT FALSE,
    status          minigame_type_status NOT NULL DEFAULT 'active',
    created_at      TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

-- ── minigame_sessions ────────────────────────────────────────

CREATE TABLE minigame_sessions (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_type               VARCHAR(64) NOT NULL REFERENCES minigame_types(id) ON DELETE RESTRICT,
    competition_id          UUID NOT NULL REFERENCES competitions(id) ON DELETE RESTRICT,
    season_id               UUID REFERENCES seasons(id) ON DELETE SET NULL,
    cycle_id                UUID REFERENCES cycles(id) ON DELETE SET NULL,

    phase                   minigame_session_phase NOT NULL DEFAULT 'created',
    revision                INTEGER NOT NULL DEFAULT 0,

    player_1_membership_id  UUID NOT NULL REFERENCES memberships(id) ON DELETE RESTRICT,
    player_2_membership_id  UUID REFERENCES memberships(id) ON DELETE RESTRICT,

    match_type              minigame_match_type NOT NULL,
    current_turn            minigame_turn_side,
    turn_number             INTEGER NOT NULL DEFAULT 0,

    game_state              JSONB NOT NULL DEFAULT '{}'::jsonb,
    settings_snapshot       JSONB NOT NULL DEFAULT '{}'::jsonb,

    buy_in_amount           INTEGER NOT NULL DEFAULT 0,

    reconnect_token_p1      VARCHAR(128),
    reconnect_token_p2      VARCHAR(128),

    terminal_reason         VARCHAR(100),
    winner_membership_id    UUID REFERENCES memberships(id) ON DELETE SET NULL,

    turn_started_at         TIMESTAMP WITHOUT TIME ZONE,
    turn_duration_ms        INTEGER NOT NULL DEFAULT 30000,
    grace_timer_ms          INTEGER NOT NULL DEFAULT 60000,

    correlation_id          UUID NOT NULL DEFAULT gen_random_uuid(),

    started_at              TIMESTAMP WITHOUT TIME ZONE,
    completed_at            TIMESTAMP WITHOUT TIME ZONE,
    created_at              TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_mg_buy_in CHECK (buy_in_amount >= 0),
    CONSTRAINT chk_mg_revision CHECK (revision >= 0),
    CONSTRAINT chk_mg_turn_number CHECK (turn_number >= 0)
);

CREATE INDEX idx_mg_sessions_active
    ON minigame_sessions (game_type, competition_id)
    WHERE phase NOT IN ('completed', 'cancelled', 'abandoned');

-- ── minigame_session_events ──────────────────────────────────

CREATE TABLE minigame_session_events (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id              UUID NOT NULL REFERENCES minigame_sessions(id) ON DELETE CASCADE,
    revision                INTEGER NOT NULL,
    event_type              VARCHAR(20) NOT NULL,
    actor_type              VARCHAR(20) NOT NULL,
    actor_membership_id     UUID,

    action_type             VARCHAR(50),
    payload                 JSONB NOT NULL DEFAULT '{}'::jsonb,
    result                  JSONB NOT NULL DEFAULT '{}'::jsonb,

    from_phase              VARCHAR(20),
    to_phase                VARCHAR(20),

    correlation_id          UUID NOT NULL,
    created_at              TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_mg_events_session ON minigame_session_events (session_id, revision);

-- ── minigame_action_receipts ─────────────────────────────────

CREATE TABLE minigame_action_receipts (
    action_id               UUID PRIMARY KEY,
    session_id              UUID NOT NULL REFERENCES minigame_sessions(id) ON DELETE CASCADE,
    actor_membership_id     UUID NOT NULL,
    client_seq              INTEGER NOT NULL,
    response                JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at              TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_mg_action_seq UNIQUE (session_id, actor_membership_id, client_seq)
);

-- ── minigame_session_settlements ─────────────────────────────

CREATE TABLE minigame_session_settlements (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id              UUID NOT NULL REFERENCES minigame_sessions(id) ON DELETE RESTRICT,
    winner_membership_id    UUID,
    loser_membership_id     UUID,
    winner_payout           INTEGER NOT NULL DEFAULT 0,
    loser_penalty           INTEGER NOT NULL DEFAULT 0,
    settlement_state        minigame_settlement_state NOT NULL DEFAULT 'pending',
    ledger_entry_ids        UUID[],
    correlation_id          UUID NOT NULL,
    settled_at              TIMESTAMP WITHOUT TIME ZONE,
    failure_reason          TEXT,
    retry_count             INTEGER NOT NULL DEFAULT 0,
    created_at              TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_mg_settlement_session UNIQUE (session_id),
    CONSTRAINT chk_mg_retry_count CHECK (retry_count >= 0 AND retry_count <= 3)
);

-- ── minigame_leaderboards ────────────────────────────────────

CREATE TABLE minigame_leaderboards (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_type               VARCHAR(64) NOT NULL REFERENCES minigame_types(id) ON DELETE CASCADE,
    competition_id          UUID NOT NULL REFERENCES competitions(id) ON DELETE CASCADE,
    membership_id           UUID NOT NULL REFERENCES memberships(id) ON DELETE CASCADE,
    wins                    INTEGER NOT NULL DEFAULT 0,
    losses                  INTEGER NOT NULL DEFAULT 0,
    current_streak          INTEGER NOT NULL DEFAULT 0,
    best_streak             INTEGER NOT NULL DEFAULT 0,
    total_matches           INTEGER NOT NULL DEFAULT 0,
    avg_tools_used          DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    avg_match_duration_sec  DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    elo_rating              INTEGER,
    updated_at              TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_mg_leaderboard UNIQUE (game_type, competition_id, membership_id)
);

-- ── minigame_policy_rules ────────────────────────────────────

CREATE TABLE minigame_policy_rules (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_type               VARCHAR(64),
    competition_id          UUID REFERENCES competitions(id) ON DELETE CASCADE,
    scope                   VARCHAR(30) NOT NULL,
    action                  VARCHAR(30) NOT NULL,
    limit_value             INTEGER NOT NULL,
    window                  VARCHAR(20) NOT NULL,
    enabled                 BOOLEAN NOT NULL DEFAULT TRUE,
    created_at              TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

COMMIT;
```

- [ ] **Step 2: Verify migration syntax**

Run: `cd backend && python -c "with open('migrations/002_minigame_engine.sql') as f: lines = f.readlines(); print(f'Migration has {len(lines)} lines, starts with: {lines[0].strip()}, ends with: {lines[-1].strip()}')""`

Expected: `Migration has ~NNN lines, starts with: -- ============================================================, ends with: COMMIT;`

- [ ] **Step 3: Commit**

```bash
git add backend/migrations/002_minigame_engine.sql
git commit -m "feat(minigames): add SQL migration 002 — 7 tables, 5 enum types, ledger type extension"
```

---

## Task 7: Integration — Wire Up and Final Verification

**Files:**
- Verify: all models discoverable by `Base.metadata.create_all`

- [ ] **Step 1: Run all minigame tests together**

Run: `cd backend && python -m pytest tests/test_minigame_engine/ -v`

Expected: All tests pass (7 enum + 12 plugin + 5 registry + 24 state machine = 48 tests)

- [ ] **Step 2: Verify imports work end-to-end**

Run:
```bash
cd backend && python -c "
from app.core.enums import MinigameSessionPhase, MinigameMatchType, MinigameSettlementState
from app.modules.minigames.plugin import GameTypePlugin
from app.modules.minigames.registry import GameTypeRegistry
from app.modules.minigames.state_machine import can_transition, is_terminal, TERMINAL_PHASES
from app.modules.minigames.models import (
    MinigameType, MinigameSession, MinigameSessionEvent,
    MinigameActionReceipt, MinigameSessionSettlement,
    MinigameLeaderboard, MinigamePolicyRule,
)
print('All imports OK')
print(f'Phases: {len(list(MinigameSessionPhase))}')
print(f'Terminal: {len(TERMINAL_PHASES)}')
print(f'Registry plugins: {len(GameTypeRegistry.list_all())}')
"
```

Expected:
```
All imports OK
Phases: 9
Terminal: 3
Registry plugins: 0
```

- [ ] **Step 3: Final commit with all tests green**

```bash
git add -A
git commit -m "feat(minigames): Sprint 0 complete — engine foundation with 7 models, plugin contract, registry, state machine (48 tests)"
```

---

## Sprint 0 Deliverables Summary

| Component | Files | Tests |
|---|---|---|
| Enums (5 new + 5 ledger) | `core/enums.py` | 7 |
| Plugin Contract | `minigames/plugin.py` | 12 |
| Game Type Registry | `minigames/registry.py` | 5 |
| Session State Machine | `minigames/state_machine.py` | 24 |
| Database Models (7) | `minigames/models.py` | via import verification |
| SQL Migration | `migrations/002_minigame_engine.sql` | via Docker rebuild |
| Model Registration | `core/models.py` | via import verification |
| **Total** | **8 files created/modified** | **48 tests** |

## What Sprint 1 Will Build On This

Sprint 1 (Session Service & Economy) will use:
- `MinigameSession` model for CRUD operations
- `state_machine.validate_transition()` for phase changes
- `GameTypeRegistry.get()` to resolve plugin logic
- `MinigameSessionEvent` for action logging
- `MinigameActionReceipt` for idempotency
- `MinigameSessionSettlement` + `LedgerEntry` for financial settlement
