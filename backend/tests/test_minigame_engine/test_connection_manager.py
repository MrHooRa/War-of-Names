"""Test connection manager — room management and player tracking."""

import uuid
import pytest
from unittest.mock import AsyncMock
from app.modules.minigames.connection_manager import ConnectionManager


@pytest.fixture
def mgr():
    return ConnectionManager()


def _ws():
    ws = AsyncMock()
    ws.send_json = AsyncMock()
    return ws


def test_connect_adds_player(mgr):
    room, mid = "r1", uuid.uuid4()
    mgr.connect(room, mid, _ws())
    assert mgr.is_connected(room, mid)
    assert mgr.room_count(room) == 1


def test_disconnect_removes_player(mgr):
    room, mid = "r1", uuid.uuid4()
    mgr.connect(room, mid, _ws())
    mgr.disconnect(room, mid)
    assert not mgr.is_connected(room, mid)
    assert mgr.room_count(room) == 0


def test_disconnect_nonexistent_safe(mgr):
    mgr.disconnect("r1", uuid.uuid4())


def test_multiple_players(mgr):
    room = "r1"
    m1, m2, m3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    mgr.connect(room, m1, _ws())
    mgr.connect(room, m2, _ws())
    mgr.connect(room, m3, _ws())
    assert mgr.room_count(room) == 3


def test_get_room_members(mgr):
    room = "r1"
    m1, m2 = uuid.uuid4(), uuid.uuid4()
    mgr.connect(room, m1, _ws())
    mgr.connect(room, m2, _ws())
    assert set(mgr.get_room_members(room)) == {m1, m2}


def test_empty_room(mgr):
    assert mgr.get_room_members("nope") == []
    assert mgr.room_count("nope") == 0


def test_get_websocket(mgr):
    room, mid = "r1", uuid.uuid4()
    ws = _ws()
    mgr.connect(room, mid, ws)
    assert mgr.get_websocket(room, mid) is ws


def test_get_websocket_unknown(mgr):
    assert mgr.get_websocket("r1", uuid.uuid4()) is None


def test_player_rooms(mgr):
    mid = uuid.uuid4()
    mgr.connect("r1", mid, _ws())
    mgr.connect("r2", mid, _ws())
    assert set(mgr.get_player_rooms(mid)) == {"r1", "r2"}


def test_disconnect_all(mgr):
    mid = uuid.uuid4()
    mgr.connect("r1", mid, _ws())
    mgr.connect("r2", mid, _ws())
    mgr.disconnect_all(mid)
    assert mgr.get_player_rooms(mid) == []
    assert mgr.room_count("r1") == 0
    assert mgr.room_count("r2") == 0


@pytest.mark.asyncio
async def test_send_to_player(mgr):
    room, mid = "r1", uuid.uuid4()
    ws = _ws()
    mgr.connect(room, mid, ws)
    result = await mgr.send_to_player(room, mid, {"type": "test"})
    assert result is True
    ws.send_json.assert_called_once_with({"type": "test"})


@pytest.mark.asyncio
async def test_send_to_unknown_returns_false(mgr):
    result = await mgr.send_to_player("r1", uuid.uuid4(), {"type": "test"})
    assert result is False
