"""Test مطارحة plugin — all 8 lifecycle hooks."""

import uuid

import pytest

from app.modules.minigames.mutaraha.plugin import MutarahaPlugin

PLAYER_1_ID = uuid.uuid4()
PLAYER_2_ID = uuid.uuid4()


@pytest.fixture
def plugin():
    return MutarahaPlugin()


@pytest.fixture
def initial_state(plugin):
    return plugin.init_session_state(
        {
            "offered_words_p1": [
                "كبسة", "ضب", "فيصل", "دلة", "عنيزة",
                "صقر", "سدر", "جريش", "تبوك", "نورة",
            ],
            "offered_words_p2": [
                "مندي", "ذيب", "خالد", "شماغ", "حائل",
                "نسر", "طلح", "هريسة", "أبها", "ريم",
            ],
            "turns_per_player": 12,
            "buy_in": 500,
            "player_1_membership_id": PLAYER_1_ID,
            "player_2_membership_id": PLAYER_2_ID,
        }
    )


@pytest.fixture
def battle_state(initial_state):
    """State with both players having selected words, in battle phase."""
    s = initial_state
    s["player_1"]["selected_words"] = ["كبسة", "ضب", "فيصل", "دلة", "عنيزة"]
    s["player_2"]["selected_words"] = ["مندي", "ذيب", "خالد", "شماغ", "حائل"]
    s["game_phase"] = "battle"
    return s


# ── validate_settings ────────────────────────────────────────


def test_validate_settings_valid(plugin):
    assert plugin.validate_settings({"minigame_buy_in": 500, "minigame_daily_limit": 2}) == []


def test_validate_settings_invalid_buy_in(plugin):
    errors = plugin.validate_settings({"minigame_buy_in": -1})
    assert len(errors) > 0


def test_validate_settings_invalid_daily(plugin):
    errors = plugin.validate_settings({"minigame_daily_limit": 0})
    assert len(errors) > 0


# ── init_session_state ───────────────────────────────────────


def test_init_state_structure(initial_state):
    assert initial_state["game_phase"] == "word_selection"
    assert len(initial_state["player_1"]["offered_words"]) == 10
    assert len(initial_state["player_2"]["offered_words"]) == 10
    assert initial_state["player_1"]["correct_guesses"] == 0
    assert initial_state["overtime_active"] is False
    assert initial_state["player_1"]["turns_taken"] == 0


def test_init_state_empty_selections(initial_state):
    assert initial_state["player_1"]["selected_words"] == []
    assert initial_state["player_2"]["selected_words"] == []


# ── validate_action ──────────────────────────────────────────


def test_validate_select_words_valid(plugin, initial_state):
    error = plugin.validate_action(
        {
            "type": "select_words",
            "payload": {
                "words": ["كبسة", "ضب", "فيصل", "دلة", "عنيزة"],
                "actor": "player_1",
            },
        },
        initial_state,
    )
    assert error is None


def test_validate_select_words_wrong_count(plugin, initial_state):
    error = plugin.validate_action(
        {"type": "select_words", "payload": {"words": ["a", "b"], "actor": "player_1"}},
        initial_state,
    )
    assert error is not None


def test_validate_select_words_rejects_non_offered_word(plugin, initial_state):
    error = plugin.validate_action(
        {
            "type": "select_words",
            "payload": {
                "words": ["كبسة", "ضب", "فيصل", "دلة", "كلمة-مفبركة"],
                "actor": "player_1",
            },
        },
        initial_state,
    )
    assert error is not None


def test_validate_tool_in_battle(plugin, battle_state):
    error = plugin.validate_action(
        {"type": "LETTER_CHECK", "payload": {"letter": "ك", "actor": "player_1"}},
        battle_state,
    )
    assert error is None


def test_validate_tool_not_in_battle(plugin, initial_state):
    error = plugin.validate_action(
        {"type": "LETTER_CHECK", "payload": {"letter": "ك", "actor": "player_1"}},
        initial_state,
    )
    assert error is not None


def test_validate_invalid_tool_type(plugin, battle_state):
    error = plugin.validate_action({"type": "INVALID_TOOL", "payload": {"actor": "player_1"}}, battle_state)
    assert error is not None


def test_validate_guess_missing_word(plugin, battle_state):
    error = plugin.validate_action(
        {"type": "GUESS", "payload": {"word_index": 0, "actor": "player_1"}},
        battle_state,
    )
    assert error is not None


def test_validate_redraw_once_only(plugin, initial_state):
    initial_state["player_1"]["used_redraw"] = True
    error = plugin.validate_action(
        {"type": "redraw", "payload": {"actor": "player_1"}},
        initial_state,
    )
    assert error is not None


def test_validate_redraw_rejected_after_selection(plugin, initial_state):
    initial_state["player_1"]["selected_words"] = ["كبسة"]
    error = plugin.validate_action(
        {"type": "redraw", "payload": {"actor": "player_1"}},
        initial_state,
    )
    assert error is not None


# ── apply_action ─────────────────────────────────────────────


def test_apply_select_words(plugin, initial_state):
    new_state, effects = plugin.apply_action(
        {
            "type": "select_words",
            "payload": {
                "words": ["كبسة", "ضب", "فيصل", "دلة", "عنيزة"],
                "actor": "player_1",
            },
        },
        initial_state,
    )
    assert new_state["player_1"]["selected_words"] == ["كبسة", "ضب", "فيصل", "دلة", "عنيزة"]


def test_apply_both_select_transitions_to_battle(plugin, initial_state):
    # Player 1 selects
    s1, _ = plugin.apply_action(
        {
            "type": "select_words",
            "payload": {
                "words": ["كبسة", "ضب", "فيصل", "دلة", "عنيزة"],
                "actor": "player_1",
            },
        },
        initial_state,
    )
    # Player 2 selects
    s2, effects = plugin.apply_action(
        {
            "type": "select_words",
            "payload": {
                "words": ["مندي", "ذيب", "خالد", "شماغ", "حائل"],
                "actor": "player_2",
            },
        },
        s1,
    )
    assert s2["game_phase"] == "battle"


def test_apply_letter_check(plugin, battle_state):
    new_state, effects = plugin.apply_action(
        {"type": "LETTER_CHECK", "payload": {"letter": "م", "actor": "player_1"}},
        battle_state,
    )
    assert len(new_state["revealed_info"]["player_1_known"]["letter_checks"]) == 1
    assert new_state["player_1"]["tool_costs"] == 20
    assert new_state["player_1"]["turns_taken"] == 1


def test_apply_guess_correct(plugin, battle_state):
    new_state, effects = plugin.apply_action(
        {"type": "GUESS", "payload": {"word_index": 0, "word": "مندي", "actor": "player_1"}},
        battle_state,
    )
    assert new_state["player_2"]["guessed_by_opponent"][0] is True
    assert new_state["player_1"]["correct_guesses"] == 1
    assert new_state["player_1"]["tool_costs"] == 0  # Correct guess is free


def test_apply_guess_wrong(plugin, battle_state):
    new_state, effects = plugin.apply_action(
        {"type": "GUESS", "payload": {"word_index": 0, "word": "خطأ", "actor": "player_1"}},
        battle_state,
    )
    assert new_state["player_2"]["guessed_by_opponent"][0] is False
    assert new_state["player_1"]["tool_costs"] == 50


def test_apply_action_uses_configured_tool_costs(plugin, battle_state):
    battle_state["settings"]["cost_letter_check"] = 33
    new_state, _ = plugin.apply_action(
        {"type": "LETTER_CHECK", "payload": {"letter": "م", "actor": "player_1"}},
        battle_state,
    )
    assert new_state["player_1"]["tool_costs"] == 33


# ── evaluate_terminal ────────────────────────────────────────


def test_terminal_knockout(plugin, battle_state):
    battle_state["player_1"]["correct_guesses"] = 5
    result = plugin.evaluate_terminal(battle_state)
    assert result is not None
    assert result["winner"] == "player_1"
    assert result["reason"] == "knockout"


def test_terminal_not_yet(plugin, battle_state):
    result = plugin.evaluate_terminal(battle_state)
    assert result is None


def test_terminal_by_score(plugin, battle_state):
    # Fill up all turns
    battle_state["player_1"]["turns_taken"] = 12
    battle_state["player_2"]["turns_taken"] = 12
    battle_state["player_1"]["correct_guesses"] = 3
    battle_state["player_2"]["correct_guesses"] = 2
    result = plugin.evaluate_terminal(battle_state)
    assert result is not None
    assert result["winner"] == "player_1"


def test_terminal_tied_goes_to_overtime(plugin, battle_state):
    battle_state["player_1"]["turns_taken"] = 12
    battle_state["player_2"]["turns_taken"] = 12
    battle_state["player_1"]["correct_guesses"] = 2
    battle_state["player_2"]["correct_guesses"] = 2
    battle_state["player_1"]["tool_costs"] = 100
    battle_state["player_2"]["tool_costs"] = 100
    result = plugin.evaluate_terminal(battle_state)
    assert result is None  # Triggers overtime


# ── evaluate_overtime ────────────────────────────────────────


def test_overtime_returns_config(plugin, battle_state):
    battle_state["player_1"]["turns_taken"] = 12
    battle_state["player_2"]["turns_taken"] = 12
    battle_state["player_1"]["correct_guesses"] = 2
    battle_state["player_2"]["correct_guesses"] = 2
    battle_state["player_1"]["tool_costs"] = 100
    battle_state["player_2"]["tool_costs"] = 100
    result = plugin.evaluate_overtime(battle_state)
    assert result is not None
    assert result["overtime_active"] is True
    assert result["game_phase"] == "overtime"


def test_no_double_overtime(plugin, battle_state):
    battle_state["overtime_active"] = True
    result = plugin.evaluate_overtime(battle_state)
    assert result is None


def test_resolve_selection_timeout_auto_picks_remaining_words(plugin, initial_state):
    initial_state["player_1"]["selected_words"] = ["كبسة", "ضب", "فيصل", "دلة", "عنيزة"]
    timeout_result = plugin.resolve_selection_timeout(initial_state)
    assert timeout_result is not None
    new_state = timeout_result["state"]
    assert len(new_state["player_2"]["selected_words"]) == 5
    assert new_state["game_phase"] == "battle"
    assert timeout_result["current_turn_index"] == 0


def test_resolve_turn_timeout_consumes_turn(plugin, battle_state):
    timeout_result = plugin.resolve_turn_timeout(battle_state, 0)
    assert timeout_result is not None
    new_state = timeout_result["state"]
    assert new_state["player_1"]["turns_taken"] == 1
    assert timeout_result["side_effects"][0]["type"] == "turn_skipped"


# ── compute_settlement ───────────────────────────────────────


def test_settlement_payout(plugin):
    result = plugin.compute_settlement({
        "buy_in": 500,
        "winner": "player_1",
        "loser": "player_2",
        "winner_membership_id": "uuid-1",
        "loser_membership_id": "uuid-2",
    })
    assert result["total_pool"] == 1000
    assert len(result["participant_results"]) == 2
    winner_r = next(r for r in result["participant_results"] if r["rank"] == 1)
    assert winner_r["payout"] == 1000
    assert winner_r["slot_index"] == 0
    assert winner_r["membership_id"] == "uuid-1"
    loser_r = next(r for r in result["participant_results"] if r["rank"] == 2)
    assert loser_r["payout"] == 0
    assert loser_r["slot_index"] == 1
    assert loser_r["membership_id"] == "uuid-2"


# ── build_public_view ────────────────────────────────────────


def test_public_view_hides_opponent_words(plugin, battle_state):
    view = plugin.build_public_view(battle_state, PLAYER_1_ID)
    # Player 2's words should be hidden (None)
    assert all(w is None for w in view["player_2"]["selected_words"])


def test_public_view_shows_own_words(plugin, battle_state):
    view = plugin.build_public_view(battle_state, PLAYER_1_ID)
    assert view["player_1"]["selected_words"] == ["كبسة", "ضب", "فيصل", "دلة", "عنيزة"]


def test_public_view_shows_guessed_opponent_words(plugin, battle_state):
    battle_state["player_2"]["guessed_by_opponent"][0] = True  # مندي guessed
    view = plugin.build_public_view(battle_state, PLAYER_1_ID)
    assert view["player_2"]["selected_words"][0] == "مندي"
    assert view["player_2"]["selected_words"][1] is None


def test_public_view_hides_opponent_tools(plugin, battle_state):
    battle_state["player_2"]["tools_used"] = [{"tool": "LETTER_CHECK", "cost": 20}]
    battle_state["player_2"]["tool_costs"] = 20
    view = plugin.build_public_view(battle_state, PLAYER_1_ID)
    assert view["player_2"]["tools_used"] == []
    assert view["player_2"]["tool_costs"] == 0


def test_public_view_hides_both_sides_for_unknown_viewer(plugin, battle_state):
    view = plugin.build_public_view(battle_state, uuid.uuid4())
    assert all(word is None for word in view["player_1"]["selected_words"])
    assert all(word is None for word in view["player_2"]["selected_words"])
