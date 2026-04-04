"""Mutaraha session helpers."""

from __future__ import annotations

from sqlalchemy import select

from app.modules.minigames.mutaraha.models import MutarahaWord


async def load_active_word_bank(session) -> list[str]:
    """Load all active words used to build authoritative session state."""
    result = await session.execute(
        select(MutarahaWord.word)
        .where(MutarahaWord.status == "active")
        .order_by(MutarahaWord.category, MutarahaWord.word)
    )
    return list(result.scalars().all())
