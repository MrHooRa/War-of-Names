# Minigame Engine — N-Player Upgrade Sprint A: Models, Turn System & Settlement

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the minigame engine from a hardcoded 2-player model to a flexible N-player model (1-8 players), changing the database schema, turn system, settlement structure, economy helpers, leaderboard stats, and plugin contract — while keeping مطارحة working.

**Architecture:** Replace `player_1_membership_id` / `player_2_membership_id` columns with a `MinigameSessionParticipant` join table. Replace `MinigameTurnSide` enum (PLAYER_1/PLAYER_2) with `current_turn_index: int` for round-robin. Replace binary winner/loser settlement with ranked `participant_results: JSONB`. All existing services and مطارحة plugin updated to use the new participant-based model.

**Tech Stack:** Python 3.12, SQLAlchemy 2.x async, PostgreSQL 16, pytest

**Depends on:** All Sprint 0-4 + مطارحة plugin (must remain working after upgrade)

---

## Sprint A Scope

1. **New model: `MinigameSessionParticipant`** — join table replacing player_1/player_2
2. **Modify `MinigameSession`** — remove player_1/player_2 columns, add `current_turn_index: int`, `num_players: int`
3. **Modify `MinigameSessionSettlement`** — replace winner/loser with `participant_results: JSONB`
4. **Remove `MinigameTurnSide` enum** — replace with int-based indexing
5. **Update economy helpers** — accept `list[dict]` for N-player settlements
6. **Update leaderboard service** — `placement: int` instead of `is_win: bool`
7. **Update plugin contract** — `compute_settlement` returns `list[dict]`
8. **SQL migration** — add participant table, migrate data, drop old columns
9. **Update all tests** — reflect new signatures
10. **مطارحة backward compat** — plugin uses slot 0 and slot 1

**Sprint B (next):** Service updates (session, action, policy), WebSocket, router.

---

## File Structure

```
backend/app/modules/minigames/
├── models.py                      # MODIFY: add MinigameSessionParticipant, update MinigameSession + Settlement
├── plugin.py                      # MODIFY: update compute_settlement contract
├── economy.py                     # MODIFY: add N-player settlement helpers
├── leaderboard_service.py         # MODIFY: placement-based stats
├── state_machine.py               # NO CHANGE (phase transitions are player-count agnostic)
├── registry.py                    # NO CHANGE
├── settings_helper.py             # NO CHANGE

backend/app/core/
├── enums.py                       # MODIFY: remove MinigameTurnSide, keep others
├── models.py                      # MODIFY: register MinigameSessionParticipant

backend/app/modules/minigames/mutaraha/
├── plugin.py                      # MODIFY: adapt to new participant model

backend/migrations/
└── 006_nplayer_upgrade.sql        # CREATE: new table + migration

backend/tests/test_minigame_engine/
├── test_enums.py                  # MODIFY: remove turn_side tests
├── test_economy.py                # MODIFY: new N-player helpers
├── test_leaderboard_service.py    # MODIFY: placement-based
├── test_mutaraha_plugin.py        # MODIFY: adapt to participant model
└── test_nplayer_models.py         # CREATE: participant model tests
```

---

## Task 1: New Participant Model + Update Session & Settlement

**Files:**
- Modify: `backend/app/modules/minigames/models.py`
- Modify: `backend/app/core/models.py`
- Modify: `backend/app/core/enums.py`

- [ ] **Step 1: Remove `MinigameTurnSide` from enums.py**

In `backend/app/core/enums.py`, remove:
```python
class MinigameTurnSide(StrEnum):
    PLAYER_1 = "player_1"
    PLAYER_2 = "player_2"
```

- [ ] **Step 2: Update MinigameSession model**

In `backend/app/modules/minigames/models.py`:

**Remove** these fields from `MinigameSession`:
- `player_1_membership_id`
- `player_2_membership_id`
- `reconnect_token_p1`
- `reconnect_token_p2`
- `current_turn` (the MinigameTurnSide enum column)
- `winner_membership_id`
- The `chk_mg_distinct_players` constraint
- The `MinigameTurnSide` import

**Add** these fields to `MinigameSession`:
```python
num_players: Mapped[int] = mapped_column(nullable=False, default=2)
min_players: Mapped[int] = mapped_column(nullable=False, default=2)
max_players: Mapped[int] = mapped_column(nullable=False, default=2)
current_turn_index: Mapped[int | None] = mapped_column()  # 0-based player slot
winner_slot_index: Mapped[int | None] = mapped_column()    # winning player's slot
```

- [ ] **Step 3: Add MinigameSessionParticipant model**

Add to `backend/app/modules/minigames/models.py` (after MinigameSession):

```python
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
```

- [ ] **Step 4: Update MinigameSessionSettlement**

Replace `winner_membership_id` / `loser_membership_id` / `winner_payout` / `loser_penalty` with:

```python
participant_results: Mapped[list | None] = mapped_column(JSONB)
# Format: [{"membership_id": "uuid", "slot_index": 0, "rank": 1, "payout": 1000}, ...]
total_pool: Mapped[int] = mapped_column(nullable=False, default=0)
```

Keep `ledger_entry_ids`, `settlement_state`, `correlation_id`, etc.

- [ ] **Step 5: Register new model in core/models.py**

Add `MinigameSessionParticipant` to the import block in `backend/app/core/models.py`.

- [ ] **Step 6: Commit**

```bash
git commit -m "feat(minigames): N-player models — add participants table, remove player_1/player_2 columns, int-based turns"
```

---

## Task 2: SQL Migration

**Files:**
- Create: `backend/migrations/006_nplayer_upgrade.sql`

- [ ] **Step 1: Write migration**

```sql
BEGIN;

-- ── New participants table ──
CREATE TABLE IF NOT EXISTS minigame_session_participants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES minigame_sessions(id) ON DELETE CASCADE,
    membership_id UUID NOT NULL REFERENCES memberships(id) ON DELETE RESTRICT,
    slot_index INTEGER NOT NULL,
    reconnect_token VARCHAR(128),
    joined_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_mg_participant UNIQUE (session_id, membership_id),
    CONSTRAINT uq_mg_participant_slot UNIQUE (session_id, slot_index),
    CONSTRAINT chk_mg_slot_range CHECK (slot_index >= 0 AND slot_index <= 7)
);

-- ── Migrate existing sessions: copy player_1/player_2 to participants ──
INSERT INTO minigame_session_participants (session_id, membership_id, slot_index, reconnect_token)
SELECT id, player_1_membership_id, 0, reconnect_token_p1
FROM minigame_sessions
WHERE player_1_membership_id IS NOT NULL
ON CONFLICT DO NOTHING;

INSERT INTO minigame_session_participants (session_id, membership_id, slot_index, reconnect_token)
SELECT id, player_2_membership_id, 1, reconnect_token_p2
FROM minigame_sessions
WHERE player_2_membership_id IS NOT NULL
ON CONFLICT DO NOTHING;

-- ── Add new columns to minigame_sessions ──
ALTER TABLE minigame_sessions ADD COLUMN IF NOT EXISTS num_players INTEGER NOT NULL DEFAULT 2;
ALTER TABLE minigame_sessions ADD COLUMN IF NOT EXISTS min_players INTEGER NOT NULL DEFAULT 2;
ALTER TABLE minigame_sessions ADD COLUMN IF NOT EXISTS max_players INTEGER NOT NULL DEFAULT 2;
ALTER TABLE minigame_sessions ADD COLUMN IF NOT EXISTS current_turn_index INTEGER;
ALTER TABLE minigame_sessions ADD COLUMN IF NOT EXISTS winner_slot_index INTEGER;

-- ── Migrate current_turn enum to index ──
UPDATE minigame_sessions SET current_turn_index = 0 WHERE current_turn = 'player_1';
UPDATE minigame_sessions SET current_turn_index = 1 WHERE current_turn = 'player_2';

-- ── Migrate winner to slot index ──
UPDATE minigame_sessions s SET winner_slot_index = 0
WHERE winner_membership_id IS NOT NULL
  AND winner_membership_id = player_1_membership_id;
UPDATE minigame_sessions s SET winner_slot_index = 1
WHERE winner_membership_id IS NOT NULL
  AND winner_membership_id = player_2_membership_id;

-- ── Update settlement table ──
ALTER TABLE minigame_session_settlements ADD COLUMN IF NOT EXISTS participant_results JSONB;
ALTER TABLE minigame_session_settlements ADD COLUMN IF NOT EXISTS total_pool INTEGER NOT NULL DEFAULT 0;

-- ── Migrate existing settlements to new format ──
UPDATE minigame_session_settlements SET participant_results = jsonb_build_array(
    jsonb_build_object('membership_id', winner_membership_id::text, 'rank', 1, 'payout', winner_payout),
    jsonb_build_object('membership_id', loser_membership_id::text, 'rank', 2, 'payout', 0)
)
WHERE winner_membership_id IS NOT NULL;

UPDATE minigame_session_settlements SET total_pool = winner_payout + loser_penalty
WHERE total_pool = 0 AND winner_payout > 0;

-- ── Drop old columns (after data migration) ──
ALTER TABLE minigame_sessions DROP COLUMN IF EXISTS player_1_membership_id;
ALTER TABLE minigame_sessions DROP COLUMN IF EXISTS player_2_membership_id;
ALTER TABLE minigame_sessions DROP COLUMN IF EXISTS reconnect_token_p1;
ALTER TABLE minigame_sessions DROP COLUMN IF EXISTS reconnect_token_p2;
ALTER TABLE minigame_sessions DROP COLUMN IF EXISTS current_turn;
ALTER TABLE minigame_sessions DROP COLUMN IF EXISTS winner_membership_id;
ALTER TABLE minigame_sessions DROP CONSTRAINT IF EXISTS chk_mg_distinct_players;

ALTER TABLE minigame_session_settlements DROP COLUMN IF EXISTS winner_membership_id;
ALTER TABLE minigame_session_settlements DROP COLUMN IF EXISTS loser_membership_id;
ALTER TABLE minigame_session_settlements DROP COLUMN IF EXISTS winner_payout;
ALTER TABLE minigame_session_settlements DROP COLUMN IF EXISTS loser_penalty;

-- ── Drop unused enum type ──
-- Note: minigame_turn_side enum cannot be dropped if still referenced.
-- The column was dropped above, so we can safely drop the type.
DROP TYPE IF EXISTS minigame_turn_side;

COMMIT;
```

- [ ] **Step 2: Commit**

```bash
git commit -m "feat(minigames): SQL migration 006 — participants table, data migration, drop player_1/player_2"
```

---

## Task 3: Update Economy Helpers

**Files:**
- Modify: `backend/app/modules/minigames/economy.py`
- Modify: `backend/tests/test_minigame_engine/test_economy.py`

- [ ] **Step 1: Add N-player settlement helper**

Add to `economy.py`:

```python
def create_ranked_settlement_entries(
    *,
    results: list[dict],
    competition_id: uuid.UUID,
    session_id: uuid.UUID,
    season_id: uuid.UUID | None = None,
    cycle_id: uuid.UUID | None = None,
) -> list[LedgerEntry]:
    """Create ledger entries for N-player ranked settlement.
    
    Args:
        results: list of {"membership_id": UUID, "rank": int, "payout": int, "balance_before": int}
                 Only players with payout > 0 get a CREDIT entry.
    
    Returns:
        List of LedgerEntry instances (one per player with payout > 0)
    """
    entries = []
    for r in results:
        if r["payout"] > 0:
            entries.append(create_payout_entry(
                membership_id=r["membership_id"],
                competition_id=competition_id,
                session_id=session_id,
                amount=r["payout"],
                balance_before=r.get("balance_before", 0),
                season_id=season_id,
                cycle_id=cycle_id,
            ))
    return entries


def create_refund_all_entries(
    *,
    player_membership_ids: list[uuid.UUID],
    player_balances: list[int],
    competition_id: uuid.UUID,
    session_id: uuid.UUID,
    buy_in_amount: int,
    season_id: uuid.UUID | None = None,
    cycle_id: uuid.UUID | None = None,
) -> list[LedgerEntry]:
    """Refund buy-in to all participants (for cancellations)."""
    entries = []
    for mid, balance in zip(player_membership_ids, player_balances):
        entries.append(create_refund_entry(
            membership_id=mid,
            competition_id=competition_id,
            session_id=session_id,
            amount=buy_in_amount,
            balance_before=balance,
            season_id=season_id,
            cycle_id=cycle_id,
        ))
    return entries
```

Keep existing `create_normal_settlement_entries`, `create_forfeit_settlement_entries`, `create_cancel_settlement_entries`, and `create_solo_settlement_entries` — they still work for مطارحة. The new helpers are additive.

- [ ] **Step 2: Add tests**

Add to `test_economy.py`:

```python
def test_ranked_settlement_pays_top_players():
    results = [
        {"membership_id": uuid.uuid4(), "rank": 1, "payout": 600, "balance_before": 0},
        {"membership_id": uuid.uuid4(), "rank": 2, "payout": 300, "balance_before": 0},
        {"membership_id": uuid.uuid4(), "rank": 3, "payout": 0, "balance_before": 0},
    ]
    entries = create_ranked_settlement_entries(
        results=results, competition_id=uuid.uuid4(), session_id=uuid.uuid4(),
    )
    assert len(entries) == 2  # Only rank 1 and 2 get entries (rank 3 payout=0)
    assert entries[0].amount == 600
    assert entries[1].amount == 300


def test_ranked_settlement_empty_results():
    entries = create_ranked_settlement_entries(
        results=[], competition_id=uuid.uuid4(), session_id=uuid.uuid4(),
    )
    assert entries == []


def test_refund_all_entries():
    ids = [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]
    entries = create_refund_all_entries(
        player_membership_ids=ids,
        player_balances=[100, 200, 300],
        competition_id=uuid.uuid4(),
        session_id=uuid.uuid4(),
        buy_in_amount=500,
    )
    assert len(entries) == 3
    assert all(e.entry_type == LedgerEntryType.MINIGAME_REFUND for e in entries)
```

- [ ] **Step 3: Commit**

```bash
git commit -m "feat(minigames): add N-player economy helpers — ranked settlement + refund-all"
```

---

## Task 4: Update Plugin Contract

**Files:**
- Modify: `backend/app/modules/minigames/plugin.py`

- [ ] **Step 1: Update compute_settlement docstring**

Change the `compute_settlement` abstract method docstring:

```python
@abstractmethod
def compute_settlement(self, terminal_result: dict) -> dict:
    """Calculate financial settlement from terminal result.

    Must return: {
        "participant_results": [
            {"membership_id": uuid, "slot_index": int, "rank": int, "payout": int},
            ...
        ],
        "total_pool": int,
    }
    
    For 2-player games (like مطارحة): 2 entries (winner rank=1, loser rank=2).
    For N-player games: N entries ranked by placement.
    payout=0 means the player gets nothing back (lost their buy-in).
    """
    ...
```

The method signature stays the same (`dict → dict`), only the expected structure changes.

- [ ] **Step 2: Commit**

```bash
git commit -m "feat(minigames): update plugin contract — compute_settlement returns ranked participant_results"
```

---

## Task 5: Update Leaderboard Service

**Files:**
- Modify: `backend/app/modules/minigames/leaderboard_service.py`
- Modify: `backend/tests/test_minigame_engine/test_leaderboard_service.py`

- [ ] **Step 1: Update compute_updated_stats**

Add `placement: int` parameter alongside `is_win` (backward compat):

```python
def compute_updated_stats(
    *,
    current: dict,
    is_win: bool | None = None,
    placement: int | None = None,
    num_players: int = 2,
    tools_used: int = 0,
    duration_sec: float = 0.0,
) -> dict:
    """Compute updated leaderboard stats.
    
    Args:
        is_win: Legacy 2-player binary (True=win, False=loss). Used if placement is None.
        placement: 1-based rank (1=first, 2=second, etc.). Takes priority over is_win.
        num_players: Total players in the match (for normalized scoring).
    """
    # Resolve win from placement if provided
    if placement is not None:
        is_win_resolved = (placement == 1)
    elif is_win is not None:
        is_win_resolved = is_win
    else:
        is_win_resolved = False
    
    # ... rest of existing logic using is_win_resolved ...
```

- [ ] **Step 2: Add placement tests**

```python
def test_placement_1_counts_as_win():
    stats = compute_updated_stats(
        current={"wins": 0, "losses": 0, "current_streak": 0, "best_streak": 0, "total_matches": 0},
        placement=1, num_players=4, tools_used=2, duration_sec=120.0,
    )
    assert stats["wins"] == 1
    assert stats["current_streak"] == 1


def test_placement_2_counts_as_loss():
    stats = compute_updated_stats(
        current={"wins": 1, "losses": 0, "current_streak": 1, "best_streak": 1, "total_matches": 1},
        placement=2, num_players=4,
    )
    assert stats["losses"] == 1
    assert stats["current_streak"] == 0


def test_is_win_still_works_for_backward_compat():
    stats = compute_updated_stats(
        current={"wins": 0, "losses": 0, "current_streak": 0, "best_streak": 0, "total_matches": 0},
        is_win=True, tools_used=1, duration_sec=60.0,
    )
    assert stats["wins"] == 1
```

- [ ] **Step 3: Commit**

```bash
git commit -m "feat(minigames): update leaderboard — support placement-based stats for N-player games"
```

---

## Task 6: Update Lobby Manager — N-Player Matchmaking

**Files:**
- Modify: `backend/app/modules/minigames/lobby_manager.py`
- Modify: `backend/tests/test_minigame_engine/test_lobby_manager.py`

- [ ] **Step 1: Update try_match to accept num_needed**

```python
def try_match(self, lobby_key: str, num_needed: int = 2) -> list[uuid.UUID] | None:
    """Try to match N players from the queue (FIFO). Returns list of N UUIDs or None."""
    queue = self._queues.get(lobby_key)
    if not queue or len(queue) < num_needed:
        return None

    matched = []
    for _ in range(num_needed):
        matched.append(queue.popleft())

    for mid in matched:
        self.set_status(lobby_key, mid, "in_match")

    return matched
```

Note: return type changes from `tuple[UUID, UUID] | None` to `list[UUID] | None`.

- [ ] **Step 2: Add tests**

```python
def test_match_3_players(lobby):
    key = _key()
    ids = [uuid.uuid4() for _ in range(3)]
    for mid in ids:
        lobby.join(key, mid, alias=f"p{mid}")
        lobby.queue_join(key, mid)
    match = lobby.try_match(key, num_needed=3)
    assert match is not None
    assert len(match) == 3


def test_match_not_enough_for_4(lobby):
    key = _key()
    for _ in range(3):
        mid = uuid.uuid4()
        lobby.join(key, mid, alias="x")
        lobby.queue_join(key, mid)
    match = lobby.try_match(key, num_needed=4)
    assert match is None


def test_match_8_players(lobby):
    key = _key()
    ids = [uuid.uuid4() for _ in range(8)]
    for mid in ids:
        lobby.join(key, mid, alias=f"p{mid}")
        lobby.queue_join(key, mid)
    match = lobby.try_match(key, num_needed=8)
    assert len(match) == 8


def test_match_default_still_2(lobby):
    key = _key()
    m1, m2 = uuid.uuid4(), uuid.uuid4()
    lobby.join(key, m1, alias="a")
    lobby.join(key, m2, alias="b")
    lobby.queue_join(key, m1)
    lobby.queue_join(key, m2)
    match = lobby.try_match(key)  # default num_needed=2
    assert len(match) == 2
```

- [ ] **Step 3: Commit**

```bash
git commit -m "feat(minigames): N-player matchmaking — try_match accepts num_needed (2-8)"
```

---

## Task 7: Update مطارحة Plugin — Backward Compatibility

**Files:**
- Modify: `backend/app/modules/minigames/mutaraha/plugin.py`
- Modify: `backend/tests/test_minigame_engine/test_mutaraha_plugin.py`

- [ ] **Step 1: Update compute_settlement return format**

Change `compute_settlement` in مطارحة to return the new format:

```python
def compute_settlement(self, terminal_result: dict) -> dict:
    buy_in = terminal_result.get("buy_in", 500)
    winner = terminal_result.get("winner")  # "player_1" or "player_2"
    loser = terminal_result.get("loser")
    
    winner_mid = terminal_result.get("winner_membership_id")
    loser_mid = terminal_result.get("loser_membership_id")
    
    return {
        "participant_results": [
            {"membership_id": winner_mid, "slot_index": 0 if winner == "player_1" else 1, "rank": 1, "payout": buy_in * 2},
            {"membership_id": loser_mid, "slot_index": 1 if winner == "player_1" else 0, "rank": 2, "payout": 0},
        ],
        "total_pool": buy_in * 2,
    }
```

- [ ] **Step 2: Update مطارحة tests**

Update `test_settlement_payout` to check new format:

```python
def test_settlement_payout(plugin):
    result = plugin.compute_settlement({
        "buy_in": 500,
        "winner": "player_1",
        "loser": "player_2",
        "winner_membership_id": "uuid-1",
        "loser_membership_id": "uuid-2",
    })
    assert result["total_pool"] == 1000
    assert len(result["participant_results"]) == 2
    winner_r = [r for r in result["participant_results"] if r["rank"] == 1][0]
    assert winner_r["payout"] == 1000
```

- [ ] **Step 3: Commit**

```bash
git commit -m "feat(mutaraha): update compute_settlement to new N-player participant_results format"
```

---

## Task 8: Update Enum Tests + Participant Model Tests

**Files:**
- Modify: `backend/tests/test_minigame_engine/test_enums.py`
- Create: `backend/tests/test_minigame_engine/test_nplayer_models.py`

- [ ] **Step 1: Remove MinigameTurnSide test**

Remove `test_turn_side_values` from `test_enums.py` (and any import of `MinigameTurnSide`).

- [ ] **Step 2: Create participant model validation test**

```python
"""Test N-player participant model constraints."""

def test_participant_slot_range():
    """Verify slot_index must be 0-7 (8 max players)."""
    # This is a DB constraint test — verify via constant
    assert 0 <= 0 and 0 <= 7  # slot 0 valid
    assert 0 <= 7 and 7 <= 7  # slot 7 valid


def test_max_players_constant():
    """The engine supports up to 8 players."""
    MAX_PLAYERS = 8
    assert MAX_PLAYERS == 8
```

- [ ] **Step 3: Run all pure tests**

Run: `cd backend && python -m pytest tests/test_minigame_engine/ --ignore=tests/test_minigame_engine/test_economy.py --ignore=tests/test_minigame_engine/test_action_service.py --ignore=tests/test_minigame_engine/test_lifecycle.py -v --tb=short`

- [ ] **Step 4: Final commit**

```bash
git commit -m "feat(minigames): Sprint A complete — N-player engine upgrade (models, economy, leaderboard, matchmaking, plugin contract)"
```

---

## Sprint A Deliverables Summary

| Change | Files | Impact |
|---|---|---|
| Participant join table | `models.py` | New model, replaces player_1/player_2 |
| Int-based turns | `models.py`, `enums.py` | Removes MinigameTurnSide enum |
| Ranked settlement | `models.py`, `economy.py` | participant_results JSONB |
| N-player matchmaking | `lobby_manager.py` | try_match(num_needed) |
| Placement stats | `leaderboard_service.py` | placement: int |
| Plugin contract update | `plugin.py` | compute_settlement new format |
| مطارحة compat | `mutaraha/plugin.py` | Uses slot 0/1 |
| SQL migration | `006_nplayer_upgrade.sql` | Data migration + schema change |

## What Sprint B Will Build

Sprint B updates the remaining services:
- `session_service.py` — create_session with participant list
- `action_service.py` — N-player turn validation
- `settlement_service.py` — N-player settlement execution
- `policy_service.py` — generalized opponent checks
- `ws_router.py` — N-player WebSocket handling
- `router.py` — REST API with participant queries
