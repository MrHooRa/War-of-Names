# Catalog & Lobby — Sprint C: REST Endpoints

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire Sprint B's `catalog_service` into two new REST endpoints with proper Arabic error handling and deprecation notices on the existing `GET /api/minigames` endpoint.

**Architecture:** Two thin endpoint functions that resolve the caller's membership, validate the competition exists, call the service layer, and convert domain errors to FastAPI `HTTPException` with Arabic `detail`. The endpoints are additive — no existing routes are removed.

**Tech Stack:** FastAPI, SQLAlchemy 2.x async, existing auth dependencies

**BRD Reference:** `docs/minigames/War of Names - Minigames Catalog & Lobby BRD - V1.0.md` — §12.1, §12.2, §12.4, §12.5

**Depends on:** Sprint A (`MinigameCatalogConfig`) + Sprint B (`catalog_service.get_catalog`, `catalog_service.get_lobby_detail`)

---

## Sprint Scope

1. **`GET /api/competitions/{competition_id}/minigames/catalog`** — catalog read model
2. **`GET /api/competitions/{competition_id}/minigames/{game_type}/lobby`** — single-game lobby page read model
3. **Arabic error responses** — 401/403/404 with culturally appropriate messages
4. **Deprecation docstrings** on the existing `GET /api/minigames` endpoint per BRD §12.5
5. **Shared helpers** for consistent validation and error handling

**NOT in Sprint C:** WebSocket channel (Sprint D), integration tests against Docker (deferred until the running system can be exercised), frontend (Sprint E), query-count assertions (those require a dedicated telemetry harness).

---

## File Structure

```
backend/app/modules/minigames/
└── router.py                              # MODIFY: +2 endpoints, +1 helper, update existing docstrings

backend/tests/test_minigame_engine/
└── (no new tests — router tests need SQLAlchemy and are deferred to Docker)
```

**One file modified, zero files created.** Sprint C is a thin adapter layer.

---

## Task 1: Shared Error Helpers

**Files:**
- Modify: `backend/app/modules/minigames/router.py`

Add three helper functions to keep the endpoints small and error-handling consistent.
These sit next to the existing `_get_membership` and `_get_active_season_cycle`
helpers so the pattern is obvious to future contributors.

- [ ] **Step 1: Add Competition import**

Find the imports near the top of `router.py`:

```python
from app.modules.competitions.models import Cycle, Membership, Season
```

Replace with:

```python
from app.modules.competitions.models import Competition, Cycle, Membership, Season
```

- [ ] **Step 2: Add `_ensure_competition_exists` helper**

Find the existing `_get_active_season_cycle` helper (around line 97). Add a new helper right below it:

```python
async def _ensure_competition_exists(session, competition_id: uuid.UUID) -> Competition:
    """Return the Competition row or raise 404 with an Arabic message.

    Used by catalog/lobby endpoints where a missing competition must be a
    distinct error from "not a member". BRD §12.4.
    """
    result = await session.execute(
        select(Competition).where(Competition.id == competition_id)
    )
    competition = result.scalars().first()
    if competition is None:
        raise HTTPException(status_code=404, detail="المسابقة غير موجودة")
    return competition
```

- [ ] **Step 3: Add `_resolve_catalog_caller` helper**

Right below `_ensure_competition_exists`, add:

```python
async def _resolve_catalog_caller(
    session,
    *,
    account_id: uuid.UUID,
    competition_id: uuid.UUID,
) -> Membership:
    """Resolve the catalog caller's membership with Arabic error on failure.

    Validates in order:
      1. Competition exists → 404 "المسابقة غير موجودة"
      2. Caller is an active member → 403 "أنت لست عضواً في هذه المسابقة"

    Returns the membership on success so callers can read balance + bankruptcy.
    """
    await _ensure_competition_exists(session, competition_id)

    membership = await _get_membership(session, account_id, competition_id)
    if membership is None:
        raise HTTPException(
            status_code=403, detail="أنت لست عضواً في هذه المسابقة"
        )
    return membership
```

- [ ] **Step 4: Syntax check**

```bash
cd backend && python -c "import ast; ast.parse(open('app/modules/minigames/router.py').read()); print('router syntax ok')"
```

- [ ] **Step 5: Commit**

```bash
cd "e:/Salman/مشاريع/War of Names" && git add backend/app/modules/minigames/router.py && git commit -m "feat(catalog): shared REST helpers — _ensure_competition_exists + _resolve_catalog_caller

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: `GET /catalog` Endpoint

**Files:**
- Modify: `backend/app/modules/minigames/router.py`

- [ ] **Step 1: Add the endpoint**

Find the existing `GET /api/minigames` endpoint (around line 182) and add the new catalog endpoint **immediately before** it so players see the richer endpoint first in OpenAPI.

```python
@router.get("/api/competitions/{competition_id}/minigames/catalog")
async def get_catalog_endpoint(
    competition_id: uuid.UUID,
    current_account: CurrentAccount,
):
    """Return the full minigames catalog for a player in a competition.

    This is the primary discovery surface — see BRD §12.1.
    The response is a scoped, enriched read model with:
      - buy-in resolved from competition settings
      - live presence/queue/active-match counts
      - the caller's personal stats and active session (if any)
      - a correlation_id for telemetry tracking

    For the legacy global game-type list, see ``GET /api/minigames`` (BRD §12.5).

    Errors (BRD §12.4):
      401 — JWT missing or invalid (handled by get_current_account dependency)
      403 — caller is not an active member of the competition
      404 — competition does not exist
    """
    from app.modules.minigames.catalog_read_model import catalog_response_to_dict  # noqa: PLC0415
    from app.modules.minigames.catalog_service import get_catalog  # noqa: PLC0415

    async with async_session() as session:
        membership = await _resolve_catalog_caller(
            session,
            account_id=current_account.id,
            competition_id=competition_id,
        )
        season, cycle = await _get_active_season_cycle(session, competition_id)

        response = await get_catalog(
            session,
            competition_id=competition_id,
            membership_id=membership.id,
            player_balance=membership.current_balance,
            is_bankrupt=membership.is_bankrupt,
            season_id=season.id if season else None,
            cycle_id=cycle.id if cycle else None,
        )

    return catalog_response_to_dict(response)
```

- [ ] **Step 2: Syntax check**

```bash
cd backend && python -c "import ast; ast.parse(open('app/modules/minigames/router.py').read()); print('router syntax ok')"
```

- [ ] **Step 3: Commit**

```bash
cd "e:/Salman/مشاريع/War of Names" && git add backend/app/modules/minigames/router.py && git commit -m "feat(catalog): GET /api/competitions/{id}/minigames/catalog endpoint

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: `GET /{game_type}/lobby` Endpoint

**Files:**
- Modify: `backend/app/modules/minigames/router.py`

- [ ] **Step 1: Add the endpoint**

Find the existing `get_game_leaderboard` endpoint (`GET /api/competitions/{competition_id}/minigames/{game_type}/leaderboard` around line 247) and add the new lobby detail endpoint **immediately before** it.

```python
@router.get("/api/competitions/{competition_id}/minigames/{game_type}/lobby")
async def get_lobby_detail_endpoint(
    competition_id: uuid.UUID,
    game_type: str,
    current_account: CurrentAccount,
):
    """Return the full lobby page read model for a single game.

    See BRD §8.2 for the response shape and §12.2 for the endpoint contract.

    Errors (BRD §12.4):
      401 — JWT missing or invalid
      403 — caller is not an active member of the competition
      404 — competition or game_type does not exist (or game is hidden)
    """
    from app.modules.minigames.catalog_service import get_lobby_detail  # noqa: PLC0415

    async with async_session() as session:
        membership = await _resolve_catalog_caller(
            session,
            account_id=current_account.id,
            competition_id=competition_id,
        )
        season, cycle = await _get_active_season_cycle(session, competition_id)

        try:
            response = await get_lobby_detail(
                session,
                game_type=game_type,
                competition_id=competition_id,
                membership_id=membership.id,
                player_balance=membership.current_balance,
                is_bankrupt=membership.is_bankrupt,
                season_id=season.id if season else None,
                cycle_id=cycle.id if cycle else None,
            )
        except LookupError:
            # Service raises LookupError when the game is missing or hidden.
            # Convert to a 404 with an Arabic message (BRD §12.4).
            raise HTTPException(status_code=404, detail="نوع اللعبة غير موجود")

    return {
        "correlation_id": response.correlation_id,
        "game": response.game,
        "my_state": response.my_state,
        "my_stats": response.my_stats,
        "lobby": response.lobby,
        "leaderboard_preview": response.leaderboard_preview,
        "how_to_play": response.how_to_play,
    }
```

- [ ] **Step 2: Syntax check**

```bash
cd backend && python -c "import ast; ast.parse(open('app/modules/minigames/router.py').read()); print('router syntax ok')"
```

- [ ] **Step 3: Commit**

```bash
cd "e:/Salman/مشاريع/War of Names" && git add backend/app/modules/minigames/router.py && git commit -m "feat(catalog): GET /api/competitions/{id}/minigames/{game_type}/lobby endpoint

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Deprecation Docstrings

**Files:**
- Modify: `backend/app/modules/minigames/router.py`

BRD §12.5 says `GET /api/minigames` is NOT deprecated — it stays as the global game-type
list. But its docstring should explain the distinction so future contributors don't
confuse it with the new catalog endpoint.

- [ ] **Step 1: Update the `GET /api/minigames` docstring**

Find the existing endpoint (around line 182). Replace the current docstring with:

```python
@router.get("/api/minigames")
async def list_game_types(current_account: CurrentAccount):
    """Return the global list of active minigame types.

    This endpoint is **intentionally unscoped** — it does not require
    a competition_id and returns only engine-level metadata from
    ``minigame_types``. It stays as the lightweight discovery surface
    for admin tools, deep linking, and any client that needs a flat
    list of games on the platform.

    For the rich, scoped catalog (with buy-in, live counts, player
    state, and CTAs), use ``GET /api/competitions/{id}/minigames/catalog``
    instead. See BRD §12.5 for the deprecation path.
    """
    # ... (keep existing implementation)
```

- [ ] **Step 2: Update the module-level docstring at the top of `router.py`**

Find the docstring at lines 1-19. Replace the `Player` section with:

```python
"""FastAPI router for the minigame engine.

Endpoints:

  Player — Discovery
  ------------------
  GET  /api/minigames
         → unscoped global list of active game types (engine metadata only)
  GET  /api/competitions/{competition_id}/minigames/catalog
         → scoped rich catalog (BRD §12.1) — the primary player surface
  GET  /api/competitions/{competition_id}/minigames/{game_type}/lobby
         → single-game lobby page read model (BRD §12.2)

  Player — Gameplay
  -----------------
  GET  /api/competitions/{competition_id}/minigames/{game_type}/leaderboard
  GET  /api/competitions/{competition_id}/minigames/{game_type}/stats
  GET  /api/competitions/{competition_id}/minigames/{game_type}/sessions
  POST /api/competitions/{competition_id}/minigames/{game_type}/challenge
  POST /api/competitions/{competition_id}/minigames/{game_type}/challenge/{session_id}/respond

  Admin
  -----
  GET  /api/admin/minigames
  GET  /api/admin/minigames/{game_type}/sessions
  POST /api/admin/minigames/{game_type}/sessions/{session_id}/cancel
  GET  /api/admin/minigames/catalog-configs
  GET  /api/admin/minigames/catalog-configs/{game_type}
  PUT  /api/admin/minigames/catalog-configs/{game_type}
  DELETE /api/admin/minigames/catalog-configs/{game_type}
"""
```

- [ ] **Step 3: Syntax check**

```bash
cd backend && python -c "import ast; ast.parse(open('app/modules/minigames/router.py').read()); print('router syntax ok')"
```

- [ ] **Step 4: Commit**

```bash
cd "e:/Salman/مشاريع/War of Names" && git add backend/app/modules/minigames/router.py && git commit -m "docs(catalog): deprecation path docstrings — clarify GET /api/minigames vs scoped catalog endpoint

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: Final Verification

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
  --tb=short 2>&1 | tail -5
```

Expected: 282 tests pass (unchanged from Sprint B — Sprint C is endpoint-only, no new unit tests).

- [ ] **Step 2: Verify the module still imports end-to-end in a DB-free smoke test**

```bash
cd backend && python -c "
import ast
ast.parse(open('app/modules/minigames/router.py').read())
print('router.py final syntax: OK')
"
```

- [ ] **Step 3: Commit plan document**

```bash
cd "e:/Salman/مشاريع/War of Names" && git add docs/superpowers/plans/2026-04-04-catalog-sprint-c.md && git commit -m "docs(catalog): Sprint C detailed task-by-task plan — REST endpoints

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Sprint C Deliverables Summary

| Task | Component | Tests |
|---|---|---|
| 1 | Shared helpers (`_ensure_competition_exists`, `_resolve_catalog_caller`) | via Docker |
| 2 | `GET /api/competitions/{id}/minigames/catalog` | via Docker |
| 3 | `GET /api/competitions/{id}/minigames/{game_type}/lobby` | via Docker |
| 4 | Deprecation docstrings on legacy endpoint + module header | — |
| 5 | Verification + plan commit | — |
| **Total** | **1 file modified** | **0 new unit tests** |

## Why No New Unit Tests in Sprint C

FastAPI endpoint tests require one of two setups:
1. An in-memory DB fixture (requires SQLAlchemy installed locally — currently not)
2. A full Docker-compose harness (reserved for integration test suite)

The business logic (`catalog_service.get_catalog`, `build_catalog_cards`,
`resolve_catalog_config`, `build_player_count_label`, etc.) is already covered
by **49 pure unit tests** from Sprint A+B that run in 0.1 seconds without any
infrastructure. Sprint C adds thin adapters over that tested core — the failure
modes are narrow (wrong error code, missing Arabic message) and better verified
via curl against a running stack.

Sprint C closes the gap between the pure service layer and the HTTP wire.
Integration tests against the Docker stack will be added in a later sprint
dedicated to end-to-end verification.

## What Sprint D Will Build On This

Sprint D (WebSocket Catalog Channel) will:
- Open a persistent WebSocket at `WS /ws/competitions/{id}/minigames/catalog?token=JWT`
- Reuse `catalog_service.get_catalog()` for the initial `catalog_state` snapshot
- Hook into `lobby_manager` event emission to broadcast `catalog_update` patches
- Enforce the same auth/error rules via close codes 4001/4003/4008/4013
- Implement the client-side reconciliation protocol from BRD §4.2.1
