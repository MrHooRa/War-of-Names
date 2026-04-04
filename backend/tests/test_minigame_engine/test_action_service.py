"""Tests for validate_action_envelope — pure function, no DB required."""

import types
import uuid

import pytest

# Import app.core.models first so all model modules are fully initialized
# before action_service.py attempts to import them — this resolves the
# circular import that arises from core/models.py importing minigames/models.py.
import app.core.models  # noqa: F401

import app.modules.minigames.action_service as action_service_module
from app.core.enums import MinigameSessionPhase as Phase
from app.modules.minigames.action_service import (
    ActionError,
    PLAYABLE_PHASES,
    process_action,
    validate_action_envelope,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

PLAYER_1 = uuid.UUID("00000000-0000-0000-0000-000000000001")
PLAYER_2 = uuid.UUID("00000000-0000-0000-0000-000000000002")
OUTSIDER = uuid.UUID("00000000-0000-0000-0000-000000000099")


def _envelope(
    actor_membership_id=PLAYER_1,
    state_revision: int = 5,
    action: dict | None = None,
) -> dict:
    """Build a minimal valid action envelope."""
    return {
        "actor_membership_id": actor_membership_id,
        "state_revision": state_revision,
        "action": action or {"type": "move"},
        "action_id": uuid.uuid4(),
        "client_seq": 1,
    }


def _duo_participants(
    p1=PLAYER_1,
    p2=PLAYER_2,
) -> list[dict]:
    """Standard 2-player participants list, ordered by slot_index."""
    return [
        {"membership_id": p1, "slot_index": 0},
        {"membership_id": p2, "slot_index": 1},
    ]


def _solo_participants(p1=PLAYER_1) -> list[dict]:
    """Solo-player participants list."""
    return [{"membership_id": p1, "slot_index": 0}]


def _call(
    *,
    envelope: dict | None = None,
    session_phase: Phase = Phase.IN_PROGRESS,
    session_revision: int = 5,
    current_turn_index: int | None = 0,
    participants: list[dict] | None = None,
    state: dict | None = None,
) -> ActionError | None:
    """Thin wrapper so individual tests only specify what they're varying."""
    return validate_action_envelope(
        envelope=envelope if envelope is not None else _envelope(),
        session_phase=session_phase,
        session_revision=session_revision,
        current_turn_index=current_turn_index,
        participants=participants if participants is not None else _duo_participants(),
        state=state,
    )


# ── Happy paths ───────────────────────────────────────────────────────────────

def test_valid_envelope_returns_none():
    """A fully valid envelope from player_1 (slot 0) on their turn returns None."""
    assert _call() is None


def test_valid_envelope_player_2_turn():
    """A valid envelope from player_2 (slot 1) on slot 1's turn returns None."""
    result = _call(
        envelope=_envelope(actor_membership_id=PLAYER_2),
        current_turn_index=1,
    )
    assert result is None


def test_accepts_overtime_phase():
    """OVERTIME is a playable phase and must be accepted."""
    assert _call(session_phase=Phase.OVERTIME) is None


def test_playable_phases_constant():
    """PLAYABLE_PHASES must contain exactly IN_PROGRESS and OVERTIME."""
    assert PLAYABLE_PHASES == frozenset({Phase.IN_PROGRESS, Phase.OVERTIME})


# ── Session phase checks ──────────────────────────────────────────────────────

@pytest.mark.parametrize("phase", [
    Phase.CREATED,
    Phase.WAITING,
    Phase.READY,
    Phase.PAUSED,
    Phase.COMPLETED,
    Phase.CANCELLED,
    Phase.ABANDONED,
])
def test_rejects_non_playable_phase(phase):
    """Any phase that is not IN_PROGRESS or OVERTIME must return SESSION_ENDED."""
    err = _call(session_phase=phase)
    assert isinstance(err, ActionError)
    assert err.code == "SESSION_ENDED"
    assert err.message_ar == "الجلسة منتهية أو غير نشطة"


def test_rejects_terminal_session_completed():
    """Convenience single-case test for COMPLETED."""
    err = _call(session_phase=Phase.COMPLETED)
    assert err is not None
    assert err.code == "SESSION_ENDED"


# ── Stale revision checks ─────────────────────────────────────────────────────

def test_rejects_stale_revision():
    """Envelope revision older than session revision must return STALE_STATE."""
    err = _call(
        envelope=_envelope(state_revision=3),
        session_revision=5,
    )
    assert isinstance(err, ActionError)
    assert err.code == "STALE_STATE"
    assert "قديمة" in err.message_ar


def test_rejects_strictly_stale_revision():
    """Revision exactly one behind current is still stale."""
    err = _call(
        envelope=_envelope(state_revision=4),
        session_revision=5,
    )
    assert err is not None
    assert err.code == "STALE_STATE"


def test_accepts_exact_revision():
    """Envelope revision == session_revision is valid (not stale)."""
    assert _call(
        envelope=_envelope(state_revision=5),
        session_revision=5,
    ) is None


def test_accepts_future_revision():
    """Envelope revision > session_revision is also accepted (client ahead)."""
    assert _call(
        envelope=_envelope(state_revision=10),
        session_revision=5,
    ) is None


def test_rejects_missing_revision():
    """Envelope with no state_revision key is treated as stale."""
    env = _envelope()
    del env["state_revision"]
    err = validate_action_envelope(
        envelope=env,
        session_phase=Phase.IN_PROGRESS,
        session_revision=5,
        current_turn_index=0,
        participants=_duo_participants(),
    )
    assert err is not None
    assert err.code == "STALE_STATE"


# ── Participant checks ────────────────────────────────────────────────────────

def test_rejects_non_participant():
    """Actor who is neither player_1 nor player_2 must return NOT_PARTICIPANT."""
    err = _call(envelope=_envelope(actor_membership_id=OUTSIDER))
    assert isinstance(err, ActionError)
    assert err.code == "NOT_PARTICIPANT"
    assert "لست مشاركاً" in err.message_ar


# ── Turn checks (2-player) ───────────────────────────────────────────────────

def test_rejects_wrong_turn_player_2_acts_on_slot_0_turn():
    """Player 2 (slot 1) acting when it is slot 0's turn must return NOT_YOUR_TURN."""
    err = _call(
        envelope=_envelope(actor_membership_id=PLAYER_2),
        current_turn_index=0,
    )
    assert isinstance(err, ActionError)
    assert err.code == "NOT_YOUR_TURN"
    assert "ليس دورك" in err.message_ar


def test_rejects_wrong_turn_player_1_acts_on_slot_1_turn():
    """Player 1 (slot 0) acting when it is slot 1's turn must return NOT_YOUR_TURN."""
    err = _call(
        envelope=_envelope(actor_membership_id=PLAYER_1),
        current_turn_index=1,
    )
    assert isinstance(err, ActionError)
    assert err.code == "NOT_YOUR_TURN"


# ── N-player turn checks (3+ participants) ────────────────────────────────────

def test_three_player_valid_slot_2_turn():
    """3 players: actor at slot 2 acting on slot 2's turn passes."""
    p3 = uuid.UUID("00000000-0000-0000-0000-000000000003")
    participants = [
        {"membership_id": PLAYER_1, "slot_index": 0},
        {"membership_id": PLAYER_2, "slot_index": 1},
        {"membership_id": p3, "slot_index": 2},
    ]
    result = _call(
        envelope=_envelope(actor_membership_id=p3),
        current_turn_index=2,
        participants=participants,
    )
    assert result is None


def test_three_player_rejects_wrong_turn():
    """3 players: slot 0 acting on slot 2's turn must return NOT_YOUR_TURN."""
    p3 = uuid.UUID("00000000-0000-0000-0000-000000000003")
    participants = [
        {"membership_id": PLAYER_1, "slot_index": 0},
        {"membership_id": PLAYER_2, "slot_index": 1},
        {"membership_id": p3, "slot_index": 2},
    ]
    err = _call(
        envelope=_envelope(actor_membership_id=PLAYER_1),
        current_turn_index=2,
        participants=participants,
    )
    assert err is not None
    assert err.code == "NOT_YOUR_TURN"


# ── Solo game: turn check must be skipped ────────────────────────────────────

def test_solo_game_skips_turn_check_slot_0():
    """Solo game (1 participant): player_1 acting with turn_index=0 passes."""
    result = validate_action_envelope(
        envelope=_envelope(actor_membership_id=PLAYER_1),
        session_phase=Phase.IN_PROGRESS,
        session_revision=5,
        current_turn_index=0,
        participants=_solo_participants(),
    )
    assert result is None


def test_solo_game_skips_turn_check_none_current_turn():
    """Solo game: current_turn_index=None is also fine — turn is irrelevant."""
    result = validate_action_envelope(
        envelope=_envelope(actor_membership_id=PLAYER_1),
        session_phase=Phase.IN_PROGRESS,
        session_revision=5,
        current_turn_index=None,
        participants=_solo_participants(),
    )
    assert result is None


def test_solo_game_still_rejects_non_participant():
    """Solo game: outsider acting must still fail NOT_PARTICIPANT."""
    err = validate_action_envelope(
        envelope=_envelope(actor_membership_id=OUTSIDER),
        session_phase=Phase.IN_PROGRESS,
        session_revision=5,
        current_turn_index=0,
        participants=_solo_participants(),
    )
    assert err is not None
    assert err.code == "NOT_PARTICIPANT"


def test_solo_game_with_overtime_phase():
    """Solo game in OVERTIME phase with valid actor passes."""
    result = validate_action_envelope(
        envelope=_envelope(actor_membership_id=PLAYER_1),
        session_phase=Phase.OVERTIME,
        session_revision=0,
        current_turn_index=0,
        participants=_solo_participants(),
    )
    assert result is None


# ── None current_turn_index in multi-player — allow (turn not yet set) ────────

def test_multiplayer_none_turn_index_allows_any_participant():
    """Multi-player with current_turn_index=None (e.g. turn not yet set) allows any participant."""
    result = _call(
        envelope=_envelope(actor_membership_id=PLAYER_2),
        current_turn_index=None,
    )
    assert result is None


def test_parallel_word_selection_skips_turn_lock_for_player_2():
    """Mutaraha word selection is parallel, so player_2 may submit while turn_index=0."""
    result = _call(
        envelope=_envelope(
            actor_membership_id=PLAYER_2,
            action={"type": "select_words", "payload": {"actor": "player_2"}},
        ),
        current_turn_index=0,
        state={"game_phase": "word_selection"},
    )
    assert result is None


def test_parallel_word_selection_does_not_skip_turn_lock_for_battle_actions():
    """Only selection-phase actions bypass turn ownership; battle actions still fail."""
    err = _call(
        envelope=_envelope(
            actor_membership_id=PLAYER_2,
            action={"type": "GUESS", "payload": {"actor": "player_2"}},
        ),
        current_turn_index=0,
        state={"game_phase": "word_selection"},
    )
    assert err is not None
    assert err.code == "NOT_YOUR_TURN"


# ── Check ordering ────────────────────────────────────────────────────────────

def test_phase_check_before_stale_check():
    """SESSION_ENDED must be returned even when revision is also stale."""
    err = _call(
        envelope=_envelope(state_revision=0),
        session_phase=Phase.COMPLETED,
        session_revision=10,
    )
    assert err is not None
    assert err.code == "SESSION_ENDED"


def test_stale_check_before_participant_check():
    """STALE_STATE must be returned before NOT_PARTICIPANT when both would fail."""
    err = _call(
        envelope=_envelope(actor_membership_id=OUTSIDER, state_revision=0),
        session_phase=Phase.IN_PROGRESS,
        session_revision=5,
    )
    assert err is not None
    assert err.code == "STALE_STATE"


def test_participant_check_before_turn_check():
    """NOT_PARTICIPANT must be returned before NOT_YOUR_TURN when both would fail."""
    # OUTSIDER is not a participant, and slot 1's turn is active
    err = _call(
        envelope=_envelope(actor_membership_id=OUTSIDER),
        current_turn_index=1,
    )
    assert err is not None
    assert err.code == "NOT_PARTICIPANT"


# ── ActionError dataclass ─────────────────────────────────────────────────────

def test_action_error_is_dataclass():
    """ActionError must carry code and message_ar as attributes."""
    err = ActionError(code="TEST", message_ar="رسالة اختبار")
    assert err.code == "TEST"
    assert err.message_ar == "رسالة اختبار"


def test_action_error_equality():
    """Two ActionError instances with same fields must be equal."""
    a = ActionError(code="X", message_ar="ي")
    b = ActionError(code="X", message_ar="ي")
    assert a == b


@pytest.mark.asyncio
async def test_process_action_returns_public_result_and_internal_state(monkeypatch):
    fixed_now = object()
    new_state = {"phase": "battle", "revealed": 2}
    side_effects = [{"type": "tool_result", "result": {"ok": True}}]
    terminal_result = {"winner": "slot_2"}
    action_id = uuid.uuid4()
    correlation_id = uuid.uuid4()

    class FakeUpdateStmt:
        def __init__(self):
            self.where_args = ()
            self.values_kwargs = {}
            self.returning_args = ()

        def where(self, *args):
            self.where_args = args
            return self

        def values(self, **kwargs):
            self.values_kwargs = kwargs
            return self

        def returning(self, *args):
            self.returning_args = args
            return self

    class FakeUpdateResult:
        def fetchone(self):
            return (5,)

    class FakeSession:
        def __init__(self):
            self.added = []
            self.executed = None

        async def execute(self, stmt):
            self.executed = stmt
            return FakeUpdateResult()

        def add(self, obj):
            self.added.append(obj)

    class FakeReceipt:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.response = kwargs["response"]

    class FakeEvent:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    captured_stmt: dict[str, FakeUpdateStmt] = {}

    def fake_update(_model):
        stmt = FakeUpdateStmt()
        captured_stmt["stmt"] = stmt
        return stmt

    monkeypatch.setattr(action_service_module, "update", fake_update)
    monkeypatch.setattr(action_service_module, "MinigameActionReceipt", FakeReceipt)
    monkeypatch.setattr(action_service_module, "MinigameSessionEvent", FakeEvent)
    monkeypatch.setattr(action_service_module, "now_riyadh_naive", lambda: fixed_now)

    class FakePlugin:
        def validate_action(self, action, state):
            assert action == {"type": "guess"}
            assert state == {"phase": "battle", "revealed": 1}
            return None

        def apply_action(self, action, state):
            assert action == {"type": "guess"}
            assert state == {"phase": "battle", "revealed": 1}
            return new_state, side_effects

        def evaluate_terminal(self, state):
            assert state == new_state
            return terminal_result

    mg_session = types.SimpleNamespace(
        id=uuid.uuid4(),
        revision=4,
        game_state={"phase": "battle", "revealed": 1},
        current_turn_index=1,
        num_players=3,
        turn_number=6,
        correlation_id=correlation_id,
        turn_started_at=None,
        updated_at=None,
    )
    envelope = {
        "action": {"type": "guess"},
        "actor_membership_id": PLAYER_2,
        "client_seq": 9,
        "action_id": action_id,
    }
    participants = [
        {"membership_id": PLAYER_1, "slot_index": 0},
        {"membership_id": PLAYER_2, "slot_index": 1},
        {"membership_id": uuid.UUID("00000000-0000-0000-0000-000000000003"), "slot_index": 2},
    ]
    session = FakeSession()

    result = await process_action(
        session,
        mg_session=mg_session,
        plugin=FakePlugin(),
        envelope=envelope,
        participants=participants,
    )

    assert result == {
        "success": True,
        "revision": 5,
        "side_effects": side_effects,
        "terminal_result": terminal_result,
        "next_turn_index": 2,
        "turn_number": 7,
        "_state": new_state,
    }
    assert captured_stmt["stmt"].values_kwargs == {
        "game_state": new_state,
        "current_turn_index": 2,
        "turn_number": 7,
        "turn_started_at": fixed_now,
        "turn_duration_ms": None,
        "revision": 5,
        "updated_at": fixed_now,
    }
    assert mg_session.game_state == new_state
    assert mg_session.current_turn_index == 2
    assert mg_session.turn_number == 7
    assert mg_session.revision == 5

    receipt = next(obj for obj in session.added if isinstance(obj, FakeReceipt))
    assert receipt.kwargs["action_id"] == action_id
    assert receipt.kwargs["actor_membership_id"] == PLAYER_2
    assert receipt.kwargs["client_seq"] == 9
    assert receipt.kwargs["response"] == {
        "success": True,
        "revision": 5,
        "side_effects": side_effects,
        "terminal_result": terminal_result,
        "next_turn_index": 2,
        "turn_number": 7,
    }

    event = next(obj for obj in session.added if isinstance(obj, FakeEvent))
    assert event.kwargs["revision"] == 5
    assert event.kwargs["actor_membership_id"] == PLAYER_2
    assert event.kwargs["result"] == {
        "side_effects": side_effects,
        "next_turn_index": 2,
        "turn_number": 7,
        "terminal_result": terminal_result,
    }
