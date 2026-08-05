from types import SimpleNamespace

from pymax.filters import Command, F, FromMe, HasAttachment
from pymax.types import Chat, Message, PhotoAttachment


def make_message(**kwargs) -> Message:
    return Message(
        id=kwargs.pop("id", 1),
        chat_id=kwargs.pop("chat_id", 100),
        sender=kwargs.pop("sender", 10),
        text=kwargs.pop("text", "hello world"),
        time=kwargs.pop("time", 1_700_000_000),
        type=kwargs.pop("type", "USER"),
        **kwargs,
    )


def make_chat(**kwargs) -> Chat:
    return Chat(
        id=kwargs.pop("id", 100),
        type=kwargs.pop("type", "CHAT"),
        status=kwargs.pop("status", "ACTIVE"),
        owner=kwargs.pop("owner", 10),
        title=kwargs.pop("title", "PyMax developers"),
        **kwargs,
    )


def make_client(user_id: int = 10) -> SimpleNamespace:
    return SimpleNamespace(me=SimpleNamespace(contact=SimpleNamespace(id=user_id)))


def make_photo() -> PhotoAttachment:
    return PhotoAttachment(
        base_url="https://example.com/photo.jpg",
        height=100,
        width=100,
        photo_id=1,
        photo_token="photo-token",
        _type="PHOTO",
    )


def test_message_container_exposes_all_message_fields() -> None:
    fields = {name for name, value in vars(type(F.message)).items() if isinstance(value, property)}

    assert fields == set(Message.model_fields)


def test_chat_container_exposes_all_chat_fields() -> None:
    fields = {name for name, value in vars(type(F.chat)).items() if isinstance(value, property)}

    assert fields == set(Chat.model_fields)


def test_message_field_filters_support_comparison_and_logical_operations() -> None:
    message = make_message()
    client = make_client()
    filter_ = F.message.text.contains("hello") & ~(F.message.sender == 20)

    assert filter_(message, client) is True
    assert (F.message.chat_id == 100)(message, client) is True
    assert (F.message.chat_id == 200)(message, client) is False


def test_chat_field_filters_support_comparison_and_logical_operations() -> None:
    chat = make_chat()
    client = make_client()
    filter_ = F.chat.title.contains("PyMax") & (F.chat.owner == 10)

    assert filter_(chat, client) is True
    assert (F.chat.status == "INACTIVE")(chat, client) is False


def test_containers_and_fields_reject_another_event_type() -> None:
    message = make_message()
    chat = make_chat()
    client = make_client()

    assert F.message(chat, client) is False
    assert F.chat(message, client) is False
    assert (F.message.id == 100)(chat, client) is False
    assert (F.chat.id == 1)(message, client) is False


def test_nested_message_containers_resolve_chat_message_fields() -> None:
    client = make_client()
    chat = make_chat(
        last_message=make_message(text="Last message"),
        pinned_message=make_message(id=2, text="Pinned message"),
    )

    assert F.chat.last_message(chat, client) is True
    assert F.chat.last_message.text.startswith("Last")(chat, client) is True
    assert (F.chat.last_message.sender == 10)(chat, client) is True
    assert F.chat.pinned_message.text.endswith("message")(chat, client) is True
    assert F.chat.last_message(make_chat(), client) is False


def test_number_field_filters_support_comparisons_and_inclusive_between() -> None:
    message = make_message(time=100)
    client = make_client()

    assert (F.message.time > 99)(message, client) is True
    assert (F.message.time >= 100)(message, client) is True
    assert (F.message.time < 101)(message, client) is True
    assert (F.message.time <= 100)(message, client) is True
    assert F.message.time.between(100, 100)(message, client) is True
    assert F.message.time.between(101, 200)(message, client) is False
    assert F.message.id.between(1, 10)(message, client) is True


def test_text_field_filters_support_case_sensitive_and_insensitive_matching() -> None:
    message = make_message(text="Hello PyMax")
    client = make_client()

    assert F.message.text.contains("hello")(message, client) is False
    assert F.message.text.contains("hello", ignore_case=True)(message, client) is True
    assert F.message.text.startswith("HELLO", ignore_case=True)(message, client) is True
    assert F.message.text.endswith("PYMAX", ignore_case=True)(message, client) is True


def test_presets_support_and_composition() -> None:
    client = make_client()
    filter_ = HasAttachment(PhotoAttachment) & FromMe()

    assert filter_(make_message(attaches=[make_photo()]), client) is True
    assert filter_(make_message(sender=20, attaches=[make_photo()]), client) is False
    assert filter_(make_message(), client) is False


def test_presets_support_or_composition() -> None:
    client = make_client()
    filter_ = Command("start") | HasAttachment(PhotoAttachment)

    assert filter_(make_message(text="/start"), client) is True
    assert filter_(make_message(text="hello", attaches=[make_photo()]), client) is True
    assert filter_(make_message(text="hello"), client) is False
