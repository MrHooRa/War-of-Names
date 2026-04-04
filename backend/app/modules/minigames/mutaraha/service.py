"""Mutaraha session helpers."""

from __future__ import annotations

import random
import uuid

from sqlalchemy import select

from app.modules.minigames.mutaraha.models import (
    MutarahaPlayerWordHistory,
    MutarahaWord,
)


def _coerce_uuid_set(raw_values) -> set[uuid.UUID]:
    values: set[uuid.UUID] = set()
    for raw in raw_values or []:
        try:
            values.add(raw if isinstance(raw, uuid.UUID) else uuid.UUID(str(raw)))
        except (TypeError, ValueError):
            continue
    return values


async def load_active_word_bank(
    session,
    *,
    categories_enabled: list[str] | None = None,
    disabled_word_ids: set[uuid.UUID] | None = None,
) -> list[MutarahaWord]:
    """Load active words filtered by the current content-governance settings."""
    stmt = select(MutarahaWord).where(MutarahaWord.status == "active")
    if categories_enabled:
        stmt = stmt.where(MutarahaWord.category.in_(categories_enabled))
    if disabled_word_ids:
        stmt = stmt.where(MutarahaWord.id.notin_(disabled_word_ids))
    stmt = stmt.order_by(MutarahaWord.category, MutarahaWord.word)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_recent_player_words(
    session,
    *,
    membership_id: uuid.UUID,
    recent_match_limit: int = 5,
) -> set[str]:
    """Return the set of words the player used across their most recent matches."""
    session_result = await session.execute(
        select(MutarahaPlayerWordHistory.session_id)
        .where(MutarahaPlayerWordHistory.membership_id == membership_id)
        .order_by(MutarahaPlayerWordHistory.used_at.desc())
    )
    session_ids: list[uuid.UUID] = []
    for (session_id,) in session_result.all():
        if session_id not in session_ids:
            session_ids.append(session_id)
        if len(session_ids) >= recent_match_limit:
            break
    if not session_ids:
        return set()

    words_result = await session.execute(
        select(MutarahaPlayerWordHistory.word).where(
            MutarahaPlayerWordHistory.membership_id == membership_id,
            MutarahaPlayerWordHistory.session_id.in_(session_ids),
        )
    )
    return set(words_result.scalars().all())


def _sample_offered_words(
    words: list[MutarahaWord],
    *,
    count: int,
    exclude_words: set[str] | None = None,
) -> list[str]:
    exclude_words = exclude_words or set()
    unique_words = list(dict.fromkeys(word.word for word in words if word.word and word.word not in exclude_words))
    if len(unique_words) <= count:
        return unique_words[:count]
    return random.sample(unique_words, count)


async def build_session_wording(
    session,
    *,
    settings: dict,
    participant_membership_ids: list[uuid.UUID],
) -> dict:
    """Build the authoritative word pool and offered words for both players."""
    categories_enabled = list(settings.get("mutaraha_categories_enabled") or [])
    disabled_word_ids = _coerce_uuid_set(settings.get("mutaraha_disabled_words"))
    recent_match_limit = int(settings.get("mutaraha_recent_match_word_limit", 5))
    words_per_draw = int(settings.get("mutaraha_words_per_draw", 10))

    available_words = await load_active_word_bank(
        session,
        categories_enabled=categories_enabled,
        disabled_word_ids=disabled_word_ids,
    )
    all_word_strings = [word.word for word in available_words]

    player_offers: dict[str, list[str]] = {}
    player_pools: dict[str, list[str]] = {}
    offered_union: set[str] = set()
    for slot_index, membership_id in enumerate(participant_membership_ids[:2]):
        recent_words = await get_recent_player_words(
            session,
            membership_id=membership_id,
            recent_match_limit=recent_match_limit,
        )
        eligible_words = [word for word in available_words if word.word not in recent_words]
        if len(eligible_words) < words_per_draw:
            eligible_words = available_words
        offered_words = _sample_offered_words(
            eligible_words,
            count=words_per_draw,
            exclude_words=offered_union,
        )
        if len(offered_words) < words_per_draw:
            offered_words = _sample_offered_words(
                available_words,
                count=words_per_draw,
                exclude_words=offered_union,
            )
        offered_union.update(offered_words)
        player_key = f"player_{slot_index + 1}"
        player_offers[player_key] = offered_words
        player_pools[player_key] = list(dict.fromkeys(word.word for word in eligible_words))

    return {
        "word_bank_words": all_word_strings,
        "offered_words_p1": player_offers.get("player_1", []),
        "offered_words_p2": player_offers.get("player_2", []),
        "word_pool_player_1": player_pools.get("player_1", all_word_strings),
        "word_pool_player_2": player_pools.get("player_2", all_word_strings),
    }


async def record_selected_words_history(
    session,
    *,
    session_id: uuid.UUID,
    game_state: dict,
    participants: list[dict],
) -> None:
    """Persist selected words so future sessions can avoid very recent repeats."""
    if not isinstance(game_state, dict):
        return
    existing = await session.execute(
        select(MutarahaPlayerWordHistory.id).where(
            MutarahaPlayerWordHistory.session_id == session_id
        )
    )
    if existing.first() is not None:
        return

    selected_words = {}
    for participant in participants:
        player_key = f"player_{participant['slot_index'] + 1}"
        selected_words[participant["membership_id"]] = list(
            (game_state.get(player_key) or {}).get("selected_words", [])
        )

    all_words = set()
    for words in selected_words.values():
        all_words.update(words)
    if not all_words:
        return

    result = await session.execute(
        select(MutarahaWord).where(MutarahaWord.word.in_(all_words))
    )
    words_by_text = {word.word: word for word in result.scalars().all()}

    for participant in participants:
        for word_text in selected_words.get(participant["membership_id"], []):
            word = words_by_text.get(word_text)
            if word is None:
                continue
            session.add(
                MutarahaPlayerWordHistory(
                    session_id=session_id,
                    membership_id=participant["membership_id"],
                    word_id=word.id,
                    word=word.word,
                    category=word.category,
                )
            )
