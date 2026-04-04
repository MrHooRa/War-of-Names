"""Pure catalog aggregator.

Combines raw DB data (from ``CatalogDataLoader``) with in-memory lobby
presence snapshots to produce the final list of ``CatalogCard``
dataclasses. This module is a pure function module — no DB access,
no async, no app.core.utils import.

The aggregator applies all the rules from:
    BRD §8.1.1 — field computation
    BRD §10.1.1 — visibility (hidden/disabled filtered out)
    BRD §15.4 — CTA priority chain (via catalog_helpers)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from app.modules.minigames.catalog_config_resolver import resolve_catalog_config
from app.modules.minigames.catalog_helpers import (
    build_player_count_label,
    resolve_card_status,
    resolve_estimated_duration,
)
from app.modules.minigames.catalog_read_model import (
    CatalogCard,
    CatalogMyState,
    CatalogMyStats,
)


# ─── Presence snapshot (injected from lobby_manager in Task 5) ─────

@dataclass
class LobbyPresenceSnapshot:
    """In-memory lobby data for a single game type.

    ``presence_count`` = how many players are in the lobby right now
    ``queue_count``    = how many of them are in the matchmaking queue
    ``in_queue``       = whether the current player is in that queue
    """

    presence_count: int = 0
    queue_count: int = 0
    in_queue: bool = False


# ─── Visibility rule ───────────────────────────────────────────────

def _is_card_visible(availability_mode: str) -> bool:
    """BRD §10.1.1 — hidden cards are filtered out entirely.

    Maintenance, coming_soon, and active cards all remain visible.
    """
    return availability_mode != "hidden"


# ─── Stats computation ─────────────────────────────────────────────

def _build_my_stats(leaderboard_row: Any | None) -> CatalogMyStats:
    """Build CatalogMyStats from an optional leaderboard row.

    BRD §8.1.1 — when the row is missing or total_matches is zero,
    returns an empty stats object with has_history=False.
    """
    if leaderboard_row is None:
        return CatalogMyStats()

    wins = int(getattr(leaderboard_row, "wins", 0) or 0)
    losses = int(getattr(leaderboard_row, "losses", 0) or 0)
    total = int(getattr(leaderboard_row, "total_matches", 0) or 0)

    if total <= 0:
        return CatalogMyStats()

    win_rate = wins / total if total > 0 else 0.0

    return CatalogMyStats(
        wins=wins,
        losses=losses,
        current_streak=int(getattr(leaderboard_row, "current_streak", 0) or 0),
        best_streak=int(getattr(leaderboard_row, "best_streak", 0) or 0),
        total_matches=total,
        win_rate=round(win_rate, 3),
        has_history=True,
    )


# ─── My state computation ─────────────────────────────────────────

def _build_my_state(
    *,
    active_session: tuple[uuid.UUID, str] | None,
    in_queue: bool,
) -> CatalogMyState:
    """Build CatalogMyState from active session lookup and queue flag."""
    if active_session is not None:
        session_id, phase = active_session
        return CatalogMyState(
            queued=False,
            in_active_match=True,
            active_session_id=str(session_id),
            active_session_phase=phase,
        )
    return CatalogMyState(
        queued=in_queue,
        in_active_match=False,
        active_session_id=None,
        active_session_phase=None,
    )


# ─── Main entry point ──────────────────────────────────────────────

def build_catalog_cards(
    *,
    raw: Any,  # CatalogRawData (SimpleNamespace-compatible for testing)
    lobby_presence: dict[str, LobbyPresenceSnapshot],
    player_balance: int,
    is_bankrupt: bool,
    membership_id: uuid.UUID,
    correlation_id: str,
) -> list[CatalogCard]:
    """Transform raw data + lobby state into a sorted list of catalog cards.

    Args:
        raw: CatalogRawData from CatalogDataLoader (or SimpleNamespace in tests)
        lobby_presence: per-game presence/queue data from lobby_manager
        player_balance: caller's current balance for eligibility check
        is_bankrupt: caller's bankruptcy flag
        membership_id: caller's membership ID (for future per-player logic)
        correlation_id: request-scoped correlation ID, stamped on every card

    Returns:
        List of CatalogCard ordered by sort_order ASC, then game_type ASC.
        Cards with availability_mode='hidden' are excluded entirely.
    """
    settings = raw.settings or {}
    default_buy_in = int(settings.get("minigame_buy_in", 500))
    kill_switch = str(settings.get("minigame_kill_switch", "off"))

    cards: list[CatalogCard] = []

    for game_type in raw.game_types:
        game_id = game_type.id
        config = raw.configs_by_game_type.get(game_id)

        # Resolve config with fallback (BRD §11.4.3)
        resolved_config, _is_fallback = resolve_catalog_config(game_type, config)

        # BRD §10.1.1 — hidden cards are filtered before any other work
        if not _is_card_visible(resolved_config["availability_mode"]):
            continue

        presence = lobby_presence.get(game_id) or LobbyPresenceSnapshot()
        counts = raw.counts_by_game_type.get(game_id, (0, 0))
        active_matches_count, recent_results_count = counts
        active_session = raw.my_active_session_by_game_type.get(game_id)
        leaderboard_row = raw.leaderboard_by_game_type.get(game_id)

        # Build the substructures
        my_stats = _build_my_stats(leaderboard_row)
        my_state = _build_my_state(
            active_session=active_session,
            in_queue=presence.in_queue,
        )

        # Resolve status (BRD §15.4)
        status, reason = resolve_card_status(
            availability_mode=resolved_config["availability_mode"],
            kill_switch_level=kill_switch,
            my_active_session_id=my_state.active_session_id,
            in_queue=my_state.queued,
            player_balance=player_balance,
            buy_in_amount=default_buy_in,
            is_bankrupt=is_bankrupt,
        )

        # Resolve duration (BRD §8.1.1)
        leaderboard_avg = (
            float(getattr(leaderboard_row, "avg_match_duration_sec", 0) or 0)
            if leaderboard_row is not None
            else None
        )
        leaderboard_match_count = (
            int(getattr(leaderboard_row, "total_matches", 0) or 0)
            if leaderboard_row is not None
            else 0
        )
        duration_sec, duration_source = resolve_estimated_duration(
            leaderboard_avg_sec=leaderboard_avg,
            leaderboard_match_count=leaderboard_match_count,
            config_duration_sec=resolved_config["estimated_duration_sec"],
        )

        # Assemble the card
        card = CatalogCard(
            game_type=game_id,
            name=game_type.name,
            short_description=resolved_config["short_description"],
            description=getattr(game_type, "description", None),
            icon=resolved_config["icon_token"],
            accent_color=resolved_config["accent_color"],
            hero_variant=resolved_config["hero_variant"],
            card_variant=resolved_config["card_variant"],
            min_players=int(game_type.min_players),
            max_players=int(game_type.max_players),
            player_count_label=build_player_count_label(
                int(game_type.min_players), int(game_type.max_players)
            ),
            estimated_duration_sec=duration_sec,
            estimated_duration_source=duration_source,
            buy_in_amount=default_buy_in,
            status=status,
            availability_reason=reason,
            expected_launch_at=resolved_config["expected_launch_at"],
            presence_count=presence.presence_count,
            queue_count=presence.queue_count,
            active_matches_count=active_matches_count,
            recent_results_count=recent_results_count,
            supports_overtime=bool(getattr(game_type, "supports_overtime", False)),
            supports_spectators=bool(getattr(game_type, "supports_spectators", False)),
            supports_ranked=bool(getattr(game_type, "supports_ranked", False)),
            supports_team_mode=bool(getattr(game_type, "supports_team_mode", False)),
            featured=bool(resolved_config["featured"]),
            sort_order=int(resolved_config["sort_order"]),
            correlation_id=correlation_id,
            my_state=my_state,
            my_stats=my_stats,
        )
        cards.append(card)

    # BRD §14 default ordering — sort_order ASC, game_type ASC for stability
    cards.sort(key=lambda c: (c.sort_order, c.game_type))
    return cards
