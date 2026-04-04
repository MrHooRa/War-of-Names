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
    membership_id: uuid.UUID
    alias: str
    status: str = "idle"  # idle | in_queue | in_match | challenging
    stats: dict = field(default_factory=dict)


class LobbyManager:

    def __init__(self):
        self._lobbies: dict[str, dict[uuid.UUID, LobbyPlayer]] = {}
        self._queues: dict[str, deque[uuid.UUID]] = {}
        self._results: dict[str, list[dict]] = {}

    def join(self, lobby_key: str, membership_id: uuid.UUID, alias: str, stats: dict | None = None) -> None:
        if lobby_key not in self._lobbies:
            self._lobbies[lobby_key] = {}
        existing = self._lobbies[lobby_key].get(membership_id)
        if existing is not None:
            existing.alias = alias
            if stats is not None:
                existing.stats = stats
            return
        self._lobbies[lobby_key][membership_id] = LobbyPlayer(
            membership_id=membership_id, alias=alias, stats=stats or {},
        )

    def leave(self, lobby_key: str, membership_id: uuid.UUID) -> None:
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
        return [
            {
                "membership_id": p.membership_id,
                "alias": p.alias,
                "status": "idle" if p.status == "in_queue" else p.status,
                "stats": p.stats,
            }
            for p in self._lobbies.get(lobby_key, {}).values()
        ]

    def get_queue_size(self, lobby_key: str) -> int:
        return len(self._queues.get(lobby_key, []))

    def is_queued(self, lobby_key: str, membership_id: uuid.UUID) -> bool:
        return membership_id in self._queues.get(lobby_key, ())

    def set_status(self, lobby_key: str, membership_id: uuid.UUID, status: str) -> None:
        lobby = self._lobbies.get(lobby_key, {})
        player = lobby.get(membership_id)
        if player:
            player.status = status

    def queue_join(self, lobby_key: str, membership_id: uuid.UUID) -> None:
        if not self.is_in_lobby(lobby_key, membership_id):
            return
        if lobby_key not in self._queues:
            self._queues[lobby_key] = deque()
        if membership_id not in self._queues[lobby_key]:
            self._queues[lobby_key].append(membership_id)
        self.set_status(lobby_key, membership_id, "in_queue")

    def queue_leave(self, lobby_key: str, membership_id: uuid.UUID) -> None:
        if lobby_key in self._queues:
            try:
                self._queues[lobby_key].remove(membership_id)
            except ValueError:
                pass
            if not self._queues[lobby_key]:
                del self._queues[lobby_key]
        if self.is_in_lobby(lobby_key, membership_id):
            self.set_status(lobby_key, membership_id, "idle")

    def clear_queue(self, lobby_key: str) -> list[uuid.UUID]:
        queued = list(self._queues.get(lobby_key, []))
        for membership_id in queued:
            if self.is_in_lobby(lobby_key, membership_id):
                self.set_status(lobby_key, membership_id, "idle")
        self._queues.pop(lobby_key, None)
        return queued

    def try_match(self, lobby_key: str, num_needed: int = 2) -> list[uuid.UUID] | None:
        """Try to match N players from the queue (FIFO).

        Args:
            lobby_key: The lobby identifier
            num_needed: Number of players required to start a match (2-8)

        Returns:
            List of N matched membership IDs, or None if not enough players in queue.
        """
        queue = self._queues.get(lobby_key)
        if not queue or len(queue) < num_needed:
            return None

        matched = []
        for _ in range(num_needed):
            matched.append(queue.popleft())

        for mid in matched:
            self.set_status(lobby_key, mid, "in_match")

        return matched

    def add_result(self, lobby_key: str, result: dict) -> None:
        if lobby_key not in self._results:
            self._results[lobby_key] = []
        self._results[lobby_key].insert(0, result)
        self._results[lobby_key] = self._results[lobby_key][:5]

    def get_recent_results(self, lobby_key: str) -> list[dict]:
        return list(self._results.get(lobby_key, []))

    def get_lobby_state(self, lobby_key: str) -> dict:
        return {
            "players": self.get_players(lobby_key),
            "active_matches": sum(1 for p in self._lobbies.get(lobby_key, {}).values() if p.status == "in_match") // 2,
            "queue_size": self.get_queue_size(lobby_key),
            "recent_results": self.get_recent_results(lobby_key),
        }


lobby_mgr = LobbyManager()
