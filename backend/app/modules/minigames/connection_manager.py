"""In-memory connection manager for WebSocket rooms.

Tracks which players are connected to which rooms, and provides
broadcast helpers. No database, no Redis — pure in-memory state.
Designed for single-server deployment (V1).
"""

from __future__ import annotations

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
        return membership_id in self._rooms.get(room, {})

    def room_count(self, room: str) -> int:
        return len(self._rooms.get(room, {}))

    def get_room_members(self, room: str) -> list[uuid.UUID]:
        return list(self._rooms.get(room, {}).keys())

    def get_websocket(self, room: str, membership_id: uuid.UUID):
        return self._rooms.get(room, {}).get(membership_id)

    def get_player_rooms(self, membership_id: uuid.UUID) -> list[str]:
        return list(self._player_rooms.get(membership_id, []))

    async def send_to_player(self, room: str, membership_id: uuid.UUID, message: dict) -> bool:
        """Send a message to a specific player. Returns True if sent."""
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
        """Broadcast to all players in a room. Returns count of successful sends."""
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


# Global singleton
manager = ConnectionManager()
