"""مطارحة deduction tools — pure functions computing tool results.

All tools receive the opponent's hidden words and game state,
and return a result dict. No DB, no async — fully unit-testable.
"""

import random
from typing import Any

# Arabic alphabet (28 letters)
ARABIC_ALPHABET = list("ابتثجحخدذرزسشصضطظعغفقكلمنهوي")

# Tool costs (display-only, subtracted from displayed net profit)
TOOL_COSTS = {
    "LETTER_CHECK": 20,
    "WORD_LENGTH": 20,
    "LETTER_ELIMINATE": 40,
    "FIRST_LETTER": 50,
    "NARROW_DOWN": 60,
    "GUESS_WRONG": 50,
    "GUESS_CORRECT": 0,
}

VALID_TOOL_TYPES = {"LETTER_CHECK", "WORD_LENGTH", "LETTER_ELIMINATE", "FIRST_LETTER", "NARROW_DOWN", "GUESS"}


def tool_letter_check(
    *,
    letter: str,
    opponent_words: list[str],
) -> dict:
    """Check if a letter appears in any of opponent's words.

    Returns: {"letter": str, "exists": bool, "count": int}
    count = number of words containing the letter (searches ALL 5, including guessed)
    """
    count = sum(1 for w in opponent_words if letter in w)
    return {"letter": letter, "exists": count > 0, "count": count}


def tool_word_length(
    *,
    opponent_words: list[str],
    guessed_mask: list[bool],
) -> dict | None:
    """Reveal length of a random unguessed word.

    Returns: {"word_index": int, "length": int} or None if all guessed
    """
    unrevealed = [i for i, g in enumerate(guessed_mask) if not g]
    if not unrevealed:
        return None
    idx = random.choice(unrevealed)
    return {"word_index": idx, "length": len(opponent_words[idx])}


def tool_letter_eliminate(
    *,
    opponent_words: list[str],
    already_eliminated: list[str],
) -> dict:
    """Remove 3 letters from the alphabet that DON'T appear in any opponent word.

    Returns: {"eliminated": list[str]} (3 letters, or fewer if not enough safe letters)
    """
    # Collect all letters used in opponent's words
    used_letters = set()
    for word in opponent_words:
        used_letters.update(word)

    # Find letters NOT used and NOT already eliminated
    safe_to_eliminate = [
        l for l in ARABIC_ALPHABET
        if l not in used_letters and l not in already_eliminated
    ]

    # Pick up to 3
    count = min(3, len(safe_to_eliminate))
    eliminated = random.sample(safe_to_eliminate, count) if count > 0 else []
    return {"eliminated": eliminated}


def tool_first_letter(
    *,
    word_index: int,
    opponent_words: list[str],
    guessed_mask: list[bool],
) -> dict | None:
    """Reveal the first letter of a specific unguessed word.

    Returns: {"word_index": int, "letter": str} or None if already guessed
    """
    if word_index < 0 or word_index >= len(opponent_words):
        return None
    if guessed_mask[word_index]:
        return None
    word = opponent_words[word_index]
    return {"word_index": word_index, "letter": word[0] if word else ""}


def tool_narrow_down(
    *,
    word_index: int,
    opponent_words: list[str],
    guessed_mask: list[bool],
    all_bank_words: list[str],
) -> dict | None:
    """Show 3 options: the real word + 2 decoys.

    Decoys are from the same category/length when possible.
    Returns: {"word_index": int, "options": list[str]} or None if unavailable
    """
    if word_index < 0 or word_index >= len(opponent_words):
        return None
    if guessed_mask[word_index]:
        return None

    real_word = opponent_words[word_index]
    real_len = len(real_word)

    # Find decoy candidates: same length, not the real word, not in opponent's words
    opponent_set = set(opponent_words)
    candidates = [
        w for w in all_bank_words
        if len(w) == real_len and w != real_word and w not in opponent_set
    ]

    if len(candidates) < 2:
        # Fallback: any word not in opponent's list
        candidates = [
            w for w in all_bank_words
            if w != real_word and w not in opponent_set
        ]

    if len(candidates) < 2:
        return None  # Tool unavailable

    decoys = random.sample(candidates, 2)
    options = [real_word] + decoys
    random.shuffle(options)
    return {"word_index": word_index, "options": options}


def tool_guess(
    *,
    word_index: int,
    guessed_word: str,
    opponent_words: list[str],
    guessed_mask: list[bool],
) -> dict:
    """Guess a specific word at a position.

    Returns: {"word_index": int, "guessed_word": str, "correct": bool, "actual_word": str | None}
    actual_word is only included if correct (to reveal it)
    """
    if word_index < 0 or word_index >= len(opponent_words):
        return {"word_index": word_index, "guessed_word": guessed_word, "correct": False, "actual_word": None}

    if guessed_mask[word_index]:
        # Already guessed — treat as wrong (wasted turn)
        return {"word_index": word_index, "guessed_word": guessed_word, "correct": False, "actual_word": None}

    actual = opponent_words[word_index]
    correct = guessed_word.strip() == actual.strip()

    return {
        "word_index": word_index,
        "guessed_word": guessed_word,
        "correct": correct,
        "actual_word": actual if correct else None,
    }


def get_tool_cost(tool_type: str, *, correct: bool = False, overtime_multiplier: int = 1) -> int:
    """Get the display cost for a tool action.

    Args:
        tool_type: one of VALID_TOOL_TYPES
        correct: for GUESS, whether the guess was correct (correct = free)
        overtime_multiplier: 2 during overtime

    Returns: cost in points (display-only, not ledger)
    """
    if tool_type == "GUESS":
        base = TOOL_COSTS["GUESS_CORRECT"] if correct else TOOL_COSTS["GUESS_WRONG"]
    else:
        base = TOOL_COSTS.get(tool_type, 0)
    return base * overtime_multiplier
