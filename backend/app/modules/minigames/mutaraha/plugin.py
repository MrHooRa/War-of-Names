"""مطارحة plugin — implements the 8 lifecycle hooks for the word duel minigame."""

import copy
import random

from app.modules.minigames.plugin import GameTypePlugin
from app.modules.minigames.mutaraha.tools import (
    TOOL_COSTS,
    VALID_TOOL_TYPES,
    get_tool_cost,
    tool_first_letter,
    tool_guess,
    tool_letter_check,
    tool_letter_eliminate,
    tool_narrow_down,
    tool_word_length,
)


class MutarahaPlugin(GameTypePlugin):
    """مطارحة — word duel 1v1 minigame plugin."""

    id = "mutaraha"
    name = "مطارحة"
    description = "مبارزة كلمات 1v1 — خمّن كلمات خصمك قبل ما يخمّن كلماتك"
    plugin_api_version = "1.0"
    settings_schema_version = "1.0"
    supports_overtime = True
    supports_spectators = False
    supports_ranked = False
    supports_team_mode = False
    min_players = 2
    max_players = 2

    @staticmethod
    def _sample_word_offers(
        word_bank_words: list[str],
        *,
        exclude: set[str] | None = None,
        count: int = 10,
    ) -> list[str]:
        exclude = exclude or set()
        unique_words = list(dict.fromkeys(word for word in word_bank_words if word))
        candidates = [word for word in unique_words if word not in exclude]
        if len(candidates) < count:
            candidates = unique_words
        if len(candidates) <= count:
            return candidates[:count]
        return random.sample(candidates, count)

    @staticmethod
    def _resolve_actor_slot(state: dict, actor_ref) -> str | None:
        if actor_ref in {"player_1", "player_2"}:
            return actor_ref
        if actor_ref is None:
            return None

        actor_id = str(actor_ref)
        player_1_membership_id = state.get("player_1_membership_id")
        player_2_membership_id = state.get("player_2_membership_id")
        if player_1_membership_id is not None and actor_id == str(player_1_membership_id):
            return "player_1"
        if player_2_membership_id is not None and actor_id == str(player_2_membership_id):
            return "player_2"
        return None

    # ── 1. validate_settings ─────────────────────────────────

    def validate_settings(self, settings: dict) -> list[str]:
        errors = []
        buy_in = settings.get("minigame_buy_in")
        if buy_in is not None and (not isinstance(buy_in, int) or buy_in < 0):
            errors.append("مبلغ الدخول يجب أن يكون عدداً صحيحاً موجباً")
        daily = settings.get("minigame_daily_limit")
        if daily is not None and (not isinstance(daily, int) or daily < 1):
            errors.append("الحد اليومي يجب أن يكون 1 أو أكثر")
        return errors

    # ── 2. init_session_state ────────────────────────────────

    def init_session_state(self, config: dict) -> dict:
        """Create initial game state.

        config may include offered_words_p1/offered_words_p2 or a full word_bank_words
        list from which both players receive 10 offered words.
        """
        settings = config.get("settings", {}) or {}
        word_bank_words = list(config.get("word_bank_words") or [])
        offered_p1 = list(config.get("offered_words_p1") or [])
        offered_p2 = list(config.get("offered_words_p2") or [])
        if not offered_p1 and word_bank_words:
            offered_p1 = self._sample_word_offers(word_bank_words, count=10)
        if not offered_p2 and word_bank_words:
            offered_p2 = self._sample_word_offers(
                word_bank_words,
                exclude=set(offered_p1),
                count=10,
            )

        turns = config.get("turns_per_player", settings.get("turns_per_player", 12))
        ot_turns = config.get("overtime_turns", settings.get("overtime_turns", 3))
        buy_in = config.get(
            "buy_in",
            settings.get("minigame_buy_in", settings.get("buy_in", 500)),
        )

        def _make_player(offered):
            return {
                "offered_words": offered,
                "selected_words": [],
                "guessed_by_opponent": [False, False, False, False, False],
                "used_redraw": False,
                "redraw_cost": 0,
                "tool_costs": 0,
                "correct_guesses": 0,
                "tools_used": [],
            }

        return {
            "game_phase": "word_selection",
            "player_1_membership_id": (
                str(config.get("player_1_membership_id"))
                if config.get("player_1_membership_id") is not None
                else None
            ),
            "player_2_membership_id": (
                str(config.get("player_2_membership_id"))
                if config.get("player_2_membership_id") is not None
                else None
            ),
            "player_1": _make_player(offered_p1),
            "player_2": _make_player(offered_p2),
            "word_bank_words": word_bank_words,
            "revealed_info": {
                "player_1_known": {
                    "letter_checks": [],
                    "word_lengths": [],
                    "eliminated_letters": [],
                    "first_letters": [],
                    "narrow_downs": [],
                    "failed_guesses": [],
                },
                "player_2_known": {
                    "letter_checks": [],
                    "word_lengths": [],
                    "eliminated_letters": [],
                    "first_letters": [],
                    "narrow_downs": [],
                    "failed_guesses": [],
                },
            },
            "settings": {
                "turns_per_player": turns,
                "overtime_turns": ot_turns,
                "overtime_cost_multiplier": 2,
                "buy_in": buy_in,
            },
            "overtime_active": False,
            "overtime_turns_remaining_p1": 0,
            "overtime_turns_remaining_p2": 0,
        }

    # ── 3. validate_action ───────────────────────────────────

    def validate_action(self, action: dict, state: dict) -> str | None:
        action_type = action.get("type")
        phase = state.get("game_phase")
        payload = action.get("payload", {})
        actor = self._resolve_actor_slot(state, payload.get("actor"))
        if actor is None:
            return "تعذر تحديد اللاعب المنفذ"

        # Word selection actions
        if action_type == "select_words":
            if phase != "word_selection":
                return "مرحلة اختيار الكلمات انتهت"
            words = payload.get("words", [])
            if not isinstance(words, list):
                return "يجب إرسال قائمة كلمات صالحة"
            if len(words) != 5:
                return "يجب اختيار 5 كلمات بالضبط"
            if len(set(words)) != 5:
                return "يجب اختيار 5 كلمات مختلفة"
            offered_words = state.get(actor, {}).get("offered_words", [])
            if any(word not in offered_words for word in words):
                return "يجب اختيار الكلمات من القائمة المعروضة فقط"
            return None

        if action_type == "redraw":
            if phase != "word_selection":
                return "مرحلة اختيار الكلمات انتهت"
            if state.get(actor, {}).get("used_redraw"):
                return "تم استخدام إعادة السحب بالفعل"
            return None

        # Battle/overtime actions
        if phase not in ("battle", "overtime"):
            return "اللعبة ليست في مرحلة المبارزة"

        if action_type not in VALID_TOOL_TYPES:
            return f"نوع الإجراء غير صالح: {action_type}"

        # Validate tool-specific payload
        if action_type == "LETTER_CHECK":
            if not payload.get("letter"):
                return "يجب تحديد الحرف"
        elif action_type == "FIRST_LETTER":
            if "word_index" not in payload:
                return "يجب تحديد رقم الكلمة"
        elif action_type == "NARROW_DOWN":
            if "word_index" not in payload:
                return "يجب تحديد رقم الكلمة"
        elif action_type == "GUESS":
            if "word_index" not in payload or not payload.get("word"):
                return "يجب تحديد رقم الكلمة والكلمة المخمّنة"

        return None

    # ── 4. apply_action ──────────────────────────────────────

    def apply_action(self, action: dict, state: dict) -> tuple[dict, list[dict]]:
        new_state = copy.deepcopy(state)
        side_effects: list[dict] = []
        action_type = action.get("type")
        payload = action.get("payload", {})

        # Determine which player is acting
        actor = self._resolve_actor_slot(new_state, payload.get("actor"))
        if actor is None:
            raise ValueError("تعذر تحديد اللاعب المنفذ")
        opponent = "player_2" if actor == "player_1" else "player_1"
        actor_known = f"{actor}_known"

        # ── Word selection actions ──
        if action_type == "select_words":
            words = payload.get("words", [])
            new_state[actor]["selected_words"] = words[:5]
            # Check if both players selected — transition to battle
            p1_ready = len(new_state["player_1"].get("selected_words", [])) == 5
            p2_ready = len(new_state["player_2"].get("selected_words", [])) == 5
            if p1_ready and p2_ready:
                new_state["game_phase"] = "battle"
                side_effects.append({"type": "phase_change", "phase": "battle"})
            return new_state, side_effects

        if action_type == "redraw":
            new_state[actor]["used_redraw"] = True
            new_state[actor]["redraw_cost"] = 20
            new_words = self._sample_word_offers(
                new_state.get("word_bank_words", []),
                exclude=set(new_state[actor].get("offered_words", [])),
                count=10,
            )
            new_state[actor]["offered_words"] = new_words
            new_state[actor]["selected_words"] = []
            side_effects.append({"type": "redraw", "actor": actor})
            return new_state, side_effects

        # ── Battle/overtime tools ──
        opponent_words = new_state[opponent]["selected_words"]
        opponent_guessed = new_state[opponent]["guessed_by_opponent"]
        multiplier = (
            new_state["settings"]["overtime_cost_multiplier"]
            if new_state.get("overtime_active")
            else 1
        )
        revealed = new_state["revealed_info"][actor_known]

        result = None
        cost = 0

        if action_type == "LETTER_CHECK":
            letter = payload["letter"]
            result = tool_letter_check(letter=letter, opponent_words=opponent_words)
            revealed["letter_checks"].append(result)
            cost = get_tool_cost("LETTER_CHECK", overtime_multiplier=multiplier)
            side_effects.append({"type": "tool_result", "tool": "LETTER_CHECK", "result": result})

        elif action_type == "WORD_LENGTH":
            result = tool_word_length(opponent_words=opponent_words, guessed_mask=opponent_guessed)
            if result:
                revealed["word_lengths"].append(result)
                cost = get_tool_cost("WORD_LENGTH", overtime_multiplier=multiplier)
                side_effects.append({"type": "tool_result", "tool": "WORD_LENGTH", "result": result})

        elif action_type == "LETTER_ELIMINATE":
            result = tool_letter_eliminate(
                opponent_words=opponent_words,
                already_eliminated=revealed["eliminated_letters"],
            )
            revealed["eliminated_letters"].extend(result.get("eliminated", []))
            cost = get_tool_cost("LETTER_ELIMINATE", overtime_multiplier=multiplier)
            side_effects.append({"type": "tool_result", "tool": "LETTER_ELIMINATE", "result": result})

        elif action_type == "FIRST_LETTER":
            word_index = payload["word_index"]
            result = tool_first_letter(
                word_index=word_index,
                opponent_words=opponent_words,
                guessed_mask=opponent_guessed,
            )
            if result:
                revealed["first_letters"].append(result)
                cost = get_tool_cost("FIRST_LETTER", overtime_multiplier=multiplier)
                side_effects.append({"type": "tool_result", "tool": "FIRST_LETTER", "result": result})

        elif action_type == "NARROW_DOWN":
            word_index = payload["word_index"]
            result = tool_narrow_down(
                word_index=word_index,
                opponent_words=opponent_words,
                guessed_mask=opponent_guessed,
                all_bank_words=new_state.get("word_bank_words", []),
            )
            if result:
                revealed["narrow_downs"].append(
                    {"word_index": result["word_index"], "options": result["options"]}
                )
                cost = get_tool_cost("NARROW_DOWN", overtime_multiplier=multiplier)
                side_effects.append({"type": "tool_result", "tool": "NARROW_DOWN", "result": result})

        elif action_type == "GUESS":
            word_index = payload["word_index"]
            guessed_word = payload["word"]
            result = tool_guess(
                word_index=word_index,
                guessed_word=guessed_word,
                opponent_words=opponent_words,
                guessed_mask=opponent_guessed,
            )
            if result["correct"]:
                new_state[opponent]["guessed_by_opponent"][word_index] = True
                new_state[actor]["correct_guesses"] += 1
                cost = get_tool_cost("GUESS", correct=True, overtime_multiplier=multiplier)
                side_effects.append(
                    {"type": "guess_correct", "word_index": word_index, "word": result["actual_word"]}
                )
            else:
                revealed["failed_guesses"].append(guessed_word)
                cost = get_tool_cost("GUESS", correct=False, overtime_multiplier=multiplier)
                side_effects.append({"type": "guess_wrong", "word_index": word_index})

        # Record tool usage
        new_state[actor]["tool_costs"] += cost
        new_state[actor]["tools_used"].append(
            {
                "tool": action_type,
                "payload": payload,
                "result": result,
                "cost": cost,
            }
        )

        return new_state, side_effects

    # ── 5. evaluate_terminal ─────────────────────────────────

    def evaluate_terminal(self, state: dict) -> dict | None:
        if state.get("game_phase") not in ("battle", "overtime"):
            return None

        p1 = state["player_1"]
        p2 = state["player_2"]
        settings = state["settings"]

        # Knockout: someone guessed all 5
        if p1["correct_guesses"] >= 5:
            return {
                "winner": "player_1",
                "loser": "player_2",
                "winner_membership_id": state.get("player_1_membership_id"),
                "loser_membership_id": state.get("player_2_membership_id"),
                "reason": "knockout",
                "winner_guesses": 5,
                "loser_guesses": p2["correct_guesses"],
            }
        if p2["correct_guesses"] >= 5:
            return {
                "winner": "player_2",
                "loser": "player_1",
                "winner_membership_id": state.get("player_2_membership_id"),
                "loser_membership_id": state.get("player_1_membership_id"),
                "reason": "knockout",
                "winner_guesses": 5,
                "loser_guesses": p1["correct_guesses"],
            }

        # Check if turns exhausted
        if state.get("overtime_active"):
            ot_turns = settings.get("overtime_turns", 3)
            ot_used_p1 = max(0, len(p1["tools_used"]) - settings.get("turns_per_player", 12))
            ot_used_p2 = max(0, len(p2["tools_used"]) - settings.get("turns_per_player", 12))
            if ot_used_p1 >= ot_turns and ot_used_p2 >= ot_turns:
                return self._resolve_by_score(p1, p2, state)
        else:
            total_turns_used = len(p1["tools_used"]) + len(p2["tools_used"])
            max_regular = settings.get("turns_per_player", 12) * 2
            if total_turns_used >= max_regular:
                # Regular turns exhausted — check who's ahead
                if p1["correct_guesses"] != p2["correct_guesses"]:
                    return self._resolve_by_score(p1, p2, state)
                # Tied guesses — check costs
                if p1["tool_costs"] != p2["tool_costs"]:
                    return self._resolve_by_score(p1, p2, state)
                # Exact tie — overtime needed (return None to trigger evaluate_overtime)
                return None

        return None

    def _resolve_by_score(self, p1: dict, p2: dict, state: dict) -> dict:
        """Determine winner by guesses, then costs, then player_2 advantage."""
        if p1["correct_guesses"] > p2["correct_guesses"]:
            winner, loser = "player_1", "player_2"
        elif p2["correct_guesses"] > p1["correct_guesses"]:
            winner, loser = "player_2", "player_1"
        elif p1["tool_costs"] + p1.get("redraw_cost", 0) < p2["tool_costs"] + p2.get("redraw_cost", 0):
            winner, loser = "player_1", "player_2"
        elif p2["tool_costs"] + p2.get("redraw_cost", 0) < p1["tool_costs"] + p1.get("redraw_cost", 0):
            winner, loser = "player_2", "player_1"
        else:
            # Exact tie — player_2 wins (compensation for going second)
            winner, loser = "player_2", "player_1"

        w = state[winner]
        l = state[loser]
        return {
            "winner": winner,
            "loser": loser,
            "winner_membership_id": state.get(f"{winner}_membership_id"),
            "loser_membership_id": state.get(f"{loser}_membership_id"),
            "reason": "score",
            "winner_guesses": w["correct_guesses"],
            "loser_guesses": l["correct_guesses"],
        }

    # ── 6. evaluate_overtime ─────────────────────────────────

    def evaluate_overtime(self, state: dict) -> dict | None:
        if state.get("overtime_active"):
            return None  # Already in overtime — no double overtime
        settings = state["settings"]
        ot_turns = settings.get("overtime_turns", 3)
        return {
            "overtime_active": True,
            "overtime_turns_remaining_p1": ot_turns,
            "overtime_turns_remaining_p2": ot_turns,
            "game_phase": "overtime",
        }

    # ── 7. compute_settlement ────────────────────────────────

    def compute_settlement(self, terminal_result: dict) -> dict:
        buy_in = terminal_result.get("buy_in", 500)
        return {
            "winner_membership_id": terminal_result.get("winner_membership_id"),
            "loser_membership_id": terminal_result.get("loser_membership_id"),
            "winner_payout": buy_in * 2,
            "loser_penalty": buy_in,
        }

    # ── 8. build_public_view ─────────────────────────────────

    def build_public_view(self, state: dict, viewer_membership_id) -> dict:
        view = copy.deepcopy(state)
        view.pop("word_bank_words", None)

        # Determine viewer role
        viewer = self._resolve_actor_slot(view, viewer_membership_id)
        if viewer is None:
            for player_key in ("player_1", "player_2"):
                player = view[player_key]
                player["selected_words"] = [None for _ in player.get("selected_words", [])]
                player["offered_words"] = []
                player["tools_used"] = []
                player["tool_costs"] = 0
            view["revealed_info"] = {}
            return view
        opponent = "player_2" if viewer == "player_1" else "player_1"
        opponent_known = f"{opponent}_known"

        # Hide opponent's selected words (only show guessed ones)
        opp = view[opponent]
        visible_words = []
        for i, word in enumerate(opp.get("selected_words", [])):
            if opp["guessed_by_opponent"][i]:
                visible_words.append(word)
            else:
                visible_words.append(None)  # Hidden
        opp["selected_words"] = visible_words

        # Hide opponent's offered words
        opp["offered_words"] = []

        # Hide opponent's revealed_info (what they know about viewer's words)
        view["revealed_info"][opponent_known] = {
            "tools_used_count": len(view[opponent].get("tools_used", [])),
            "correct_guesses": view[opponent]["correct_guesses"],
        }

        # Hide opponent's tool details
        opp["tools_used"] = []
        opp["tool_costs"] = 0  # Don't reveal exact spend

        return view
