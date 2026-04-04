"""Test lobby manager — presence, queue, and matchmaking."""

import uuid
import pytest
from app.modules.minigames.lobby_manager import LobbyManager


@pytest.fixture
def lobby():
    return LobbyManager()


def _key():
    return f"mutaraha:{uuid.uuid4()}"


def test_join_lobby(lobby):
    key, mid = _key(), uuid.uuid4()
    lobby.join(key, mid, alias="الصقر")
    assert lobby.is_in_lobby(key, mid)
    assert lobby.get_player_count(key) == 1


def test_leave_lobby(lobby):
    key, mid = _key(), uuid.uuid4()
    lobby.join(key, mid, alias="الصقر")
    lobby.leave(key, mid)
    assert not lobby.is_in_lobby(key, mid)


def test_get_players_list(lobby):
    key = _key()
    m1, m2 = uuid.uuid4(), uuid.uuid4()
    lobby.join(key, m1, alias="الصقر")
    lobby.join(key, m2, alias="الفهد")
    players = lobby.get_players(key)
    assert {p["alias"] for p in players} == {"الصقر", "الفهد"}


def test_default_status_idle(lobby):
    key, mid = _key(), uuid.uuid4()
    lobby.join(key, mid, alias="X")
    assert lobby.get_players(key)[0]["status"] == "idle"


def test_queue_join(lobby):
    key, mid = _key(), uuid.uuid4()
    lobby.join(key, mid, alias="الصقر")
    lobby.queue_join(key, mid)
    assert lobby.get_players(key)[0]["status"] == "in_queue"


def test_queue_join_ignores_non_lobby_player(lobby):
    key, mid = _key(), uuid.uuid4()
    lobby.queue_join(key, mid)
    assert lobby.get_player_count(key) == 0
    assert lobby.try_match(key) is None


def test_queue_leave(lobby):
    key, mid = _key(), uuid.uuid4()
    lobby.join(key, mid, alias="الصقر")
    lobby.queue_join(key, mid)
    lobby.queue_leave(key, mid)
    assert lobby.get_players(key)[0]["status"] == "idle"


def test_queue_match_fifo(lobby):
    key = _key()
    m1, m2 = uuid.uuid4(), uuid.uuid4()
    lobby.join(key, m1, alias="الصقر")
    lobby.join(key, m2, alias="الفهد")
    lobby.queue_join(key, m1)
    lobby.queue_join(key, m2)
    match = lobby.try_match(key)
    assert match is not None
    assert set(match) == {m1, m2}


def test_no_match_single(lobby):
    key, mid = _key(), uuid.uuid4()
    lobby.join(key, mid, alias="الصقر")
    lobby.queue_join(key, mid)
    assert lobby.try_match(key) is None


def test_matched_status_in_match(lobby):
    key = _key()
    m1, m2 = uuid.uuid4(), uuid.uuid4()
    lobby.join(key, m1, alias="A")
    lobby.join(key, m2, alias="B")
    lobby.queue_join(key, m1)
    lobby.queue_join(key, m2)
    lobby.try_match(key)
    for p in lobby.get_players(key):
        assert p["status"] == "in_match"


def test_set_status(lobby):
    key, mid = _key(), uuid.uuid4()
    lobby.join(key, mid, alias="X")
    lobby.set_status(key, mid, "challenging")
    assert lobby.get_players(key)[0]["status"] == "challenging"


def test_rejoin_preserves_existing_status(lobby):
    key, mid = _key(), uuid.uuid4()
    lobby.join(key, mid, alias="X")
    lobby.set_status(key, mid, "in_match")
    lobby.join(key, mid, alias="X-2", stats={"wins": 3})
    player = lobby.get_players(key)[0]
    assert player["alias"] == "X-2"
    assert player["status"] == "in_match"
    assert player["stats"] == {"wins": 3}


def test_add_result(lobby):
    key = _key()
    lobby.add_result(key, {"winner_alias": "الصقر"})
    assert len(lobby.get_recent_results(key)) == 1


def test_results_max_5(lobby):
    key = _key()
    for i in range(7):
        lobby.add_result(key, {"winner_alias": f"p{i}"})
    results = lobby.get_recent_results(key)
    assert len(results) == 5
    assert results[0]["winner_alias"] == "p6"


def test_lobby_state_snapshot(lobby):
    key = _key()
    m1 = uuid.uuid4()
    lobby.join(key, m1, alias="الصقر")
    lobby.add_result(key, {"winner": "X"})
    state = lobby.get_lobby_state(key)
    assert "players" in state
    assert "active_matches" in state
    assert "recent_results" in state


def test_leave_also_removes_from_queue(lobby):
    key, mid = _key(), uuid.uuid4()
    lobby.join(key, mid, alias="X")
    lobby.queue_join(key, mid)
    lobby.leave(key, mid)
    assert not lobby.is_in_lobby(key, mid)
    # Queue should not match after leave
    m2 = uuid.uuid4()
    lobby.join(key, m2, alias="Y")
    lobby.queue_join(key, m2)
    assert lobby.try_match(key) is None


def test_match_3_players(lobby):
    key = _key()
    ids = [uuid.uuid4() for _ in range(3)]
    for i, mid in enumerate(ids):
        lobby.join(key, mid, alias=f"player_{i}")
        lobby.queue_join(key, mid)
    match = lobby.try_match(key, num_needed=3)
    assert match is not None
    assert len(match) == 3
    # All matched players should be in_match status
    players = lobby.get_players(key)
    assert all(p["status"] == "in_match" for p in players)


def test_match_not_enough_for_4(lobby):
    key = _key()
    for i in range(3):
        mid = uuid.uuid4()
        lobby.join(key, mid, alias=f"p{i}")
        lobby.queue_join(key, mid)
    match = lobby.try_match(key, num_needed=4)
    assert match is None  # Only 3 in queue, need 4


def test_match_8_players(lobby):
    """Verify max 8 players supported."""
    key = _key()
    ids = [uuid.uuid4() for _ in range(8)]
    for i, mid in enumerate(ids):
        lobby.join(key, mid, alias=f"p{i}")
        lobby.queue_join(key, mid)
    match = lobby.try_match(key, num_needed=8)
    assert match is not None
    assert len(match) == 8


def test_match_default_num_needed_is_2(lobby):
    """Backward compat: calling try_match without num_needed still matches 2 players."""
    key = _key()
    m1, m2 = uuid.uuid4(), uuid.uuid4()
    lobby.join(key, m1, alias="a")
    lobby.join(key, m2, alias="b")
    lobby.queue_join(key, m1)
    lobby.queue_join(key, m2)
    match = lobby.try_match(key)  # no num_needed = defaults to 2
    assert match is not None
    assert len(match) == 2
    assert set(match) == {m1, m2}


def test_match_fifo_order_with_6_players(lobby):
    """Queue should match players in FIFO order."""
    key = _key()
    ids = [uuid.uuid4() for _ in range(6)]
    for i, mid in enumerate(ids):
        lobby.join(key, mid, alias=f"p{i}")
        lobby.queue_join(key, mid)
    # Match first 4
    match1 = lobby.try_match(key, num_needed=4)
    assert list(match1) == ids[:4]  # First 4 in queue order
    # Match remaining 2
    match2 = lobby.try_match(key, num_needed=2)
    assert list(match2) == ids[4:]
