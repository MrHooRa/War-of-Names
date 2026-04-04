"""Pure lifecycle tests for the N-player minigame services."""

from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import patch

import app.core.models  # noqa: F401

from app.core.enums import LedgerDirection, MinigameSessionPhase as Phase
from app.modules.minigames.action_service import ActionError, validate_action_envelope
from app.modules.minigames.economy import (
    create_buy_in_entry,
    create_normal_settlement_entries,
    create_solo_settlement_entries,
)
from app.modules.minigames.session_service import (
    compute_transition_update,
    validate_session_creation,
)
from app.modules.minigames.settlement_service import (
    SettlementType,
    compute_settlement_type,
)

_FIXED_NOW = datetime(2026, 4, 1, 12, 0, 0)
_PATCH_NOW = patch(
    "app.modules.minigames.session_service._now",
    return_value=_FIXED_NOW,
)


def _transition(**kwargs):
    with _PATCH_NOW:
        return compute_transition_update(**kwargs)


def _participants(*membership_ids: uuid.UUID) -> list[dict]:
    return [
        {"membership_id": membership_id, "slot_index": slot_index}
        for slot_index, membership_id in enumerate(membership_ids)
    ]


class TestFull1v1LifecycleHappyPath:
    COMPETITION_ID = uuid.uuid4()
    SESSION_ID = uuid.uuid4()
    PLAYER_1 = uuid.uuid4()
    PLAYER_2 = uuid.uuid4()
    BUY_IN = 100

    def test_full_1v1_lifecycle_happy_path(self):
        errors = validate_session_creation(
            game_type_id="mutaraha",
            plugin_exists=True,
            plugin_status="active",
            player_balance=500,
            buy_in_amount=self.BUY_IN,
            is_bankrupt=False,
        )
        assert errors == []

        p1_balance_before = 500
        p2_balance_before = 300
        entry_p1 = create_buy_in_entry(
            membership_id=self.PLAYER_1,
            competition_id=self.COMPETITION_ID,
            session_id=self.SESSION_ID,
            amount=self.BUY_IN,
            balance_before=p1_balance_before,
        )
        entry_p2 = create_buy_in_entry(
            membership_id=self.PLAYER_2,
            competition_id=self.COMPETITION_ID,
            session_id=self.SESSION_ID,
            amount=self.BUY_IN,
            balance_before=p2_balance_before,
        )
        assert entry_p1.direction == LedgerDirection.DEBIT
        assert entry_p2.direction == LedgerDirection.DEBIT
        assert entry_p1.balance_after == p1_balance_before - self.BUY_IN
        assert entry_p2.balance_after == p2_balance_before - self.BUY_IN

        revision = 0
        upd1 = _transition(
            current_phase=Phase.CREATED,
            target_phase=Phase.WAITING,
            current_revision=revision,
        )
        revision = upd1["revision"]

        upd2 = _transition(
            current_phase=Phase.WAITING,
            target_phase=Phase.READY,
            current_revision=revision,
        )
        revision = upd2["revision"]

        upd3 = _transition(
            current_phase=Phase.READY,
            target_phase=Phase.IN_PROGRESS,
            current_revision=revision,
        )
        revision = upd3["revision"]
        assert upd3["phase"] == Phase.IN_PROGRESS
        assert upd3["current_turn_index"] == 0
        assert upd3["started_at"] == _FIXED_NOW

        envelope = {
            "state_revision": revision,
            "actor_membership_id": self.PLAYER_1,
            "action": {"type": "guess"},
        }
        action_err = validate_action_envelope(
            envelope=envelope,
            session_phase=Phase.IN_PROGRESS,
            session_revision=revision,
            current_turn_index=0,
            participants=_participants(self.PLAYER_1, self.PLAYER_2),
        )
        assert action_err is None

        upd4 = _transition(
            current_phase=Phase.IN_PROGRESS,
            target_phase=Phase.COMPLETED,
            current_revision=revision,
            terminal_reason="player_won",
            winner_slot_index=0,
        )
        assert upd4["phase"] == Phase.COMPLETED
        assert upd4["winner_slot_index"] == 0
        assert upd4["terminal_reason"] == "player_won"
        assert upd4["completed_at"] == _FIXED_NOW

        stype = compute_settlement_type(
            phase="completed",
            terminal_reason="player_won",
            winner_membership_id=self.PLAYER_1,
            is_solo=False,
        )
        assert stype == SettlementType.NORMAL

        entries = create_normal_settlement_entries(
            winner_membership_id=self.PLAYER_1,
            loser_membership_id=self.PLAYER_2,
            competition_id=self.COMPETITION_ID,
            session_id=self.SESSION_ID,
            buy_in_amount=self.BUY_IN,
            winner_balance=entry_p1.balance_after,
        )
        assert len(entries) == 1
        payout = entries[0]
        assert payout.direction == LedgerDirection.CREDIT
        assert payout.amount == self.BUY_IN * 2
        assert payout.balance_after == entry_p1.balance_after + self.BUY_IN * 2


class TestSoloLifecycle:
    COMPETITION_ID = uuid.uuid4()
    SESSION_ID = uuid.uuid4()
    PLAYER_1 = uuid.uuid4()
    BUY_IN = 50

    def test_solo_lifecycle(self):
        errors = validate_session_creation(
            game_type_id="mutaraha",
            plugin_exists=True,
            plugin_status="active",
            player_balance=200,
            buy_in_amount=self.BUY_IN,
            is_bankrupt=False,
        )
        assert errors == []

        entry_p1 = create_buy_in_entry(
            membership_id=self.PLAYER_1,
            competition_id=self.COMPETITION_ID,
            session_id=self.SESSION_ID,
            amount=self.BUY_IN,
            balance_before=200,
        )
        assert entry_p1.direction == LedgerDirection.DEBIT
        assert entry_p1.balance_after == 150

        revision = 0
        revision = _transition(
            current_phase=Phase.CREATED,
            target_phase=Phase.WAITING,
            current_revision=revision,
        )["revision"]
        revision = _transition(
            current_phase=Phase.WAITING,
            target_phase=Phase.READY,
            current_revision=revision,
        )["revision"]
        upd3 = _transition(
            current_phase=Phase.READY,
            target_phase=Phase.IN_PROGRESS,
            current_revision=revision,
        )
        revision = upd3["revision"]
        assert upd3["current_turn_index"] == 0

        action_err = validate_action_envelope(
            envelope={
                "state_revision": revision,
                "actor_membership_id": self.PLAYER_1,
                "action": {"type": "answer"},
            },
            session_phase=Phase.IN_PROGRESS,
            session_revision=revision,
            current_turn_index=0,
            participants=_participants(self.PLAYER_1),
        )
        assert action_err is None

        upd4 = _transition(
            current_phase=Phase.IN_PROGRESS,
            target_phase=Phase.COMPLETED,
            current_revision=revision,
            terminal_reason="solo_complete",
            winner_slot_index=0,
        )
        assert upd4["phase"] == Phase.COMPLETED

        stype = compute_settlement_type(
            phase="completed",
            terminal_reason="solo_complete",
            winner_membership_id=self.PLAYER_1,
            is_solo=True,
        )
        assert stype == SettlementType.SOLO

        reward = self.BUY_IN * 2
        entries = create_solo_settlement_entries(
            player_membership_id=self.PLAYER_1,
            competition_id=self.COMPETITION_ID,
            session_id=self.SESSION_ID,
            reward_amount=reward,
            player_balance=entry_p1.balance_after,
        )
        assert len(entries) == 1
        assert entries[0].direction == LedgerDirection.CREDIT
        assert entries[0].amount == reward
        assert entries[0].balance_after == entry_p1.balance_after + reward


class TestCancelLifecycle:
    def test_cancel_lifecycle(self):
        stype = compute_settlement_type(
            phase="cancelled",
            terminal_reason="admin_cancelled",
            winner_membership_id=None,
            is_solo=False,
        )
        assert stype == SettlementType.CANCEL


class TestAbandonWithWinnerLifecycle:
    def test_abandon_with_winner_lifecycle(self):
        winner_id = uuid.uuid4()
        stype = compute_settlement_type(
            phase="abandoned",
            terminal_reason="player_disconnected",
            winner_membership_id=winner_id,
            is_solo=False,
        )
        assert stype == SettlementType.FORFEIT


class TestActionRejectedInTerminalSession:
    PLAYER_1 = uuid.uuid4()
    PLAYER_2 = uuid.uuid4()

    def test_action_rejected_in_terminal_session(self):
        error = validate_action_envelope(
            envelope={
                "state_revision": 5,
                "actor_membership_id": self.PLAYER_1,
                "action": {"type": "guess"},
            },
            session_phase=Phase.COMPLETED,
            session_revision=5,
            current_turn_index=0,
            participants=_participants(self.PLAYER_1, self.PLAYER_2),
        )

        assert isinstance(error, ActionError)
        assert error.code == "SESSION_ENDED"
        assert "منتهية" in error.message_ar or "غير نشطة" in error.message_ar
