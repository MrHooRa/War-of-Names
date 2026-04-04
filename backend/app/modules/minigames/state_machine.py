"""Session state machine — defines valid phase transitions.

The transition map encodes BRD Section 6.3. Terminal states (COMPLETED,
CANCELLED, ABANDONED) have no outgoing transitions. Once reached, all
further actions are rejected.
"""

from app.core.enums import MinigameSessionPhase as Phase

PhaseLike = Phase | str


def _normalize_phase(phase: PhaseLike) -> Phase | None:
    """Convert enum-like input to a Phase member, if recognized."""
    if isinstance(phase, Phase):
        return phase
    try:
        return Phase(phase)
    except ValueError:
        return None


def _phase_label(phase: PhaseLike) -> str:
    """Render enum-like phase input safely in error messages."""
    normalized = _normalize_phase(phase)
    return normalized.value if normalized is not None else str(phase)


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
    Phase.OVERTIME: {Phase.COMPLETED, Phase.PAUSED, Phase.ABANDONED},
    # Both players can fail to reconnect, which cancels with refunds.
    Phase.PAUSED: {Phase.IN_PROGRESS, Phase.OVERTIME, Phase.ABANDONED, Phase.CANCELLED},
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


def can_transition(from_phase: PhaseLike, to_phase: PhaseLike) -> bool:
    """Check whether a state transition is allowed."""
    from_normalized = _normalize_phase(from_phase)
    to_normalized = _normalize_phase(to_phase)
    if from_normalized is None or to_normalized is None:
        return False
    return to_normalized in TRANSITION_MAP.get(from_normalized, set())


def validate_transition(from_phase: PhaseLike, to_phase: PhaseLike) -> None:
    """Raise ValueError if the transition is not allowed."""
    if not can_transition(from_phase, to_phase):
        raise ValueError(
            f"انتقال غير صالح: {_phase_label(from_phase)} → {_phase_label(to_phase)}"
        )


def is_terminal(phase: PhaseLike) -> bool:
    """Check whether a phase is a terminal (final) state."""
    normalized = _normalize_phase(phase)
    return normalized in TERMINAL_PHASES if normalized is not None else False
