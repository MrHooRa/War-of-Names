"""Tests for validate_action_envelope — pure function, no DB required."""

import uuid
import pytest

# Import app.core.models first so all model modules are fully initialized
# before action_service.py attempts to import them — this resolves the
# circular import that arises from core/models.py importing minigames/models.py.
import app.core.models  # noqa: F401

from app.core.enums import MinigameSessionPhase as Phase, MinigameTurnSide
from app.modules.minigames.action_service import (
    ActionError,
    PLAYABLE_PHASES,
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


def _call(
    *,
    envelope: dict | None = None,
    session_phase: Phase = Phase.IN_PROGRESS,
    session_revision: int = 5,
    current_turn: MinigameTurnSide = MinigameTurnSide.PLAYER_1,
    player_1_membership_id=PLAYER_1,
    player_2_membership_id=PLAYER_2,
) -> ActionError | None:
    """Thin wrapper so individual tests only specify what they're varying."""
    return validate_action_envelope(
        envelope=envelope if envelope is not None else _envelope(),
        session_phase=session_phase,
        session_revision=session_revision,
        current_turn=current_turn,
        player_1_membership_id=player_1_membership_id,
        player_2_membership_id=player_2_membership_id,
    )


# ── Happy paths ───────────────────────────────────────────────────────────────

def test_valid_envelope_returns_none():
    """A fully valid envelope from player_1 on their turn returns None."""
    assert _call() is None


def test_valid_envelope_player_2_turn():
    """A valid envelope from player_2 on player_2's turn returns None."""
    result = _call(
        envelope=_envelope(actor_membership_id=PLAYER_2),
        current_turn=MinigameTurnSide.PLAYER_2,
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
        current_turn=MinigameTurnSide.PLAYER_1,
        player_1_membership_id=PLAYER_1,
        player_2_membership_id=PLAYER_2,
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


# ── Turn checks (1v1) ─────────────────────────────────────────────────────────

def test_rejects_wrong_turn_player_2_acts_on_player_1_turn():
    """Player 2 acting when it is player 1's turn must return NOT_YOUR_TURN."""
    err = _call(
        envelope=_envelope(actor_membership_id=PLAYER_2),
        current_turn=MinigameTurnSide.PLAYER_1,
    )
    assert isinstance(err, ActionError)
    assert err.code == "NOT_YOUR_TURN"
    assert "ليس دورك" in err.message_ar


def test_rejects_wrong_turn_player_1_acts_on_player_2_turn():
    """Player 1 acting when it is player 2's turn must return NOT_YOUR_TURN."""
    err = _call(
        envelope=_envelope(actor_membership_id=PLAYER_1),
        current_turn=MinigameTurnSide.PLAYER_2,
    )
    assert isinstance(err, ActionError)
    assert err.code == "NOT_YOUR_TURN"


# ── Solo game: turn check must be skipped ────────────────────────────────────

def test_solo_game_skips_turn_check_player_1_turn():
    """Solo game (player_2=None): player_1 acting with current_turn=PLAYER_1 passes."""
    result = validate_action_envelope(
        envelope=_envelope(actor_membership_id=PLAYER_1),
        session_phase=Phase.IN_PROGRESS,
        session_revision=5,
        current_turn=MinigameTurnSide.PLAYER_1,
        player_1_membership_id=PLAYER_1,
        player_2_membership_id=None,
    )
    assert result is None


def test_solo_game_skips_turn_check_player_2_turn_value():
    """Solo game (player_2=None): player_1 acting with current_turn=PLAYER_2 still passes.

    The turn side value is irrelevant for solo games — no check should occur.
    """
    result = validate_action_envelope(
        envelope=_envelope(actor_membership_id=PLAYER_1),
        session_phase=Phase.IN_PROGRESS,
        session_revision=5,
        current_turn=MinigameTurnSide.PLAYER_2,
        player_1_membership_id=PLAYER_1,
        player_2_membership_id=None,
    )
    assert result is None


def test_solo_game_skips_turn_check_none_current_turn():
    """Solo game (player_2=None): current_turn=None is also fine — turn is irrelevant."""
    result = validate_action_envelope(
        envelope=_envelope(actor_membership_id=PLAYER_1),
        session_phase=Phase.IN_PROGRESS,
        session_revision=5,
        current_turn=None,
        player_1_membership_id=PLAYER_1,
        player_2_membership_id=None,
    )
    assert result is None


def test_solo_game_still_rejects_non_participant():
    """Solo game: outsider acting must still fail NOT_PARTICIPANT."""
    err = validate_action_envelope(
        envelope=_envelope(actor_membership_id=OUTSIDER),
        session_phase=Phase.IN_PROGRESS,
        session_revision=5,
        current_turn=MinigameTurnSide.PLAYER_1,
        player_1_membership_id=PLAYER_1,
        player_2_membership_id=None,
    )
    assert err is not None
    assert err.code == "NOT_PARTICIPANT"


def test_solo_game_with_overtime_phase():
    """Solo game in OVERTIME phase with valid actor passes."""
    result = validate_action_envelope(
        envelope=_envelope(actor_membership_id=PLAYER_1),
        session_phase=Phase.OVERTIME,
        session_revision=0,
        current_turn=MinigameTurnSide.PLAYER_1,
        player_1_membership_id=PLAYER_1,
        player_2_membership_id=None,
    )
    assert result is None


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
    # OUTSIDER is not a participant, and PLAYER_2 turn is active
    err = _call(
        envelope=_envelope(actor_membership_id=OUTSIDER),
        current_turn=MinigameTurnSide.PLAYER_2,
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
