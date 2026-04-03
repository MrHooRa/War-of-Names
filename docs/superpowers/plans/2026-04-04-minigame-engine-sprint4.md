# Minigame Engine — Sprint 4: WebSocket Layer, Lobby & Real-Time Game Play

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the WebSocket layer that powers lobby presence, real-time matchmaking (queue), live game sessions (action submission + state sync), and reconnection — making the minigame engine fully playable end-to-end.

**Architecture:** Three WebSocket-related modules: `connection_manager.py` (in-memory room management — who's connected, broadcast helpers), `lobby_manager.py` (lobby presence, queue matchmaking, challenge delivery), and `ws_router.py` (FastAPI WebSocket endpoint with message dispatch). Authentication via JWT token as query parameter. No Redis for V1 — in-memory only (single-server deployment). All game logic delegates to existing services from Sprint 1-3.

**Tech Stack:** Python 3.12, FastAPI WebSocket, asyncio, jose (JWT), existing services

**BRD Reference:** `docs/minigames/War of Names - Minigame Engine BRD - V1.0.md` — Sections 10-12, 17

**Depends on:** Sprint 0-3 (all services, models, settings, policy)

---

## Sprint 4 Scope

1. **Connection manager** — in-memory rooms, player tracking, broadcast helpers
2. **Lobby manager** — lobby state (who's online, recent results), queue join/leave, FIFO matchmaking
3. **WebSocket router** — single `/ws/minigames/{competition_id}/{game_type}` endpoint with message dispatch
4. **Message handlers** — lobby_join, lobby_leave, queue_join, queue_leave, challenge_send, challenge_respond, action_submit, heartbeat
5. **Wire into main.py** — register WebSocket route

**NOT in Sprint 4:** Reconnection protocol (can be added incrementally), timer enforcement (server-side turn expiry), spectator mode. The foundation works without these — they're Sprint 5 polish.

---

## File Structure

```
backend/app/modules/minigames/
├── (existing Sprint 0-3 files)
├── connection_manager.py      # CREATE: in-memory room/player tracking
├── lobby_manager.py           # CREATE: lobby state, queue, matchmaking
└── ws_router.py               # CREATE: WebSocket endpoint + message dispatch

backend/app/main.py             # MODIFY: register WS route

backend/tests/test_minigame_engine/
├── test_connection_manager.py  # CREATE
├── test_lobby_manager.py       # CREATE
└── test_message_dispatch.py    # CREATE
```

---

## Task 1: Connection Manager — Room & Player Tracking

**Files:**
- Create: `backend/app/modules/minigames/connection_manager.py`
- Create: `backend/tests/test_minigame_engine/test_connection_manager.py`

The connection manager is pure in-memory state — no DB, no async. Fully unit-testable.

- [ ] **Step 1: Write tests**

Create `backend/tests/test_minigame_engine/test_connection_manager.py`:

```python
"""Test connection manager — room management and broadcast tracking."""

import uuid
import pytest
from unittest.mock import AsyncMock

from app.modules.minigames.connection_manager import ConnectionManager


@pytest.fixture
def manager():
    return ConnectionManager()


@pytest.fixture
def mock_ws():
    ws = AsyncMock()
    ws.send_json = AsyncMock()
    return ws


# ── Connect / Disconnect ────────────────────────────────────

def test_connect_adds_player(manager, mock_ws):
    room = "lobby:mutaraha:comp1"
    mid = uuid.uuid4()
    manager.connect(room, mid, mock_ws)
    assert manager.is_connected(room, mid)
    assert manager.room_count(room) == 1


def test_disconnect_removes_player(manager, mock_ws):
    room = "lobby:mutaraha:comp1"
    mid = uuid.uuid4()
    manager.connect(room, mid, mock_ws)
    manager.disconnect(room, mid)
    assert not manager.is_connected(room, mid)
    assert manager.room_count(room) == 0


def test_disconnect_nonexistent_is_safe(manager):
    manager.disconnect("room", uuid.uuid4())  # Should not raise


def test_multiple_players_in_room(manager, mock_ws):
    room = "lobby:mutaraha:comp1"
    m1, m2, m3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    ws1, ws2, ws3 = AsyncMock(), AsyncMock(), AsyncMock()
    manager.connect(room, m1, ws1)
    manager.connect(room, m2, ws2)
    manager.connect(room, m3, ws3)
    assert manager.room_count(room) == 3


def test_get_room_members(manager, mock_ws):
    room = "test_room"
    m1, m2 = uuid.uuid4(), uuid.uuid4()
    ws1, ws2 = AsyncMock(), AsyncMock()
    manager.connect(room, m1, ws1)
    manager.connect(room, m2, ws2)
    members = manager.get_room_members(room)
    assert {m1, m2} == set(members)


def test_empty_room_returns_empty(manager):
    assert manager.get_room_members("nonexistent") == []
    assert manager.room_count("nonexistent") == 0


def test_get_websocket(manager, mock_ws):
    room = "r"
    mid = uuid.uuid4()
    manager.connect(room, mid, mock_ws)
    assert manager.get_websocket(room, mid) is mock_ws


def test_get_websocket_unknown_returns_none(manager):
    assert manager.get_websocket("r", uuid.uuid4()) is None


# ── Player's rooms ───────────────────────────────────────────

def test_player_rooms(manager, mock_ws):
    mid = uuid.uuid4()
    manager.connect("room_a", mid, mock_ws)
    manager.connect("room_b", mid, AsyncMock())
    rooms = manager.get_player_rooms(mid)
    assert set(rooms) == {"room_a", "room_b"}


def test_disconnect_all(manager, mock_ws):
    mid = uuid.uuid4()
    manager.connect("r1", mid, mock_ws)
    manager.connect("r2", mid, AsyncMock())
    manager.disconnect_all(mid)
    assert manager.get_player_rooms(mid) == []
    assert manager.room_count("r1") == 0
    assert manager.room_count("r2") == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_minigame_engine/test_connection_manager.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement connection manager**

Create `backend/app/modules/minigames/connection_manager.py`:

```python
"""In-memory connection manager for WebSocket rooms.

Tracks which players are connected to which rooms, and provides
broadcast helpers. No database, no Redis — pure in-memory state.
Designed for single-server deployment (V1).

Rooms are string keys like:
  - "lobby:{game_type}:{competition_id}" for lobby presence
  - "session:{session_id}" for active game sessions
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

logger = logging.getLogger("minigames.ws")


class ConnectionManager:
    """Manages WebSocket connections organized by rooms."""

    def __init__(self):
        # room_id → {membership_id → websocket}
        self._rooms: dict[str, dict[uuid.UUID, Any]] = {}
        # membership_id → set of room_ids (reverse index)
        self._player_rooms: dict[uuid.UUID, set[str]] = {}

    def connect(self, room: str, membership_id: uuid.UUID, websocket) -> None:
        """Add a player to a room."""
        if room not in self._rooms:
            self._rooms[room] = {}
        self._rooms[room][membership_id] = websocket

        if membership_id not in self._player_rooms:
            self._player_rooms[membership_id] = set()
        self._player_rooms[membership_id].add(room)

    def disconnect(self, room: str, membership_id: uuid.UUID) -> None:
        """Remove a player from a room."""
        if room in self._rooms:
            self._rooms[room].pop(membership_id, None)
            if not self._rooms[room]:
                del self._rooms[room]

        if membership_id in self._player_rooms:
            self._player_rooms[membership_id].discard(room)
            if not self._player_rooms[membership_id]:
                del self._player_rooms[membership_id]

    def disconnect_all(self, membership_id: uuid.UUID) -> None:
        """Remove a player from all rooms."""
        rooms = list(self._player_rooms.get(membership_id, []))
        for room in rooms:
            self.disconnect(room, membership_id)

    def is_connected(self, room: str, membership_id: uuid.UUID) -> bool:
        """Check if a player is in a specific room."""
        return membership_id in self._rooms.get(room, {})

    def room_count(self, room: str) -> int:
        """Count players in a room."""
        return len(self._rooms.get(room, {}))

    def get_room_members(self, room: str) -> list[uuid.UUID]:
        """Get all membership IDs in a room."""
        return list(self._rooms.get(room, {}).keys())

    def get_websocket(self, room: str, membership_id: uuid.UUID):
        """Get the WebSocket for a specific player in a room."""
        return self._rooms.get(room, {}).get(membership_id)

    def get_player_rooms(self, membership_id: uuid.UUID) -> list[str]:
        """Get all rooms a player is in."""
        return list(self._player_rooms.get(membership_id, []))

    async def send_to_player(self, room: str, membership_id: uuid.UUID, message: dict) -> bool:
        """Send a message to a specific player in a room. Returns True if sent."""
        ws = self.get_websocket(room, membership_id)
        if ws is None:
            return False
        try:
            await ws.send_json(message)
            return True
        except Exception:
            logger.warning("Failed to send to %s in %s", membership_id, room)
            self.disconnect(room, membership_id)
            return False

    async def broadcast(self, room: str, message: dict, exclude: uuid.UUID | None = None) -> int:
        """Broadcast a message to all players in a room. Returns count of successful sends."""
        members = dict(self._rooms.get(room, {}))
        sent = 0
        for mid, ws in members.items():
            if mid == exclude:
                continue
            try:
                await ws.send_json(message)
                sent += 1
            except Exception:
                logger.warning("Broadcast failed for %s in %s", mid, room)
                self.disconnect(room, mid)
        return sent


# Global singleton instance
manager = ConnectionManager()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_minigame_engine/test_connection_manager.py -v`
Expected: All 12 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/modules/minigames/connection_manager.py backend/tests/test_minigame_engine/test_connection_manager.py
git commit -m "feat(minigames): add connection manager — in-memory room tracking, broadcast, player indexing"
```

---

## Task 2: Lobby Manager — Presence, Queue & Matchmaking

**Files:**
- Create: `backend/app/modules/minigames/lobby_manager.py`
- Create: `backend/tests/test_minigame_engine/test_lobby_manager.py`

The lobby manager tracks player statuses and manages the matchmaking queue. It's in-memory state with pure testable logic.

- [ ] **Step 1: Write tests**

Create `backend/tests/test_minigame_engine/test_lobby_manager.py`:

```python
"""Test lobby manager — presence, queue, and matchmaking."""

import uuid
import pytest
from app.modules.minigames.lobby_manager import LobbyManager


@pytest.fixture
def lobby():
    return LobbyManager()


def _lobby_key(game_type="mutaraha", comp_id=None):
    return f"{game_type}:{comp_id or uuid.uuid4()}"


# ── Presence ──────────────────────────────────────────────────

def test_join_lobby(lobby):
    key = _lobby_key()
    mid = uuid.uuid4()
    lobby.join(key, mid, alias="الصقر")
    assert lobby.is_in_lobby(key, mid)
    assert lobby.get_player_count(key) == 1


def test_leave_lobby(lobby):
    key = _lobby_key()
    mid = uuid.uuid4()
    lobby.join(key, mid, alias="الصقر")
    lobby.leave(key, mid)
    assert not lobby.is_in_lobby(key, mid)


def test_get_players_list(lobby):
    key = _lobby_key()
    m1, m2 = uuid.uuid4(), uuid.uuid4()
    lobby.join(key, m1, alias="الصقر")
    lobby.join(key, m2, alias="الفهد")
    players = lobby.get_players(key)
    aliases = {p["alias"] for p in players}
    assert aliases == {"الصقر", "الفهد"}


def test_player_status_default_idle(lobby):
    key = _lobby_key()
    mid = uuid.uuid4()
    lobby.join(key, mid, alias="X")
    players = lobby.get_players(key)
    assert players[0]["status"] == "idle"


# ── Queue ─────────────────────────────────────────────────────

def test_queue_join(lobby):
    key = _lobby_key()
    mid = uuid.uuid4()
    lobby.join(key, mid, alias="الصقر")
    lobby.queue_join(key, mid)
    players = lobby.get_players(key)
    player = [p for p in players if p["membership_id"] == mid][0]
    assert player["status"] == "in_queue"


def test_queue_leave(lobby):
    key = _lobby_key()
    mid = uuid.uuid4()
    lobby.join(key, mid, alias="الصقر")
    lobby.queue_join(key, mid)
    lobby.queue_leave(key, mid)
    players = lobby.get_players(key)
    player = [p for p in players if p["membership_id"] == mid][0]
    assert player["status"] == "idle"


def test_queue_match_fifo(lobby):
    key = _lobby_key()
    m1, m2 = uuid.uuid4(), uuid.uuid4()
    lobby.join(key, m1, alias="الصقر")
    lobby.join(key, m2, alias="الفهد")
    lobby.queue_join(key, m1)
    lobby.queue_join(key, m2)
    match = lobby.try_match(key)
    assert match is not None
    assert set(match) == {m1, m2}


def test_queue_no_match_single_player(lobby):
    key = _lobby_key()
    m1 = uuid.uuid4()
    lobby.join(key, m1, alias="الصقر")
    lobby.queue_join(key, m1)
    match = lobby.try_match(key)
    assert match is None


def test_matched_players_status_changes(lobby):
    key = _lobby_key()
    m1, m2 = uuid.uuid4(), uuid.uuid4()
    lobby.join(key, m1, alias="الصقر")
    lobby.join(key, m2, alias="الفهد")
    lobby.queue_join(key, m1)
    lobby.queue_join(key, m2)
    lobby.try_match(key)
    players = lobby.get_players(key)
    for p in players:
        assert p["status"] == "in_match"


# ── Challenge status ─────────────────────────────────────────

def test_set_status_challenging(lobby):
    key = _lobby_key()
    mid = uuid.uuid4()
    lobby.join(key, mid, alias="الصقر")
    lobby.set_status(key, mid, "challenging")
    players = lobby.get_players(key)
    assert players[0]["status"] == "challenging"


# ── Recent results ───────────────────────────────────────────

def test_add_recent_result(lobby):
    key = _lobby_key()
    lobby.add_result(key, {"winner_alias": "الصقر", "loser_alias": "الفهد", "duration_sec": 120})
    results = lobby.get_recent_results(key)
    assert len(results) == 1


def test_recent_results_max_5(lobby):
    key = _lobby_key()
    for i in range(7):
        lobby.add_result(key, {"winner_alias": f"p{i}"})
    results = lobby.get_recent_results(key)
    assert len(results) == 5
    assert results[0]["winner_alias"] == "p6"  # Most recent first
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_minigame_engine/test_lobby_manager.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement lobby manager**

Create `backend/app/modules/minigames/lobby_manager.py`:

```python
"""Lobby manager — player presence, queue, and matchmaking.

In-memory state tracking for lobby presence and FIFO queue matchmaking.
No database, no Redis — pure in-memory for V1 (single server).

Lobby keys: "{game_type}:{competition_id}"
"""

from __future__ import annotations

import uuid
from collections import deque
from dataclasses import dataclass, field


@dataclass
class LobbyPlayer:
    """A player's presence in a lobby."""
    membership_id: uuid.UUID
    alias: str
    status: str = "idle"  # idle | in_queue | in_match | challenging
    stats: dict = field(default_factory=dict)


class LobbyManager:
    """Manages lobby state for all game types and competitions."""

    def __init__(self):
        # lobby_key → {membership_id → LobbyPlayer}
        self._lobbies: dict[str, dict[uuid.UUID, LobbyPlayer]] = {}
        # lobby_key → deque of membership_ids (FIFO queue)
        self._queues: dict[str, deque[uuid.UUID]] = {}
        # lobby_key → list of recent results (newest first, max 5)
        self._results: dict[str, list[dict]] = {}

    # ── Presence ─────────────────────────────────────────────

    def join(self, lobby_key: str, membership_id: uuid.UUID, alias: str, stats: dict | None = None) -> None:
        """Add a player to a lobby."""
        if lobby_key not in self._lobbies:
            self._lobbies[lobby_key] = {}
        self._lobbies[lobby_key][membership_id] = LobbyPlayer(
            membership_id=membership_id,
            alias=alias,
            stats=stats or {},
        )

    def leave(self, lobby_key: str, membership_id: uuid.UUID) -> None:
        """Remove a player from a lobby (also removes from queue)."""
        if lobby_key in self._lobbies:
            self._lobbies[lobby_key].pop(membership_id, None)
            if not self._lobbies[lobby_key]:
                del self._lobbies[lobby_key]
        self.queue_leave(lobby_key, membership_id)

    def is_in_lobby(self, lobby_key: str, membership_id: uuid.UUID) -> bool:
        return membership_id in self._lobbies.get(lobby_key, {})

    def get_player_count(self, lobby_key: str) -> int:
        return len(self._lobbies.get(lobby_key, {}))

    def get_players(self, lobby_key: str) -> list[dict]:
        """Get all players in a lobby as dicts."""
        players = self._lobbies.get(lobby_key, {})
        return [
            {
                "membership_id": p.membership_id,
                "alias": p.alias,
                "status": p.status,
                "stats": p.stats,
            }
            for p in players.values()
        ]

    def set_status(self, lobby_key: str, membership_id: uuid.UUID, status: str) -> None:
        """Update a player's status in the lobby."""
        lobby = self._lobbies.get(lobby_key, {})
        player = lobby.get(membership_id)
        if player:
            player.status = status

    # ── Queue ────────────────────────────────────────────────

    def queue_join(self, lobby_key: str, membership_id: uuid.UUID) -> None:
        """Add a player to the matchmaking queue (FIFO)."""
        if lobby_key not in self._queues:
            self._queues[lobby_key] = deque()
        if membership_id not in self._queues[lobby_key]:
            self._queues[lobby_key].append(membership_id)
        self.set_status(lobby_key, membership_id, "in_queue")

    def queue_leave(self, lobby_key: str, membership_id: uuid.UUID) -> None:
        """Remove a player from the queue."""
        if lobby_key in self._queues:
            try:
                self._queues[lobby_key].remove(membership_id)
            except ValueError:
                pass
            if not self._queues[lobby_key]:
                del self._queues[lobby_key]
        # Reset status to idle if still in lobby
        if self.is_in_lobby(lobby_key, membership_id):
            self.set_status(lobby_key, membership_id, "idle")

    def try_match(self, lobby_key: str) -> tuple[uuid.UUID, uuid.UUID] | None:
        """Try to match two players from the queue (FIFO). Returns (p1, p2) or None."""
        queue = self._queues.get(lobby_key)
        if not queue or len(queue) < 2:
            return None

        p1 = queue.popleft()
        p2 = queue.popleft()

        self.set_status(lobby_key, p1, "in_match")
        self.set_status(lobby_key, p2, "in_match")

        return (p1, p2)

    # ── Recent Results ───────────────────────────────────────

    def add_result(self, lobby_key: str, result: dict) -> None:
        """Add a match result (newest first, max 5)."""
        if lobby_key not in self._results:
            self._results[lobby_key] = []
        self._results[lobby_key].insert(0, result)
        self._results[lobby_key] = self._results[lobby_key][:5]

    def get_recent_results(self, lobby_key: str) -> list[dict]:
        return list(self._results.get(lobby_key, []))

    def get_lobby_state(self, lobby_key: str) -> dict:
        """Get full lobby state snapshot for initial sync."""
        return {
            "players": self.get_players(lobby_key),
            "active_matches": sum(
                1 for p in self._lobbies.get(lobby_key, {}).values()
                if p.status == "in_match"
            ) // 2,  # Each match has 2 players
            "recent_results": self.get_recent_results(lobby_key),
        }


# Global singleton instance
lobby_mgr = LobbyManager()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_minigame_engine/test_lobby_manager.py -v`
Expected: All 14 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/modules/minigames/lobby_manager.py backend/tests/test_minigame_engine/test_lobby_manager.py
git commit -m "feat(minigames): add lobby manager — presence tracking, FIFO queue matchmaking, recent results"
```

---

## Task 3: WebSocket Router — Message Dispatch

**Files:**
- Create: `backend/app/modules/minigames/ws_router.py`
- Modify: `backend/app/main.py`

This is the WebSocket endpoint that receives messages, dispatches to handlers, and uses the connection/lobby managers.

- [ ] **Step 1: Create WebSocket router**

Create `backend/app/modules/minigames/ws_router.py`:

```python
"""WebSocket router for minigame engine.

Single endpoint: /ws/minigames/{competition_id}/{game_type}?token=JWT

Handles: lobby_join, lobby_leave, queue_join, queue_leave,
         challenge_send, challenge_respond, action_submit, heartbeat
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy import select

from app.modules.minigames.connection_manager import manager as conn_mgr
from app.modules.minigames.lobby_manager import lobby_mgr

logger = logging.getLogger("minigames.ws")

ws_router = APIRouter()


async def _authenticate_ws(websocket: WebSocket, token: str | None) -> dict | None:
    """Validate JWT token for WebSocket connection. Returns account info or None."""
    if not token:
        return None
    try:
        from jose import jwt
        from app.config import settings
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        account_id = payload.get("sub")
        if not account_id:
            return None
        return {"account_id": uuid.UUID(account_id)}
    except Exception:
        return None


async def _resolve_membership(account_id: uuid.UUID, competition_id: uuid.UUID) -> dict | None:
    """Resolve membership for the authenticated account in this competition."""
    from app.core.database import async_session
    from app.core.enums import MembershipStatus
    from app.modules.competitions.models import Membership

    async with async_session() as session:
        result = await session.execute(
            select(Membership).where(
                Membership.account_id == account_id,
                Membership.competition_id == competition_id,
                Membership.status == MembershipStatus.ACTIVE,
            )
        )
        m = result.scalars().first()
        if not m:
            return None
        return {
            "membership_id": m.id,
            "alias": m.current_alias or "مجهول",
            "balance": m.current_balance,
            "is_bankrupt": m.is_bankrupt,
        }


async def _send_error(websocket: WebSocket, code: str, message_ar: str):
    """Send an error message to the client."""
    await websocket.send_json({"type": "error", "code": code, "message_ar": message_ar})


async def _handle_message(
    websocket: WebSocket,
    msg: dict,
    competition_id: uuid.UUID,
    game_type: str,
    membership_info: dict,
):
    """Dispatch a WebSocket message to the appropriate handler."""
    msg_type = msg.get("type")
    mid = membership_info["membership_id"]
    alias = membership_info["alias"]
    lobby_key = f"{game_type}:{competition_id}"

    if msg_type == "lobby_join":
        lobby_mgr.join(lobby_key, mid, alias=alias)
        conn_mgr.connect(f"lobby:{lobby_key}", mid, websocket)
        # Send full lobby state to the joining player
        state = lobby_mgr.get_lobby_state(lobby_key)
        await websocket.send_json({"type": "lobby_state", **state})
        # Notify others
        await conn_mgr.broadcast(
            f"lobby:{lobby_key}",
            {"type": "lobby_update", "update_type": "join", "player": {"membership_id": str(mid), "alias": alias, "status": "idle"}},
            exclude=mid,
        )

    elif msg_type == "lobby_leave":
        lobby_mgr.leave(lobby_key, mid)
        conn_mgr.disconnect(f"lobby:{lobby_key}", mid)
        await conn_mgr.broadcast(
            f"lobby:{lobby_key}",
            {"type": "lobby_update", "update_type": "leave", "membership_id": str(mid)},
        )

    elif msg_type == "queue_join":
        lobby_mgr.queue_join(lobby_key, mid)
        await conn_mgr.broadcast(
            f"lobby:{lobby_key}",
            {"type": "lobby_update", "update_type": "status_change", "membership_id": str(mid), "status": "in_queue"},
        )
        # Try to match
        match = lobby_mgr.try_match(lobby_key)
        if match:
            p1_id, p2_id = match
            await _handle_queue_match(websocket, lobby_key, competition_id, game_type, p1_id, p2_id)

    elif msg_type == "queue_leave":
        lobby_mgr.queue_leave(lobby_key, mid)
        await conn_mgr.broadcast(
            f"lobby:{lobby_key}",
            {"type": "lobby_update", "update_type": "status_change", "membership_id": str(mid), "status": "idle"},
        )

    elif msg_type == "challenge_send":
        target_mid = msg.get("target_membership_id")
        if target_mid:
            target_mid = uuid.UUID(target_mid) if isinstance(target_mid, str) else target_mid
            lobby_mgr.set_status(lobby_key, mid, "challenging")
            # Send challenge notification to target via their lobby connection
            target_ws = conn_mgr.get_websocket(f"lobby:{lobby_key}", target_mid)
            if target_ws:
                await target_ws.send_json({
                    "type": "challenge_received",
                    "from_alias": alias,
                    "from_membership_id": str(mid),
                    "game_type": game_type,
                })
            else:
                await _send_error(websocket, "TARGET_OFFLINE", "اللاعب المستهدف غير متصل")

    elif msg_type == "challenge_respond":
        # This is handled via REST API (Sprint 2) — WebSocket just notifies
        pass

    elif msg_type == "action_submit":
        await _handle_action_submit(websocket, msg, competition_id, game_type, membership_info)

    elif msg_type == "heartbeat":
        await websocket.send_json({"type": "heartbeat_ack"})

    else:
        await _send_error(websocket, "UNKNOWN_MESSAGE", f"نوع الرسالة غير معروف: {msg_type}")


async def _handle_queue_match(
    websocket: WebSocket,
    lobby_key: str,
    competition_id: uuid.UUID,
    game_type: str,
    p1_id: uuid.UUID,
    p2_id: uuid.UUID,
):
    """Handle a successful queue match — create session and notify both players."""
    from app.core.database import async_session
    from app.core.enums import MinigameMatchType
    from app.modules.minigames.session_service import create_session
    from app.modules.minigames.settings_helper import get_minigame_settings

    async with async_session() as session:
        from app.modules.competitions.models import Cycle, Season
        season_r = await session.execute(
            select(Season).where(Season.competition_id == competition_id, Season.status == "active").limit(1)
        )
        season = season_r.scalars().first()
        cycle = None
        if season:
            cycle_r = await session.execute(
                select(Cycle).where(Cycle.season_id == season.id, Cycle.status == "active").limit(1)
            )
            cycle = cycle_r.scalars().first()

        mg_settings = await get_minigame_settings(session, competition_id=competition_id, season_id=season.id if season else None, cycle_id=cycle.id if cycle else None)

        mg_session = await create_session(
            session,
            game_type=game_type,
            competition_id=competition_id,
            player_1_membership_id=p1_id,
            player_2_membership_id=p2_id,
            match_type=MinigameMatchType.QUEUE,
            buy_in_amount=mg_settings["minigame_buy_in"],
            settings_snapshot={k: v for k, v in mg_settings.items()},
            season_id=season.id if season else None,
            cycle_id=cycle.id if cycle else None,
            turn_duration_ms=mg_settings["minigame_turn_duration_sec"] * 1000,
            grace_timer_ms=mg_settings["minigame_grace_timer_sec"] * 1000,
        )
        await session.commit()

    # Notify both players
    match_data = {
        "type": "match_found",
        "session_id": str(mg_session.id),
        "game_type": game_type,
    }
    p1_ws = conn_mgr.get_websocket(f"lobby:{lobby_key}", p1_id)
    p2_ws = conn_mgr.get_websocket(f"lobby:{lobby_key}", p2_id)
    if p1_ws:
        await p1_ws.send_json(match_data)
    if p2_ws:
        await p2_ws.send_json(match_data)

    # Broadcast status update to lobby
    await conn_mgr.broadcast(
        f"lobby:{lobby_key}",
        {"type": "lobby_update", "update_type": "match_started", "player_ids": [str(p1_id), str(p2_id)]},
        exclude=None,
    )


async def _handle_action_submit(
    websocket: WebSocket,
    msg: dict,
    competition_id: uuid.UUID,
    game_type: str,
    membership_info: dict,
):
    """Handle an action submission during a live game."""
    from app.core.database import async_session
    from app.modules.minigames.action_service import check_idempotency, process_action, validate_action_envelope
    from app.modules.minigames.models import MinigameSession
    from app.modules.minigames.registry import GameTypeRegistry

    envelope = msg.get("envelope", {})
    session_id = envelope.get("session_id")
    if not session_id:
        await _send_error(websocket, "MISSING_SESSION", "معرّف الجلسة مفقود")
        return

    session_id = uuid.UUID(session_id) if isinstance(session_id, str) else session_id
    action_id = envelope.get("action_id")
    if action_id:
        action_id = uuid.UUID(action_id) if isinstance(action_id, str) else action_id
        envelope["action_id"] = action_id
    envelope["session_id"] = session_id
    envelope["actor_membership_id"] = membership_info["membership_id"]

    async with async_session() as session:
        # Check idempotency
        if action_id:
            cached = await check_idempotency(session, action_id)
            if cached is not None:
                await websocket.send_json({"type": "action_ack", "action_id": str(action_id), **cached})
                return

        # Load session
        result = await session.execute(
            select(MinigameSession).where(MinigameSession.id == session_id)
        )
        mg_session = result.scalars().first()
        if not mg_session:
            await _send_error(websocket, "SESSION_NOT_FOUND", "الجلسة غير موجودة")
            return

        # Validate envelope
        error = validate_action_envelope(
            envelope=envelope,
            session_phase=mg_session.phase,
            session_revision=mg_session.revision,
            current_turn=mg_session.current_turn,
            player_1_membership_id=mg_session.player_1_membership_id,
            player_2_membership_id=mg_session.player_2_membership_id,
        )
        if error:
            await websocket.send_json({"type": "action_reject", "action_id": str(action_id), "code": error.code, "message_ar": error.message_ar})
            return

        # Get plugin
        plugin = GameTypeRegistry.get(game_type)
        if not plugin:
            await _send_error(websocket, "PLUGIN_NOT_FOUND", "نوع اللعبة غير مسجل")
            return

        # Process action
        try:
            action_result = await process_action(session, mg_session=mg_session, plugin=plugin, envelope=envelope)
        except ValueError as e:
            await websocket.send_json({"type": "action_reject", "action_id": str(action_id), "code": "INVALID_ACTION", "message_ar": str(e)})
            return

        await session.commit()

    # Send ack to acting player
    await websocket.send_json({"type": "action_ack", "action_id": str(action_id), **action_result})

    # Send state patch to opponent
    session_room = f"session:{session_id}"
    opponent_id = (
        mg_session.player_2_membership_id
        if membership_info["membership_id"] == mg_session.player_1_membership_id
        else mg_session.player_1_membership_id
    )
    if opponent_id:
        # Build public view for opponent
        public_state = plugin.build_public_view(action_result.get("new_state", {}), opponent_id)
        await conn_mgr.send_to_player(
            session_room,
            opponent_id,
            {"type": "state_patch", "revision": action_result.get("revision"), "state": public_state},
        )

    # Handle terminal
    if action_result.get("terminal"):
        await conn_mgr.broadcast(
            session_room,
            {"type": "transition_event", "from_phase": "in_progress", "to_phase": "completed", "terminal": action_result["terminal"]},
        )


@ws_router.websocket("/ws/minigames/{competition_id}/{game_type}")
async def minigame_websocket(
    websocket: WebSocket,
    competition_id: uuid.UUID,
    game_type: str,
    token: str | None = Query(default=None),
):
    """Main WebSocket endpoint for minigame engine.

    Connect with: ws://host/ws/minigames/{competition_id}/{game_type}?token=JWT
    """
    # Authenticate
    auth = await _authenticate_ws(websocket, token)
    if not auth:
        await websocket.close(code=4001, reason="يرجى تسجيل الدخول")
        return

    # Resolve membership
    membership_info = await _resolve_membership(auth["account_id"], competition_id)
    if not membership_info:
        await websocket.close(code=4003, reason="أنت لست عضواً في هذه المسابقة")
        return

    await websocket.accept()
    mid = membership_info["membership_id"]
    logger.info("WS connected: %s in %s/%s", mid, competition_id, game_type)

    try:
        while True:
            data = await websocket.receive_json()
            try:
                await _handle_message(websocket, data, competition_id, game_type, membership_info)
            except Exception:
                logger.exception("Error handling WS message: %s", data.get("type"))
                await _send_error(websocket, "INTERNAL_ERROR", "حدث خطأ غير متوقع")
    except WebSocketDisconnect:
        logger.info("WS disconnected: %s", mid)
    finally:
        # Clean up: remove from all rooms and lobby
        lobby_key = f"{game_type}:{competition_id}"
        lobby_mgr.leave(lobby_key, mid)
        conn_mgr.disconnect_all(mid)
```

- [ ] **Step 2: Register WebSocket route in main.py**

Read `backend/app/main.py` first. Add after the minigames router import:

```python
from app.modules.minigames.ws_router import ws_router as minigames_ws_router
```

And add after `app.include_router(minigames_router)`:

```python
app.include_router(minigames_ws_router)
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/modules/minigames/ws_router.py backend/app/main.py
git commit -m "feat(minigames): add WebSocket router — lobby, queue matchmaking, action submit, heartbeat"
```

---

## Task 4: Final Verification

- [ ] **Step 1: Run all pure tests**

Run: `cd backend && python -m pytest tests/test_minigame_engine/test_enums.py tests/test_minigame_engine/test_plugin_contract.py tests/test_minigame_engine/test_registry.py tests/test_minigame_engine/test_state_machine.py tests/test_minigame_engine/test_session_service.py tests/test_minigame_engine/test_settlement_service.py tests/test_minigame_engine/test_policy_service.py tests/test_minigame_engine/test_leaderboard_service.py tests/test_minigame_engine/test_settings_helper.py tests/test_minigame_engine/test_connection_manager.py tests/test_minigame_engine/test_lobby_manager.py -v --tb=short 2>&1 | tail -10`

Expected: All tests pass (~146+)

- [ ] **Step 2: Final commit**

```bash
git add -A
git commit -m "feat(minigames): Sprint 4 complete — WebSocket layer, lobby presence, queue matchmaking, real-time game play"
```

---

## Sprint 4 Deliverables Summary

| Component | File | Tests |
|---|---|---|
| Connection manager | `minigames/connection_manager.py` | 12 |
| Lobby manager | `minigames/lobby_manager.py` | 14 |
| WebSocket router | `minigames/ws_router.py` | via Docker integration |
| Main.py wiring | `main.py` (modified) | via Docker integration |
| **Total** | **3 files created, 1 modified** | **~26 new tests** |

## Engine Complete — What's Next

After Sprint 4, the minigame engine is fully operational:
- **REST API** for session management, leaderboards, admin controls
- **WebSocket** for real-time lobby, matchmaking, and game play
- **Plugin system** ready for مطارحة (the first game)

Next step: **Build the مطارحة plugin** using the engine — implement the 8 lifecycle hooks, word bank, 6 deduction tools, and cinematic UX.
