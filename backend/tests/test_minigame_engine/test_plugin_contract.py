"""Verify plugin contract interface and a dummy implementation."""

import pytest
from app.modules.minigames.plugin import GameTypePlugin


class DummyPlugin(GameTypePlugin):
    """Minimal valid plugin for testing the contract."""

    id = "test_dummy"
    name = "لعبة تجريبية"
    description = "لعبة للاختبار فقط"
    plugin_api_version = "1.0"
    settings_schema_version = "1.0"
    supports_overtime = False
    supports_spectators = False
    supports_ranked = False
    supports_team_mode = False
    min_players = 2
    max_players = 2

    def validate_settings(self, settings: dict) -> list[str]:
        return []

    def init_session_state(self, config: dict) -> dict:
        return {"turn": 0, "scores": [0, 0]}

    def validate_action(self, action: dict, state: dict) -> str | None:
        if action.get("type") not in ("move", "pass"):
            return "نوع الإجراء غير صالح"
        return None

    def apply_action(self, action: dict, state: dict) -> tuple[dict, list[dict]]:
        new_state = {**state, "turn": state["turn"] + 1}
        side_effects = [{"type": "sound", "name": "click"}]
        return new_state, side_effects

    def evaluate_terminal(self, state: dict) -> dict | None:
        if state["turn"] >= 10:
            return {"winner": "player_1", "reason": "turn_limit"}
        return None

    def evaluate_overtime(self, state: dict) -> dict | None:
        return None

    def compute_settlement(self, terminal_result: dict) -> dict:
        return {
            "participant_results": [
                {"membership_id": None, "slot_index": 0, "rank": 1, "payout": 1000},
                {"membership_id": None, "slot_index": 1, "rank": 2, "payout": 0},
            ],
            "total_pool": 1000,
        }

    def build_public_view(self, state: dict, viewer_membership_id) -> dict:
        return {"turn": state["turn"], "my_view": True}


def test_dummy_plugin_satisfies_contract():
    plugin = DummyPlugin()
    assert plugin.id == "test_dummy"
    assert plugin.min_players == 2
    assert plugin.max_players == 2


def test_validate_settings_returns_empty_for_valid():
    plugin = DummyPlugin()
    errors = plugin.validate_settings({"some": "config"})
    assert errors == []


def test_init_session_state_returns_dict():
    plugin = DummyPlugin()
    state = plugin.init_session_state({})
    assert isinstance(state, dict)
    assert state["turn"] == 0


def test_validate_action_returns_none_for_valid():
    plugin = DummyPlugin()
    error = plugin.validate_action({"type": "move"}, {"turn": 0})
    assert error is None


def test_validate_action_returns_error_for_invalid():
    plugin = DummyPlugin()
    error = plugin.validate_action({"type": "invalid"}, {"turn": 0})
    assert error == "نوع الإجراء غير صالح"


def test_apply_action_returns_new_state_and_effects():
    plugin = DummyPlugin()
    new_state, effects = plugin.apply_action({"type": "move"}, {"turn": 0, "scores": [0, 0]})
    assert new_state["turn"] == 1
    assert len(effects) == 1


def test_evaluate_terminal_returns_none_mid_game():
    plugin = DummyPlugin()
    result = plugin.evaluate_terminal({"turn": 5})
    assert result is None


def test_evaluate_terminal_returns_result_at_end():
    plugin = DummyPlugin()
    result = plugin.evaluate_terminal({"turn": 10})
    assert result is not None
    assert result["winner"] == "player_1"


def test_compute_settlement_returns_payout():
    plugin = DummyPlugin()
    settlement = plugin.compute_settlement({"winner": "player_1"})
    assert settlement["total_pool"] == 1000
    assert len(settlement["participant_results"]) == 2
    winner = next(r for r in settlement["participant_results"] if r["rank"] == 1)
    assert winner["payout"] == 1000
    loser = next(r for r in settlement["participant_results"] if r["rank"] == 2)
    assert loser["payout"] == 0


def test_build_public_view_returns_filtered_state():
    plugin = DummyPlugin()
    view = plugin.build_public_view({"turn": 3, "secret": "hidden"}, viewer_membership_id=1)
    assert view["turn"] == 3
    assert "secret" not in view


def test_cannot_instantiate_abstract_directly():
    with pytest.raises(TypeError):
        GameTypePlugin()


def test_missing_required_metadata_fails_on_instantiation():
    class MissingIdPlugin(GameTypePlugin):
        name = "لعبة ناقصة"
        description = "تفتقد المعرّف"
        plugin_api_version = "1.0"
        settings_schema_version = "1.0"
        supports_overtime = False
        supports_spectators = False
        supports_ranked = False
        supports_team_mode = False
        min_players = 2
        max_players = 2

        def validate_settings(self, settings: dict) -> list[str]:
            return []

        def init_session_state(self, config: dict) -> dict:
            return {}

        def validate_action(self, action: dict, state: dict) -> str | None:
            return None

        def apply_action(self, action: dict, state: dict) -> tuple[dict, list[dict]]:
            return state, []

        def evaluate_terminal(self, state: dict) -> dict | None:
            return None

        def evaluate_overtime(self, state: dict) -> dict | None:
            return None

        def compute_settlement(self, terminal_result: dict) -> dict:
            return {}

        def build_public_view(self, state: dict, viewer_membership_id) -> dict:
            return {}

    with pytest.raises(TypeError, match="id مفقود"):
        MissingIdPlugin()


def test_invalid_player_bounds_fail_on_instantiation():
    class InvalidBoundsPlugin(GameTypePlugin):
        id = "invalid_bounds"
        name = "لعبة غير صالحة"
        description = "حدود اللاعبين غير صحيحة"
        plugin_api_version = "1.0"
        settings_schema_version = "1.0"
        supports_overtime = False
        supports_spectators = False
        supports_ranked = False
        supports_team_mode = False
        min_players = 3
        max_players = 2

        def validate_settings(self, settings: dict) -> list[str]:
            return []

        def init_session_state(self, config: dict) -> dict:
            return {}

        def validate_action(self, action: dict, state: dict) -> str | None:
            return None

        def apply_action(self, action: dict, state: dict) -> tuple[dict, list[dict]]:
            return state, []

        def evaluate_terminal(self, state: dict) -> dict | None:
            return None

        def evaluate_overtime(self, state: dict) -> dict | None:
            return None

        def compute_settlement(self, terminal_result: dict) -> dict:
            return {}

        def build_public_view(self, state: dict, viewer_membership_id) -> dict:
            return {}

    with pytest.raises(TypeError, match="max_players يجب أن يكون أكبر من أو يساوي min_players"):
        InvalidBoundsPlugin()
