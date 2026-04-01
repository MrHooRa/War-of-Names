"""In-memory game type registry.

Plugins register at import time. The engine looks up plugins by id
when creating sessions or resolving game-specific logic.
"""

from app.modules.minigames.plugin import GameTypePlugin


class GameTypeRegistry:
    """Singleton registry mapping game type IDs to plugin instances."""

    _plugins: dict[str, GameTypePlugin] = {}

    @classmethod
    def register(cls, plugin: GameTypePlugin) -> None:
        """Register a game type plugin. Raises ValueError on duplicate id."""
        if plugin.id in cls._plugins:
            raise ValueError(f"اللعبة '{plugin.id}' مسجلة مسبقاً")
        cls._plugins[plugin.id] = plugin

    @classmethod
    def get(cls, game_type_id: str) -> GameTypePlugin | None:
        """Look up a plugin by its id. Returns None if not found."""
        return cls._plugins.get(game_type_id)

    @classmethod
    def list_all(cls) -> list[GameTypePlugin]:
        """Return all registered plugins."""
        return list(cls._plugins.values())
