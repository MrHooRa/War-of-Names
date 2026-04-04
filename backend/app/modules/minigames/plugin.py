"""Abstract base class defining the plugin contract for minigames.

Every minigame must subclass GameTypePlugin and implement all abstract
methods. The engine calls these hooks at specific lifecycle points —
see BRD Section 5.2 for when each hook fires.
"""

from abc import ABC, ABCMeta, abstractmethod


REQUIRED_PLUGIN_METADATA: dict[str, type] = {
    "id": str,
    "name": str,
    "description": str,
    "plugin_api_version": str,
    "settings_schema_version": str,
    "supports_overtime": bool,
    "supports_spectators": bool,
    "supports_ranked": bool,
    "supports_team_mode": bool,
    "min_players": int,
    "max_players": int,
}


def _validate_metadata_field(plugin_cls: type, field_name: str, expected_type: type) -> str | None:
    if not hasattr(plugin_cls, field_name):
        return f"{field_name} مفقود"

    value = getattr(plugin_cls, field_name)
    if expected_type is bool and type(value) is not bool:
        return f"{field_name} يجب أن يكون قيمة منطقية"
    if expected_type is int and type(value) is not int:
        return f"{field_name} يجب أن يكون عدداً صحيحاً"
    if expected_type is str and (not isinstance(value, str) or not value.strip()):
        return f"{field_name} يجب أن يكون نصاً غير فارغ"

    if expected_type not in {bool, int, str} and not isinstance(value, expected_type):
        return f"{field_name} يجب أن يكون من النوع {expected_type.__name__}"

    return None


def _validate_plugin_metadata(plugin_cls: type) -> None:
    errors = [
        error
        for field_name, expected_type in REQUIRED_PLUGIN_METADATA.items()
        if (error := _validate_metadata_field(plugin_cls, field_name, expected_type)) is not None
    ]

    if not errors:
        if plugin_cls.min_players < 1:
            errors.append("min_players يجب أن يكون 1 أو أكثر")
        if plugin_cls.max_players < plugin_cls.min_players:
            errors.append("max_players يجب أن يكون أكبر من أو يساوي min_players")

    if errors:
        raise TypeError(f"تعريف plugin غير صالح لـ {plugin_cls.__name__}: {', '.join(errors)}")


class GameTypePluginMeta(ABCMeta):
    """Keep ABC semantics while validating required plugin metadata on instantiation."""

    def __call__(cls, *args, **kwargs):
        if not getattr(cls, "__abstractmethods__", False):
            _validate_plugin_metadata(cls)
        return super().__call__(*args, **kwargs)


class GameTypePlugin(ABC, metaclass=GameTypePluginMeta):
    """Contract that every minigame plugin must satisfy.

    Class attributes (set by subclass):
        id: Unique identifier, e.g. "mutaraha"
        name: Arabic display name, e.g. "مطارحة"
        description: Short Arabic description
        plugin_api_version: Engine API version this plugin targets
        settings_schema_version: Version of this plugin's settings schema
        supports_overtime: Whether evaluate_overtime is meaningful
        supports_spectators: Reserved for future use
        supports_ranked: Whether ELO matchmaking is supported
        supports_team_mode: Reserved for future use
        min_players: Minimum players required (typically 2)
        max_players: Maximum players allowed (typically 2)
    """

    id: str
    name: str
    description: str
    plugin_api_version: str
    settings_schema_version: str
    supports_overtime: bool
    supports_spectators: bool
    supports_ranked: bool
    supports_team_mode: bool
    min_players: int
    max_players: int

    @abstractmethod
    def validate_settings(self, settings: dict) -> list[str]:
        """Validate admin-provided settings. Return list of error messages (empty = valid)."""
        ...

    @abstractmethod
    def init_session_state(self, config: dict) -> dict:
        """Create initial game state when a session starts."""
        ...

    @abstractmethod
    def validate_action(self, action: dict, state: dict) -> str | None:
        """Check if an action is legal. Return None if valid, Arabic error string if not."""
        ...

    @abstractmethod
    def apply_action(self, action: dict, state: dict) -> tuple[dict, list[dict]]:
        """Execute a validated action. Return (new_state, side_effects)."""
        ...

    @abstractmethod
    def evaluate_terminal(self, state: dict) -> dict | None:
        """Check if game has ended. Return terminal result dict or None if still playing."""
        ...

    @abstractmethod
    def evaluate_overtime(self, state: dict) -> dict | None:
        """Handle tied state after regular turns. Return overtime config or None."""
        ...

    @abstractmethod
    def compute_settlement(self, terminal_result: dict) -> dict:
        """Calculate financial settlement from terminal result.

        Must return: {
            "participant_results": [
                {"membership_id": uuid, "slot_index": int, "rank": int, "payout": int},
                ...
            ],
            "total_pool": int,
        }

        For 2-player games (like مطارحة): 2 entries (winner rank=1, loser rank=2).
        For N-player games: N entries ranked by placement.
        payout=0 means the player gets nothing back (lost their buy-in).
        """
        ...

    @abstractmethod
    def build_public_view(self, state: dict, viewer_membership_id) -> dict:
        """Return sanitized state safe to send to a specific player."""
        ...

    def migrate_settings(self, old_version: str, new_version: str, data: dict) -> dict:
        """Migrate persisted settings between schema versions.

        Default behavior is a no-op pass-through for plugins that have not
        introduced schema migrations yet.
        """
        return data

    def migrate_session(self, old_version: str, new_version: str, data: dict) -> dict:
        """Migrate persisted session state between schema versions.

        Default behavior is a no-op pass-through for backwards compatibility.
        """
        return data
