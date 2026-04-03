# Minigame Engine — Sprint 3: Settings Integration, Seed Data & Admin Controls

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace all hardcoded minigame constants with the existing settings cascade, seed MinigameType records + minigame setting definitions, add kill switch support, and extend admin endpoints for settings management and session event viewing.

**Architecture:** Uses the existing `SettingDefinition`/`SettingValue` system and `get_settings_batch()` from `app.modules.settings.service`. New minigame settings are seeded via `_seed_settings()` in `seed.py`. The router replaces hardcoded constants with settings lookups. Kill switches use the existing `MinigameType.status` field (active/disabled) plus a new setting `minigame_kill_switch_level` per competition.

**Tech Stack:** Python 3.12, SQLAlchemy 2.x async, FastAPI, pytest

**BRD Reference:** `docs/minigames/War of Names - Minigame Engine BRD - V1.0.md` — Sections 14, 16

**Depends on:** Sprint 0 (models), Sprint 1 (services), Sprint 2 (router, policy)

---

## Sprint 3 Scope

1. **Seed minigame setting definitions** — 7 settings (buy_in, daily_cap, same_opponent_limit, turn_duration, overtime_enabled, grace_timer, kill_switch_level)
2. **Seed MinigameType record** — ensure at least a placeholder "mutaraha" type exists in DB
3. **Settings helper** — `get_minigame_settings()` that loads all minigame settings via cascade
4. **Router settings integration** — replace hardcoded `_DEFAULT_BUY_IN=500`, `_DAILY_CAP=2`, `_SAME_OPPONENT_LIMIT=1` with settings lookups
5. **Kill switch** — check `minigame_kill_switch_level` before creating sessions; admin endpoint to set it
6. **Admin endpoints** — session events viewer, settings update, kill switch control
7. **Unit tests** for settings helper and kill switch logic

**NOT in Sprint 3:** WebSocket, lobby, frontend. Those are Sprint 4.

---

## File Structure

```
backend/app/modules/minigames/
├── (existing Sprint 0-2 files)
├── settings_helper.py             # CREATE: minigame settings loader + kill switch check
└── router.py                      # MODIFY: replace hardcoded constants with settings

backend/app/core/
└── seed.py                        # MODIFY: add minigame settings + MinigameType seed

backend/tests/test_minigame_engine/
└── test_settings_helper.py        # CREATE: kill switch + settings defaults tests
```

---

## Task 1: Seed Minigame Settings + MinigameType

**Files:**
- Modify: `backend/app/core/seed.py`

- [ ] **Step 1: Read current seed.py to understand pattern**

Read `backend/app/core/seed.py` lines 374-440 to see how SETTING_IDS and settings_data are structured. Also read lines 660-690 to see how settings are persisted.

- [ ] **Step 2: Add minigame setting IDs**

Add to the `SETTING_IDS` dict in `seed.py` (after the last entry):

```python
    # Minigame engine settings
    "minigame_enabled": uuid.UUID("00000000-0000-0000-0000-000000000070"),
    "minigame_buy_in": uuid.UUID("00000000-0000-0000-0000-000000000071"),
    "minigame_daily_limit": uuid.UUID("00000000-0000-0000-0000-000000000072"),
    "minigame_same_opponent_limit": uuid.UUID("00000000-0000-0000-0000-000000000073"),
    "minigame_turn_duration_sec": uuid.UUID("00000000-0000-0000-0000-000000000074"),
    "minigame_overtime_enabled": uuid.UUID("00000000-0000-0000-0000-000000000075"),
    "minigame_grace_timer_sec": uuid.UUID("00000000-0000-0000-0000-000000000076"),
    "minigame_kill_switch": uuid.UUID("00000000-0000-0000-0000-000000000077"),
```

- [ ] **Step 3: Add minigame setting definitions to settings_data**

Add to the `settings_data` list in `_seed_settings()` (after the last existing entry):

```python
        # ── Minigame Engine ──
        {
            "id": SETTING_IDS["minigame_enabled"],
            "key": "minigame_enabled",
            "category": "minigame",
            "data_type": SettingDataType.BOOLEAN,
            "default_value": {"v": False},
            "description": "تفعيل الألعاب المصغرة في المسابقة",
            "is_per_competition": True,
        },
        {
            "id": SETTING_IDS["minigame_buy_in"],
            "key": "minigame_buy_in",
            "category": "minigame",
            "data_type": SettingDataType.INTEGER,
            "default_value": {"v": 500},
            "allowed_values": {"min": 0, "max": 50000},
            "description": "مبلغ الدخول للعبة المصغرة (نقاط)",
            "is_per_competition": True,
        },
        {
            "id": SETTING_IDS["minigame_daily_limit"],
            "key": "minigame_daily_limit",
            "category": "minigame",
            "data_type": SettingDataType.INTEGER,
            "default_value": {"v": 2},
            "allowed_values": {"min": 1, "max": 50},
            "description": "الحد الأقصى لعدد المباريات يومياً لكل لاعب",
            "is_per_competition": True,
        },
        {
            "id": SETTING_IDS["minigame_same_opponent_limit"],
            "key": "minigame_same_opponent_limit",
            "category": "minigame",
            "data_type": SettingDataType.INTEGER,
            "default_value": {"v": 1},
            "allowed_values": {"min": 1, "max": 10},
            "description": "الحد الأقصى لمبارزة نفس الخصم في الدورة الواحدة",
            "is_per_competition": True,
        },
        {
            "id": SETTING_IDS["minigame_turn_duration_sec"],
            "key": "minigame_turn_duration_sec",
            "category": "minigame",
            "data_type": SettingDataType.INTEGER,
            "default_value": {"v": 30},
            "allowed_values": {"min": 10, "max": 120},
            "description": "مدة الدور بالثواني",
            "is_per_competition": True,
        },
        {
            "id": SETTING_IDS["minigame_overtime_enabled"],
            "key": "minigame_overtime_enabled",
            "category": "minigame",
            "data_type": SettingDataType.BOOLEAN,
            "default_value": {"v": True},
            "description": "تفعيل الوقت الإضافي عند التعادل",
            "is_per_competition": True,
        },
        {
            "id": SETTING_IDS["minigame_grace_timer_sec"],
            "key": "minigame_grace_timer_sec",
            "category": "minigame",
            "data_type": SettingDataType.INTEGER,
            "default_value": {"v": 60},
            "allowed_values": {"min": 15, "max": 300},
            "description": "مهلة إعادة الاتصال بالثواني",
            "is_per_competition": True,
        },
        {
            "id": SETTING_IDS["minigame_kill_switch"],
            "key": "minigame_kill_switch",
            "category": "minigame",
            "data_type": SettingDataType.STRING,
            "default_value": {"v": "off"},
            "allowed_values": {"options": ["off", "soft", "hard", "emergency"]},
            "description": "مفتاح إيقاف الألعاب المصغرة (off/soft/hard/emergency)",
            "is_per_competition": True,
        },
```

- [ ] **Step 4: Add MinigameType seed function**

Add a new function `_seed_minigame_types` in `seed.py` and call it from the main `seed()` function:

```python
async def _seed_minigame_types(session: AsyncSession) -> None:
    """Seed minigame type registry with known game types."""
    from app.modules.minigames.models import MinigameType

    types_data = [
        {
            "id": "mutaraha",
            "name": "مطارحة",
            "description": "مبارزة كلمات 1v1 — خمّن كلمات خصمك قبل ما يخمّن كلماتك",
            "min_players": 2,
            "max_players": 2,
            "supports_overtime": True,
        },
    ]

    for td in types_data:
        existing = await session.get(MinigameType, td["id"])
        if existing:
            continue
        session.add(MinigameType(**td))

    await session.commit()
```

Then in the main `seed()` function, add the call after the last existing seed call:

```python
    await _seed_minigame_types(session)
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/seed.py
git commit -m "feat(minigames): seed minigame settings (8 definitions) + MinigameType record for مطارحة"
```

---

## Task 2: Settings Helper + Kill Switch Logic

**Files:**
- Create: `backend/app/modules/minigames/settings_helper.py`
- Create: `backend/tests/test_minigame_engine/test_settings_helper.py`

- [ ] **Step 1: Write tests for kill switch and defaults**

Create `backend/tests/test_minigame_engine/test_settings_helper.py`:

```python
"""Test settings helper — defaults and kill switch logic."""

from app.modules.minigames.settings_helper import (
    MINIGAME_SETTING_KEYS,
    MINIGAME_DEFAULTS,
    check_kill_switch,
    KillSwitchLevel,
)


# ── Defaults ─────────────────────────────────────────────────

def test_all_setting_keys_have_defaults():
    for key in MINIGAME_SETTING_KEYS:
        assert key in MINIGAME_DEFAULTS, f"Missing default for {key}"


def test_default_buy_in():
    assert MINIGAME_DEFAULTS["minigame_buy_in"] == 500


def test_default_daily_limit():
    assert MINIGAME_DEFAULTS["minigame_daily_limit"] == 2


def test_default_kill_switch():
    assert MINIGAME_DEFAULTS["minigame_kill_switch"] == "off"


# ── Kill switch levels ───────────────────────────────────────

def test_kill_switch_off():
    result = check_kill_switch("off")
    assert result.level == KillSwitchLevel.OFF
    assert result.can_create_session is True
    assert result.can_matchmake is True


def test_kill_switch_soft():
    result = check_kill_switch("soft")
    assert result.level == KillSwitchLevel.SOFT
    assert result.can_create_session is True  # Active sessions continue
    assert result.can_matchmake is False


def test_kill_switch_hard():
    result = check_kill_switch("hard")
    assert result.level == KillSwitchLevel.HARD
    assert result.can_create_session is False
    assert result.can_matchmake is False


def test_kill_switch_emergency():
    result = check_kill_switch("emergency")
    assert result.level == KillSwitchLevel.EMERGENCY
    assert result.can_create_session is False
    assert result.can_matchmake is False
    assert result.cancel_active is True


def test_kill_switch_unknown_treated_as_off():
    result = check_kill_switch("unknown_value")
    assert result.level == KillSwitchLevel.OFF
    assert result.can_create_session is True


def test_kill_switch_none_treated_as_off():
    result = check_kill_switch(None)
    assert result.level == KillSwitchLevel.OFF
    assert result.can_create_session is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_minigame_engine/test_settings_helper.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement settings helper**

Create `backend/app/modules/minigames/settings_helper.py`:

```python
"""Minigame settings helper — loads settings via cascade with fallback defaults.

Pure functions:
    check_kill_switch — evaluate kill switch level and permissions

Async:
    get_minigame_settings — loads all minigame settings via cascade
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import uuid
    from sqlalchemy.ext.asyncio import AsyncSession

# All minigame setting keys
MINIGAME_SETTING_KEYS: list[str] = [
    "minigame_enabled",
    "minigame_buy_in",
    "minigame_daily_limit",
    "minigame_same_opponent_limit",
    "minigame_turn_duration_sec",
    "minigame_overtime_enabled",
    "minigame_grace_timer_sec",
    "minigame_kill_switch",
]

# Fallback defaults (used when DB settings are missing)
MINIGAME_DEFAULTS: dict[str, Any] = {
    "minigame_enabled": False,
    "minigame_buy_in": 500,
    "minigame_daily_limit": 2,
    "minigame_same_opponent_limit": 1,
    "minigame_turn_duration_sec": 30,
    "minigame_overtime_enabled": True,
    "minigame_grace_timer_sec": 60,
    "minigame_kill_switch": "off",
}


class KillSwitchLevel(StrEnum):
    OFF = "off"
    SOFT = "soft"
    HARD = "hard"
    EMERGENCY = "emergency"


@dataclass
class KillSwitchStatus:
    """Result of evaluating kill switch level."""
    level: KillSwitchLevel
    can_create_session: bool
    can_matchmake: bool
    cancel_active: bool = False
    message_ar: str = ""


def check_kill_switch(value: str | None) -> KillSwitchStatus:
    """Evaluate kill switch level and return permissions.

    BRD Section 16.3:
    - off: everything works
    - soft: no new matchmaking, active sessions continue
    - hard: no new sessions at all
    - emergency: cancel all active sessions + refund
    """
    if value is None or value not in {e.value for e in KillSwitchLevel}:
        return KillSwitchStatus(
            level=KillSwitchLevel.OFF,
            can_create_session=True,
            can_matchmake=True,
        )

    level = KillSwitchLevel(value)

    if level == KillSwitchLevel.OFF:
        return KillSwitchStatus(
            level=level,
            can_create_session=True,
            can_matchmake=True,
        )

    if level == KillSwitchLevel.SOFT:
        return KillSwitchStatus(
            level=level,
            can_create_session=True,
            can_matchmake=False,
            message_ar="التوفيق معطل مؤقتاً — المباريات الجارية مستمرة",
        )

    if level == KillSwitchLevel.HARD:
        return KillSwitchStatus(
            level=level,
            can_create_session=False,
            can_matchmake=False,
            message_ar="الألعاب المصغرة معطلة حالياً",
        )

    # EMERGENCY
    return KillSwitchStatus(
        level=level,
        can_create_session=False,
        can_matchmake=False,
        cancel_active=True,
        message_ar="إيقاف طارئ — جميع الجلسات ملغاة مع استرداد",
    )


async def get_minigame_settings(
    session: "AsyncSession",
    *,
    competition_id: "uuid.UUID",
    season_id: "uuid.UUID | None" = None,
    cycle_id: "uuid.UUID | None" = None,
) -> dict[str, Any]:
    """Load all minigame settings via cascade, with fallback defaults.

    Returns dict like:
        {"minigame_buy_in": 500, "minigame_daily_limit": 2, ...}
    """
    from app.modules.settings.service import get_settings_batch

    raw = await get_settings_batch(
        session,
        MINIGAME_SETTING_KEYS,
        competition_id=competition_id,
        season_id=season_id,
        cycle_id=cycle_id,
    )

    # Apply fallback defaults for any missing keys
    result = {}
    for key in MINIGAME_SETTING_KEYS:
        value = raw.get(key)
        if value is None:
            value = MINIGAME_DEFAULTS[key]
        result[key] = value

    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_minigame_engine/test_settings_helper.py -v`
Expected: All 11 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/modules/minigames/settings_helper.py backend/tests/test_minigame_engine/test_settings_helper.py
git commit -m "feat(minigames): add settings helper — kill switch logic + defaults + cascade loader"
```

---

## Task 3: Router Settings Integration + Admin Endpoints

**Files:**
- Modify: `backend/app/modules/minigames/router.py`

Replace the hardcoded constants with settings lookups and add admin endpoints for settings/kill switch.

- [ ] **Step 1: Replace hardcoded constants in router**

In `router.py`:
1. Remove `_DEFAULT_BUY_IN`, `_DAILY_CAP`, `_SAME_OPPONENT_LIMIT` constants
2. In `send_challenge()`: load settings via `get_minigame_settings()` and use values from there
3. Add kill switch check before creating sessions
4. Add admin endpoint `PATCH /api/admin/minigames/{game_type}/kill-switch` to set kill switch level
5. Add admin endpoint `GET /api/admin/minigames/{game_type}/sessions/{session_id}/events` to view session events

The key changes in `send_challenge()`:

```python
# Before (hardcoded):
buy_in_amount=_DEFAULT_BUY_IN,
daily_cap=_DAILY_CAP,
same_opponent_limit=_SAME_OPPONENT_LIMIT,

# After (from settings):
from app.modules.minigames.settings_helper import get_minigame_settings, check_kill_switch

mg_settings = await get_minigame_settings(session, competition_id=competition_id, season_id=season.id if season else None, cycle_id=cycle.id if cycle else None)

# Check kill switch
ks = check_kill_switch(mg_settings.get("minigame_kill_switch"))
if not ks.can_create_session:
    raise HTTPException(status_code=403, detail=ks.message_ar)

buy_in = mg_settings["minigame_buy_in"]
daily_cap = mg_settings["minigame_daily_limit"]
same_opp = mg_settings["minigame_same_opponent_limit"]
```

New admin endpoints:

```python
# Kill switch control
class KillSwitchRequest(BaseModel):
    level: str  # "off", "soft", "hard", "emergency"

@router.patch("/api/admin/minigames/{game_type}/kill-switch")
async def admin_set_kill_switch(
    game_type: str,
    body: KillSwitchRequest,
    admin: AdminAccount,
    competition_id: uuid.UUID | None = None,
):
    """Set kill switch level for a game type."""
    # Validate level
    if body.level not in ("off", "soft", "hard", "emergency"):
        raise HTTPException(status_code=400, detail="مستوى غير صالح")
    
    # Update setting via SettingValue
    # ... (upsert minigame_kill_switch for this competition)
    return {"success": True, "data": {"level": body.level, "message": "تم تحديث مفتاح الإيقاف"}}


# Session events viewer
@router.get("/api/admin/minigames/{game_type}/sessions/{session_id}/events")
async def admin_get_session_events(
    game_type: str,
    session_id: uuid.UUID,
    admin: AdminAccount,
):
    """Admin: view all events for a session."""
    # Query MinigameSessionEvent ordered by revision ASC
    return {"success": True, "data": [...]}
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/modules/minigames/router.py
git commit -m "feat(minigames): integrate settings cascade — replace hardcoded values, add kill switch + session events endpoints"
```

---

## Task 4: Final Verification

- [ ] **Step 1: Run all pure tests**

Run: `cd backend && python -m pytest tests/test_minigame_engine/test_enums.py tests/test_minigame_engine/test_plugin_contract.py tests/test_minigame_engine/test_registry.py tests/test_minigame_engine/test_state_machine.py tests/test_minigame_engine/test_session_service.py tests/test_minigame_engine/test_settlement_service.py tests/test_minigame_engine/test_policy_service.py tests/test_minigame_engine/test_leaderboard_service.py tests/test_minigame_engine/test_settings_helper.py -v --tb=short 2>&1 | tail -10`

Expected: All tests pass (~121+)

- [ ] **Step 2: Final commit**

```bash
git add -A
git commit -m "feat(minigames): Sprint 3 complete — settings integration, kill switches, seed data, admin controls"
```

---

## Sprint 3 Deliverables Summary

| Component | File | Tests |
|---|---|---|
| Seed data | `core/seed.py` (modified) | via Docker rebuild |
| Settings helper | `minigames/settings_helper.py` | 11 |
| Router integration | `minigames/router.py` (modified) | via Docker integration |
| **Total** | **1 created, 2 modified** | **~11 new tests** |

## What Sprint 4 Will Build On This

Sprint 4 (WebSocket + Lobby) will use:
- `get_minigame_settings()` for game configuration
- `check_kill_switch()` before lobby join + queue operations
- MinigameType seed record for "mutaraha" (exists in DB after seed)
- All services from Sprint 0-2 for real-time game play
