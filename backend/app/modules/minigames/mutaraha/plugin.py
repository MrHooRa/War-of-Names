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

    @staticmethod
    def _setting_int(settings: dict, key: str, default: int) -> int:
        value = settings.get(key, default)
        if isinstance(value, bool):
            return default
        if isinstance(value, (int, float)):
            return int(value)
        return default

    @staticmethod
    def _setting_bool(settings: dict, key: str, default: bool) -> bool:
        value = settings.get(key, default)
        if isinstance(value, bool):
            return value
        return default

    def _words_to_select(self, state: dict) -> int:
        return self._setting_int(state.get("settings", {}) or {}, "words_to_select", 5)

    def _record_turn_consumed(self, state: dict, actor: str) -> None:
        state[actor]["turns_taken"] = state[actor].get("turns_taken", 0) + 1
        if not state.get("overtime_active"):
            return
        remaining_key = "overtime_turns_remaining_p1" if actor == "player_1" else "overtime_turns_remaining_p2"
        state[remaining_key] = max(
            0,
            self._setting_int(state, remaining_key, state.get(remaining_key, 0)) - 1,
        )

    # ── 1. validate_settings ─────────────────────────────────

    def validate_settings(self, settings: dict) -> list[str]:
        errors = []
        buy_in = settings.get("mutaraha_buy_in", settings.get("minigame_buy_in"))
        if buy_in is not None and (not isinstance(buy_in, int) or buy_in < 0):
            errors.append("مبلغ الدخول يجب أن يكون عدداً صحيحاً موجباً")
        daily = settings.get("mutaraha_daily_limit", settings.get("minigame_daily_limit"))
        if daily is not None and (not isinstance(daily, int) or daily < 1):
            errors.append("الحد اليومي يجب أن يكون 1 أو أكثر")
        turns_per_player = settings.get("mutaraha_turns_per_player")
        if turns_per_player is not None and (not isinstance(turns_per_player, int) or turns_per_player < 1):
            errors.append("عدد الأدوار لكل لاعب يجب أن يكون 1 أو أكثر")
        words_per_draw = settings.get("mutaraha_words_per_draw")
        words_to_select = settings.get("mutaraha_words_to_select")
        if words_per_draw is not None and (not isinstance(words_per_draw, int) or words_per_draw < 2):
            errors.append("عدد الكلمات في السحب يجب أن يكون 2 أو أكثر")
        if words_to_select is not None and (not isinstance(words_to_select, int) or words_to_select < 1):
            errors.append("عدد الكلمات المختارة يجب أن يكون 1 أو أكثر")
        if (
            isinstance(words_per_draw, int)
            and isinstance(words_to_select, int)
            and words_per_draw < words_to_select * 2
        ):
            errors.append("عدد الكلمات في السحب يجب أن يكون على الأقل ضعف عدد الكلمات المختارة")
        return errors

    # ── 2. init_session_state ────────────────────────────────

    def init_session_state(self, config: dict) -> dict:
        """Create initial game state.

        config may include offered_words_p1/offered_words_p2 or a full word_bank_words
        list from which both players receive 10 offered words.
        """
        settings = config.get("settings", {}) or {}
        word_bank_words = list(config.get("word_bank_words") or [])
        word_pool_p1 = list(config.get("word_pool_player_1") or word_bank_words)
        word_pool_p2 = list(config.get("word_pool_player_2") or word_bank_words)
        offered_p1 = list(config.get("offered_words_p1") or [])
        offered_p2 = list(config.get("offered_words_p2") or [])
        words_per_draw = config.get(
            "words_per_draw",
            self._setting_int(settings, "mutaraha_words_per_draw", 10),
        )
        words_to_select = config.get(
            "words_to_select",
            self._setting_int(settings, "mutaraha_words_to_select", 5),
        )
        if not offered_p1 and word_bank_words:
            offered_p1 = self._sample_word_offers(word_pool_p1, count=words_per_draw)
        if not offered_p2 and word_bank_words:
            offered_p2 = self._sample_word_offers(
                word_pool_p2,
                exclude=set(offered_p1),
                count=words_per_draw,
            )

        turns = config.get(
            "turns_per_player",
            self._setting_int(settings, "mutaraha_turns_per_player", 12),
        )
        ot_turns = config.get(
            "overtime_turns",
            self._setting_int(settings, "mutaraha_overtime_turns", 3),
        )
        regular_turn_duration_sec = config.get(
            "turn_duration_sec",
            self._setting_int(
                settings,
                "mutaraha_turn_duration_sec",
                self._setting_int(settings, "minigame_turn_duration_sec", 30),
            ),
        )
        selection_duration_sec = config.get(
            "selection_duration_sec",
            self._setting_int(settings, "mutaraha_selection_duration_sec", 45),
        )
        overtime_turn_duration_sec = config.get(
            "overtime_turn_duration_sec",
            self._setting_int(settings, "mutaraha_overtime_turn_sec", 20),
        )
        overtime_enabled = config.get(
            "overtime_enabled",
            self._setting_bool(
                settings,
                "mutaraha_overtime_enabled",
                self._setting_bool(settings, "minigame_overtime_enabled", True),
            ),
        )
        overtime_cost_multiplier = config.get(
            "overtime_cost_multiplier",
            self._setting_int(settings, "mutaraha_overtime_cost_multiplier", 2),
        )
        redraw_cost = config.get(
            "redraw_cost",
            self._setting_int(settings, "mutaraha_redraw_cost", 20),
        )
        buy_in = config.get(
            "buy_in",
            settings.get(
                "mutaraha_buy_in",
                settings.get("minigame_buy_in", settings.get("buy_in", 500)),
            ),
        )

        def _make_player(offered):
            return {
                "offered_words": offered,
                "selected_words": [],
                "guessed_by_opponent": [False] * words_to_select,
                "used_redraw": False,
                "redraw_cost": 0,
                "tool_costs": 0,
                "correct_guesses": 0,
                "tools_used": [],
                "turns_taken": 0,
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
            "word_pool_player_1": word_pool_p1,
            "word_pool_player_2": word_pool_p2,
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
                "words_per_draw": words_per_draw,
                "words_to_select": words_to_select,
                "selection_duration_sec": selection_duration_sec,
                "turn_duration_sec": regular_turn_duration_sec,
                "overtime_enabled": overtime_enabled,
                "overtime_turns": ot_turns,
                "overtime_turn_duration_sec": overtime_turn_duration_sec,
                "overtime_cost_multiplier": overtime_cost_multiplier,
                "redraw_cost": redraw_cost,
                "cost_letter_check": self._setting_int(settings, "mutaraha_cost_letter_check", 20),
                "cost_word_length": self._setting_int(settings, "mutaraha_cost_word_length", 20),
                "cost_letter_eliminate": self._setting_int(settings, "mutaraha_cost_letter_eliminate", 40),
                "cost_first_letter": self._setting_int(settings, "mutaraha_cost_first_letter", 50),
                "cost_narrow_down": self._setting_int(settings, "mutaraha_cost_narrow_down", 60),
                "cost_wrong_guess": self._setting_int(settings, "mutaraha_cost_wrong_guess", 50),
                "buy_in": buy_in,
            },
            "word_selection_deadline": None,
            "current_turn_deadline": None,
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
            words_to_select = self._words_to_select(state)
            if len(words) != words_to_select:
                return f"يجب اختيار {words_to_select} كلمات بالضبط"
            if len(set(words)) != words_to_select:
                return f"يجب اختيار {words_to_select} كلمات مختلفة"
            offered_words = state.get(actor, {}).get("offered_words", [])
            if any(word not in offered_words for word in words):
                return "يجب اختيار الكلمات من القائمة المعروضة فقط"
            return None

        if action_type == "redraw":
            if phase != "word_selection":
                return "مرحلة اختيار الكلمات انتهت"
            if state.get(actor, {}).get("used_redraw"):
                return "تم استخدام إعادة السحب بالفعل"
            if state.get(actor, {}).get("selected_words"):
                return "لا يمكن إعادة السحب بعد اختيار أي كلمة"
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
            words_to_select = self._words_to_select(new_state)
            words = payload.get("words", [])
            new_state[actor]["selected_words"] = words[:words_to_select]
            # Check if both players selected — transition to battle
            p1_ready = len(new_state["player_1"].get("selected_words", [])) == words_to_select
            p2_ready = len(new_state["player_2"].get("selected_words", [])) == words_to_select
            if p1_ready and p2_ready:
                new_state["game_phase"] = "battle"
                side_effects.append({"type": "phase_change", "phase": "battle"})
            return new_state, side_effects

        if action_type == "redraw":
            new_state[actor]["used_redraw"] = True
            settings = new_state.get("settings", {}) or {}
            words_per_draw = self._setting_int(settings, "words_per_draw", 10)
            new_state[actor]["redraw_cost"] = self._setting_int(settings, "redraw_cost", 20)
            new_words = self._sample_word_offers(
                new_state.get(f"word_pool_{actor}", []),
                exclude=set(new_state[actor].get("offered_words", [])),
                count=words_per_draw,
            )
            new_state[actor]["offered_words"] = new_words
            new_state[actor]["selected_words"] = []
            side_effects.append({"type": "redraw", "actor": actor})
            return new_state, side_effects

        # ── Battle/overtime tools ──
        opponent_words = new_state[opponent]["selected_words"]
        opponent_guessed = new_state[opponent]["guessed_by_opponent"]
        settings = new_state.get("settings", {}) or {}
        multiplier = (
            settings["overtime_cost_multiplier"]
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
            cost = get_tool_cost("LETTER_CHECK", overtime_multiplier=multiplier, settings=settings)
            side_effects.append({"type": "tool_result", "tool": "LETTER_CHECK", "result": result})

        elif action_type == "WORD_LENGTH":
            result = tool_word_length(opponent_words=opponent_words, guessed_mask=opponent_guessed)
            if result:
                revealed["word_lengths"].append(result)
                cost = get_tool_cost("WORD_LENGTH", overtime_multiplier=multiplier, settings=settings)
                side_effects.append({"type": "tool_result", "tool": "WORD_LENGTH", "result": result})

        elif action_type == "LETTER_ELIMINATE":
            result = tool_letter_eliminate(
                opponent_words=opponent_words,
                already_eliminated=revealed["eliminated_letters"],
            )
            revealed["eliminated_letters"].extend(result.get("eliminated", []))
            cost = get_tool_cost("LETTER_ELIMINATE", overtime_multiplier=multiplier, settings=settings)
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
                cost = get_tool_cost("FIRST_LETTER", overtime_multiplier=multiplier, settings=settings)
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
                cost = get_tool_cost("NARROW_DOWN", overtime_multiplier=multiplier, settings=settings)
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
                cost = get_tool_cost(
                    "GUESS",
                    correct=True,
                    overtime_multiplier=multiplier,
                    settings=settings,
                )
                side_effects.append(
                    {"type": "guess_correct", "word_index": word_index, "word": result["actual_word"]}
                )
            else:
                revealed["failed_guesses"].append(guessed_word)
                cost = get_tool_cost(
                    "GUESS",
                    correct=False,
                    overtime_multiplier=multiplier,
                    settings=settings,
                )
                side_effects.append({"type": "guess_wrong", "word_index": word_index})

        # Record tool usage
        self._record_turn_consumed(new_state, actor)
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
        words_to_select = self._setting_int(settings, "words_to_select", 5)
        regular_turns = self._setting_int(settings, "turns_per_player", 12)
        overtime_turns = self._setting_int(settings, "overtime_turns", 3)
        p1_turns_taken = p1.get("turns_taken", len(p1.get("tools_used", [])))
        p2_turns_taken = p2.get("turns_taken", len(p2.get("tools_used", [])))

        # Knockout: someone guessed all target words
        if p1["correct_guesses"] >= words_to_select:
            return {
                "winner": "player_1",
                "loser": "player_2",
                "winner_membership_id": state.get("player_1_membership_id"),
                "loser_membership_id": state.get("player_2_membership_id"),
                "reason": "knockout",
                "winner_guesses": words_to_select,
                "loser_guesses": p2["correct_guesses"],
            }
        if p2["correct_guesses"] >= words_to_select:
            return {
                "winner": "player_2",
                "loser": "player_1",
                "winner_membership_id": state.get("player_2_membership_id"),
                "loser_membership_id": state.get("player_1_membership_id"),
                "reason": "knockout",
                "winner_guesses": words_to_select,
                "loser_guesses": p1["correct_guesses"],
            }

        # Check if turns exhausted
        if state.get("overtime_active"):
            if p1_turns_taken >= regular_turns + overtime_turns and p2_turns_taken >= regular_turns + overtime_turns:
                return self._resolve_by_score(p1, p2, state)
        else:
            if p1_turns_taken >= regular_turns and p2_turns_taken >= regular_turns:
                # Regular turns exhausted — check who's ahead
                if p1["correct_guesses"] != p2["correct_guesses"]:
                    return self._resolve_by_score(p1, p2, state)
                # Tied guesses — check costs
                if p1["tool_costs"] != p2["tool_costs"]:
                    return self._resolve_by_score(p1, p2, state)
                # Exact tie — overtime needed (return None to trigger evaluate_overtime)
                if not self._setting_bool(settings, "overtime_enabled", True):
                    return self._resolve_by_score(p1, p2, state)
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
        if state.get("game_phase") != "battle":
            return None

        p1 = state["player_1"]
        p2 = state["player_2"]
        settings = state["settings"]
        if not self._setting_bool(settings, "overtime_enabled", True):
            return None
        regular_turns = self._setting_int(settings, "turns_per_player", 12)
        p1_turns_taken = p1.get("turns_taken", len(p1.get("tools_used", [])))
        p2_turns_taken = p2.get("turns_taken", len(p2.get("tools_used", [])))
        if p1_turns_taken < regular_turns or p2_turns_taken < regular_turns:
            return None
        if p1["correct_guesses"] != p2["correct_guesses"]:
            return None
        if p1["tool_costs"] != p2["tool_costs"]:
            return None

        ot_turns = self._setting_int(settings, "overtime_turns", 3)
        return {
            "overtime_active": True,
            "overtime_turns_remaining_p1": ot_turns,
            "overtime_turns_remaining_p2": ot_turns,
            "game_phase": "overtime",
        }

    def resolve_selection_timeout(self, state: dict) -> dict | None:
        """Auto-pick any missing words when the selection timer expires."""
        if state.get("game_phase") != "word_selection":
            return None

        new_state = copy.deepcopy(state)
        side_effects: list[dict] = []
        words_to_select = self._words_to_select(new_state)

        for actor in ("player_1", "player_2"):
            selected = list(new_state[actor].get("selected_words", []))
            if len(selected) >= words_to_select:
                continue
            offered = list(new_state[actor].get("offered_words", []))
            remaining_candidates = [word for word in offered if word not in selected]
            needed = words_to_select - len(selected)
            auto_selected = remaining_candidates[:]
            if len(auto_selected) > needed:
                auto_selected = random.sample(auto_selected, needed)
            selected.extend(auto_selected[:needed])
            new_state[actor]["selected_words"] = selected[:words_to_select]
            side_effects.append({"type": "auto_select", "actor": actor})

        p1_ready = len(new_state["player_1"].get("selected_words", [])) == words_to_select
        p2_ready = len(new_state["player_2"].get("selected_words", [])) == words_to_select
        if p1_ready and p2_ready:
            new_state["game_phase"] = "battle"
            side_effects.append({"type": "phase_change", "phase": "battle"})

        return {
            "state": new_state,
            "side_effects": side_effects,
            "current_turn_index": 0 if new_state.get("game_phase") == "battle" else None,
        }

    def resolve_turn_timeout(self, state: dict, actor_slot_index: int | None) -> dict | None:
        """Skip the active player's turn when the turn timer expires."""
        if state.get("game_phase") not in {"battle", "overtime"}:
            return None
        if actor_slot_index not in {0, 1}:
            return None

        new_state = copy.deepcopy(state)
        actor = "player_1" if actor_slot_index == 0 else "player_2"
        self._record_turn_consumed(new_state, actor)
        return {
            "state": new_state,
            "side_effects": [{"type": "turn_skipped", "actor": actor}],
        }

    # ── 7. compute_settlement ────────────────────────────────

    def compute_settlement(self, terminal_result: dict) -> dict:
        """Return settlement payload in the N-player participant_results format.

        For مطارحة (1v1) the winner takes the full pool (2x buy_in); the loser
        already paid the buy_in on session creation, so no extra penalty is
        deducted here — the loser's payout is simply 0.
        """
        buy_in = terminal_result.get("buy_in", 500)
        winner = terminal_result.get("winner")  # "player_1" or "player_2"
        winner_mid = terminal_result.get("winner_membership_id")
        loser_mid = terminal_result.get("loser_membership_id")

        winner_slot = 0 if winner == "player_1" else 1
        loser_slot = 1 - winner_slot

        return {
            "participant_results": [
                {
                    "membership_id": winner_mid,
                    "slot_index": winner_slot,
                    "rank": 1,
                    "payout": buy_in * 2,
                },
                {
                    "membership_id": loser_mid,
                    "slot_index": loser_slot,
                    "rank": 2,
                    "payout": 0,
                },
            ],
            "total_pool": buy_in * 2,
        }

    # ── 8. build_public_view ─────────────────────────────────

    def build_public_view(self, state: dict, viewer_membership_id) -> dict:
        view = copy.deepcopy(state)
        view.pop("word_bank_words", None)
        view.pop("word_pool_player_1", None)
        view.pop("word_pool_player_2", None)

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
