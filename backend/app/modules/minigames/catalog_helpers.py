"""Pure helper functions for catalog aggregation.

All functions in this module are stateless, synchronous, and have zero
database or async dependencies. They encode the business rules from
BRD §9.1, §15.4, and §8.1.1.
"""

from __future__ import annotations

# BRD §8.1.1 — leaderboard needs ≥10 matches before its average is trusted
LEADERBOARD_STATS_MIN_MATCHES = 10

# Kill-switch levels that block new session creation (BRD §16.3)
KILL_SWITCH_BLOCKING_LEVELS = frozenset({"hard", "emergency"})

# Availability modes that hide the card from players (BRD §10.1.1)
CARD_LOCKED_AVAILABILITY_MODES = frozenset({"maintenance", "coming_soon", "hidden"})


# ─── Player count label (BRD §9.1) ─────────────────────────────────

def build_player_count_label(min_players: int, max_players: int) -> str:
    """Return the human-readable player-count badge text.

    BRD §9.1 rules:
        min == max == 1                → "منفرد"
        min == max == 2                → "1v1"
        min == max (other)             → "{N} لاعبين"
        min != max                     → "{min}-{max} لاعبين"
        invalid (min>max or <=0)       → "" (caller must hide CTA)
    """
    if min_players <= 0 or max_players <= 0:
        return ""
    if min_players > max_players:
        return ""

    if min_players == max_players:
        if min_players == 1:
            return "منفرد"
        if min_players == 2:
            return "1v1"
        return f"{min_players} لاعبين"

    return f"{min_players}-{max_players} لاعبين"


# ─── Card status resolution (BRD §15.4) ────────────────────────────

def resolve_card_status(
    *,
    availability_mode: str,
    kill_switch_level: str,
    my_active_session_id: str | None,
    in_queue: bool,
    player_balance: int,
    buy_in_amount: int,
    is_bankrupt: bool,
) -> tuple[str, str | None]:
    """Determine the status and optional Arabic reason for a game card.

    Returns (status, availability_reason). BRD §15.4 priority order:
        1. in_match    → player has active session, always wins
        2. queued      → player in matchmaking queue
        3. insufficient_balance → bankrupt or balance < buy_in
        4. maintenance → hard/emergency kill switch OR availability_mode=maintenance
        5. coming_soon → availability_mode=coming_soon
        6. hidden      → availability_mode=hidden (caller filters out)
        7. playable    → default

    Note: insufficient_balance takes priority over maintenance/coming_soon
    because the kill switch doesn't help a player who can't afford anyway.
    """
    # Priority 1: active session
    if my_active_session_id is not None:
        return ("in_match", None)

    # Priority 2: queued
    if in_queue:
        return ("queued", None)

    # Priority 3: insufficient balance / bankrupt
    if is_bankrupt or player_balance < buy_in_amount:
        return (
            "insufficient_balance",
            f"رصيد غير كافٍ — تحتاج {buy_in_amount} نقطة للدخول",
        )

    # Priority 4: maintenance (kill switch or config)
    if kill_switch_level in KILL_SWITCH_BLOCKING_LEVELS:
        return ("maintenance", "صيانة مؤقتة — نرجع قريباً")
    if availability_mode == "maintenance":
        return ("maintenance", "صيانة مؤقتة — نرجع قريباً")

    # Priority 5: coming soon
    if availability_mode == "coming_soon":
        return ("coming_soon", None)

    # Priority 6: hidden (surface filters this out but we still return it)
    if availability_mode == "hidden":
        return ("hidden", None)

    # Default
    return ("playable", None)


# ─── Estimated duration resolution (BRD §8.1.1) ─────────────────────

def resolve_estimated_duration(
    *,
    leaderboard_avg_sec: float | None,
    leaderboard_match_count: int,
    config_duration_sec: int | None,
) -> tuple[int | None, str | None]:
    """Return (duration_sec, source) using the priority chain in BRD §8.1.1.

    Priority:
        1. leaderboard stats — if avg is set AND match_count >= 10
        2. catalog config    — if configured and positive
        3. null              — no estimate available

    Source strings: "stats", "config", or None.
    """
    if (
        leaderboard_avg_sec is not None
        and leaderboard_avg_sec > 0
        and leaderboard_match_count >= LEADERBOARD_STATS_MIN_MATCHES
    ):
        return (int(leaderboard_avg_sec), "stats")

    if config_duration_sec is not None and config_duration_sec > 0:
        return (config_duration_sec, "config")

    return (None, None)
