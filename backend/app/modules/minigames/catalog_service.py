"""Catalog aggregation service — public entry points.

Two async functions for the REST layer in Sprint C:

    get_catalog       — full catalog for a player in a competition
    get_lobby_detail  — single-game lobby page read model

Both produce the read models defined in BRD §8.1 and §8.2.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.minigames.catalog_aggregator import (
    LobbyPresenceSnapshot,
    build_catalog_cards,
)
from app.modules.minigames.catalog_data_loader import CatalogDataLoader
from app.modules.minigames.catalog_read_model import (
    CatalogResponse,
    LobbyPageResponse,
    catalog_card_to_dict,
)
from app.modules.minigames.lobby_manager import lobby_mgr


# ─── Lobby presence extraction ─────────────────────────────────────

def _presence_snapshot_for_player(
    *,
    game_type: str,
    competition_id: uuid.UUID,
    membership_id: uuid.UUID,
) -> LobbyPresenceSnapshot:
    """Read the in-memory lobby snapshot for one (game_type, competition_id).

    Returns an empty snapshot if the lobby has never been opened.
    """
    lobby_key = f"{game_type}:{competition_id}"

    # Use LobbyManager public API — get_player_count + get_queue_size + is_queued
    try:
        presence = lobby_mgr.get_player_count(lobby_key)
        queue = lobby_mgr.get_queue_size(lobby_key)
        in_queue = lobby_mgr.is_queued(lobby_key, membership_id)
    except Exception:
        return LobbyPresenceSnapshot(presence_count=0, queue_count=0, in_queue=False)

    return LobbyPresenceSnapshot(
        presence_count=int(presence),
        queue_count=int(queue),
        in_queue=bool(in_queue),
    )


def _build_presence_map(
    *,
    game_types: list,
    competition_id: uuid.UUID,
    membership_id: uuid.UUID,
) -> dict[str, LobbyPresenceSnapshot]:
    """Build per-game presence snapshots from the in-memory lobby manager."""
    return {
        gt.id: _presence_snapshot_for_player(
            game_type=gt.id,
            competition_id=competition_id,
            membership_id=membership_id,
        )
        for gt in game_types
    }


# ─── get_catalog ──────────────────────────────────────────────────

async def get_catalog(
    session: AsyncSession,
    *,
    competition_id: uuid.UUID,
    membership_id: uuid.UUID,
    player_balance: int,
    is_bankrupt: bool,
    season_id: uuid.UUID | None = None,
    cycle_id: uuid.UUID | None = None,
    correlation_id: str | None = None,
) -> CatalogResponse:
    """Produce the full catalog response for a player in a competition.

    Issues exactly 6 SQL queries (delegated to ``CatalogDataLoader``)
    plus a handful of in-memory lookups against ``lobby_mgr``. No
    N+1 anywhere.
    """
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())

    loader = CatalogDataLoader()
    raw = await loader.load_all(
        session,
        competition_id=competition_id,
        membership_id=membership_id,
        season_id=season_id,
        cycle_id=cycle_id,
    )

    presence_map = _build_presence_map(
        game_types=raw.game_types,
        competition_id=competition_id,
        membership_id=membership_id,
    )

    cards = build_catalog_cards(
        raw=raw,
        lobby_presence=presence_map,
        player_balance=player_balance,
        is_bankrupt=is_bankrupt,
        membership_id=membership_id,
        correlation_id=correlation_id,
    )

    return CatalogResponse(correlation_id=correlation_id, games=cards)


# ─── get_lobby_detail ─────────────────────────────────────────────

async def get_lobby_detail(
    session: AsyncSession,
    *,
    game_type: str,
    competition_id: uuid.UUID,
    membership_id: uuid.UUID,
    player_balance: int,
    is_bankrupt: bool,
    season_id: uuid.UUID | None = None,
    cycle_id: uuid.UUID | None = None,
    correlation_id: str | None = None,
) -> LobbyPageResponse:
    """Produce the full lobby page response for one game in a competition.

    Reuses the catalog loader (which fetches all game types) and then
    extracts the single matching card. This keeps the query count
    low and avoids a second code path for single-game aggregation.
    """
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())

    catalog = await get_catalog(
        session,
        competition_id=competition_id,
        membership_id=membership_id,
        player_balance=player_balance,
        is_bankrupt=is_bankrupt,
        season_id=season_id,
        cycle_id=cycle_id,
        correlation_id=correlation_id,
    )

    target_card = next((c for c in catalog.games if c.game_type == game_type), None)
    if target_card is None:
        # Game either doesn't exist or is hidden — return an empty shell
        # that the REST layer can convert to a 404.
        raise LookupError(f"game_type '{game_type}' not found in catalog")

    card_dict = catalog_card_to_dict(target_card)

    # Full lobby snapshot from in-memory manager
    lobby_key = f"{game_type}:{competition_id}"
    try:
        lobby_snapshot = lobby_mgr.get_lobby_state(lobby_key)
    except Exception:
        lobby_snapshot = {
            "players": [],
            "queue_size": 0,
            "active_matches": 0,
            "recent_results": [],
        }

    return LobbyPageResponse(
        correlation_id=correlation_id,
        game={
            "game_type": card_dict["game_type"],
            "name": card_dict["name"],
            "description": card_dict["description"],
            "icon": card_dict["icon"],
            "accent_color": card_dict["accent_color"],
            "hero_variant": card_dict["hero_variant"],
            "min_players": card_dict["min_players"],
            "max_players": card_dict["max_players"],
            "player_count_label": card_dict["player_count_label"],
            "buy_in_amount": card_dict["buy_in_amount"],
            "estimated_duration_sec": card_dict["estimated_duration_sec"],
            "estimated_duration_source": card_dict["estimated_duration_source"],
            "supports_overtime": card_dict["supports_overtime"],
            "supports_spectators": card_dict["supports_spectators"],
        },
        my_state=card_dict["my_state"],
        my_stats=card_dict["my_stats"],
        lobby=lobby_snapshot,
        leaderboard_preview=[],
        how_to_play={"summary_steps": []},
    )
