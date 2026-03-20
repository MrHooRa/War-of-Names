# Phase 3: Season/Cycle/Competition 360 Review & Completion Pass

**Date:** 2026-03-19
**Scope:** Domain completion and correction for the Season → Cycle operational model

---

## A. 360 Review — What Exists, What's Weak, What's Missing

### What Existed Before This Phase

| Layer | State |
|---|---|
| **Models** | Competition, Season, Cycle, Membership fully defined with correct FK chains |
| **Enums** | SeasonStatus, CycleStatus (DRAFT/ACTIVE/PAUSED/COMPLETED/ARCHIVED), ProtectionType, BankruptcyState, NotificationType (CYCLE_STARTED, CYCLE_ENDED) |
| **Admin endpoints** | CRUD for seasons/cycles, `POST /cycles/{id}/end` (with inline event logic), `POST /cycles/{id}/activate` (bare status change) |
| **Player endpoints** | `/api/me/dashboard` (no season/cycle info), `/api/me/competition-context` (season_id/cycle_id only, no labels/dates) |
| **Frontend Admin** | AdminSeasonsPage with basic create/status/end but no start-with-events, no advance, no broadcast |
| **Frontend Player** | Zero season/cycle visibility on Dashboard, Lobby, or AppLayout header |
| **Settings cascade** | SettingScope enum supports GLOBAL/COMPETITION/SEASON/CYCLE but no resolution logic exists |

### What Was Structurally Wrong

1. **No cycle START endpoint with real events** — `activate` just set status, no protection reset, no bankruptcy recovery, no notifications
2. **`end_cycle` used `NotificationType.SYSTEM_UPDATE`** which doesn't exist in the enum (should be `CYCLE_ENDED`)
3. **Business logic inlined in route handler** — the cycle end logic was 60+ lines inside the admin router, not reusable
4. **Dashboard returned zero temporal context** — a player had no idea what season or cycle they were in
5. **AppLayout header** used a static `seasonText` prop (from GameInfo.current_season) instead of the real active season
6. **useCompetitionContext hook** returned season_id/cycle_id but no human-readable labels or dates
7. **No advance operation** — admin had to manually end one cycle then activate the next

---

## B. Design Direction

**Cycle as an Operational Engine:** Each cycle transition (start/end) triggers real gameplay events:
- Protection reset (all temporary protections cleared)
- Bankruptcy recovery (all is_bankrupt flags cleared, BankruptcyRecords marked CLEARED)
- Member notifications (CYCLE_STARTED / CYCLE_ENDED with appropriate messages)
- Status cascading (only one active cycle per season)

**Season as Live Identity:** Season name and cycle label are visible everywhere players look — header, dashboard, lobby.

**Service Layer Pattern:** All cycle lifecycle logic lives in `cycle_service.py`, callable from admin routes, future auto-progression jobs, or any internal trigger.

---

## C. Closure Plan — What Was Implemented

### Backend

1. **Created `backend/app/modules/competitions/cycle_service.py`**
   - `start_cycle()` — full lifecycle: deactivate other cycles, activate this one, clear protections, clear bankruptcies, notify members
   - `end_cycle()` — full lifecycle: complete cycle, clear protections, clear bankruptcies (with BankruptcyRecord resolution), notify members
   - `advance_to_next_cycle()` — end current + start next in single operation
   - `broadcast_to_competition()` — send announcement to all active members
   - Internal helpers: `_get_competition_members()`, `_clear_protections()`, `_clear_bankruptcies()`, `_notify_members()`
   - `CycleTransitionResult` class for structured reporting

2. **Refactored `backend/app/modules/admin/router.py`**
   - New `POST /api/admin/cycles/{id}/start` — starts cycle with full lifecycle events
   - Refactored `POST /api/admin/cycles/{id}/end` — now delegates to service
   - Kept `POST /api/admin/cycles/{id}/activate` — simple status change (backward compat)
   - New `POST /api/admin/cycles/{id}/advance` — ends active + starts this one
   - New `POST /api/admin/competitions/{id}/broadcast` — sends announcement to all members
   - Added `BroadcastBody` Pydantic model

3. **Enriched `backend/app/modules/dashboard/router.py`**
   - `/api/me/dashboard` now returns: `season_id`, `season_name`, `cycle_id`, `cycle_label`, `cycle_starts_at`, `cycle_ends_at`

4. **Enriched `backend/app/modules/competitions/router.py`**
   - `/api/me/competition-context` now returns: `season_name`, `cycle_label`, `cycle_starts_at`, `cycle_ends_at`

### Frontend

5. **Rewrote `frontend/src/pages/admin/AdminSeasonsPage.jsx`**
   - Start cycle button (for draft/paused cycles when no active cycle exists)
   - Advance button (end current + start this, when another cycle is active)
   - End cycle button (for active cycles)
   - Broadcast form (title + message → all competition members)
   - Result banners with detailed transition reports
   - Active cycle indicator (pulsing radio icon, highlighted row)

6. **Updated `frontend/src/hooks/useCompetitionContext.js`**
   - Now exposes: `competitionName`, `seasonName`, `cycleLabel`, `cycleStartsAt`, `cycleEndsAt`

7. **Updated `frontend/src/components/AppLayout.jsx`**
   - Header now shows real season name + cycle label (from useCompetitionContext)
   - Removed `seasonText` prop dependency

8. **Updated `frontend/src/pages/DashboardPage.jsx`**
   - Season/cycle badges in hero section (below competition name)
   - Season and cycle info in Quick Info sidebar

9. **Updated `frontend/src/pages/LobbyPage.jsx`**
   - Status indicator now shows season name + cycle label

---

## D. File Structure

### New Files
```
backend/app/modules/competitions/cycle_service.py    # Cycle lifecycle service
```

### Modified Files
```
backend/app/modules/admin/router.py                  # New endpoints + refactored cycle ops
backend/app/modules/dashboard/router.py               # Season/cycle context in dashboard
backend/app/modules/competitions/router.py             # Season/cycle labels in competition-context
frontend/src/pages/admin/AdminSeasonsPage.jsx          # Full rewrite with operational depth
frontend/src/hooks/useCompetitionContext.js             # Added season/cycle fields
frontend/src/components/AppLayout.jsx                  # Real season name in header
frontend/src/pages/DashboardPage.jsx                   # Season/cycle visibility
frontend/src/pages/LobbyPage.jsx                       # Season/cycle in lobby header
```

---

## E. API Report

### New Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/admin/cycles/{id}/start` | Start cycle with full lifecycle events (protection reset, bankruptcy recovery, notifications) |
| POST | `/api/admin/cycles/{id}/advance` | End active cycle + start this one in single operation |
| POST | `/api/admin/competitions/{id}/broadcast` | Send announcement to all active competition members |

### Modified Endpoints

| Method | Path | Change |
|--------|------|--------|
| POST | `/api/admin/cycles/{id}/end` | Refactored to use cycle_service (same behavior, fixed notification type) |
| GET | `/api/me/dashboard` | Added `season_id`, `season_name`, `cycle_id`, `cycle_label`, `cycle_starts_at`, `cycle_ends_at` |
| GET | `/api/me/competition-context` | Added `season_name`, `cycle_label`, `cycle_starts_at`, `cycle_ends_at` |

### Unchanged Endpoints

| Method | Path | Note |
|--------|------|------|
| POST | `/api/admin/cycles/{id}/activate` | Kept as simple status change (no events) for backward compat |

---

## F. Data Report

### Models Unchanged
No schema changes required. All models (Season, Cycle, Membership, BankruptcyRecord, ProtectionRecord) already had the correct fields.

### Data Flow Changes
- `BankruptcyRecord.status` is now properly updated to `CLEARED` with `resolved_at` timestamp when cycles end (previously only membership.is_bankrupt was reset)
- Protection reset now uses the service layer consistently

---

## G. Verification Steps

1. **Build passes:** `npx vite build` succeeds with no errors
2. **Cycle start:** POST `/api/admin/cycles/{id}/start` → returns `protections_cleared`, `bankruptcies_cleared`, `members_notified`
3. **Cycle end:** POST `/api/admin/cycles/{id}/end` → same structured result
4. **Cycle advance:** POST `/api/admin/cycles/{id}/advance` → returns combined `ended` + `started` results
5. **Broadcast:** POST `/api/admin/competitions/{id}/broadcast` → sends notifications to all members
6. **Dashboard:** GET `/api/me/dashboard` → includes `season_name`, `cycle_label`
7. **Competition context:** GET `/api/me/competition-context` → includes `season_name`, `cycle_label`, dates
8. **Admin page:** Start/End/Advance buttons appear contextually based on cycle state
9. **Player pages:** Season + cycle names visible in AppLayout header, Dashboard hero, Dashboard sidebar, Lobby header

---

## H. Acceptance Checklist

- [x] Cycle lifecycle service created with start/end/advance operations
- [x] Each cycle transition triggers: protection reset, bankruptcy recovery, member notifications
- [x] BankruptcyRecords properly marked as CLEARED on cycle end
- [x] Fixed broken NotificationType (SYSTEM_UPDATE → CYCLE_ENDED)
- [x] Admin can start a cycle (with full events)
- [x] Admin can end a cycle (with full events)
- [x] Admin can advance to next cycle (end + start in one operation)
- [x] Admin can broadcast announcements to all competition members
- [x] Player dashboard shows season name and cycle label
- [x] Player lobby shows season name and cycle label
- [x] AppLayout header shows real season name (not static text)
- [x] useCompetitionContext hook returns season/cycle labels and dates
- [x] Frontend build passes with no errors
- [x] Business logic extracted from route handlers into service layer

---

## I. What Remains (Future Work)

1. **Settings cascade resolution** — SettingScope supports GLOBAL/COMPETITION/SEASON/CYCLE but no `resolve_setting()` function exists to walk the cascade
2. **Auto-progression** — Automatic cycle advancement based on `ends_at` dates (requires a scheduled job / cron)
3. **Season-scoped player state** — `current_balance` is competition-wide, not season-scoped; rankings could be filtered by season
4. **Attack service hardcodes settings** — Should read from settings cascade instead of constants
5. **Cycle countdown/timer** — Frontend has `cycle_ends_at` now but no countdown UI component yet
6. **Cycle detail view** — Admin could benefit from a dedicated cycle detail page showing members' protection/bankruptcy state within that cycle
