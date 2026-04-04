"""Tests for catalog read model dataclasses.

Verifies shape, defaults, and serialization helpers.
"""

import uuid
from datetime import datetime

from app.modules.minigames.catalog_read_model import (
    CatalogCard,
    CatalogMyState,
    CatalogMyStats,
    CatalogResponse,
    LobbyPageResponse,
    catalog_card_to_dict,
    catalog_response_to_dict,
)


def _sample_card(**overrides):
    base = dict(
        game_type="mutaraha",
        name="مطارحة",
        short_description="مبارزة كلمات 1v1",
        description="خمّن كلمات خصمك قبل ما يخمّن كلماتك",
        icon="lucide:swords",
        accent_color="#D84315",
        hero_variant="duel",
        card_variant="standard",
        min_players=2,
        max_players=2,
        player_count_label="1v1",
        estimated_duration_sec=300,
        estimated_duration_source="stats",
        buy_in_amount=500,
        status="playable",
        availability_reason=None,
        expected_launch_at=None,
        presence_count=3,
        queue_count=1,
        active_matches_count=1,
        recent_results_count=5,
        supports_overtime=True,
        supports_spectators=False,
        supports_ranked=False,
        supports_team_mode=False,
        featured=True,
        sort_order=10,
        correlation_id=str(uuid.uuid4()),
        my_state=CatalogMyState(
            queued=False,
            in_active_match=False,
            active_session_id=None,
            active_session_phase=None,
        ),
        my_stats=CatalogMyStats(
            wins=5,
            losses=2,
            current_streak=3,
            best_streak=4,
            total_matches=7,
            win_rate=0.714,
            has_history=True,
        ),
    )
    base.update(overrides)
    return CatalogCard(**base)


class TestCatalogCard:
    def test_construction_with_all_fields(self):
        card = _sample_card()
        assert card.game_type == "mutaraha"
        assert card.player_count_label == "1v1"
        assert card.my_stats.has_history is True

    def test_my_state_defaults(self):
        state = CatalogMyState()
        assert state.queued is False
        assert state.in_active_match is False
        assert state.active_session_id is None
        assert state.active_session_phase is None

    def test_my_stats_empty_player_defaults(self):
        stats = CatalogMyStats()
        assert stats.wins == 0
        assert stats.losses == 0
        assert stats.total_matches == 0
        assert stats.win_rate == 0.0
        assert stats.has_history is False


class TestSerializationHelpers:
    def test_catalog_card_to_dict_includes_all_fields(self):
        card = _sample_card()
        d = catalog_card_to_dict(card)
        assert d["game_type"] == "mutaraha"
        assert d["player_count_label"] == "1v1"
        assert d["my_state"]["queued"] is False
        assert d["my_stats"]["wins"] == 5
        assert d["my_stats"]["has_history"] is True

    def test_catalog_card_to_dict_with_active_session_phase(self):
        card = _sample_card(
            my_state=CatalogMyState(
                queued=False,
                in_active_match=True,
                active_session_id="00000000-0000-0000-0000-000000000001",
                active_session_phase="in_progress",
            )
        )
        d = catalog_card_to_dict(card)
        assert d["my_state"]["in_active_match"] is True
        assert d["my_state"]["active_session_phase"] == "in_progress"

    def test_catalog_card_to_dict_with_expected_launch_at(self):
        when = datetime(2026, 6, 1, 0, 0, 0)
        card = _sample_card(expected_launch_at=when, status="coming_soon")
        d = catalog_card_to_dict(card)
        assert d["expected_launch_at"] == "2026-06-01T00:00:00"

    def test_catalog_card_to_dict_expected_launch_at_null(self):
        card = _sample_card()
        d = catalog_card_to_dict(card)
        assert d["expected_launch_at"] is None

    def test_catalog_response_to_dict(self):
        card = _sample_card()
        cid = str(uuid.uuid4())
        resp = CatalogResponse(correlation_id=cid, games=[card])
        d = catalog_response_to_dict(resp)
        assert d["correlation_id"] == cid
        assert len(d["games"]) == 1
        assert d["games"][0]["game_type"] == "mutaraha"


class TestLobbyPageResponse:
    def test_construction(self):
        resp = LobbyPageResponse(
            correlation_id="test-id",
            game={"game_type": "mutaraha", "name": "مطارحة"},
            my_state={"queued": False, "in_active_match": False},
            my_stats={"wins": 0, "losses": 0, "has_history": False},
            lobby={"players": [], "queue_size": 0, "active_matches": [], "recent_results": []},
            leaderboard_preview=[],
            how_to_play={"summary_steps": []},
        )
        assert resp.correlation_id == "test-id"
        assert resp.game["game_type"] == "mutaraha"
