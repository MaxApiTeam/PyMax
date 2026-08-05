from __future__ import annotations

import pytest

from pymax.dispatch import Dispatcher, Router
from pymax.dispatch.enums import EventType
from pymax.filters import F
from pymax.protocol import Command, Opcode
from tests.conftest import FakeApp, chat_payload, frame, message_payload


@pytest.mark.asyncio
async def test_dispatcher_routes_message_events_through_filters_and_raw_handler() -> None:
    app = FakeApp()
    router: Router[str] = Router()
    dispatcher: Dispatcher[str] = Dispatcher(app, router)
    dispatcher.bind_client("client")
    seen: list[tuple[str, int | str]] = []

    def is_start(message, _client):
        return message.text == "/start"

    def has_chat(message, _client):
        return message.chat_id == 100

    @router.on_message(is_start, has_chat)
    async def on_message(message, client):
        seen.append((client, message.id))

    @router.on_raw()
    def on_raw(raw_frame, client):
        seen.append((client, f"raw:{raw_frame.opcode}"))

    await dispatcher.dispatch(
        frame(
            {"chatId": 100, "message": message_payload(1, 100, "/start")},
            opcode=Opcode.NOTIF_MESSAGE,
            cmd=Command.REQUEST,
        )
    )

    assert seen == [
        ("client", 1),
        ("client", f"raw:{int(Opcode.NOTIF_MESSAGE)}"),
    ]


@pytest.mark.asyncio
async def test_dispatcher_evaluates_all_magic_filters() -> None:
    app = FakeApp()
    router: Router[str] = Router()
    dispatcher: Dispatcher[str] = Dispatcher(app, router)
    dispatcher.bind_client("client")
    seen: list[int] = []

    @router.on_message(F.message.text.contains("start"), F.message.chat_id == 200)
    async def on_message(message, _client):
        seen.append(message.id)

    await dispatcher.dispatch(
        frame(
            {"chatId": 100, "message": message_payload(1, 100, "/start")},
            opcode=Opcode.NOTIF_MESSAGE,
            cmd=Command.REQUEST,
        )
    )

    assert seen == []


@pytest.mark.asyncio
async def test_dispatcher_maps_chat_delete_and_internal_attach_events() -> None:
    app = FakeApp()
    router: Router[str] = Router()
    child: Router[str] = Router()
    router.include_router(child)
    dispatcher: Dispatcher[str] = Dispatcher(app, router)
    dispatcher.bind_client("client")
    seen: list[tuple[str, object, object | None]] = []

    @child.on_chat_update()
    async def on_chat(chat, _client):
        seen.append(
            (
                "chat",
                chat.id,
                chat.pinned_message._actions is app.api.messages,
            )
        )

    @router.on_message_delete()
    async def on_delete(event, _client):
        seen.append(("delete", tuple(event.message_ids), None))

    @dispatcher.on_internal(EventType.FILE_READY)
    async def on_file(signal, _client):
        seen.append(("file", signal.file_id, None))

    @dispatcher.on_internal(EventType.VOICE_READY)
    async def on_voice(signal, _client):
        seen.append(("voice", signal.audio_id, None))

    await dispatcher.dispatch(
        frame(
            {
                "chat": {
                    **chat_payload(5),
                    "pinnedMessage": message_payload(9, 5),
                }
            },
            opcode=Opcode.NOTIF_CHAT,
            cmd=Command.REQUEST,
        )
    )
    await dispatcher.dispatch(
        frame(
            {
                "chat": chat_payload(5),
                "messageIds": [1, 2],
            },
            opcode=Opcode.NOTIF_MSG_DELETE,
            cmd=Command.REQUEST,
        )
    )
    await dispatcher.dispatch(
        frame({"fileId": 99}, opcode=Opcode.NOTIF_ATTACH, cmd=Command.REQUEST)
    )
    await dispatcher.dispatch(
        frame({"audioId": 100}, opcode=Opcode.NOTIF_ATTACH, cmd=Command.REQUEST)
    )

    assert seen == [
        ("chat", 5, True),
        ("delete", (1, 2), None),
        ("file", 99, None),
        ("voice", 100, None),
    ]


@pytest.mark.asyncio
async def test_dispatcher_maps_web_removed_message_to_delete_event() -> None:
    app = FakeApp()
    router: Router[str] = Router()
    dispatcher: Dispatcher[str] = Dispatcher(app, router)
    dispatcher.bind_client("client")
    seen: list[tuple[int, list[int], int | None, bool, bool]] = []

    @router.on_message_delete()
    async def on_delete(event, _client):
        seen.append(
            (
                event.chat_id,
                event.message_ids,
                event.message.id if event.message is not None else None,
                event.ttl,
                event.message is not None and event.message._actions is app.api.messages,
            )
        )

    await dispatcher.dispatch(
        frame(
            {
                "chatId": 0,
                "message": {
                    "id": "116738762887754287",
                    "time": 1781292158321,
                    "type": "USER",
                    "status": "REMOVED",
                    "text": "deleted",
                    "attaches": [],
                },
                "unread": 0,
                "mark": 1781292158321,
            },
            opcode=Opcode.NOTIF_MESSAGE,
            cmd=Command.REQUEST,
        )
    )

    assert seen == [
        (
            0,
            [116738762887754287],
            116738762887754287,
            False,
            True,
        )
    ]


@pytest.mark.asyncio
async def test_dispatcher_maps_typing_event() -> None:
    app = FakeApp()
    router: Router[str] = Router()
    dispatcher: Dispatcher[str] = Dispatcher(app, router)
    dispatcher.bind_client("client")
    seen: list[tuple[str, object]] = []

    @router.on_typing()
    async def on_typing(event, _client):
        seen.append(("typing", (event.chat_id, event.user_id)))

    await dispatcher.dispatch(
        frame(
            {"chatId": 239067070, "userId": 17620943},
            opcode=Opcode.NOTIF_TYPING,
            cmd=Command.REQUEST,
        )
    )

    assert seen == [("typing", (239067070, 17620943))]


@pytest.mark.asyncio
async def test_dispatcher_maps_reaction_update_event() -> None:
    app = FakeApp()
    router: Router[str] = Router()
    dispatcher: Dispatcher[str] = Dispatcher(app, router)
    dispatcher.bind_client("client")
    seen: list[tuple[str, int, int, int, str]] = []

    @router.on_reaction_update()
    async def on_reaction_update(event, _client):
        seen.append(
            (
                event.message_id,
                event.chat_id,
                event.total_count,
                event.counters[0].count,
                event.counters[0].reaction,
            )
        )

    await dispatcher.dispatch(
        frame(
            {
                "messageId": "116739131144745294",
                "chatId": 239067070,
                "counters": [{"count": 1, "reaction": "👍"}],
                "totalCount": 1,
            },
            opcode=Opcode.NOTIF_MSG_REACTIONS_CHANGED,
            cmd=Command.REQUEST,
        )
    )

    assert seen == [("116739131144745294", 239067070, 1, 1, "👍")]


@pytest.mark.asyncio
async def test_dispatcher_maps_message_read_event() -> None:
    app = FakeApp()
    router: Router[str] = Router()
    dispatcher: Dispatcher[str] = Dispatcher(app, router)
    dispatcher.bind_client("client")
    seen: list[tuple[bool, int, int, int]] = []

    @router.on_message_read()
    async def on_message_read(event, _client):
        seen.append(
            (
                event.set_as_unread,
                event.chat_id,
                event.user_id,
                event.mark,
            )
        )

    await dispatcher.dispatch(
        frame(
            {
                "setAsUnread": False,
                "chatId": 239067070,
                "userId": 17620943,
                "mark": 1781354533949,
            },
            opcode=Opcode.NOTIF_MARK,
            cmd=Command.REQUEST,
        )
    )

    assert seen == [(False, 239067070, 17620943, 1781354533949)]


@pytest.mark.asyncio
async def test_dispatcher_maps_presence_event() -> None:
    app = FakeApp()
    router: Router[str] = Router()
    dispatcher: Dispatcher[str] = Dispatcher(app, router)
    dispatcher.bind_client("client")
    seen: list[tuple[int, int, int | None]] = []

    @router.on_presence()
    async def on_presence(event, _client):
        seen.append(
            (
                event.user_id,
                event.presence.status,
                event.presence.seen,
            )
        )

    await dispatcher.dispatch(
        frame(
            {
                "presence": {
                    "seen": 1781354531,
                    "status": 1,
                },
                "userId": 17620943,
            },
            opcode=Opcode.NOTIF_PRESENCE,
            cmd=Command.REQUEST,
        )
    )

    assert seen == [(17620943, 1, 1781354531)]


@pytest.mark.asyncio
async def test_dispatcher_maps_partial_presence_event_without_status() -> None:
    app = FakeApp()
    router: Router[str] = Router()
    dispatcher: Dispatcher[str] = Dispatcher(app, router)
    dispatcher.bind_client("client")
    seen: list[tuple[int, int | None, int | None]] = []

    @router.on_presence()
    async def on_presence(event, _client):
        seen.append(
            (
                event.user_id,
                event.presence.status,
                event.presence.seen,
            )
        )

    await dispatcher.dispatch(
        frame(
            {
                "presence": {"seen": 1781360047},
                "userId": 17620943,
            },
            opcode=Opcode.NOTIF_PRESENCE,
            cmd=Command.REQUEST,
        )
    )

    assert seen == [(17620943, None, 1781360047)]


@pytest.mark.asyncio
async def test_dispatcher_requires_bound_client_for_callbacks() -> None:
    dispatcher: Dispatcher[str] = Dispatcher(FakeApp())

    async def callback(_event, _client):
        return None

    with pytest.raises(RuntimeError, match="client is not bound"):
        await dispatcher._call(callback, object())
