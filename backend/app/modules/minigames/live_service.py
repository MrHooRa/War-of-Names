"""Live session helpers for minigame creation, start, overtime, and settlement."""

from __future__ import annotations

import copy
import uuid
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import LedgerEntryType, MinigameSessionPhase as Phase
from app.core.utils import now_riyadh_naive
from app.modules.competitions.models import Membership
from app.modules.minigames import (
    economy,
    leaderboard_service,
    policy_service,
    settlement_service,
    session_service,
)
from app.modules.minigames.models import MinigameSession
from app.modules.scoring.models import LedgerEntry
from app.modules.minigames.runtime_state import (
    resolve_state_timer_duration_ms,
    stamp_phase_deadlines,
)

CHALLENGE_EXPIRY_SECONDS = 300


def _player_key_for_slot(slot_index: int) -> str | None:
    if 0 <= slot_index < 8:
        return f"player_{slot_index + 1}"
    return None


def _coerce_uuid(value) -> uuid.UUID | None:
    if isinstance(value, uuid.UUID):
        return value
    if isinstance(value, str) and value:
        return uuid.UUID(value)
    return None


def _alias_for_membership(membership: Membership | None) -> str:
    if membership is None:
        return "مجهول"
    return membership.current_alias or "مجهول"


async def get_memberships_by_ids(
    session: AsyncSession,
    membership_ids: list[uuid.UUID],
) -> dict[uuid.UUID, Membership]:
    """Load memberships keyed by id."""
    unique_ids = list(dict.fromkeys(membership_ids))
    if not unique_ids:
        return {}

    result = await session.execute(
        select(Membership).where(Membership.id.in_(unique_ids))
    )
    return {
        membership.id: membership
        for membership in result.scalars().all()
    }


async def validate_match_candidate(
    session: AsyncSession,
    *,
    membership: Membership,
    game_type: str,
    plugin_status: str,
    competition_id: uuid.UUID,
    buy_in_amount: int,
    daily_cap: int,
    same_opponent_limit: int,
    opponent_membership_ids: list[uuid.UUID],
    cycle_id: uuid.UUID | None = None,
) -> str | None:
    """Return the first session-creation/policy error for a participant."""
    creation_errors = session_service.validate_session_creation(
        game_type_id=game_type,
        plugin_exists=True,
        plugin_status=plugin_status,
        player_balance=membership.current_balance,
        buy_in_amount=buy_in_amount,
        is_bankrupt=membership.is_bankrupt,
    )
    if creation_errors:
        return creation_errors[0]

    matches_today = await policy_service.count_player_matches_today(
        session,
        membership_id=membership.id,
        game_type=game_type,
        competition_id=competition_id,
    )

    matches_with_opponent = 0
    if cycle_id is not None:
        opponent_counts: list[int] = []
        for opponent_membership_id in opponent_membership_ids:
            if opponent_membership_id == membership.id:
                continue
            opponent_counts.append(
                await policy_service.count_opponent_matches_this_cycle(
                    session,
                    membership_id=membership.id,
                    opponent_membership_id=opponent_membership_id,
                    game_type=game_type,
                    competition_id=competition_id,
                    cycle_id=cycle_id,
                )
            )
        matches_with_opponent = max(opponent_counts, default=0)

    blocks = policy_service.run_all_checks(
        matches_today=matches_today,
        daily_cap=daily_cap,
        matches_with_opponent_this_cycle=matches_with_opponent,
        same_opponent_limit=same_opponent_limit,
        player_balance=membership.current_balance,
        buy_in_amount=buy_in_amount,
        is_bankrupt=membership.is_bankrupt,
    )
    if blocks:
        return blocks[0].message_ar
    return None


async def get_session_participants_with_balances(
    session: AsyncSession,
    session_id: uuid.UUID,
) -> list[dict]:
    """Return session participants with balance and alias metadata."""
    participants = await session_service.get_session_participants(session, session_id)
    memberships = await get_memberships_by_ids(
        session,
        [participant["membership_id"] for participant in participants],
    )
    enriched: list[dict] = []
    for participant in participants:
        membership = memberships.get(participant["membership_id"])
        enriched.append(
            {
                **participant,
                "balance": membership.current_balance if membership is not None else 0,
                "alias": _alias_for_membership(membership),
            }
        )
    return enriched


def build_challenge_expiry(*, created_at=None, timeout_seconds: int = CHALLENGE_EXPIRY_SECONDS) -> str:
    """Return an ISO timestamp for when a challenge invitation expires."""
    base = created_at or now_riyadh_naive()
    return (base + timedelta(seconds=timeout_seconds)).isoformat()


async def initialize_session_state(
    session: AsyncSession,
    *,
    mg_session: MinigameSession,
    plugin,
    participants: list[dict] | None = None,
) -> dict:
    """Ensure a session has an initialized game_state and return it."""
    if isinstance(mg_session.game_state, dict) and mg_session.game_state:
        return mg_session.game_state

    participants = participants or await session_service.get_session_participants(
        session,
        mg_session.id,
    )
    init_config = {
        "session_id": str(mg_session.id),
        "competition_id": str(mg_session.competition_id),
        "game_type": mg_session.game_type,
        "participants": [
            {
                "membership_id": str(participant["membership_id"]),
                "slot_index": participant["slot_index"],
            }
            for participant in participants
        ],
        "buy_in": mg_session.buy_in_amount,
        "settings": dict(mg_session.settings_snapshot or {}),
    }
    if participants:
        init_config["player_1_membership_id"] = str(participants[0]["membership_id"])
    if len(participants) > 1:
        init_config["player_2_membership_id"] = str(participants[1]["membership_id"])

    if mg_session.game_type == "mutaraha":
        from app.modules.minigames.mutaraha.service import build_session_wording  # noqa: PLC0415

        init_config.update(
            await build_session_wording(
                session,
                settings=init_config["settings"],
                participant_membership_ids=[
                    participant["membership_id"] for participant in participants
                ],
            )
        )

    initial_state = plugin.init_session_state(init_config)
    if not isinstance(initial_state, dict):
        raise ValueError("الحالة الأولية للعبة غير صالحة")
    timer_duration_ms = resolve_state_timer_duration_ms(
        initial_state,
        fallback_ms=getattr(mg_session, "turn_duration_ms", None),
    )
    if timer_duration_ms is not None:
        initial_state = stamp_phase_deadlines(
            initial_state,
            started_at=now_riyadh_naive(),
            duration_ms=timer_duration_ms,
        )
        mg_session.turn_duration_ms = timer_duration_ms
    mg_session.game_state = initial_state
    await session.flush()
    return initial_state


async def ensure_buy_in_debited(
    session: AsyncSession,
    *,
    mg_session: MinigameSession,
    participants: list[dict] | None = None,
) -> list[dict]:
    """Debit buy-in once per participant and refresh balances."""
    participants = participants or await get_session_participants_with_balances(
        session,
        mg_session.id,
    )

    existing_result = await session.execute(
        select(LedgerEntry).where(
            LedgerEntry.source_type == "minigame_session",
            LedgerEntry.source_id == mg_session.id,
            LedgerEntry.entry_type == LedgerEntryType.MINIGAME_BUY_IN,
        )
    )
    existing_entries = list(existing_result.scalars().all())
    if len(existing_entries) >= len(participants):
        return await get_session_participants_with_balances(session, mg_session.id)

    memberships = await get_memberships_by_ids(
        session,
        [participant["membership_id"] for participant in participants],
    )
    for participant in participants:
        membership = memberships.get(participant["membership_id"])
        if membership is None:
            continue
        entry = economy.create_buy_in_entry(
            membership_id=membership.id,
            competition_id=mg_session.competition_id,
            session_id=mg_session.id,
            amount=mg_session.buy_in_amount,
            balance_before=membership.current_balance,
            season_id=mg_session.season_id,
            cycle_id=mg_session.cycle_id,
        )
        session.add(entry)
        membership.current_balance = entry.balance_after

    await session.flush()
    return await get_session_participants_with_balances(session, mg_session.id)


def _session_start_path(current_phase: Phase | str) -> list[Phase]:
    try:
        phase = current_phase if isinstance(current_phase, Phase) else Phase(current_phase)
    except ValueError:
        phase = current_phase

    paths = {
        Phase.CREATED: [Phase.WAITING, Phase.READY, Phase.IN_PROGRESS],
        Phase.WAITING: [Phase.READY, Phase.IN_PROGRESS],
        Phase.READY: [Phase.IN_PROGRESS],
        Phase.PAUSED: [Phase.IN_PROGRESS],
    }
    return list(paths.get(phase, []))


async def start_session(
    session: AsyncSession,
    *,
    mg_session: MinigameSession,
    plugin,
    participants: list[dict] | None = None,
    actor_type: str = "system",
    actor_membership_id: uuid.UUID | None = None,
) -> tuple[MinigameSession, list[dict]]:
    """Initialize the game, debit buy-ins, and transition to IN_PROGRESS."""
    participants = participants or await get_session_participants_with_balances(
        session,
        mg_session.id,
    )
    await initialize_session_state(
        session,
        mg_session=mg_session,
        plugin=plugin,
        participants=participants,
    )
    participants = await ensure_buy_in_debited(
        session,
        mg_session=mg_session,
        participants=participants,
    )

    selection_phase = isinstance(mg_session.game_state, dict) and mg_session.game_state.get("game_phase") == "word_selection"
    initial_timer_ms = resolve_state_timer_duration_ms(
        mg_session.game_state,
        fallback_ms=getattr(mg_session, "turn_duration_ms", None),
    )
    for phase in _session_start_path(mg_session.phase):
        extra_updates = None
        if phase == Phase.IN_PROGRESS and selection_phase:
            extra_updates = {
                "current_turn_index": None,
            }
            if initial_timer_ms is not None:
                extra_updates["turn_duration_ms"] = initial_timer_ms
        transitioned = await session_service.transition_session(
            session,
            session_id=mg_session.id,
            expected_revision=mg_session.revision,
            target_phase=phase,
            actor_type=actor_type,
            actor_membership_id=actor_membership_id,
            extra_updates=extra_updates,
        )
        if transitioned is None:
            raise RuntimeError("فشل بدء الجلسة بسبب تعارض متزامن")
        mg_session = transitioned

    if initial_timer_ms is not None:
        mg_session.game_state = stamp_phase_deadlines(
            mg_session.game_state,
            started_at=mg_session.turn_started_at or now_riyadh_naive(),
            duration_ms=initial_timer_ms,
        )
        await session.flush()

    return mg_session, participants


async def enter_overtime(
    session: AsyncSession,
    *,
    mg_session: MinigameSession,
    plugin,
    actor_type: str = "system",
    actor_membership_id: uuid.UUID | None = None,
) -> MinigameSession | None:
    """Transition an active session into overtime using plugin-provided state."""
    overtime_result = plugin.evaluate_overtime(mg_session.game_state)
    if not overtime_result:
        return None

    new_state = copy.deepcopy(mg_session.game_state)
    new_state.update(overtime_result)
    overtime_duration_ms = resolve_state_timer_duration_ms(
        new_state,
        fallback_ms=getattr(mg_session, "turn_duration_ms", None),
    )
    if overtime_duration_ms is not None:
        new_state = stamp_phase_deadlines(
            new_state,
            started_at=now_riyadh_naive(),
            duration_ms=overtime_duration_ms,
        )
    transitioned = await session_service.transition_session(
        session,
        session_id=mg_session.id,
        expected_revision=mg_session.revision,
        target_phase=Phase.OVERTIME,
        actor_type=actor_type,
        actor_membership_id=actor_membership_id,
        extra_updates={
            "game_state": new_state,
            "turn_duration_ms": overtime_duration_ms,
        },
        payload={"overtime": overtime_result},
        result={"game_phase": new_state.get("game_phase")},
    )
    if transitioned is None:
        raise RuntimeError("فشل تفعيل الوقت الإضافي بسبب تعارض متزامن")

    transitioned.game_state = new_state
    return transitioned


def build_forfeit_terminal_result(
    *,
    participants: list[dict],
    winner_membership_id: uuid.UUID,
    loser_membership_id: uuid.UUID | None = None,
    reason: str = "grace_timeout",
    buy_in_amount: int = 0,
) -> dict:
    """Build a 1v1-compatible terminal result for disconnect forfeits."""
    winner = next(
        (
            participant
            for participant in participants
            if participant["membership_id"] == winner_membership_id
        ),
        None,
    )
    if winner is None:
        raise ValueError("الفائز غير مشارك في الجلسة")

    if loser_membership_id is None:
        loser = next(
            (
                participant
                for participant in participants
                if participant["membership_id"] != winner_membership_id
            ),
            None,
        )
        loser_membership_id = loser["membership_id"] if loser is not None else None

    winner_key = _player_key_for_slot(winner["slot_index"]) or "player_1"
    loser_key = None
    if loser_membership_id is not None:
        loser = next(
            (
                participant
                for participant in participants
                if participant["membership_id"] == loser_membership_id
            ),
            None,
        )
        if loser is not None:
            loser_key = _player_key_for_slot(loser["slot_index"])

    return {
        "winner": winner_key,
        "loser": loser_key,
        "winner_membership_id": str(winner_membership_id),
        "loser_membership_id": str(loser_membership_id) if loser_membership_id else None,
        "reason": reason,
        "buy_in": buy_in_amount,
    }


def _tools_used_by_membership(state: dict, participants: list[dict]) -> dict[uuid.UUID, int]:
    counts: dict[uuid.UUID, int] = {}
    for participant in participants:
        player_key = _player_key_for_slot(participant["slot_index"])
        player_state = state.get(player_key or "", {})
        counts[participant["membership_id"]] = len(player_state.get("tools_used", []))
    return counts


def _duration_seconds(mg_session: MinigameSession) -> float:
    if not mg_session.started_at or not mg_session.completed_at:
        return 0.0
    return max(0.0, (mg_session.completed_at - mg_session.started_at).total_seconds())


def build_recent_result(
    *,
    mg_session: MinigameSession,
    participant_results: list[dict],
    participants: list[dict],
    terminal_reason: str | None,
) -> dict:
    """Build a compact lobby-friendly recent result payload."""
    alias_by_mid = {
        str(participant["membership_id"]): participant.get("alias") or "مجهول"
        for participant in participants
    }
    winner = next(
        (result for result in participant_results if result.get("rank") == 1),
        None,
    )
    winner_membership_id = None
    if winner is not None:
        raw_winner_id = winner.get("membership_id")
        winner_membership_id = str(raw_winner_id) if raw_winner_id is not None else None
    return {
        "session_id": str(mg_session.id),
        "game_type": mg_session.game_type,
        "winner_membership_id": winner_membership_id,
        "winner_alias": alias_by_mid.get(winner_membership_id) if winner_membership_id else None,
        "winner_payout": winner.get("payout", 0) if winner else 0,
        "terminal_reason": terminal_reason,
        "completed_at": mg_session.completed_at.isoformat() if mg_session.completed_at else None,
    }


async def finalize_session(
    session: AsyncSession,
    *,
    mg_session: MinigameSession,
    plugin,
    participants: list[dict] | None,
    terminal_result: dict | None,
    target_phase: Phase,
    terminal_reason: str | None = None,
    actor_type: str = "system",
    actor_membership_id: uuid.UUID | None = None,
) -> dict:
    """Transition to a terminal phase, settle, and update the leaderboard."""
    participants = participants or await get_session_participants_with_balances(
        session,
        mg_session.id,
    )
    terminal_reason = terminal_reason or (terminal_result or {}).get("reason")

    winner_slot_index = None
    winner_membership_id = _coerce_uuid((terminal_result or {}).get("winner_membership_id"))
    if winner_membership_id is not None:
        winner_slot_index = next(
            (
                participant["slot_index"]
                for participant in participants
                if participant["membership_id"] == winner_membership_id
            ),
            None,
        )

    transitioned = await session_service.transition_session(
        session,
        session_id=mg_session.id,
        expected_revision=mg_session.revision,
        target_phase=target_phase,
        terminal_reason=terminal_reason,
        winner_slot_index=winner_slot_index,
        actor_type=actor_type,
        actor_membership_id=actor_membership_id,
    )
    if transitioned is None:
        raise RuntimeError("فشل إنهاء الجلسة بسبب تعارض متزامن")
    mg_session = transitioned

    stats_update: dict[str, dict] = {}
    if target_phase == Phase.CANCELLED:
        settlement = await settlement_service.execute_cancel_settlement(
            session,
            mg_session=mg_session,
            participants=participants,
        )
        participant_results = settlement.participant_results or []
    else:
        settlement_input = dict(terminal_result or {})
        settlement_input.setdefault("buy_in", mg_session.buy_in_amount)
        plugin_settlement = plugin.compute_settlement(settlement_input)
        settlement = await settlement_service.execute_settlement(
            session,
            mg_session=mg_session,
            participants=participants,
            plugin_settlement=plugin_settlement,
        )
        participant_results = plugin_settlement.get("participant_results", [])
        tool_counts = _tools_used_by_membership(mg_session.game_state, participants)
        duration_sec = _duration_seconds(mg_session)
        for result in participant_results:
            membership_id = _coerce_uuid(result.get("membership_id"))
            if membership_id is None:
                continue
            await leaderboard_service.update_leaderboard(
                session,
                game_type=mg_session.game_type,
                competition_id=mg_session.competition_id,
                membership_id=membership_id,
                is_win=result.get("rank") == 1,
                tools_used=tool_counts.get(membership_id, 0),
                duration_sec=duration_sec,
            )
            stats_update[str(membership_id)] = {
                "rank": result.get("rank", 0),
                "payout": result.get("payout", 0),
                "tools_used": tool_counts.get(membership_id, 0),
                "duration_sec": duration_sec,
            }

        if mg_session.game_type == "mutaraha":
            from app.modules.minigames.mutaraha.service import record_selected_words_history  # noqa: PLC0415

            await record_selected_words_history(
                session,
                session_id=mg_session.id,
                game_state=mg_session.game_state,
                participants=participants,
            )

    return {
        "session": mg_session,
        "settlement": settlement,
        "participant_results": participant_results,
        "stats_update": stats_update,
        "lobby_result": build_recent_result(
            mg_session=mg_session,
            participant_results=participant_results,
            participants=participants,
            terminal_reason=terminal_reason,
        ),
    }
