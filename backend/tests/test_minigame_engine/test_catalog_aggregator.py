"""Tests for the pure catalog aggregator.

Uses SimpleNamespace stubs for all DB-backed objects so the tests run
without SQLAlchemy. This is the core unit test surface for
BRD §8.1.1 (every field) and §10.1.1 (visibility rules).
"""

import uuid
from dataclasses import dataclass
from datetime import datetime
from types import SimpleNamespace

import pytest

from app.modules.minigames.catalog_aggregator import (
    LobbyPresenceSnapshot,
    build_catalog_cards,
)


# ─── Stub builders ─────────────────────────────────────────────────

def _game_type(game_id="mutaraha", **overrides):
    base = dict(
        id=game_id,
        name="مطارحة",
        description="duel game",
        min_players=2,
        max_players=2,
        supports_overtime=True,
        supports_spectators=False,
        supports_ranked=False,
        supports_team_mode=False,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _config(**overrides):
    base = dict(
        game_type="mutaraha",
        short_description="مبارزة كلمات 1v1",
        icon_token="lucide:swords",
        accent_color="#D84315",
        hero_variant="duel",
        card_variant="standard",
        estimated_duration_sec=300,
        featured=True,
        sort_order=10,
        availability_mode="active",
        marketing_label=None,
        expected_launch_at=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _leaderboard(**overrides):
    base = dict(
        game_type="mutaraha",
        wins=5,
        losses=2,
        current_streak=3,
        best_streak=4,
        total_matches=7,
        avg_match_duration_sec=285.0,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _raw(
    game_types=None,
    configs_by_game_type=None,
    settings=None,
    counts_by_game_type=None,
    my_active_session_by_game_type=None,
    leaderboard_by_game_type=None,
):
    return SimpleNamespace(
        game_types=game_types if game_types is not None else [_game_type()],
        configs_by_game_type=(
            configs_by_game_type
            if configs_by_game_type is not None
            else {"mutaraha": _config()}
        ),
        settings=settings
        if settings is not None
        else {
            "minigame_buy_in": 500,
            "minigame_kill_switch": "off",
        },
        counts_by_game_type=(
            counts_by_game_type
            if counts_by_game_type is not None
            else {"mutaraha": (1, 5)}
        ),
        my_active_session_by_game_type=(
            my_active_session_by_game_type
            if my_active_session_by_game_type is not None
            else {}
        ),
        leaderboard_by_game_type=(
            leaderboard_by_game_type
            if leaderboard_by_game_type is not None
            else {}
        ),
    )


def _presence(**overrides):
    base = dict(
        mutaraha=LobbyPresenceSnapshot(presence_count=3, queue_count=1, in_queue=False)
    )
    base.update(overrides)
    return base


# ─── Happy path ────────────────────────────────────────────────────

class TestHappyPath:
    def test_single_playable_card(self):
        cards = build_catalog_cards(
            raw=_raw(),
            lobby_presence=_presence(),
            player_balance=1000,
            is_bankrupt=False,
            membership_id=uuid.uuid4(),
            correlation_id="cid-1",
        )
        assert len(cards) == 1
        card = cards[0]
        assert card.game_type == "mutaraha"
        assert card.name == "مطارحة"
        assert card.player_count_label == "1v1"
        assert card.status == "playable"
        assert card.buy_in_amount == 500
        assert card.presence_count == 3
        assert card.queue_count == 1
        assert card.active_matches_count == 1
        assert card.recent_results_count == 5
        assert card.correlation_id == "cid-1"
        assert card.my_stats.has_history is False  # no leaderboard row
        assert card.my_stats.wins == 0


# ─── Visibility rules (BRD §10.1.1) ────────────────────────────────

class TestVisibility:
    def test_hidden_config_is_filtered_out(self):
        cards = build_catalog_cards(
            raw=_raw(configs_by_game_type={"mutaraha": _config(availability_mode="hidden")}),
            lobby_presence=_presence(),
            player_balance=1000,
            is_bankrupt=False,
            membership_id=uuid.uuid4(),
            correlation_id="cid",
        )
        assert cards == []

    def test_maintenance_card_is_visible_as_locked(self):
        cards = build_catalog_cards(
            raw=_raw(
                configs_by_game_type={
                    "mutaraha": _config(availability_mode="maintenance")
                }
            ),
            lobby_presence=_presence(),
            player_balance=1000,
            is_bankrupt=False,
            membership_id=uuid.uuid4(),
            correlation_id="cid",
        )
        assert len(cards) == 1
        assert cards[0].status == "maintenance"
        assert cards[0].availability_reason is not None

    def test_coming_soon_card_is_visible(self):
        cards = build_catalog_cards(
            raw=_raw(
                configs_by_game_type={
                    "mutaraha": _config(availability_mode="coming_soon")
                }
            ),
            lobby_presence=_presence(),
            player_balance=1000,
            is_bankrupt=False,
            membership_id=uuid.uuid4(),
            correlation_id="cid",
        )
        assert len(cards) == 1
        assert cards[0].status == "coming_soon"

    def test_missing_config_falls_back_to_hidden(self):
        """BRD §11.4.3 — missing config → hidden by default (filtered out)."""
        cards = build_catalog_cards(
            raw=_raw(configs_by_game_type={}),
            lobby_presence=_presence(),
            player_balance=1000,
            is_bankrupt=False,
            membership_id=uuid.uuid4(),
            correlation_id="cid",
        )
        assert cards == []

    def test_kill_switch_emergency_forces_maintenance(self):
        cards = build_catalog_cards(
            raw=_raw(settings={"minigame_buy_in": 500, "minigame_kill_switch": "emergency"}),
            lobby_presence=_presence(),
            player_balance=1000,
            is_bankrupt=False,
            membership_id=uuid.uuid4(),
            correlation_id="cid",
        )
        assert len(cards) == 1
        assert cards[0].status == "maintenance"


# ─── My state / my stats ───────────────────────────────────────────

class TestMyStateAndStats:
    def test_active_session_overrides_status(self):
        session_id = uuid.uuid4()
        cards = build_catalog_cards(
            raw=_raw(
                my_active_session_by_game_type={
                    "mutaraha": (session_id, "in_progress")
                }
            ),
            lobby_presence=_presence(),
            player_balance=0,  # would be insufficient
            is_bankrupt=True,  # would normally block
            membership_id=uuid.uuid4(),
            correlation_id="cid",
        )
        assert cards[0].status == "in_match"
        assert cards[0].my_state.active_session_id == str(session_id)
        assert cards[0].my_state.active_session_phase == "in_progress"
        assert cards[0].my_state.in_active_match is True

    def test_in_queue_overrides_balance(self):
        cards = build_catalog_cards(
            raw=_raw(),
            lobby_presence={
                "mutaraha": LobbyPresenceSnapshot(
                    presence_count=3, queue_count=1, in_queue=True
                )
            },
            player_balance=0,
            is_bankrupt=True,
            membership_id=uuid.uuid4(),
            correlation_id="cid",
        )
        assert cards[0].status == "queued"
        assert cards[0].my_state.queued is True

    def test_insufficient_balance(self):
        cards = build_catalog_cards(
            raw=_raw(),
            lobby_presence=_presence(),
            player_balance=100,
            is_bankrupt=False,
            membership_id=uuid.uuid4(),
            correlation_id="cid",
        )
        assert cards[0].status == "insufficient_balance"
        assert "500" in (cards[0].availability_reason or "")

    def test_leaderboard_present_fills_stats(self):
        cards = build_catalog_cards(
            raw=_raw(leaderboard_by_game_type={"mutaraha": _leaderboard()}),
            lobby_presence=_presence(),
            player_balance=1000,
            is_bankrupt=False,
            membership_id=uuid.uuid4(),
            correlation_id="cid",
        )
        stats = cards[0].my_stats
        assert stats.wins == 5
        assert stats.losses == 2
        assert stats.total_matches == 7
        assert stats.has_history is True
        assert stats.win_rate == pytest.approx(5 / 7, rel=1e-3)

    def test_zero_matches_win_rate_safe(self):
        lb = _leaderboard(wins=0, losses=0, total_matches=0)
        cards = build_catalog_cards(
            raw=_raw(leaderboard_by_game_type={"mutaraha": lb}),
            lobby_presence=_presence(),
            player_balance=1000,
            is_bankrupt=False,
            membership_id=uuid.uuid4(),
            correlation_id="cid",
        )
        stats = cards[0].my_stats
        assert stats.total_matches == 0
        assert stats.win_rate == 0.0
        assert stats.has_history is False


# ─── Duration source resolution ────────────────────────────────────

class TestDurationSource:
    def test_stats_source_when_enough_matches(self):
        lb = _leaderboard(total_matches=42, avg_match_duration_sec=275.5)
        cards = build_catalog_cards(
            raw=_raw(leaderboard_by_game_type={"mutaraha": lb}),
            lobby_presence=_presence(),
            player_balance=1000,
            is_bankrupt=False,
            membership_id=uuid.uuid4(),
            correlation_id="cid",
        )
        assert cards[0].estimated_duration_sec == 275
        assert cards[0].estimated_duration_source == "stats"

    def test_config_source_when_not_enough_matches(self):
        lb = _leaderboard(total_matches=5, avg_match_duration_sec=275.5)
        cards = build_catalog_cards(
            raw=_raw(leaderboard_by_game_type={"mutaraha": lb}),
            lobby_presence=_presence(),
            player_balance=1000,
            is_bankrupt=False,
            membership_id=uuid.uuid4(),
            correlation_id="cid",
        )
        # Config says 300
        assert cards[0].estimated_duration_sec == 300
        assert cards[0].estimated_duration_source == "config"


# ─── Sort order ────────────────────────────────────────────────────

class TestSortOrder:
    def test_cards_sorted_by_sort_order_ascending(self):
        raw = _raw(
            game_types=[
                _game_type(game_id="game_a"),
                _game_type(game_id="game_b"),
                _game_type(game_id="game_c"),
            ],
            configs_by_game_type={
                "game_a": _config(game_type="game_a", sort_order=30),
                "game_b": _config(game_type="game_b", sort_order=10),
                "game_c": _config(game_type="game_c", sort_order=20),
            },
            counts_by_game_type={"game_a": (0, 0), "game_b": (0, 0), "game_c": (0, 0)},
        )
        cards = build_catalog_cards(
            raw=raw,
            lobby_presence={
                "game_a": LobbyPresenceSnapshot(0, 0, False),
                "game_b": LobbyPresenceSnapshot(0, 0, False),
                "game_c": LobbyPresenceSnapshot(0, 0, False),
            },
            player_balance=1000,
            is_bankrupt=False,
            membership_id=uuid.uuid4(),
            correlation_id="cid",
        )
        assert [c.game_type for c in cards] == ["game_b", "game_c", "game_a"]
