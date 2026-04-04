"""Test مطارحة deduction tools."""

import pytest
from app.modules.minigames.mutaraha.tools import (
    ARABIC_ALPHABET,
    TOOL_COSTS,
    VALID_TOOL_TYPES,
    tool_letter_check,
    tool_word_length,
    tool_letter_eliminate,
    tool_first_letter,
    tool_narrow_down,
    tool_guess,
    get_tool_cost,
)


SAMPLE_WORDS = ["كبسة", "ضب", "فيصل", "دلة", "عنيزة"]
ALL_GUESSED = [True, True, True, True, True]
NONE_GUESSED = [False, False, False, False, False]
SOME_GUESSED = [True, False, True, False, False]


# ── LETTER_CHECK ─────────────────────────────────────────────

def test_letter_check_found():
    result = tool_letter_check(letter="ك", opponent_words=SAMPLE_WORDS)
    assert result["exists"] is True
    assert result["count"] >= 1


def test_letter_check_not_found():
    result = tool_letter_check(letter="ش", opponent_words=SAMPLE_WORDS)
    assert result["exists"] is False
    assert result["count"] == 0


def test_letter_check_multiple_words():
    # "ة" appears in كبسة, دلة, عنيزة = 3
    result = tool_letter_check(letter="ة", opponent_words=SAMPLE_WORDS)
    assert result["count"] == 3


# ── WORD_LENGTH ──────────────────────────────────────────────

def test_word_length_returns_valid():
    result = tool_word_length(opponent_words=SAMPLE_WORDS, guessed_mask=NONE_GUESSED)
    assert result is not None
    assert 0 <= result["word_index"] <= 4
    assert result["length"] == len(SAMPLE_WORDS[result["word_index"]])


def test_word_length_skips_guessed():
    # Only index 1 (ضب) is unguessed
    mask = [True, False, True, True, True]
    result = tool_word_length(opponent_words=SAMPLE_WORDS, guessed_mask=mask)
    assert result is not None
    assert result["word_index"] == 1
    assert result["length"] == len("ضب")


def test_word_length_all_guessed_returns_none():
    result = tool_word_length(opponent_words=SAMPLE_WORDS, guessed_mask=ALL_GUESSED)
    assert result is None


# ── LETTER_ELIMINATE ─────────────────────────────────────────

def test_letter_eliminate_returns_3():
    result = tool_letter_eliminate(opponent_words=SAMPLE_WORDS, already_eliminated=[])
    assert len(result["eliminated"]) <= 3
    # None of the eliminated should be in any word
    used = set()
    for w in SAMPLE_WORDS:
        used.update(w)
    for letter in result["eliminated"]:
        assert letter not in used


def test_letter_eliminate_respects_already_eliminated():
    result1 = tool_letter_eliminate(opponent_words=SAMPLE_WORDS, already_eliminated=[])
    result2 = tool_letter_eliminate(
        opponent_words=SAMPLE_WORDS,
        already_eliminated=result1["eliminated"],
    )
    # No overlap between the two sets
    assert set(result1["eliminated"]).isdisjoint(set(result2["eliminated"]))


# ── FIRST_LETTER ─────────────────────────────────────────────

def test_first_letter_reveals():
    result = tool_first_letter(word_index=0, opponent_words=SAMPLE_WORDS, guessed_mask=NONE_GUESSED)
    assert result is not None
    assert result["letter"] == "ك"  # كبسة
    assert result["word_index"] == 0


def test_first_letter_guessed_returns_none():
    mask = [True, False, False, False, False]
    result = tool_first_letter(word_index=0, opponent_words=SAMPLE_WORDS, guessed_mask=mask)
    assert result is None


def test_first_letter_invalid_index():
    result = tool_first_letter(word_index=99, opponent_words=SAMPLE_WORDS, guessed_mask=NONE_GUESSED)
    assert result is None


# ── NARROW_DOWN ──────────────────────────────────────────────

def test_narrow_down_returns_3_options():
    bank = ["كبسة", "جريش", "مرقوق", "سليق", "مندي", "صالونة"]
    result = tool_narrow_down(
        word_index=0, opponent_words=SAMPLE_WORDS,
        guessed_mask=NONE_GUESSED, all_bank_words=bank,
    )
    assert result is not None
    assert len(result["options"]) == 3
    assert "كبسة" in result["options"]


def test_narrow_down_guessed_returns_none():
    bank = ["كبسة", "جريش", "مرقوق"]
    result = tool_narrow_down(
        word_index=0, opponent_words=SAMPLE_WORDS,
        guessed_mask=[True, False, False, False, False],
        all_bank_words=bank,
    )
    assert result is None


def test_narrow_down_insufficient_bank_returns_none():
    # Bank only has opponent's words — no valid decoys
    result = tool_narrow_down(
        word_index=0, opponent_words=SAMPLE_WORDS,
        guessed_mask=NONE_GUESSED, all_bank_words=SAMPLE_WORDS,
    )
    assert result is None


# ── GUESS ────────────────────────────────────────────────────

def test_guess_correct():
    result = tool_guess(
        word_index=0, guessed_word="كبسة",
        opponent_words=SAMPLE_WORDS, guessed_mask=NONE_GUESSED,
    )
    assert result["correct"] is True
    assert result["actual_word"] == "كبسة"


def test_guess_wrong():
    result = tool_guess(
        word_index=0, guessed_word="جريش",
        opponent_words=SAMPLE_WORDS, guessed_mask=NONE_GUESSED,
    )
    assert result["correct"] is False
    assert result["actual_word"] is None


def test_guess_already_guessed():
    result = tool_guess(
        word_index=0, guessed_word="كبسة",
        opponent_words=SAMPLE_WORDS, guessed_mask=[True, False, False, False, False],
    )
    assert result["correct"] is False


def test_guess_invalid_index():
    result = tool_guess(
        word_index=99, guessed_word="test",
        opponent_words=SAMPLE_WORDS, guessed_mask=NONE_GUESSED,
    )
    assert result["correct"] is False


# ── TOOL COSTS ───────────────────────────────────────────────

def test_cost_letter_check():
    assert get_tool_cost("LETTER_CHECK") == 20


def test_cost_guess_correct_is_free():
    assert get_tool_cost("GUESS", correct=True) == 0


def test_cost_guess_wrong():
    assert get_tool_cost("GUESS", correct=False) == 50


def test_cost_overtime_doubles():
    assert get_tool_cost("LETTER_CHECK", overtime_multiplier=2) == 40
    assert get_tool_cost("NARROW_DOWN", overtime_multiplier=2) == 120


def test_valid_tool_types():
    assert "LETTER_CHECK" in VALID_TOOL_TYPES
    assert "GUESS" in VALID_TOOL_TYPES
    assert len(VALID_TOOL_TYPES) == 6


def test_arabic_alphabet_length():
    assert len(ARABIC_ALPHABET) == 28
