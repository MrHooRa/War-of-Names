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
