from __future__ import annotations

import asyncio
from collections import deque
from types import SimpleNamespace

import pytest

from pymax.app import App
from pymax.auth.models import AuthResult
from pymax.base import BaseClient
from pymax.dispatch import Dispatcher, EventType, Router
from pymax.exceptions import ApiError
from pymax.protocol import Command, InboundFrame, Opcode
from pymax.session.models import SessionInfo
from tests.conftest import frame, make_config, profile_payload


class RuntimeStore:
    def __init__(self, loaded: SessionInfo | None = None) -> None:
        self.loaded = loaded
        self.saved: list[SessionInfo] = []
        self.deleted: list[str] = []
        self.deleted_all = False
        self.closed = False

    async def load_session(self) -> SessionInfo | None:
        return self.loaded

    async def save_session(self, session: SessionInfo) -> None:
        self.saved.append(session)
        self.loaded = session

    async def update_token(self, old_token: str, new_token: str) -> None:
        if self.loaded and self.loaded.token == old_token:
            self.loaded = self.loaded.model_copy(update={"token": new_token})

    async def delete_session(self, token: str) -> None:
        self.deleted.append(token)
        if self.loaded and self.loaded.token == token:
            self.loaded = None

    async def delete_all_sessions(self) -> None:
        self.deleted_all = True
        self.loaded = None

    async def close(self) -> None:
        self.closed = True


class RuntimeConnection:
    def __init__(self, responses: list[InboundFrame]) -> None:
        self.responses = deque(responses)
        self.protocol = SimpleNamespace(version=10)
        self.sent = []
        self.opened = False
        self.closed = False
        self.failed = None
        self.on_event = None
        self.on_close = None
        self._seq = -1

    async def open(self) -> None:
        self.opened = True

    async def close(self) -> None:
        self.closed = True
        self.opened = False

    async def fail(self, exc: Exception | None = None) -> None:
        self.failed = exc
        self.opened = False
        if self.on_close:
            self.on_close(exc)

    async def request(self, outbound, timeout=None):
        self.sent.append((outbound, timeout))
        return self.responses.popleft()

    async def wait_closed(self) -> None:
        return None

    def next_seq(self) -> int:
        self._seq += 1
        return self._seq

    @property
    def is_open(self) -> bool:
        return self.opened


class StaticAuthFlow:
    async def authenticate(self, app: App) -> AuthResult:
        return AuthResult(token="auth-token")


class RuntimeClient(BaseClient["RuntimeClient"]):
    def __init__(self, app: App["RuntimeClient"], router: Router["RuntimeClient"]) -> None:
        self._app = app
        self._connection = app.connection
        self._router = router
        self._config = app.config
        self._auth_flow = app.auth_flow
        self.extra_config = SimpleNamespace(
            reconnect=False,
            reconnect_delay=0,
            token=app.config.token,
        )

    def _build_connection(self) -> RuntimeConnection:
        return self._connection


@pytest.mark.asyncio
async def test_app_start_with_config_token_handshakes_logs_in_and_saves_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def idle_ping_loop(self):
        await asyncio.Event().wait()

    monkeypatch.setattr(App, "_ping_loop", idle_ping_loop)
    store = RuntimeStore()
    config = make_config().model_copy(update={"token": "config-token", "store": store})
    connection = RuntimeConnection(
        [
            frame({"callsSeed": 123}),
            frame(
                {
                    "profile": profile_payload(77),
                    "token": "login-token",
                    "contacts": [profile_payload(77)["contact"]],
                    "chats": [],
                    "messages": {},
                }
            ),
        ]
    )
    app: App[object] = App(connection, config, StaticAuthFlow())

    await app.start()

    assert app.started is True
    assert app.me is not None
    assert app.me.contact.id == 77
    assert store.saved[0].token == "config-token"
    assert [sent[0].opcode for sent in connection.sent] == [
        Opcode.SESSION_INIT,
        Opcode.LOGIN,
    ]

    await app.close()
    assert connection.closed is True
    assert store.closed is True


@pytest.mark.asyncio
async def test_app_start_emits_login_errors_to_root_router(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def idle_ping_loop(self):
        await asyncio.Event().wait()

    monkeypatch.setattr(App, "_ping_loop", idle_ping_loop)
    store = RuntimeStore()
    config = make_config().model_copy(update={"token": "config-token", "store": store})
    connection = RuntimeConnection(
        [
            frame({"callsSeed": 123}),
            InboundFrame(
                opcode=Opcode.LOGIN,
                cmd=Command.ERROR,
                seq=1,
                payload={
                    "error": "login_failed",
                    "title": "Login failed",
                    "message": "Login failed",
                    "localizedMessage": "Login failed",
                },
            ),
        ]
    )
    root_router: Router[object] = Router()
    app: App[object] = App(connection, config, StaticAuthFlow(), root_router)
    client = object()
    app.dispatcher.bind_client(client)
    seen = []

    @root_router.on_error()
    async def on_error(exc, ctx):
        seen.append((exc, ctx))

    await app.start()

    assert len(seen) == 1
    exc, ctx = seen[0]
    assert isinstance(exc, ApiError)
    assert ctx.client is client
    assert ctx.event_type is EventType.ON_START
    assert ctx.event is None
    assert ctx.router is root_router
    assert ctx.handler is None
    assert app.started is False
    assert connection.closed is True
    assert store.closed is True

    await app.close()


@pytest.mark.asyncio
async def test_client_start_does_not_emit_on_start_after_handled_login_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def idle_ping_loop(self):
        await asyncio.Event().wait()

    monkeypatch.setattr(App, "_ping_loop", idle_ping_loop)
    store = RuntimeStore()
    config = make_config().model_copy(update={"token": "config-token", "store": store})
    connection = RuntimeConnection(
        [
            frame({"callsSeed": 123}),
            InboundFrame(
                opcode=Opcode.LOGIN,
                cmd=Command.ERROR,
                seq=1,
                payload={
                    "error": "login_failed",
                    "title": "Login failed",
                    "message": "Login failed",
                    "localizedMessage": "Login failed",
                },
            ),
        ]
    )
    root_router: Router[RuntimeClient] = Router()
    app: App[RuntimeClient] = App(connection, config, StaticAuthFlow(), root_router)
    client = RuntimeClient(app, root_router)
    app.dispatcher.bind_client(client)
    errors: list[Exception] = []
    started = False

    @root_router.on_error()
    async def on_error(exc, ctx):
        errors.append(exc)

    @root_router.on_start()
    async def on_start(_client):
        nonlocal started
        started = True

    await client.start()

    assert len(errors) == 1
    assert isinstance(errors[0], ApiError)
    assert started is False
    assert app.started is False
    assert connection.closed is True
    assert store.closed is True


@pytest.mark.asyncio
async def test_client_start_emits_disconnect_before_reraising_without_reconnect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def idle_ping_loop(self):
        await asyncio.Event().wait()

    async def fail_wait_closed() -> None:
        raise ConnectionError("Connection lost")

    monkeypatch.setattr(App, "_ping_loop", idle_ping_loop)
    store = RuntimeStore()
    config = make_config().model_copy(update={"token": "config-token", "store": store})
    connection = RuntimeConnection(
        [
            frame({"callsSeed": 123}),
            frame(
                {
                    "profile": profile_payload(77),
                    "token": "login-token",
                    "contacts": [profile_payload(77)["contact"]],
                    "chats": [],
                    "messages": {},
                }
            ),
        ]
    )
    connection.wait_closed = fail_wait_closed
    root_router: Router[RuntimeClient] = Router()
    app: App[RuntimeClient] = App(connection, config, StaticAuthFlow(), root_router)
    client = RuntimeClient(app, root_router)
    app.dispatcher.bind_client(client)
    seen: list[tuple[str, bool, float]] = []

    @root_router.on_disconnect()
    async def on_disconnect(exc, reconnect, delay):
        seen.append((str(exc), reconnect, delay))

    with pytest.raises(ConnectionError, match="Connection lost"):
        await client.start()

    assert seen == [("Connection lost", False, 0)]
    assert connection.closed is True
    assert store.closed is True


@pytest.mark.asyncio
async def test_emit_disconnect_logs_handler_errors_without_raising() -> None:
    app = SimpleNamespace()
    router: Router[object] = Router()
    dispatcher: Dispatcher[object] = Dispatcher(app, router)
    dispatcher.bind_client(object())
    seen: list[str] = []

    @router.on_disconnect()
    async def broken(_exc, _reconnect, _delay):
        raise RuntimeError("handler failed")

    @router.on_disconnect()
    async def next_handler(exc, reconnect, delay):
        seen.append(f"{exc}:{reconnect}:{delay}")

    await dispatcher.emit_disconnect(ConnectionError("lost"), True, 1.5)

    assert seen == ["lost:True:1.5"]


@pytest.mark.asyncio
async def test_client_relogin_deletes_loaded_session_only() -> None:
    session = SessionInfo(token="token", device_id="dev", phone="")
    store = RuntimeStore(session)
    config = make_config().model_copy(update={"store": store, "token": "config-token"})
    connection = RuntimeConnection([])
    root_router: Router[RuntimeClient] = Router()
    app: App[RuntimeClient] = App(connection, config, StaticAuthFlow(), root_router)
    app.session = session
    client = RuntimeClient(app, root_router)
    app.dispatcher.bind_client(client)

    await client.relogin(start=False)

    assert store.deleted == ["token"]
    assert store.deleted_all is False
    assert store.loaded is None
    assert client.extra_config.token is None
    assert client._config.token is None


@pytest.mark.asyncio
async def test_client_relogin_requires_loaded_session() -> None:
    store = RuntimeStore()
    config = make_config().model_copy(update={"store": store})
    connection = RuntimeConnection([])
    root_router: Router[RuntimeClient] = Router()
    app: App[RuntimeClient] = App(connection, config, StaticAuthFlow(), root_router)
    client = RuntimeClient(app, root_router)
    app.dispatcher.bind_client(client)

    with pytest.raises(RuntimeError, match="Cannot relogin before session is loaded"):
        await client.relogin(start=False)

    assert store.deleted == []
    assert store.deleted_all is False


@pytest.mark.asyncio
async def test_app_invoke_turns_error_frames_into_api_error() -> None:
    store = RuntimeStore(SessionInfo(token="token", device_id="dev", phone="+7"))
    config = make_config().model_copy(update={"store": store})
    connection = RuntimeConnection(
        [
            InboundFrame(
                opcode=Opcode.PING,
                cmd=Command.ERROR,
                seq=1,
                payload={
                    "error": "rate_limited",
                    "title": "Slow down",
                    "message": "Too many requests",
                    "localizedMessage": "Too many requests",
                },
            )
        ]
    )
    app: App[object] = App(connection, config, StaticAuthFlow())

    with pytest.raises(ApiError) as exc_info:
        await app.invoke(Opcode.PING, {"interactive": True})

    assert exc_info.value.error == "rate_limited"
    assert exc_info.value.opcode == Opcode.PING
    assert connection.sent[0][0].seq == 0


@pytest.mark.asyncio
async def test_app_invoke_uses_config_timeout_and_allows_override() -> None:
    store = RuntimeStore(SessionInfo(token="token", device_id="dev", phone="+7"))
    config = make_config().model_copy(update={"request_timeout": 12.5, "store": store})
    connection = RuntimeConnection([frame({}), frame({})])
    app: App[object] = App(connection, config, StaticAuthFlow())

    await app.invoke(Opcode.PING, {"interactive": True})
    await app.invoke(Opcode.PING, {"interactive": True}, timeout=3.0)

    assert connection.sent[0][1] == 12.5
    assert connection.sent[1][1] == 3.0


@pytest.mark.asyncio
async def test_app_marks_stopped_and_cancels_ping_on_connection_loss(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def idle_ping_loop(self):
        await asyncio.Event().wait()

    monkeypatch.setattr(App, "_ping_loop", idle_ping_loop)
    store = RuntimeStore()
    config = make_config().model_copy(update={"token": "config-token", "store": store})
    connection = RuntimeConnection(
        [
            frame({"callsSeed": 123}),
            frame(
                {
                    "profile": profile_payload(77),
                    "contacts": [profile_payload(77)["contact"]],
                    "chats": [],
                    "messages": {},
                }
            ),
        ]
    )
    app: App[object] = App(connection, config, StaticAuthFlow())

    await app.start()
    assert app.started is True
    ping_task = app._ping_task
    assert ping_task is not None

    await connection.fail(ConnectionError("lost"))
    await asyncio.sleep(0)

    assert app.started is False
    assert ping_task.cancelled()

    await app.close()
