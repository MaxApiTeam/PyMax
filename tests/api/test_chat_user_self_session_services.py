from __future__ import annotations

import pytest

from pymax.api.session.enums import DeviceType
from pymax.exceptions import PyMaxError
from pymax.protocol import Opcode
from pymax.session.models import SessionInfo
from tests.conftest import (
    FakeApp,
    chat_payload,
    frame,
    member_payload,
    message_payload,
    profile_payload,
    user_payload,
)


def test_base_mixin_exposes_chat_join_request_and_bot_methods() -> None:
    from pymax.infra import BaseMixin

    for method_name in (
        "get_join_requests",
        "confirm_join_requests",
        "confirm_join_request",
        "decline_join_requests",
        "decline_join_request",
        "get_bot_init_data",
        "change_password",
    ):
        assert hasattr(BaseMixin, method_name)


@pytest.mark.asyncio
async def test_get_chats_uses_cache_fetches_misses_and_preserves_order() -> None:
    app = FakeApp([frame({"chats": [chat_payload(2), chat_payload(3)]})])
    from pymax.types.domain import Chat

    app.chats = [Chat.model_validate(chat_payload(1)).bind(app.api.messages, app.api.chats)]

    chats = await app.api.chats.get_chats([1, 2, 3])

    assert [chat.id for chat in chats] == [1, 2, 3]
    assert app.calls[0].opcode == Opcode.CHAT_INFO
    assert app.calls[0].payload["chatIds"] == [2, 3]


@pytest.mark.asyncio
async def test_get_chat_raises_when_response_does_not_contain_chat() -> None:
    app = FakeApp([frame({"chats": []})])

    with pytest.raises(PyMaxError, match="Chat not found"):
        await app.api.chats.get_chat(999)


@pytest.mark.asyncio
async def test_join_group_validates_link_and_caches_joined_chat() -> None:
    app = FakeApp([frame({"chat": chat_payload(10)})])

    with pytest.raises(ValueError, match="Invalid group link"):
        await app.api.chats.join_group("https://example.com/nope")

    chat = await app.api.chats.join_group("https://max.ru/join/abc")

    assert chat.id == 10
    assert app.chats == [chat]
    assert app.calls[0].opcode == Opcode.CHAT_JOIN
    assert app.calls[0].payload["link"] == "join/abc"


@pytest.mark.asyncio
async def test_join_channel_accepts_raw_or_invite_links() -> None:
    app = FakeApp(
        [
            frame({"chat": chat_payload(11, "CHANNEL")}),
            frame({"chat": chat_payload(12, "CHANNEL")}),
        ]
    )

    raw_chat = await app.api.chats.join_channel("https://max.ru/channel/news")
    invite_chat = await app.api.chats.join_channel("https://max.ru/join/abc")

    assert raw_chat.id == 11
    assert invite_chat.id == 12
    assert [call.opcode for call in app.calls] == [
        Opcode.CHAT_JOIN,
        Opcode.CHAT_JOIN,
    ]
    assert app.calls[0].payload["link"] == "https://max.ru/channel/news"
    assert app.calls[1].payload["link"] == "join/abc"


@pytest.mark.asyncio
async def test_create_group_returns_chat_and_message_and_updates_cache() -> None:
    app = FakeApp([frame({**message_payload(7, 10), "chat": chat_payload(10)})])

    result = await app.api.chats.create_group("Team", [1, 2], notify=False)

    assert result is not None
    chat, message = result
    assert chat.id == 10
    assert message.id == 7
    assert app.chats == [chat]
    assert app.calls[0].opcode == Opcode.MSG_SEND
    assert app.calls[0].payload["message"]["attaches"][0]["title"] == "Team"
    assert app.calls[0].payload["notify"] is False


@pytest.mark.asyncio
async def test_leave_group_removes_cached_chat() -> None:
    from pymax.types.domain import Chat

    app = FakeApp([frame({})])
    app.chats = [
        Chat.model_validate(chat_payload(10)).bind(app.api.messages, app.api.chats),
        Chat.model_validate(chat_payload(11)).bind(app.api.messages, app.api.chats),
    ]

    await app.api.chats.leave_group(10)

    assert [chat.id for chat in app.chats or []] == [11]
    assert app.calls[0].opcode == Opcode.CHAT_LEAVE


@pytest.mark.asyncio
async def test_chat_mixin_delete_chat_uses_last_event_time_and_removes_cached_chat() -> None:
    from pymax.infra.chat import ChatMixin
    from pymax.types.domain import Chat

    class Client(ChatMixin):
        def __init__(self, app: FakeApp) -> None:
            self._app = app

    app = FakeApp([frame({})])
    chat = Chat.model_validate(
        {
            **chat_payload(10),
            "lastEventTime": 456,
        }
    ).bind(app.api.messages, app.api.chats)
    app.chats = [
        chat,
        Chat.model_validate(chat_payload(11)).bind(app.api.messages, app.api.chats),
    ]
    client = Client(app)

    await client.delete_chat(
        chat.id,
        last_event_time=chat.last_event_time,
        for_all=False,
    )

    assert [chat.id for chat in app.chats or []] == [11]
    assert app.calls[0].opcode == Opcode.CHAT_DELETE
    assert app.calls[0].payload == {
        "chatId": 10,
        "lastEventTime": 456,
        "forAll": False,
    }


@pytest.mark.asyncio
async def test_group_mutation_methods_update_cache_and_parse_optional_chats() -> None:
    app = FakeApp(
        [
            frame({"chat": chat_payload(10, "CHAT")}),
            frame({"chat": chat_payload(10, "CHAT")}),
            frame({"chat": chat_payload(10, "CHAT")}),
            frame({"chat": chat_payload(10, "CHAT")}),
            frame({"chat": chat_payload(10, "CHAT")}),
            frame({"chat": chat_payload(10, "CHAT")}),
            frame({"chat": chat_payload(10, "CHAT")}),
            frame({"chats": [chat_payload(20, "CHANNEL")]}),
        ]
    )

    assert await app.api.chats.invite_users_to_group(10, [1, 2]) is not None
    assert await app.api.chats.invite_users_to_channel(10, [3]) is not None
    assert await app.api.chats.remove_users_from_group(10, [2], clean_msg_period=0)
    await app.api.chats.change_group_settings(10, all_can_pin_message=True)
    await app.api.chats.change_group_profile(10, "New title", "Description")
    resolved = await app.api.chats.resolve_group_by_link("https://max.ru/join/abc")
    reworked = await app.api.chats.rework_invite_link(10)
    fetched = await app.api.chats.fetch_chats(marker=123)

    assert resolved is not None
    assert reworked.id == 10
    assert [chat.id for chat in fetched] == [20]
    assert [call.opcode for call in app.calls] == [
        Opcode.CHAT_MEMBERS_UPDATE,
        Opcode.CHAT_MEMBERS_UPDATE,
        Opcode.CHAT_MEMBERS_UPDATE,
        Opcode.CHAT_UPDATE,
        Opcode.CHAT_UPDATE,
        Opcode.LINK_INFO,
        Opcode.CHAT_UPDATE,
        Opcode.CHATS_LIST,
    ]
    assert app.calls[3].payload["options"]["ALL_CAN_PIN_MESSAGE"] is True
    assert app.calls[4].payload["theme"] == "New title"
    assert app.calls[-1].payload["marker"] == 123


@pytest.mark.asyncio
async def test_join_request_methods_fetch_confirm_decline_and_update_cache() -> None:
    app = FakeApp(
        [
            frame({"members": [member_payload(2)]}),
            frame({"chat": chat_payload(10, "CHAT")}),
            frame({"chat": chat_payload(10, "CHAT")}),
            frame({"chat": chat_payload(10, "CHAT")}),
        ]
    )

    requests = await app.api.chats.get_join_requests(10, count=5)
    confirmed = await app.api.chats.confirm_join_requests(
        10,
        [2, 3],
        show_history=False,
    )
    confirmed_one = await app.api.chats.confirm_join_request(10, 4)
    declined = await app.api.chats.decline_join_request(10, 5)

    assert [request.contact.id for request in requests] == [2]
    assert requests[0].contact._actions is app.api.users
    assert confirmed is not None
    assert confirmed_one is not None
    assert declined is not None
    assert [chat.id for chat in app.chats or []] == [10]
    assert [call.opcode for call in app.calls] == [
        Opcode.CHAT_MEMBERS,
        Opcode.CHAT_MEMBERS_UPDATE,
        Opcode.CHAT_MEMBERS_UPDATE,
        Opcode.CHAT_MEMBERS_UPDATE,
    ]
    assert app.calls[0].payload == {
        "chatId": 10,
        "type": "JOIN_REQUEST",
        "count": 5,
    }
    assert app.calls[1].payload["operation"] == "add"
    assert app.calls[1].payload["userIds"] == [2, 3]
    assert app.calls[1].payload["showHistory"] is False
    assert app.calls[2].payload["operation"] == "add"
    assert app.calls[2].payload["userIds"] == [4]
    assert app.calls[3].payload["operation"] == "remove"
    assert app.calls[3].payload["userIds"] == [5]
    assert "showHistory" not in app.calls[3].payload


@pytest.mark.asyncio
async def test_user_service_fetches_caches_searches_and_removes_contacts() -> None:
    app = FakeApp(
        [
            frame({"contacts": [user_payload(2), user_payload(3)]}),
            frame({"contact": user_payload(4)}),
            frame({"contact": user_payload(2)}),
        ]
    )
    app.users[1] = __import__("pymax.types.domain", fromlist=["User"]).User.model_validate(
        user_payload(1)
    )

    users = await app.api.users.get_users([1, 2, 3])
    found = await app.api.users.search_by_phone("+79990000004")
    removed = await app.api.users.remove_contact(2)

    assert [user.id for user in users] == [1, 2, 3]
    assert found.id == 4
    assert found._actions is app.api.users
    assert removed is True
    assert 2 not in app.users
    assert [call.opcode for call in app.calls] == [
        Opcode.CONTACT_INFO,
        Opcode.CONTACT_INFO_BY_PHONE,
        Opcode.CONTACT_UPDATE,
    ]


@pytest.mark.asyncio
async def test_user_service_get_user_add_contact_sessions_and_chat_id() -> None:
    app = FakeApp(
        [
            frame({"contacts": [user_payload(5)]}),
            frame({"contact": user_payload(6)}),
            frame({"sessions": [{"id": "s1", "deviceId": "device"}]}),
        ]
    )

    user = await app.api.users.get_user(5)
    added = await app.api.users.add_contact(6)
    sessions = await app.api.users.get_sessions()

    assert user is not None
    assert user.id == 5
    assert user._actions is app.api.users
    assert added.id == 6
    assert added._actions is app.api.users
    assert sessions[0].device_id == "device"
    assert app.api.users.get_chat_id(10, 3) == 9
    assert [call.opcode for call in app.calls] == [
        Opcode.CONTACT_INFO,
        Opcode.CONTACT_UPDATE,
        Opcode.SESSIONS_INFO,
    ]


@pytest.mark.asyncio
async def test_user_mixin_import_contacts_delegates_to_user_service() -> None:
    from pymax.infra.user import UserMixin
    from pymax.types import ContactInfo

    class Client(UserMixin):
        def __init__(self, app: FakeApp) -> None:
            self._app = app

    app = FakeApp([frame({"contacts": [user_payload(7)]})])
    client = Client(app)

    contacts = await client.import_contacts(
        [
            ContactInfo(
                phone="+79990000007",
                first_name="Ada",
                last_name=None,
            )
        ]
    )

    assert [contact.id for contact in contacts] == [7]
    assert app.users[7] is contacts[0]
    assert contacts[0]._actions is app.api.users
    assert app.calls[0].opcode == Opcode.SYNC
    assert app.calls[0].payload == {
        "contactList": {
            "+79990000007": {
                "firstName": "Ada",
            }
        }
    }


@pytest.mark.asyncio
async def test_self_service_change_profile_and_close_all_sessions() -> None:
    app = FakeApp(
        [
            frame({"profile": profile_payload(9)}),
            frame({"token": "new-token"}),
        ]
    )
    app.session = SessionInfo(token="old-token", device_id="dev", phone="+7")

    assert await app.api.account.change_profile("Ink", description="hello") is True
    assert app.me is not None
    assert app.me.contact.id == 9
    assert app.me.contact._actions is app.api.users
    assert app.users[9].id == 9

    assert await app.api.account.close_all_sessions() is True
    assert app.store.updated_tokens == [("old-token", "new-token")]
    assert [call.opcode for call in app.calls] == [
        Opcode.PROFILE,
        Opcode.SESSIONS_CLOSE,
    ]


@pytest.mark.asyncio
async def test_close_all_sessions_returns_false_without_session_or_token() -> None:
    app = FakeApp()
    assert await app.api.account.close_all_sessions() is False

    app.session = SessionInfo(token="old-token", device_id="dev", phone="+7")
    app.responses.append(frame({}))
    assert await app.api.account.close_all_sessions() is False
    assert app.store.updated_tokens == []


@pytest.mark.asyncio
async def test_self_service_profile_photo_folders_and_logout() -> None:
    app = FakeApp(
        [
            frame({"url": "https://upload.profile"}),
            frame(
                {
                    "folder": {"id": "folder-1", "title": "Work"},
                    "folderSync": 1,
                }
            ),
            frame(
                {
                    "folders": [{"id": "folder-1", "title": "Work"}],
                    "folderSync": 2,
                }
            ),
            frame({"folder": {"id": "folder-1", "title": "New"}, "folderSync": 3}),
            frame({"foldersOrder": [], "folderSync": 4}),
            frame({}),
        ]
    )

    assert await app.api.account.request_profile_photo_upload_url() == "https://upload.profile"
    created = await app.api.account.create_folder("Work", [10])
    folders = await app.api.account.get_folders(folder_sync=1)
    updated = await app.api.account.update_folder("folder-1", "New", [11])
    deleted = await app.api.account.delete_folder("folder-1")
    assert await app.api.account.logout() is True

    assert created.folder is not None
    assert created.folder.title == "Work"
    assert [folder.id for folder in folders.folders] == ["folder-1"]
    assert updated.folder is not None
    assert updated.folder.title == "New"
    assert deleted.folder_sync == 4
    assert [call.opcode for call in app.calls] == [
        Opcode.PHOTO_UPLOAD,
        Opcode.FOLDERS_UPDATE,
        Opcode.FOLDERS_GET,
        Opcode.FOLDERS_UPDATE,
        Opcode.FOLDERS_DELETE,
        Opcode.LOGOUT,
    ]


@pytest.mark.asyncio
async def test_session_handshake_switches_between_mobile_and_web_payloads() -> None:
    mobile_app = FakeApp([frame({"callsSeed": 101})])
    mobile_response = await mobile_app.api.session.handshake(
        "mt",
        mobile_app.config.device.user_agent,
        "device",
    )

    web_app = FakeApp([frame({"serverTime": 123})], device_type=DeviceType.WEB)
    web_response = await web_app.api.session.handshake(
        "ignored",
        web_app.config.device.user_agent,
        "web-device",
    )

    assert mobile_app.calls[0].opcode == Opcode.SESSION_INIT
    assert mobile_app.calls[0].payload["mt_instanceid"] == "mt"
    assert web_app.calls[0].payload["deviceId"] == "web-device"
    assert web_app.calls[0].payload["userAgent"]["deviceType"] == DeviceType.WEB
    assert "mt_instanceid" not in web_app.calls[0].payload
    assert mobile_response is not None
    assert mobile_response.calls_seed == 101
    assert web_response.calls_seed is None


@pytest.mark.asyncio
async def test_bots_service_parses_init_data() -> None:
    app = FakeApp([frame({"queryId": "query", "url": "https://app"})])

    init_data = await app.api.bots.get_init_data(1, 2, start_param="x")

    assert init_data.query_id == "query"
    assert app.calls[0].opcode == Opcode.WEB_APP_INIT_DATA
    assert app.calls[0].payload == {"botId": 1, "chatId": 2, "startParam": "x"}
