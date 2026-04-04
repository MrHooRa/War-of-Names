"""Test settings helper — defaults and kill switch logic."""

from app.modules.minigames.settings_helper import (
    MINIGAME_SETTING_KEYS,
    MINIGAME_DEFAULTS,
    check_kill_switch,
    get_setting_defaults_for_game,
    get_setting_keys_for_game,
    KillSwitchLevel,
)


def test_all_setting_keys_have_defaults():
    for key in MINIGAME_SETTING_KEYS:
        assert key in MINIGAME_DEFAULTS, f"Missing default for {key}"


def test_default_buy_in():
    assert MINIGAME_DEFAULTS["minigame_buy_in"] == 500


def test_default_daily_limit():
    assert MINIGAME_DEFAULTS["minigame_daily_limit"] == 2


def test_default_kill_switch():
    assert MINIGAME_DEFAULTS["minigame_kill_switch"] == "off"


def test_kill_switch_off():
    result = check_kill_switch("off")
    assert result.level == KillSwitchLevel.OFF
    assert result.can_create_session is True
    assert result.can_matchmake is True


def test_kill_switch_soft():
    result = check_kill_switch("soft")
    assert result.level == KillSwitchLevel.SOFT
    assert result.can_create_session is True
    assert result.can_matchmake is False


def test_kill_switch_hard():
    result = check_kill_switch("hard")
    assert result.level == KillSwitchLevel.HARD
    assert result.can_create_session is False
    assert result.can_matchmake is False


def test_kill_switch_emergency():
    result = check_kill_switch("emergency")
    assert result.level == KillSwitchLevel.EMERGENCY
    assert result.can_create_session is False
    assert result.can_matchmake is False
    assert result.cancel_active is True


def test_kill_switch_unknown_treated_as_off():
    result = check_kill_switch("unknown_value")
    assert result.level == KillSwitchLevel.OFF
    assert result.can_create_session is True


def test_kill_switch_none_treated_as_off():
    result = check_kill_switch(None)
    assert result.level == KillSwitchLevel.OFF
    assert result.can_create_session is True


def test_mutaraha_specific_keys_are_exposed():
    keys = get_setting_keys_for_game("mutaraha")
    assert "mutaraha_turn_duration_sec" in keys
    assert "mutaraha_queue_timeout_sec" in keys


def test_mutaraha_specific_defaults_are_available():
    defaults = get_setting_defaults_for_game("mutaraha")
    assert defaults["mutaraha_words_per_draw"] == 10
    assert defaults["mutaraha_challenge_timeout_sec"] == 60
