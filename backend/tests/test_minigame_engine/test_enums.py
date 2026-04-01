"""Verify minigame enums exist and have expected members."""

from app.core.enums import (
    MinigameSessionPhase,
    MinigameMatchType,
    MinigameSettlementState,
    MinigameTurnSide,
    MinigameTypeStatus,
)


def test_session_phase_has_all_states():
    phases = {p.value for p in MinigameSessionPhase}
    expected = {"created", "waiting", "ready", "in_progress", "overtime", "paused", "completed", "cancelled", "abandoned"}
    assert phases == expected


def test_session_phase_terminal_states():
    terminal = {"completed", "cancelled", "abandoned"}
    for phase in MinigameSessionPhase:
        if phase.value in terminal:
            assert phase in (
                MinigameSessionPhase.COMPLETED,
                MinigameSessionPhase.CANCELLED,
                MinigameSessionPhase.ABANDONED,
            )


def test_match_type_values():
    assert MinigameMatchType.CHALLENGE.value == "challenge"
    assert MinigameMatchType.QUEUE.value == "queue"


def test_settlement_state_values():
    states = {s.value for s in MinigameSettlementState}
    assert states == {"pending", "settled", "failed", "reconciled"}


def test_turn_side_values():
    assert MinigameTurnSide.PLAYER_1.value == "player_1"
    assert MinigameTurnSide.PLAYER_2.value == "player_2"


def test_type_status_values():
    statuses = {s.value for s in MinigameTypeStatus}
    assert statuses == {"active", "disabled", "deprecated"}


def test_ledger_entry_type_has_minigame_values():
    from app.core.enums import LedgerEntryType
    minigame_types = {
        "minigame_buy_in",
        "minigame_payout",
        "minigame_forfeit",
        "minigame_refund",
        "minigame_cancel_penalty",
    }
    existing = {t.value for t in LedgerEntryType}
    assert minigame_types.issubset(existing)
