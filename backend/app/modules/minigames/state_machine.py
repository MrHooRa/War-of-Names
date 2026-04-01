"""Session state machine — defines valid phase transitions.

The transition map encodes BRD Section 6.3. Terminal states (COMPLETED,
CANCELLED, ABANDONED) have no outgoing transitions. Once reached, all
further actions are rejected.
"""

from app.core.enums import MinigameSessionPhase as Phase

# Valid transitions: from_phase → set of allowed to_phases
TRANSITION_MAP: dict[Phase, set[Phase]] = {
    Phase.CREATED: {Phase.WAITING, Phase.CANCELLED},
    Phase.WAITING: {Phase.READY, Phase.CANCELLED},
    Phase.READY: {Phase.IN_PROGRESS, Phase.CANCELLED},
    Phase.IN_PROGRESS: {
        Phase.COMPLETED,
        Phase.OVERTIME,
        Phase.PAUSED,
        Phase.ABANDONED,
        Phase.CANCELLED,
    },
    Phase.OVERTIME: {Phase.COMPLETED, Phase.ABANDONED},
    Phase.PAUSED: {Phase.IN_PROGRESS, Phase.ABANDONED},
    # Terminal states — no outgoing transitions
    Phase.COMPLETED: set(),
    Phase.CANCELLED: set(),
    Phase.ABANDONED: set(),
}

TERMINAL_PHASES: frozenset[Phase] = frozenset({
    Phase.COMPLETED,
    Phase.CANCELLED,
    Phase.ABANDONED,
})


def can_transition(from_phase: Phase, to_phase: Phase) -> bool:
    """Check whether a state transition is allowed."""
    return to_phase in TRANSITION_MAP.get(from_phase, set())


def validate_transition(from_phase: Phase, to_phase: Phase) -> None:
    """Raise ValueError if the transition is not allowed."""
    if not can_transition(from_phase, to_phase):
        raise ValueError(
            f"انتقال غير صالح: {from_phase.value} → {to_phase.value}"
        )


def is_terminal(phase: Phase) -> bool:
    """Check whether a phase is a terminal (final) state."""
    return phase in TERMINAL_PHASES
