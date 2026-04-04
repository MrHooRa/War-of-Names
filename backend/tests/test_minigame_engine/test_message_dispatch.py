"""WebSocket message-dispatch tests with a tiny fastapi shim.

These tests stay dependency-light: they exercise the dispatcher and the
in-memory lobby/connection state without importing the real FastAPI package.
"""

from __future__ import annotations

import importlib
import sys
import types
import uuid
from unittest.mock import AsyncMock

import pytest

from app.modules.minigames.connection_manager import ConnectionManager
from app.modules.minigames.lobby_manager import LobbyManager


@pytest.fixture
def ws_module(monkeypatch):
    fastapi = types.ModuleType("fastapi")

    class APIRouter:
        def websocket(self, _path):
            def decorator(fn):
                return fn

            return decorator

    class WebSocket:
        pass

    class WebSocketDisconnect(Exception):
        pass

    fastapi.APIRouter = APIRouter
    fastapi.Query = lambda default=None: default
    fastapi.WebSocket = WebSocket
    fastapi.WebSocketDisconnect = WebSocketDisconnect

    monkeypatch.setitem(sys.modules, "fastapi", fastapi)
    sys.modules.pop("app.modules.minigames.ws_router", None)

    module = importlib.import_module("app.modules.minigames.ws_router")
    monkeypatch.setattr(module, "manager", ConnectionManager())
    monkeypatch.setattr(module, "lobby_mgr", LobbyManager())
    return module


def _membership(alias: str = "A") -> dict:
    return {"membership_id": uuid.uuid4(), "alias": alias}


@pytest.mark.asyncio
async def test_queue_join_requires_lobby_presence(ws_module, monkeypatch):
    websocket = AsyncMock()
    membership_info = _membership()
    queue_match = AsyncMock()
    monkeypatch.setattr(ws_module, "_handle_queue_match", queue_match)

    await ws_module._handle_message(
        websocket,
        {"type": "queue_join"},
        uuid.uuid4(),
        "mutaraha",
        membership_info,
    )

    queue_match.assert_not_awaited()
    assert websocket.send_json.await_count == 1
    assert websocket.send_json.await_args.args[0] == {
        "type": "error",
        "code": "NOT_IN_LOBBY",
        "message": "يجب دخول اللوبي قبل الطابور",
    }


@pytest.mark.asyncio
async def test_second_queue_join_triggers_match_handler(ws_module, monkeypatch):
    competition_id = uuid.uuid4()
    info_1 = _membership("الصقر")
    info_2 = _membership("الفهد")
    ws_1 = AsyncMock()
    ws_2 = AsyncMock()
    queue_match = AsyncMock()
    monkeypatch.setattr(ws_module, "_handle_queue_match", queue_match)

    await ws_module._handle_message(ws_1, {"type": "lobby_join"}, competition_id, "mutaraha", info_1)
    await ws_module._handle_message(ws_2, {"type": "lobby_join"}, competition_id, "mutaraha", info_2)

    await ws_module._handle_message(ws_1, {"type": "queue_join"}, competition_id, "mutaraha", info_1)
    queue_match.assert_not_awaited()

    await ws_module._handle_message(ws_2, {"type": "queue_join"}, competition_id, "mutaraha", info_2)

    queue_match.assert_awaited_once()
    assert queue_match.await_args.args == (
        f"mutaraha:{competition_id}",
        competition_id,
        "mutaraha",
        info_1["membership_id"],
        info_2["membership_id"],
    )


@pytest.mark.asyncio
async def test_challenge_send_to_offline_target_resets_status(ws_module):
    competition_id = uuid.uuid4()
    membership_info = _membership("المهاجم")
    websocket = AsyncMock()

    await ws_module._handle_message(
        websocket,
        {"type": "lobby_join"},
        competition_id,
        "mutaraha",
        membership_info,
    )

    await ws_module._handle_message(
        websocket,
        {"type": "challenge_send", "target_membership_id": str(uuid.uuid4())},
        competition_id,
        "mutaraha",
        membership_info,
    )

    lobby_key = f"mutaraha:{competition_id}"
    players = ws_module.lobby_mgr.get_players(lobby_key)
    assert len(players) == 1
    assert players[0]["status"] == "idle"

    sent_messages = [call.args[0] for call in websocket.send_json.await_args_list]
    assert {
        "type": "error",
        "code": "TARGET_OFFLINE",
        "message": "اللاعب المستهدف غير متصل",
    } in sent_messages


@pytest.mark.asyncio
async def test_action_submit_overrides_forged_actor_membership(ws_module, monkeypatch):
    competition_id = uuid.uuid4()
    membership_info = _membership("المقاتل")
    session_id = uuid.uuid4()
    opponent_id = uuid.uuid4()
    websocket = AsyncMock()
    captured: dict = {}

    class Field:
        def __init__(self, name):
            self.name = name

        def __eq__(self, other):
            return (self.name, other)

    class FakeQuery:
        def __init__(self, model):
            self.model = model
            self.filters = []

        def where(self, *conditions):
            self.filters.extend(conditions)
            return self

    class FakeResult:
        def __init__(self, value):
            self.value = value

        def scalar_one_or_none(self):
            return self.value

    class FakeDb:
        def __init__(self, session_obj):
            self.session_obj = session_obj
            self.committed = False

        async def execute(self, query):
            assert ("id", session_id) in query.filters
            assert ("competition_id", competition_id) in query.filters
            assert ("game_type", "mutaraha") in query.filters
            return FakeResult(self.session_obj)

        async def commit(self):
            self.committed = True

        async def rollback(self):
            raise AssertionError("rollback should not be called for a valid action")

    class FakeSessionContext:
        def __init__(self, db):
            self.db = db

        async def __aenter__(self):
            return self.db

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeMinigameSession:
        id = Field("id")
        competition_id = Field("competition_id")
        game_type = Field("game_type")

    session_obj = types.SimpleNamespace(
        id=session_id,
        competition_id=competition_id,
        game_type="mutaraha",
        phase="in_progress",
        revision=4,
        current_turn="player_1",
        turn_number=0,
        player_1_membership_id=membership_info["membership_id"],
        player_2_membership_id=opponent_id,
        game_state={"game_phase": "battle"},
    )
    fake_db = FakeDb(session_obj)

    async def fake_check_idempotency(_db, _action_id):
        return None

    async def fake_process_action(_db, *, mg_session, plugin, envelope):
        captured["envelope"] = dict(envelope)
        assert mg_session is session_obj
        assert hasattr(plugin, "build_public_view")
        return {"success": True, "revision": 5}

    def fake_validate_action_envelope(**kwargs):
        captured["validated_envelope"] = dict(kwargs["envelope"])
        return None

    fake_sqlalchemy = types.ModuleType("sqlalchemy")
    fake_sqlalchemy.select = lambda model: FakeQuery(model)
    fake_core_db = types.ModuleType("app.core.database")
    fake_core_db.async_session = lambda: FakeSessionContext(fake_db)
    fake_models = types.ModuleType("app.modules.minigames.models")
    fake_models.MinigameSession = FakeMinigameSession
    fake_action_service = types.ModuleType("app.modules.minigames.action_service")
    fake_action_service.validate_action_envelope = fake_validate_action_envelope
    fake_action_service.check_idempotency = fake_check_idempotency
    fake_action_service.process_action = fake_process_action
    fake_registry = types.ModuleType("app.modules.minigames.registry")
    fake_registry.GameTypeRegistry = types.SimpleNamespace(
        get=lambda game_type: types.SimpleNamespace(build_public_view=lambda state, viewer_id: state)
    )

    monkeypatch.setitem(sys.modules, "sqlalchemy", fake_sqlalchemy)
    monkeypatch.setitem(sys.modules, "app.core.database", fake_core_db)
    monkeypatch.setitem(sys.modules, "app.modules.minigames.models", fake_models)
    monkeypatch.setitem(sys.modules, "app.modules.minigames.action_service", fake_action_service)
    monkeypatch.setitem(sys.modules, "app.modules.minigames.registry", fake_registry)

    await ws_module._handle_action_submit(
        websocket,
        {
            "type": "action_submit",
            "session_id": str(session_id),
            "envelope": {
                "actor_membership_id": str(uuid.uuid4()),
                "state_revision": "4",
                "client_seq": "2",
                "action": {"type": "guess"},
            },
        },
        competition_id,
        "mutaraha",
        membership_info,
    )

    assert fake_db.committed is True
    assert captured["validated_envelope"]["actor_membership_id"] == membership_info["membership_id"]
    assert captured["validated_envelope"]["session_id"] == session_id
    assert captured["validated_envelope"]["state_revision"] == 4
    assert captured["validated_envelope"]["client_seq"] == 2
    assert websocket.send_json.await_count == 1
    assert websocket.send_json.await_args.args[0] == {
        "type": "action_ack",
        "action_id": None,
        "result": {"success": True, "revision": 5},
        "cached": False,
    }


@pytest.mark.asyncio
async def test_action_submit_sends_public_state_and_sanitizes_opponent_notification(ws_module, monkeypatch):
    competition_id = uuid.uuid4()
    session_id = uuid.uuid4()
    actor_info = _membership("المهاجم")
    opponent_id = uuid.uuid4()
    actor_ws = AsyncMock()
    opponent_ws = AsyncMock()
    captured: dict = {}

    ws_module.manager.connect(f"session:{session_id}", actor_info["membership_id"], actor_ws)
    ws_module.manager.connect(f"session:{session_id}", opponent_id, opponent_ws)

    class Field:
        def __init__(self, name):
            self.name = name

        def __eq__(self, other):
            return (self.name, other)

    class FakeQuery:
        def __init__(self, model):
            self.model = model
            self.filters = []

        def where(self, *conditions):
            self.filters.extend(conditions)
            return self

    class FakeResult:
        def __init__(self, value):
            self.value = value

        def scalar_one_or_none(self):
            return self.value

    class FakeDb:
        def __init__(self, session_obj):
            self.session_obj = session_obj

        async def execute(self, query):
            assert ("id", session_id) in query.filters
            assert ("competition_id", competition_id) in query.filters
            assert ("game_type", "mutaraha") in query.filters
            return FakeResult(self.session_obj)

        async def commit(self):
            return None

        async def rollback(self):
            raise AssertionError("rollback should not be called for a valid action")

    class FakeSessionContext:
        def __init__(self, db):
            self.db = db

        async def __aenter__(self):
            return self.db

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeMinigameSession:
        id = Field("id")
        competition_id = Field("competition_id")
        game_type = Field("game_type")

    session_obj = types.SimpleNamespace(
        id=session_id,
        competition_id=competition_id,
        game_type="mutaraha",
        phase="in_progress",
        revision=4,
        current_turn="player_1",
        turn_number=0,
        player_1_membership_id=actor_info["membership_id"],
        player_2_membership_id=opponent_id,
        game_state={"game_phase": "battle"},
    )
    fake_db = FakeDb(session_obj)

    async def fake_check_idempotency(_db, _action_id):
        return None

    async def fake_process_action(_db, *, mg_session, plugin, envelope):
        captured["envelope"] = dict(envelope)
        assert mg_session is session_obj
        return {
            "success": True,
            "revision": 5,
            "side_effects": [{"type": "tool_result", "result": {"secret": 1}}],
            "_state": {"game_phase": "battle", "revision": 5},
            "_current_turn": "player_2",
            "_turn_number": 1,
        }

    def fake_validate_action_envelope(**kwargs):
        return None

    class FakePlugin:
        def build_public_view(self, state, viewer_membership_id):
            return {"viewer": str(viewer_membership_id), "phase": state["game_phase"]}

    fake_sqlalchemy = types.ModuleType("sqlalchemy")
    fake_sqlalchemy.select = lambda model: FakeQuery(model)
    fake_core_db = types.ModuleType("app.core.database")
    fake_core_db.async_session = lambda: FakeSessionContext(fake_db)
    fake_models = types.ModuleType("app.modules.minigames.models")
    fake_models.MinigameSession = FakeMinigameSession
    fake_action_service = types.ModuleType("app.modules.minigames.action_service")
    fake_action_service.validate_action_envelope = fake_validate_action_envelope
    fake_action_service.check_idempotency = fake_check_idempotency
    fake_action_service.process_action = fake_process_action
    fake_registry = types.ModuleType("app.modules.minigames.registry")
    fake_registry.GameTypeRegistry = types.SimpleNamespace(get=lambda game_type: FakePlugin())

    monkeypatch.setitem(sys.modules, "sqlalchemy", fake_sqlalchemy)
    monkeypatch.setitem(sys.modules, "app.core.database", fake_core_db)
    monkeypatch.setitem(sys.modules, "app.modules.minigames.models", fake_models)
    monkeypatch.setitem(sys.modules, "app.modules.minigames.action_service", fake_action_service)
    monkeypatch.setitem(sys.modules, "app.modules.minigames.registry", fake_registry)

    await ws_module._handle_action_submit(
        actor_ws,
        {
            "type": "action_submit",
            "session_id": str(session_id),
            "envelope": {
                "state_revision": 4,
                "client_seq": 2,
                "action": {"type": "GUESS"},
            },
        },
        competition_id,
        "mutaraha",
        actor_info,
    )

    actor_messages = [call.args[0] for call in actor_ws.send_json.await_args_list]
    assert actor_messages[0] == {
        "type": "action_ack",
        "action_id": None,
        "result": {
            "success": True,
            "revision": 5,
            "side_effects": [{"type": "tool_result", "result": {"secret": 1}}],
        },
        "cached": False,
    }
    assert actor_messages[1] == {
        "type": "game_state",
        "session_id": str(session_id),
        "phase": "in_progress",
        "revision": 5,
        "current_turn": "player_2",
        "turn_number": 1,
        "state": {"viewer": str(actor_info["membership_id"]), "phase": "battle"},
    }

    opponent_messages = [call.args[0] for call in opponent_ws.send_json.await_args_list]
    assert opponent_messages[0] == {
        "type": "opponent_action",
        "session_id": str(session_id),
        "revision": 5,
        "action_type": "GUESS",
        "actor_membership_id": str(actor_info["membership_id"]),
    }
    assert opponent_messages[1] == {
        "type": "game_state",
        "session_id": str(session_id),
        "phase": "in_progress",
        "revision": 5,
        "current_turn": "player_2",
        "turn_number": 1,
        "state": {"viewer": str(opponent_id), "phase": "battle"},
    }
