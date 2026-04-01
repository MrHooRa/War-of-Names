"""Abstract base class defining the plugin contract for minigames.

Every minigame must subclass GameTypePlugin and implement all abstract
methods. The engine calls these hooks at specific lifecycle points —
see BRD Section 5.2 for when each hook fires.
"""

from abc import ABC, abstractmethod


class GameTypePlugin(ABC):
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
            winner_membership_id, loser_membership_id,
            winner_payout, loser_penalty
        }
        """
        ...

    @abstractmethod
    def build_public_view(self, state: dict, viewer_membership_id) -> dict:
        """Return sanitized state safe to send to a specific player."""
        ...
