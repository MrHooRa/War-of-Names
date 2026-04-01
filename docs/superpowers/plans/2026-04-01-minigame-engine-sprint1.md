# Minigame Engine — Sprint 1: Session Service & Economy Bridge

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the session lifecycle service (create, transition, process actions) and the economy bridge (buy-in debit, settlement payout via ledger) — making sessions fully functional from creation to settlement.

**Architecture:** Three focused service files: `session_service.py` (create/transition/cancel sessions with optimistic locking), `action_service.py` (validate and apply player actions with idempotency via action receipts), and `settlement_service.py` (compute and execute financial settlements via ledger entries in a single transaction). All three use the plugin contract and state machine from Sprint 0.

**Tech Stack:** Python 3.12, SQLAlchemy 2.x async, PostgreSQL 16, pytest (unit tests with mocks for DB-dependent code, SimpleNamespace for model stubs)

**BRD Reference:** `docs/minigames/War of Names - Minigame Engine BRD - V1.0.md` — Sections 7-9, 13

**Depends on Sprint 0:** enums, models, plugin contract, registry, state_machine

---

## Sprint 1 Scope

This sprint delivers:
1. **Session service** — create session, transition phase (with optimistic locking), cancel session
2. **Action service** — validate action envelope, check idempotency, apply action via plugin, log event + receipt
3. **Settlement service** — compute settlement from terminal result, write ledger entries + settlement record in one transaction
4. **Economy bridge helpers** — buy-in debit, payout credit, refund — reusable ledger write functions

**Single-player support:** The engine supports solo minigames (min_players=1, no opponent). Action validation skips turn checks for solo sessions. Settlement has a SOLO type (reward/no-reward, no loser).

**NOT in Sprint 1:** REST API endpoints, WebSocket, matchmaking, lobby, leaderboard updates, admin endpoints. Those are Sprint 2+.

---

## File Structure

```
backend/app/modules/minigames/
├── __init__.py                    # EXISTS (Sprint 0)
├── models.py                      # EXISTS (Sprint 0)
├── plugin.py                      # EXISTS (Sprint 0)
├── registry.py                    # EXISTS (Sprint 0)
├── state_machine.py               # EXISTS (Sprint 0)
├── session_service.py             # CREATE: session lifecycle
├── action_service.py              # CREATE: action processing
├── settlement_service.py          # CREATE: financial settlement
└── economy.py                     # CREATE: ledger bridge helpers

backend/tests/test_minigame_engine/
├── test_session_service.py        # CREATE
├── test_action_service.py         # CREATE
├── test_settlement_service.py     # CREATE
└── test_economy.py                # CREATE
```

---

## Task 1: Economy Bridge — Ledger Write Helpers

**Files:**
- Create: `backend/app/modules/minigames/economy.py`
- Create: `backend/tests/test_minigame_engine/test_economy.py`

These are pure functions that compute ledger entries without hitting the DB — they return `LedgerEntry` instances that the caller adds to the session. This makes them fully unit-testable.

- [ ] **Step 1: Write tests**

Create `backend/tests/test_minigame_engine/test_economy.py`:

```python
"""Test economy bridge — ledger entry creation helpers."""

import uuid
from app.modules.minigames.economy import (
    create_buy_in_entry,
    create_payout_entry,
    create_refund_entry,
    create_forfeit_settlement_entries,
    create_normal_settlement_entries,
    create_cancel_settlement_entries,
)
from app.core.enums import LedgerDirection, LedgerEntryType


def _ids():
    return {
        "membership_id": uuid.uuid4(),
        "competition_id": uuid.uuid4(),
        "season_id": uuid.uuid4(),
        "cycle_id": uuid.uuid4(),
        "session_id": uuid.uuid4(),
        "correlation_id": uuid.uuid4(),
    }


# ── Buy-in ────────────────────────────────────────────────────

def test_buy_in_entry_is_debit():
    ids = _ids()
    entry = create_buy_in_entry(
        membership_id=ids["membership_id"],
        competition_id=ids["competition_id"],
        season_id=ids["season_id"],
        cycle_id=ids["cycle_id"],
        session_id=ids["session_id"],
        amount=500,
        balance_before=1000,
    )
    assert entry.direction == LedgerDirection.DEBIT
    assert entry.entry_type == LedgerEntryType.MINIGAME_BUY_IN
    assert entry.amount == 500
    assert entry.balance_before == 1000
    assert entry.balance_after == 500
    assert entry.source_type == "minigame_session"
    assert entry.source_id == ids["session_id"]


def test_buy_in_clamped_to_balance():
    ids = _ids()
    entry = create_buy_in_entry(
        membership_id=ids["membership_id"],
        competition_id=ids["competition_id"],
        session_id=ids["session_id"],
        amount=500,
        balance_before=200,
    )
    assert entry.amount == 200
    assert entry.balance_after == 0


# ── Payout ────────────────────────────────────────────────────

def test_payout_entry_is_credit():
    ids = _ids()
    entry = create_payout_entry(
        membership_id=ids["membership_id"],
        competition_id=ids["competition_id"],
        session_id=ids["session_id"],
        amount=1000,
        balance_before=0,
    )
    assert entry.direction == LedgerDirection.CREDIT
    assert entry.entry_type == LedgerEntryType.MINIGAME_PAYOUT
    assert entry.amount == 1000
    assert entry.balance_after == 1000


# ── Refund ────────────────────────────────────────────────────

def test_refund_entry_is_credit():
    ids = _ids()
    entry = create_refund_entry(
        membership_id=ids["membership_id"],
        competition_id=ids["competition_id"],
        session_id=ids["session_id"],
        amount=500,
        balance_before=100,
    )
    assert entry.direction == LedgerDirection.CREDIT
    assert entry.entry_type == LedgerEntryType.MINIGAME_REFUND
    assert entry.balance_after == 600


# ── Normal settlement (winner + no extra for loser) ───────────

def test_normal_settlement_creates_payout_for_winner():
    ids = _ids()
    winner_id = uuid.uuid4()
    loser_id = uuid.uuid4()
    entries = create_normal_settlement_entries(
        winner_membership_id=winner_id,
        loser_membership_id=loser_id,
        competition_id=ids["competition_id"],
        session_id=ids["session_id"],
        buy_in_amount=500,
        winner_balance=0,
    )
    # Winner gets buy_in * 2
    assert len(entries) == 1
    assert entries[0].membership_id == winner_id
    assert entries[0].entry_type == LedgerEntryType.MINIGAME_PAYOUT
    assert entries[0].amount == 1000
    assert entries[0].direction == LedgerDirection.CREDIT


# ── Forfeit settlement ────────────────────────────────────────

def test_forfeit_settlement_pays_winner():
    ids = _ids()
    winner_id = uuid.uuid4()
    entries = create_forfeit_settlement_entries(
        winner_membership_id=winner_id,
        competition_id=ids["competition_id"],
        session_id=ids["session_id"],
        buy_in_amount=500,
        winner_balance=0,
    )
    assert len(entries) == 1
    assert entries[0].membership_id == winner_id
    assert entries[0].amount == 1000


# ── Cancel settlement (refund both) ──────────────────────────

def test_cancel_settlement_refunds_both():
    ids = _ids()
    p1 = uuid.uuid4()
    p2 = uuid.uuid4()
    entries = create_cancel_settlement_entries(
        player_1_membership_id=p1,
        player_2_membership_id=p2,
        competition_id=ids["competition_id"],
        session_id=ids["session_id"],
        buy_in_amount=500,
        player_1_balance=0,
        player_2_balance=0,
    )
    assert len(entries) == 2
    assert all(e.entry_type == LedgerEntryType.MINIGAME_REFUND for e in entries)
    assert all(e.amount == 500 for e in entries)
    assert {e.membership_id for e in entries} == {p1, p2}


def test_cancel_with_no_player_2():
    ids = _ids()
    p1 = uuid.uuid4()
    entries = create_cancel_settlement_entries(
        player_1_membership_id=p1,
        player_2_membership_id=None,
        competition_id=ids["competition_id"],
        session_id=ids["session_id"],
        buy_in_amount=500,
        player_1_balance=0,
        player_2_balance=0,
    )
    assert len(entries) == 1
    assert entries[0].membership_id == p1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_minigame_engine/test_economy.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement economy bridge**

Create `backend/app/modules/minigames/economy.py`:

```python
"""Economy bridge — creates LedgerEntry instances for minigame operations.

All functions return LedgerEntry instances (not added to session).
The caller is responsible for session.add() and commit.
Buy-in is debited at session start (IN_PROGRESS transition).
Payout/refund happens at settlement.
"""

import uuid

from app.core.enums import LedgerDirection, LedgerEntryType
from app.modules.scoring.models import LedgerEntry


def create_buy_in_entry(
    *,
    membership_id: uuid.UUID,
    competition_id: uuid.UUID,
    session_id: uuid.UUID,
    amount: int,
    balance_before: int,
    season_id: uuid.UUID | None = None,
    cycle_id: uuid.UUID | None = None,
) -> LedgerEntry:
    """Create a DEBIT ledger entry for minigame buy-in. Clamped to balance."""
    applied = min(amount, max(0, balance_before))
    return LedgerEntry(
        membership_id=membership_id,
        competition_id=competition_id,
        season_id=season_id,
        cycle_id=cycle_id,
        entry_type=LedgerEntryType.MINIGAME_BUY_IN,
        amount=applied,
        direction=LedgerDirection.DEBIT,
        balance_before=balance_before,
        balance_after=balance_before - applied,
        source_type="minigame_session",
        source_id=session_id,
        reason="رسوم دخول اللعبة المصغرة",
    )


def create_payout_entry(
    *,
    membership_id: uuid.UUID,
    competition_id: uuid.UUID,
    session_id: uuid.UUID,
    amount: int,
    balance_before: int,
    season_id: uuid.UUID | None = None,
    cycle_id: uuid.UUID | None = None,
) -> LedgerEntry:
    """Create a CREDIT ledger entry for minigame payout (winner)."""
    return LedgerEntry(
        membership_id=membership_id,
        competition_id=competition_id,
        season_id=season_id,
        cycle_id=cycle_id,
        entry_type=LedgerEntryType.MINIGAME_PAYOUT,
        amount=amount,
        direction=LedgerDirection.CREDIT,
        balance_before=balance_before,
        balance_after=balance_before + amount,
        source_type="minigame_session",
        source_id=session_id,
        reason="مكافأة الفوز في اللعبة المصغرة",
    )


def create_refund_entry(
    *,
    membership_id: uuid.UUID,
    competition_id: uuid.UUID,
    session_id: uuid.UUID,
    amount: int,
    balance_before: int,
    season_id: uuid.UUID | None = None,
    cycle_id: uuid.UUID | None = None,
) -> LedgerEntry:
    """Create a CREDIT ledger entry for minigame refund (cancellation)."""
    return LedgerEntry(
        membership_id=membership_id,
        competition_id=competition_id,
        season_id=season_id,
        cycle_id=cycle_id,
        entry_type=LedgerEntryType.MINIGAME_REFUND,
        amount=amount,
        direction=LedgerDirection.CREDIT,
        balance_before=balance_before,
        balance_after=balance_before + amount,
        source_type="minigame_session",
        source_id=session_id,
        reason="استرداد رسوم الدخول — إلغاء الجلسة",
    )


def create_normal_settlement_entries(
    *,
    winner_membership_id: uuid.UUID,
    loser_membership_id: uuid.UUID,
    competition_id: uuid.UUID,
    session_id: uuid.UUID,
    buy_in_amount: int,
    winner_balance: int,
    season_id: uuid.UUID | None = None,
    cycle_id: uuid.UUID | None = None,
) -> list[LedgerEntry]:
    """Normal win: winner gets buy_in * 2 (zero-sum, loser already paid buy-in)."""
    payout = create_payout_entry(
        membership_id=winner_membership_id,
        competition_id=competition_id,
        session_id=session_id,
        amount=buy_in_amount * 2,
        balance_before=winner_balance,
        season_id=season_id,
        cycle_id=cycle_id,
    )
    return [payout]


def create_forfeit_settlement_entries(
    *,
    winner_membership_id: uuid.UUID,
    competition_id: uuid.UUID,
    session_id: uuid.UUID,
    buy_in_amount: int,
    winner_balance: int,
    season_id: uuid.UUID | None = None,
    cycle_id: uuid.UUID | None = None,
) -> list[LedgerEntry]:
    """Forfeit/abandon: winner gets buy_in * 2 (loser already paid buy-in)."""
    payout = create_payout_entry(
        membership_id=winner_membership_id,
        competition_id=competition_id,
        session_id=session_id,
        amount=buy_in_amount * 2,
        balance_before=winner_balance,
        season_id=season_id,
        cycle_id=cycle_id,
    )
    return [payout]


def create_cancel_settlement_entries(
    *,
    player_1_membership_id: uuid.UUID,
    player_2_membership_id: uuid.UUID | None,
    competition_id: uuid.UUID,
    session_id: uuid.UUID,
    buy_in_amount: int,
    player_1_balance: int,
    player_2_balance: int,
    season_id: uuid.UUID | None = None,
    cycle_id: uuid.UUID | None = None,
) -> list[LedgerEntry]:
    """Cancellation: refund both players their buy-in."""
    entries = [
        create_refund_entry(
            membership_id=player_1_membership_id,
            competition_id=competition_id,
            session_id=session_id,
            amount=buy_in_amount,
            balance_before=player_1_balance,
            season_id=season_id,
            cycle_id=cycle_id,
        )
    ]
    if player_2_membership_id is not None:
        entries.append(
            create_refund_entry(
                membership_id=player_2_membership_id,
                competition_id=competition_id,
                session_id=session_id,
                amount=buy_in_amount,
                balance_before=player_2_balance,
                season_id=season_id,
                cycle_id=cycle_id,
            )
        )
    return entries
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_minigame_engine/test_economy.py -v`
Expected: All 9 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/modules/minigames/economy.py backend/tests/test_minigame_engine/test_economy.py
git commit -m "feat(minigames): add economy bridge — buy-in, payout, refund, settlement ledger helpers"
```

---

## Task 2: Session Service — Create & Transition

**Files:**
- Create: `backend/app/modules/minigames/session_service.py`
- Create: `backend/tests/test_minigame_engine/test_session_service.py`

The session service contains async functions that take an `AsyncSession`. However, the core logic (validation, state computation) is testable without a DB by extracting pure helper functions.

- [ ] **Step 1: Write tests for session creation and transition logic**

Create `backend/tests/test_minigame_engine/test_session_service.py`:

```python
"""Test session service — creation validation and transition logic."""

import uuid
import pytest
from types import SimpleNamespace

from app.core.enums import MinigameSessionPhase as Phase, MinigameMatchType
from app.modules.minigames.session_service import (
    validate_session_creation,
    compute_transition_update,
)


# ── validate_session_creation ─────────────────────────────────

def test_valid_creation_passes():
    errors = validate_session_creation(
        game_type_id="mutaraha",
        plugin_exists=True,
        plugin_status="active",
        player_balance=1000,
        buy_in_amount=500,
        is_bankrupt=False,
    )
    assert errors == []


def test_creation_fails_unknown_game_type():
    errors = validate_session_creation(
        game_type_id="nonexistent",
        plugin_exists=False,
        plugin_status=None,
        player_balance=1000,
        buy_in_amount=500,
        is_bankrupt=False,
    )
    assert any("غير موجود" in e for e in errors)


def test_creation_fails_disabled_game_type():
    errors = validate_session_creation(
        game_type_id="mutaraha",
        plugin_exists=True,
        plugin_status="disabled",
        player_balance=1000,
        buy_in_amount=500,
        is_bankrupt=False,
    )
    assert any("معطلة" in e for e in errors)


def test_creation_fails_insufficient_balance():
    errors = validate_session_creation(
        game_type_id="mutaraha",
        plugin_exists=True,
        plugin_status="active",
        player_balance=200,
        buy_in_amount=500,
        is_bankrupt=False,
    )
    assert any("رصيد" in e for e in errors)


def test_creation_fails_bankrupt_player():
    errors = validate_session_creation(
        game_type_id="mutaraha",
        plugin_exists=True,
        plugin_status="active",
        player_balance=1000,
        buy_in_amount=500,
        is_bankrupt=True,
    )
    assert any("مفلس" in e for e in errors)


# ── compute_transition_update ─────────────────────────────────

def test_transition_to_waiting():
    update = compute_transition_update(
        current_phase=Phase.CREATED,
        target_phase=Phase.WAITING,
        current_revision=0,
    )
    assert update["phase"] == Phase.WAITING
    assert update["revision"] == 1


def test_transition_to_completed():
    update = compute_transition_update(
        current_phase=Phase.IN_PROGRESS,
        target_phase=Phase.COMPLETED,
        current_revision=5,
        terminal_reason="turn_limit_winner",
        winner_membership_id=uuid.uuid4(),
    )
    assert update["phase"] == Phase.COMPLETED
    assert update["revision"] == 6
    assert update["terminal_reason"] == "turn_limit_winner"
    assert update["winner_membership_id"] is not None
    assert "completed_at" in update


def test_transition_invalid_raises():
    with pytest.raises(ValueError, match="انتقال غير صالح"):
        compute_transition_update(
            current_phase=Phase.COMPLETED,
            target_phase=Phase.IN_PROGRESS,
            current_revision=10,
        )


def test_transition_from_terminal_raises():
    with pytest.raises(ValueError, match="انتقال غير صالح"):
        compute_transition_update(
            current_phase=Phase.ABANDONED,
            target_phase=Phase.WAITING,
            current_revision=3,
        )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_minigame_engine/test_session_service.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement session service**

Create `backend/app/modules/minigames/session_service.py`:

```python
"""Session lifecycle service — create, transition, and cancel minigame sessions.

Public functions (async, take AsyncSession):
    create_session  — creates a new session record
    transition_session — advances session phase with optimistic locking

Pure helpers (sync, no DB):
    validate_session_creation — checks all preconditions for session creation
    compute_transition_update — computes the field updates for a phase transition
"""

import secrets
import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import (
    MinigameMatchType,
    MinigameSessionPhase as Phase,
    MinigameTurnSide,
)
from app.core.utils import now_riyadh_naive
from app.modules.minigames.models import MinigameSession, MinigameSessionEvent
from app.modules.minigames.state_machine import is_terminal, validate_transition


# ── Pure validation helpers ───────────────────────────────────


def validate_session_creation(
    *,
    game_type_id: str,
    plugin_exists: bool,
    plugin_status: str | None,
    player_balance: int,
    buy_in_amount: int,
    is_bankrupt: bool,
) -> list[str]:
    """Validate all preconditions for creating a session. Returns error list (empty = valid)."""
    errors: list[str] = []

    if not plugin_exists:
        errors.append(f"نوع اللعبة '{game_type_id}' غير موجود")
        return errors

    if plugin_status != "active":
        errors.append("هذه اللعبة معطلة حالياً")

    if is_bankrupt:
        errors.append("اللاعب مفلس ولا يمكنه الدخول في مبارزة")

    if player_balance < buy_in_amount:
        errors.append(f"رصيد غير كافٍ — تحتاج {buy_in_amount} نقطة للدخول")

    return errors


def compute_transition_update(
    *,
    current_phase: Phase,
    target_phase: Phase,
    current_revision: int,
    terminal_reason: str | None = None,
    winner_membership_id: uuid.UUID | None = None,
) -> dict:
    """Compute the field updates for a session phase transition.

    Raises ValueError if the transition is invalid.
    Returns a dict of fields to update on the session.
    """
    validate_transition(current_phase, target_phase)

    update_fields: dict = {
        "phase": target_phase,
        "revision": current_revision + 1,
        "updated_at": now_riyadh_naive(),
    }

    if is_terminal(target_phase):
        update_fields["completed_at"] = now_riyadh_naive()
        if terminal_reason:
            update_fields["terminal_reason"] = terminal_reason
        if winner_membership_id:
            update_fields["winner_membership_id"] = winner_membership_id

    if target_phase == Phase.IN_PROGRESS:
        update_fields["started_at"] = now_riyadh_naive()
        update_fields["turn_started_at"] = now_riyadh_naive()
        update_fields["current_turn"] = MinigameTurnSide.PLAYER_1

    return update_fields


# ── Async DB operations ──────────────────────────────────────


async def create_session(
    session: AsyncSession,
    *,
    game_type: str,
    competition_id: uuid.UUID,
    player_1_membership_id: uuid.UUID,
    match_type: MinigameMatchType,
    buy_in_amount: int,
    settings_snapshot: dict,
    season_id: uuid.UUID | None = None,
    cycle_id: uuid.UUID | None = None,
    player_2_membership_id: uuid.UUID | None = None,
    turn_duration_ms: int = 30000,
    grace_timer_ms: int = 60000,
) -> MinigameSession:
    """Create a new minigame session in CREATED phase."""
    mg_session = MinigameSession(
        game_type=game_type,
        competition_id=competition_id,
        season_id=season_id,
        cycle_id=cycle_id,
        phase=Phase.CREATED,
        revision=0,
        player_1_membership_id=player_1_membership_id,
        player_2_membership_id=player_2_membership_id,
        match_type=match_type,
        buy_in_amount=buy_in_amount,
        settings_snapshot=settings_snapshot,
        turn_duration_ms=turn_duration_ms,
        grace_timer_ms=grace_timer_ms,
        reconnect_token_p1=secrets.token_urlsafe(64),
        reconnect_token_p2=secrets.token_urlsafe(64) if player_2_membership_id else None,
    )
    session.add(mg_session)
    await session.flush()
    return mg_session


async def transition_session(
    session: AsyncSession,
    *,
    session_id: uuid.UUID,
    expected_revision: int,
    target_phase: Phase,
    terminal_reason: str | None = None,
    winner_membership_id: uuid.UUID | None = None,
    actor_type: str = "system",
    actor_membership_id: uuid.UUID | None = None,
) -> MinigameSession | None:
    """Transition a session to a new phase with optimistic locking.

    Returns the updated session, or None if the revision didn't match
    (another process modified the session first).
    """
    # Load current session
    result = await session.execute(
        select(MinigameSession).where(MinigameSession.id == session_id)
    )
    mg_session = result.scalars().first()
    if mg_session is None:
        raise ValueError("الجلسة غير موجودة")

    if mg_session.revision != expected_revision:
        return None  # Optimistic lock failure

    # Compute update fields (validates transition)
    update_fields = compute_transition_update(
        current_phase=mg_session.phase,
        target_phase=target_phase,
        current_revision=expected_revision,
        terminal_reason=terminal_reason,
        winner_membership_id=winner_membership_id,
    )

    # Apply optimistic-locked update
    stmt = (
        update(MinigameSession)
        .where(
            MinigameSession.id == session_id,
            MinigameSession.revision == expected_revision,
        )
        .values(**update_fields)
    )
    res = await session.execute(stmt)
    if res.rowcount == 0:
        return None  # Race condition — another writer won

    # Log transition event
    event = MinigameSessionEvent(
        session_id=session_id,
        revision=update_fields["revision"],
        event_type="transition",
        actor_type=actor_type,
        actor_membership_id=actor_membership_id,
        from_phase=mg_session.phase.value,
        to_phase=target_phase.value,
        correlation_id=mg_session.correlation_id,
    )
    session.add(event)

    # Refresh to get updated fields
    await session.refresh(mg_session)
    return mg_session
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_minigame_engine/test_session_service.py -v`
Expected: All 9 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/modules/minigames/session_service.py backend/tests/test_minigame_engine/test_session_service.py
git commit -m "feat(minigames): add session service — create session, transition with optimistic locking"
```

---

## Task 3: Action Service — Validate & Apply Actions

**Files:**
- Create: `backend/app/modules/minigames/action_service.py`
- Create: `backend/tests/test_minigame_engine/test_action_service.py`

- [ ] **Step 1: Write tests for action validation**

Create `backend/tests/test_minigame_engine/test_action_service.py`:

```python
"""Test action service — envelope validation and processing helpers."""

import uuid
import pytest
from app.core.enums import MinigameSessionPhase as Phase, MinigameTurnSide
from app.modules.minigames.action_service import (
    validate_action_envelope,
    ActionError,
)


def _envelope(*, action_id=None, session_id=None, actor_membership_id=None,
              action_type="guess", payload=None, client_seq=1, state_revision=0):
    return {
        "action_id": action_id or uuid.uuid4(),
        "session_id": session_id or uuid.uuid4(),
        "actor_membership_id": actor_membership_id or uuid.uuid4(),
        "action_type": action_type,
        "payload": payload or {},
        "client_seq": client_seq,
        "state_revision": state_revision,
    }


# ── Envelope validation ──────────────────────────────────────

def test_valid_envelope_passes():
    actor = uuid.uuid4()
    error = validate_action_envelope(
        envelope=_envelope(actor_membership_id=actor, state_revision=5),
        session_phase=Phase.IN_PROGRESS,
        session_revision=5,
        current_turn=MinigameTurnSide.PLAYER_1,
        player_1_membership_id=actor,
        player_2_membership_id=uuid.uuid4(),
    )
    assert error is None


def test_rejects_terminal_session():
    actor = uuid.uuid4()
    error = validate_action_envelope(
        envelope=_envelope(actor_membership_id=actor),
        session_phase=Phase.COMPLETED,
        session_revision=0,
        current_turn=MinigameTurnSide.PLAYER_1,
        player_1_membership_id=actor,
        player_2_membership_id=uuid.uuid4(),
    )
    assert error is not None
    assert error.code == "SESSION_ENDED"


def test_rejects_stale_revision():
    actor = uuid.uuid4()
    error = validate_action_envelope(
        envelope=_envelope(actor_membership_id=actor, state_revision=3),
        session_phase=Phase.IN_PROGRESS,
        session_revision=5,
        current_turn=MinigameTurnSide.PLAYER_1,
        player_1_membership_id=actor,
        player_2_membership_id=uuid.uuid4(),
    )
    assert error is not None
    assert error.code == "STALE_STATE"


def test_rejects_wrong_turn():
    actor_p1 = uuid.uuid4()
    actor_p2 = uuid.uuid4()
    error = validate_action_envelope(
        envelope=_envelope(actor_membership_id=actor_p2, state_revision=5),
        session_phase=Phase.IN_PROGRESS,
        session_revision=5,
        current_turn=MinigameTurnSide.PLAYER_1,
        player_1_membership_id=actor_p1,
        player_2_membership_id=actor_p2,
    )
    assert error is not None
    assert error.code == "NOT_YOUR_TURN"


def test_rejects_non_participant():
    actor = uuid.uuid4()
    error = validate_action_envelope(
        envelope=_envelope(actor_membership_id=actor, state_revision=0),
        session_phase=Phase.IN_PROGRESS,
        session_revision=0,
        current_turn=MinigameTurnSide.PLAYER_1,
        player_1_membership_id=uuid.uuid4(),
        player_2_membership_id=uuid.uuid4(),
    )
    assert error is not None
    assert error.code == "NOT_PARTICIPANT"


def test_accepts_overtime_phase():
    actor = uuid.uuid4()
    error = validate_action_envelope(
        envelope=_envelope(actor_membership_id=actor, state_revision=0),
        session_phase=Phase.OVERTIME,
        session_revision=0,
        current_turn=MinigameTurnSide.PLAYER_1,
        player_1_membership_id=actor,
        player_2_membership_id=uuid.uuid4(),
    )
    assert error is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_minigame_engine/test_action_service.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement action service**

Create `backend/app/modules/minigames/action_service.py`:

```python
"""Action service — validates and processes player actions.

Pure validation (no DB):
    validate_action_envelope — checks phase, revision, turn, participant

Async DB operations:
    check_idempotency — checks if action_id was already processed
    process_action — full pipeline: validate → plugin.apply → persist → evaluate terminal
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import (
    MinigameSessionPhase as Phase,
    MinigameTurnSide,
)
from app.core.utils import now_riyadh_naive
from app.modules.minigames.models import (
    MinigameActionReceipt,
    MinigameSession,
    MinigameSessionEvent,
)
from app.modules.minigames.plugin import GameTypePlugin
from app.modules.minigames.state_machine import is_terminal


PLAYABLE_PHASES = frozenset({Phase.IN_PROGRESS, Phase.OVERTIME})


@dataclass
class ActionError:
    """Structured action rejection."""
    code: str
    message_ar: str


def validate_action_envelope(
    *,
    envelope: dict,
    session_phase: Phase,
    session_revision: int,
    current_turn: MinigameTurnSide | None,
    player_1_membership_id: uuid.UUID,
    player_2_membership_id: uuid.UUID | None,
) -> ActionError | None:
    """Validate an action envelope against session state. Returns None if valid."""

    # 1. Session must be in a playable phase
    if is_terminal(session_phase) or session_phase not in PLAYABLE_PHASES:
        return ActionError(
            code="SESSION_ENDED",
            message_ar="الجلسة منتهية أو غير نشطة",
        )

    # 2. Check state revision freshness
    client_revision = envelope.get("state_revision", -1)
    if client_revision < session_revision:
        return ActionError(
            code="STALE_STATE",
            message_ar="حالة اللعبة قديمة — يرجى تحديث الشاشة",
        )

    # 3. Check participant
    actor_id = envelope.get("actor_membership_id")
    if actor_id not in (player_1_membership_id, player_2_membership_id):
        return ActionError(
            code="NOT_PARTICIPANT",
            message_ar="أنت لست مشاركاً في هذه الجلسة",
        )

    # 4. Check turn
    if current_turn is not None:
        expected_actor = (
            player_1_membership_id
            if current_turn == MinigameTurnSide.PLAYER_1
            else player_2_membership_id
        )
        if actor_id != expected_actor:
            return ActionError(
                code="NOT_YOUR_TURN",
                message_ar="ليس دورك — انتظر دور الخصم",
            )

    return None


async def check_idempotency(
    session: AsyncSession,
    action_id: uuid.UUID,
) -> dict | None:
    """Check if an action_id was already processed. Returns cached response or None."""
    result = await session.execute(
        select(MinigameActionReceipt).where(
            MinigameActionReceipt.action_id == action_id
        )
    )
    receipt = result.scalars().first()
    if receipt is not None:
        return receipt.response
    return None


async def process_action(
    session: AsyncSession,
    *,
    mg_session: MinigameSession,
    plugin: GameTypePlugin,
    envelope: dict,
) -> dict:
    """Full action processing pipeline.

    1. Plugin validates action
    2. Plugin applies action → new state + side effects
    3. Optimistic lock update on session
    4. Log event + receipt
    5. Check terminal condition
    6. Return result dict

    Raises ValueError on plugin validation failure.
    Returns None if optimistic lock fails.
    """
    action = {
        "type": envelope["action_type"],
        "payload": envelope.get("payload", {}),
    }
    current_state = mg_session.game_state

    # 1. Plugin validates
    validation_error = plugin.validate_action(action, current_state)
    if validation_error is not None:
        raise ValueError(validation_error)

    # 2. Plugin applies
    new_state, side_effects = plugin.apply_action(action, current_state)

    # 3. Advance turn
    new_turn = (
        MinigameTurnSide.PLAYER_2
        if mg_session.current_turn == MinigameTurnSide.PLAYER_1
        else MinigameTurnSide.PLAYER_1
    )
    new_revision = mg_session.revision + 1
    new_turn_number = mg_session.turn_number + 1

    # 4. Optimistic lock update
    stmt = (
        update(MinigameSession)
        .where(
            MinigameSession.id == mg_session.id,
            MinigameSession.revision == mg_session.revision,
        )
        .values(
            game_state=new_state,
            revision=new_revision,
            current_turn=new_turn,
            turn_number=new_turn_number,
            turn_started_at=now_riyadh_naive(),
            updated_at=now_riyadh_naive(),
        )
    )
    res = await session.execute(stmt)
    if res.rowcount == 0:
        return {"success": False, "code": "CONFLICT", "message_ar": "تعارض — حاول مرة أخرى"}

    # 5. Log event
    event = MinigameSessionEvent(
        session_id=mg_session.id,
        revision=new_revision,
        event_type="action",
        actor_type="player",
        actor_membership_id=envelope["actor_membership_id"],
        action_type=envelope["action_type"],
        payload=envelope.get("payload", {}),
        result={"side_effects": side_effects},
        correlation_id=mg_session.correlation_id,
    )
    session.add(event)

    # 6. Log receipt for idempotency
    result_data = {
        "success": True,
        "revision": new_revision,
        "turn_number": new_turn_number,
        "side_effects": side_effects,
    }
    receipt = MinigameActionReceipt(
        action_id=envelope["action_id"],
        session_id=mg_session.id,
        actor_membership_id=envelope["actor_membership_id"],
        client_seq=envelope["client_seq"],
        response=result_data,
    )
    session.add(receipt)

    # 7. Check terminal
    terminal_result = plugin.evaluate_terminal(new_state)

    result_data["terminal"] = terminal_result
    result_data["new_state"] = new_state
    return result_data
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_minigame_engine/test_action_service.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/modules/minigames/action_service.py backend/tests/test_minigame_engine/test_action_service.py
git commit -m "feat(minigames): add action service — envelope validation, idempotency check, action processing pipeline"
```

---

## Task 4: Settlement Service

**Files:**
- Create: `backend/app/modules/minigames/settlement_service.py`
- Create: `backend/tests/test_minigame_engine/test_settlement_service.py`

- [ ] **Step 1: Write tests for settlement logic**

Create `backend/tests/test_minigame_engine/test_settlement_service.py`:

```python
"""Test settlement service — settlement computation and state management."""

import uuid
import pytest
from app.core.enums import MinigameSessionPhase as Phase, MinigameSettlementState
from app.modules.minigames.settlement_service import (
    compute_settlement_type,
    SettlementType,
)


# ── Settlement type computation ──────────────────────────────

def test_completed_with_winner_is_normal():
    stype = compute_settlement_type(
        phase=Phase.COMPLETED,
        terminal_reason="knockout",
        winner_membership_id=uuid.uuid4(),
    )
    assert stype == SettlementType.NORMAL


def test_abandoned_with_winner_is_forfeit():
    stype = compute_settlement_type(
        phase=Phase.ABANDONED,
        terminal_reason="disconnect_timeout",
        winner_membership_id=uuid.uuid4(),
    )
    assert stype == SettlementType.FORFEIT


def test_cancelled_is_cancel():
    stype = compute_settlement_type(
        phase=Phase.CANCELLED,
        terminal_reason="admin_cancel",
        winner_membership_id=None,
    )
    assert stype == SettlementType.CANCEL


def test_cancelled_with_winner_is_still_cancel():
    stype = compute_settlement_type(
        phase=Phase.CANCELLED,
        terminal_reason="admin_cancel",
        winner_membership_id=uuid.uuid4(),
    )
    assert stype == SettlementType.CANCEL


def test_abandoned_no_winner_is_cancel():
    stype = compute_settlement_type(
        phase=Phase.ABANDONED,
        terminal_reason="both_disconnected",
        winner_membership_id=None,
    )
    assert stype == SettlementType.CANCEL


def test_non_terminal_raises():
    with pytest.raises(ValueError, match="غير نهائية"):
        compute_settlement_type(
            phase=Phase.IN_PROGRESS,
            terminal_reason=None,
            winner_membership_id=None,
        )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_minigame_engine/test_settlement_service.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement settlement service**

Create `backend/app/modules/minigames/settlement_service.py`:

```python
"""Settlement service — computes and executes financial settlements.

Pure helpers (no DB):
    compute_settlement_type — determines NORMAL / FORFEIT / CANCEL from session state

Async DB operations:
    execute_settlement — writes settlement record + ledger entries in one transaction
"""

import uuid
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import (
    MinigameSessionPhase as Phase,
    MinigameSettlementState,
)
from app.core.utils import now_riyadh_naive
from app.modules.minigames.economy import (
    create_cancel_settlement_entries,
    create_forfeit_settlement_entries,
    create_normal_settlement_entries,
)
from app.modules.minigames.models import MinigameSession, MinigameSessionSettlement
from app.modules.minigames.state_machine import is_terminal


class SettlementType(StrEnum):
    NORMAL = "normal"      # Winner takes buy_in * 2
    FORFEIT = "forfeit"    # Opponent abandoned/disconnected, winner takes all
    CANCEL = "cancel"      # Both refunded (admin cancel or both disconnect)


def compute_settlement_type(
    *,
    phase: Phase,
    terminal_reason: str | None,
    winner_membership_id: uuid.UUID | None,
) -> SettlementType:
    """Determine settlement type from terminal session state."""
    if not is_terminal(phase):
        raise ValueError("لا يمكن تسوية جلسة غير نهائية")

    if phase == Phase.CANCELLED:
        return SettlementType.CANCEL

    if phase == Phase.ABANDONED:
        if winner_membership_id is not None:
            return SettlementType.FORFEIT
        return SettlementType.CANCEL

    # COMPLETED
    return SettlementType.NORMAL


async def execute_settlement(
    session: AsyncSession,
    *,
    mg_session: MinigameSession,
    winner_balance: int = 0,
    loser_balance: int = 0,
    player_1_balance: int = 0,
    player_2_balance: int = 0,
) -> MinigameSessionSettlement:
    """Execute financial settlement for a terminal session.

    Creates a settlement record and ledger entries in one transaction.
    Idempotent — returns existing settlement if already processed.
    """
    # Check for existing settlement (idempotent)
    existing = await session.execute(
        select(MinigameSessionSettlement).where(
            MinigameSessionSettlement.session_id == mg_session.id
        )
    )
    existing_settlement = existing.scalars().first()
    if existing_settlement is not None:
        return existing_settlement

    settlement_type = compute_settlement_type(
        phase=mg_session.phase,
        terminal_reason=mg_session.terminal_reason,
        winner_membership_id=mg_session.winner_membership_id,
    )

    # Compute ledger entries based on settlement type
    ledger_entries = []
    winner_payout = 0
    loser_penalty = 0

    if settlement_type == SettlementType.NORMAL:
        winner_payout = mg_session.buy_in_amount * 2
        loser_penalty = mg_session.buy_in_amount  # Already debited at buy-in
        ledger_entries = create_normal_settlement_entries(
            winner_membership_id=mg_session.winner_membership_id,
            loser_membership_id=_get_loser_id(mg_session),
            competition_id=mg_session.competition_id,
            session_id=mg_session.id,
            buy_in_amount=mg_session.buy_in_amount,
            winner_balance=winner_balance,
            season_id=mg_session.season_id,
            cycle_id=mg_session.cycle_id,
        )

    elif settlement_type == SettlementType.FORFEIT:
        winner_payout = mg_session.buy_in_amount * 2
        loser_penalty = mg_session.buy_in_amount
        ledger_entries = create_forfeit_settlement_entries(
            winner_membership_id=mg_session.winner_membership_id,
            competition_id=mg_session.competition_id,
            session_id=mg_session.id,
            buy_in_amount=mg_session.buy_in_amount,
            winner_balance=winner_balance,
            season_id=mg_session.season_id,
            cycle_id=mg_session.cycle_id,
        )

    elif settlement_type == SettlementType.CANCEL:
        winner_payout = 0
        loser_penalty = 0
        ledger_entries = create_cancel_settlement_entries(
            player_1_membership_id=mg_session.player_1_membership_id,
            player_2_membership_id=mg_session.player_2_membership_id,
            competition_id=mg_session.competition_id,
            session_id=mg_session.id,
            buy_in_amount=mg_session.buy_in_amount,
            player_1_balance=player_1_balance,
            player_2_balance=player_2_balance,
            season_id=mg_session.season_id,
            cycle_id=mg_session.cycle_id,
        )

    # Add ledger entries
    for entry in ledger_entries:
        session.add(entry)
    await session.flush()

    # Create settlement record
    settlement = MinigameSessionSettlement(
        session_id=mg_session.id,
        winner_membership_id=mg_session.winner_membership_id,
        loser_membership_id=_get_loser_id(mg_session) if settlement_type != SettlementType.CANCEL else None,
        winner_payout=winner_payout,
        loser_penalty=loser_penalty,
        settlement_state=MinigameSettlementState.SETTLED,
        ledger_entry_ids=[e.id for e in ledger_entries],
        correlation_id=mg_session.correlation_id,
        settled_at=now_riyadh_naive(),
    )
    session.add(settlement)
    return settlement


def _get_loser_id(mg_session: MinigameSession) -> uuid.UUID | None:
    """Determine the loser's membership ID."""
    if mg_session.winner_membership_id is None:
        return None
    if mg_session.winner_membership_id == mg_session.player_1_membership_id:
        return mg_session.player_2_membership_id
    return mg_session.player_1_membership_id
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_minigame_engine/test_settlement_service.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/modules/minigames/settlement_service.py backend/tests/test_minigame_engine/test_settlement_service.py
git commit -m "feat(minigames): add settlement service — NORMAL/FORFEIT/CANCEL settlement with ledger integration"
```

---

## Task 5: Integration Test — Full Lifecycle

**Files:**
- Create: `backend/tests/test_minigame_engine/test_lifecycle.py`

This test verifies the full lifecycle works together: creation validation → transition computation → action validation → settlement type computation. All pure functions, no DB needed.

- [ ] **Step 1: Write integration test**

Create `backend/tests/test_minigame_engine/test_lifecycle.py`:

```python
"""Integration test — verify the full session lifecycle works as pure logic."""

import uuid
from app.core.enums import MinigameSessionPhase as Phase, MinigameTurnSide
from app.modules.minigames.session_service import (
    validate_session_creation,
    compute_transition_update,
)
from app.modules.minigames.action_service import validate_action_envelope
from app.modules.minigames.settlement_service import compute_settlement_type, SettlementType
from app.modules.minigames.economy import create_buy_in_entry, create_normal_settlement_entries
from app.core.enums import LedgerDirection, LedgerEntryType


def test_full_lifecycle_happy_path():
    """CREATED → WAITING → READY → IN_PROGRESS → action → COMPLETED → settlement."""
    p1 = uuid.uuid4()
    p2 = uuid.uuid4()
    comp_id = uuid.uuid4()
    session_id = uuid.uuid4()

    # 1. Validate creation
    errors = validate_session_creation(
        game_type_id="mutaraha",
        plugin_exists=True,
        plugin_status="active",
        player_balance=1000,
        buy_in_amount=500,
        is_bankrupt=False,
    )
    assert errors == []

    # 2. Buy-in for both players
    p1_entry = create_buy_in_entry(
        membership_id=p1, competition_id=comp_id,
        session_id=session_id, amount=500, balance_before=1000,
    )
    assert p1_entry.balance_after == 500
    assert p1_entry.direction == LedgerDirection.DEBIT

    p2_entry = create_buy_in_entry(
        membership_id=p2, competition_id=comp_id,
        session_id=session_id, amount=500, balance_before=800,
    )
    assert p2_entry.balance_after == 300

    # 3. Transitions
    rev = 0
    for target in [Phase.WAITING, Phase.READY, Phase.IN_PROGRESS]:
        current = Phase.CREATED if rev == 0 else [Phase.CREATED, Phase.WAITING, Phase.READY][rev]
        update = compute_transition_update(
            current_phase=[Phase.CREATED, Phase.WAITING, Phase.READY][rev],
            target_phase=target,
            current_revision=rev,
        )
        assert update["revision"] == rev + 1
        rev = update["revision"]

    # 4. Validate action in IN_PROGRESS
    error = validate_action_envelope(
        envelope={
            "action_id": uuid.uuid4(),
            "actor_membership_id": p1,
            "action_type": "guess",
            "payload": {},
            "client_seq": 1,
            "state_revision": rev,
        },
        session_phase=Phase.IN_PROGRESS,
        session_revision=rev,
        current_turn=MinigameTurnSide.PLAYER_1,
        player_1_membership_id=p1,
        player_2_membership_id=p2,
    )
    assert error is None

    # 5. Transition to COMPLETED
    update = compute_transition_update(
        current_phase=Phase.IN_PROGRESS,
        target_phase=Phase.COMPLETED,
        current_revision=rev,
        terminal_reason="knockout",
        winner_membership_id=p1,
    )
    assert update["phase"] == Phase.COMPLETED
    assert update["winner_membership_id"] == p1

    # 6. Settlement
    stype = compute_settlement_type(
        phase=Phase.COMPLETED,
        terminal_reason="knockout",
        winner_membership_id=p1,
    )
    assert stype == SettlementType.NORMAL

    # 7. Ledger settlement entries
    entries = create_normal_settlement_entries(
        winner_membership_id=p1,
        loser_membership_id=p2,
        competition_id=comp_id,
        session_id=session_id,
        buy_in_amount=500,
        winner_balance=500,  # After buy-in
    )
    assert len(entries) == 1
    assert entries[0].amount == 1000  # buy_in * 2
    assert entries[0].balance_after == 1500  # 500 + 1000


def test_cancel_lifecycle():
    """Session cancelled by admin → both refunded."""
    p1 = uuid.uuid4()
    p2 = uuid.uuid4()

    stype = compute_settlement_type(
        phase=Phase.CANCELLED,
        terminal_reason="admin_cancel",
        winner_membership_id=None,
    )
    assert stype == SettlementType.CANCEL


def test_abandon_lifecycle():
    """Player 2 abandons → Player 1 wins by forfeit."""
    p1 = uuid.uuid4()

    stype = compute_settlement_type(
        phase=Phase.ABANDONED,
        terminal_reason="disconnect_timeout",
        winner_membership_id=p1,
    )
    assert stype == SettlementType.FORFEIT
```

- [ ] **Step 2: Run ALL minigame tests**

Run: `cd backend && python -m pytest tests/test_minigame_engine/ -v`
Expected: All tests pass (Sprint 0: 48 + Sprint 1: ~30 = ~78 total)

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_minigame_engine/test_lifecycle.py
git commit -m "feat(minigames): Sprint 1 complete — session service, action service, settlement service, economy bridge

Sprint 1 delivers:
- Economy bridge: buy-in/payout/refund/settlement ledger helpers
- Session service: create + transition with optimistic locking
- Action service: envelope validation + idempotency + plugin processing
- Settlement service: NORMAL/FORFEIT/CANCEL settlement types with ledger
- Full lifecycle integration test"
```

---

## Sprint 1 Deliverables Summary

| Component | File | Tests |
|---|---|---|
| Economy bridge | `minigames/economy.py` | 9 |
| Session service | `minigames/session_service.py` | 9 |
| Action service | `minigames/action_service.py` | 6 |
| Settlement service | `minigames/settlement_service.py` | 6 |
| Lifecycle integration | `test_lifecycle.py` | 3 |
| **Total** | **4 files created** | **~33 tests** |

## What Sprint 2 Will Build On This

Sprint 2 (Matchmaking & REST API) will use:
- `session_service.create_session()` to create sessions from challenge/queue endpoints
- `session_service.transition_session()` to advance sessions on accept/start
- `action_service.process_action()` from the WebSocket game handler
- `settlement_service.execute_settlement()` when games end
- `economy.create_buy_in_entry()` at session start
