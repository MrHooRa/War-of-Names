"""Test the in-memory game type registry."""

import pytest
from app.modules.minigames.registry import GameTypeRegistry
from app.modules.minigames.plugin import GameTypePlugin


class FakePlugin(GameTypePlugin):
    id = "fake_game"
    name = "لعبة وهمية"
    description = "لعبة للاختبار"
    plugin_api_version = "1.0"
    settings_schema_version = "1.0"
    supports_overtime = False
    supports_spectators = False
    supports_ranked = False
    supports_team_mode = False
    min_players = 2
    max_players = 2

    def validate_settings(self, settings): return []
    def init_session_state(self, config): return {}
    def validate_action(self, action, state): return None
    def apply_action(self, action, state): return state, []
    def evaluate_terminal(self, state): return None
    def evaluate_overtime(self, state): return None
    def compute_settlement(self, result): return {"winner_payout": 0, "loser_penalty": 0}
    def build_public_view(self, state, vid): return state


class AnotherFakePlugin(GameTypePlugin):
    id = "another_fake"
    name = "لعبة أخرى"
    description = "لعبة ثانية"
    plugin_api_version = "1.0"
    settings_schema_version = "1.0"
    supports_overtime = True
    supports_spectators = False
    supports_ranked = False
    supports_team_mode = False
    min_players = 2
    max_players = 4

    def validate_settings(self, settings): return []
    def init_session_state(self, config): return {}
    def validate_action(self, action, state): return None
    def apply_action(self, action, state): return state, []
    def evaluate_terminal(self, state): return None
    def evaluate_overtime(self, state): return None
    def compute_settlement(self, result): return {"winner_payout": 0, "loser_penalty": 0}
    def build_public_view(self, state, vid): return state


@pytest.fixture(autouse=True)
def clean_registry():
    """Reset the registry before each test."""
    GameTypeRegistry._plugins.clear()
    yield
    GameTypeRegistry._plugins.clear()


def test_register_and_get():
    plugin = FakePlugin()
    GameTypeRegistry.register(plugin)
    found = GameTypeRegistry.get("fake_game")
    assert found is plugin


def test_get_unknown_returns_none():
    assert GameTypeRegistry.get("nonexistent") is None


def test_register_duplicate_raises():
    GameTypeRegistry.register(FakePlugin())
    with pytest.raises(ValueError, match="مسجلة مسبقاً"):
        GameTypeRegistry.register(FakePlugin())


def test_list_all_returns_registered():
    GameTypeRegistry.register(FakePlugin())
    GameTypeRegistry.register(AnotherFakePlugin())
    all_plugins = GameTypeRegistry.list_all()
    assert len(all_plugins) == 2
    ids = {p.id for p in all_plugins}
    assert ids == {"fake_game", "another_fake"}


def test_list_all_empty():
    assert GameTypeRegistry.list_all() == []
