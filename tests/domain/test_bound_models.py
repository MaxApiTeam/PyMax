from __future__ import annotations

import pytest

from pymax.types.domain import Chat, Message, User
from tests.conftest import chat_payload, message_payload, user_payload


class MessageActions:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple, dict]] = []

    async def send_message(self, *args, **kwargs):
        self.calls.append(("send_message", args, kwargs))
        return "sent"

    async def forward_message(self, *args, **kwargs):
        self.calls.append(("forward_message", args, kwargs))
        return "forwarded"

    async def get_message(self, *args, **kwargs):
        self.calls.append(("get_message", args, kwargs))
        return "message"

    async def get_messages(self, *args, **kwargs):
        self.calls.append(("get_messages", args, kwargs))
        return ["messages"]

    async def edit_message(self, *args, **kwargs):
        self.calls.append(("edit_message", args, kwargs))
        return "edited"

    async def pin_message(self, *args, **kwargs):
        self.calls.append(("pin_message", args, kwargs))
        return True

    async def delete_message(self, *args, **kwargs):
        self.calls.append(("delete_message", args, kwargs))
        return True

    async def read_message(self, *args, **kwargs):
        self.calls.append(("read_message", args, kwargs))
        return "read"

    async def add_reaction(self, *args, **kwargs):
        self.calls.append(("add_reaction", args, kwargs))
        return "reacted"

    async def remove_reaction(self, *args, **kwargs):
        self.calls.append(("remove_reaction", args, kwargs))
        return "removed"

    async def get_reactions(self, *args, **kwargs):
        self.calls.append(("get_reactions", args, kwargs))
        return {"10": "reaction"}

    async def fetch_history(self, *args, **kwargs):
        self.calls.append(("fetch_history", args, kwargs))
        return ["history"]


class ChatActions:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple, dict]] = []

    async def leave_group(self, *args, **kwargs):
        self.calls.append(("leave_group", args, kwargs))

    async def leave_channel(self, *args, **kwargs):
        self.calls.append(("leave_channel", args, kwargs))

    async def invite_users_to_group(self, *args, **kwargs):
        self.calls.append(("invite_users_to_group", args, kwargs))
        return "group"

    async def invite_users_to_channel(self, *args, **kwargs):
        self.calls.append(("invite_users_to_channel", args, kwargs))
        return "channel"

    async def remove_users_from_group(self, *args, **kwargs):
        self.calls.append(("remove_users_from_group", args, kwargs))
        return True

    async def change_group_settings(self, *args, **kwargs):
        self.calls.append(("change_group_settings", args, kwargs))

    async def rework_invite_link(self, *args, **kwargs):
        self.calls.append(("rework_invite_link", args, kwargs))
        return "new-link"

    async def delete_chat(self, *args, **kwargs):
        self.calls.append(("delete_chat", args, kwargs))


class UserActions:
    async def add_contact(self, user_id):
        return f"add:{user_id}"

    async def remove_contact(self, user_id):
        return user_id == 1

    def get_chat_id(self, first, second):
        return first ^ second


@pytest.mark.asyncio
async def test_message_bound_methods_delegate_with_chat_and_message_ids() -> None:
    actions = MessageActions()
    message = Message.model_validate(message_payload(10, 100)).bind(actions)

    assert await message.reply("reply") == "sent"
    assert await message.answer("answer", reply_to=9) == "sent"
    assert await message.forward(200, notify=False) == "forwarded"
    assert (
        await message.edit(
            "edited",
            attachments=["file"],
        )
        == "edited"
    )
    assert await message.pin(notify_pin=False) is True
    assert await message.delete(for_me=True) is True
    assert await message.read() == "read"
    assert await message.react("👍") == "reacted"
    assert await message.unreact() == "removed"
    assert await message.get_reactions() == {"10": "reaction"}

    assert actions.calls[0][2]["reply_to"] == 10
    assert actions.calls[1][2]["reply_to"] == 9
    assert actions.calls[2][2] == {
        "chat_id": 200,
        "message_id": 10,
        "source_chat_id": 100,
        "notify": False,
    }
    assert actions.calls[3][2]["message_id"] == 10
    assert actions.calls[3][2]["attachments"] == ["file"]
    assert actions.calls[5][2]["message_ids"] == [10]
    assert actions.calls[7][2]["message_id"] == 10


@pytest.mark.asyncio
async def test_unbound_message_raises_helpful_runtime_errors() -> None:
    with pytest.raises(RuntimeError, match="not bound"):
        await Message.model_validate(message_payload(10, 100)).answer("x")

    with pytest.raises(RuntimeError, match="chat_id"):
        await Message.model_validate(message_payload(10, None)).bind(MessageActions()).answer("x")


@pytest.mark.asyncio
async def test_chat_bound_methods_delegate_by_chat_type() -> None:
    messages = MessageActions()
    chats = ChatActions()
    group = Chat.model_validate(
        {
            **chat_payload(100, "CHAT"),
            "lastEventTime": 555,
        }
    ).bind(messages, chats)
    channel = Chat.model_validate(chat_payload(200, "CHANNEL")).bind(messages, chats)

    assert await group.answer("hello") == "sent"
    assert await group.history(backward=1) == ["history"]
    assert await group.get_message(10) == "message"
    assert await group.get_messages([10, 11]) == ["messages"]
    await group.leave()
    await channel.leave()
    assert await group.invite([1, 2]) == "group"
    assert await channel.invite([3]) == "channel"
    assert await group.remove_users([2]) is True
    assert await group.pin_message(10) is True
    await group.update_settings(all_can_pin_message=True)
    assert await group.rework_invite_link() == "new-link"
    await group.delete(for_all=False)

    assert messages.calls[0][2]["chat_id"] == 100
    assert chats.calls[0][0] == "leave_group"
    assert chats.calls[1][0] == "leave_channel"
    assert chats.calls[-1] == (
        "delete_chat",
        (100,),
        {
            "last_event_time": 555,
            "for_all": False,
        },
    )
    assert group.is_group is True
    assert channel.is_channel is True


def test_chat_bind_also_binds_nested_messages() -> None:
    messages = MessageActions()
    chats = ChatActions()
    payload = {
        **chat_payload(100, "CHAT"),
        "lastMessage": message_payload(10, 100),
        "pinnedMessage": message_payload(11, 100),
    }

    chat = Chat.model_validate(payload).bind(messages, chats)

    assert chat.last_message is not None
    assert chat.pinned_message is not None
    assert chat.last_message._actions is messages
    assert chat.pinned_message._actions is messages


@pytest.mark.asyncio
async def test_dialog_leave_and_unbound_chat_raise_errors() -> None:
    dialog = Chat.model_validate(chat_payload(1, "DIALOG")).bind(MessageActions(), ChatActions())

    with pytest.raises(RuntimeError, match="Cannot leave dialog"):
        await dialog.leave()

    with pytest.raises(RuntimeError, match="not bound"):
        await Chat.model_validate(chat_payload(2)).answer("x")


@pytest.mark.asyncio
async def test_user_bound_methods_delegate_to_user_service() -> None:
    user = User.model_validate(user_payload(1)).bind(UserActions())

    assert await user.add_contact() == "add:1"
    assert await user.remove_contact() is True
    assert user.get_chat_id(7) == 6

    with pytest.raises(RuntimeError, match="not bound"):
        await User.model_validate(user_payload(2)).add_contact()
