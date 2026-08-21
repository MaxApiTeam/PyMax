from __future__ import annotations

import pytest

from pymax.api.messages.enums import ItemType, MessagePayloadKey
from pymax.api.uploads.payloads import AttachPhotoPayload
from pymax.exceptions import UploadError
from pymax.files import File, Photo, Video, Voice
from pymax.protocol import Opcode
from pymax.types.domain.attachments import VideoRequest
from tests.conftest import FakeApp, frame, message_payload


@pytest.mark.asyncio
async def test_send_message_formats_markdown_uploads_attachments_and_binds_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("pymax.api.messages.service.time.time", lambda: 1000.0)
    app = FakeApp([frame(message_payload(55, 100, "Hello bold"))])
    photo = Photo(raw=b"image", name="image.jpg")

    result = await app.api.messages.send_message(
        100,
        "Hello **bold**",
        reply_to=44,
        attachments=[photo],
        notify=False,
    )

    assert result is not None
    assert result.id == 55
    assert result._actions is app.api.messages
    assert app.api.uploads.calls == [("photo", photo)]
    assert app.calls[0].opcode == Opcode.MSG_SEND
    sent = app.calls[0].payload
    assert sent["chatId"] == 100
    assert sent["notify"] is False
    assert sent["message"]["text"] == "Hello bold"
    assert sent["message"]["cid"] == 1000001
    assert sent["message"]["link"] == {"type": "REPLY", "messageId": 44}
    assert sent["message"]["elements"][0]["type"] == "STRONG"
    assert sent["message"]["attaches"][0]["photoToken"] == "photo-token"


@pytest.mark.asyncio
async def test_send_message_raises_when_attachment_upload_fails() -> None:
    app = FakeApp()
    app.api.uploads.photo_result = None

    with pytest.raises(UploadError, match="Photo uploading failed"):
        await app.api.messages.send_message(
            100,
            "photo",
            attachments=[Photo(raw=b"image", name="image.jpg")],
        )

    assert app.calls == []


@pytest.mark.asyncio
async def test_forward_message_builds_payload_and_binds_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("pymax.api.messages.service.time.time", lambda: 1000.0)
    app = FakeApp([frame(message_payload(55, 200, "forwarded"))])

    result = await app.api.messages.forward_message(
        chat_id=200,
        message_id=116742887450236083,
        source_chat_id=100,
        notify=False,
    )

    assert result is not None
    assert result.id == 55
    assert result._actions is app.api.messages
    assert app.calls[0].opcode == Opcode.MSG_SEND
    assert app.calls[0].payload == {
        "chatId": 200,
        "message": {
            "cid": -1000001,
            "link": {
                "type": "FORWARD",
                "messageId": "116742887450236083",
                "chatId": 100,
            },
            "attaches": [],
        },
        "notify": False,
    }


@pytest.mark.asyncio
async def test_forward_message_defaults_source_to_target_chat() -> None:
    app = FakeApp([frame(message_payload(55, 200, "forwarded"))])

    await app.api.messages.forward_message(chat_id=200, message_id="55")

    assert app.calls[0].payload["message"]["link"]["chatId"] == 200


@pytest.mark.asyncio
async def test_upload_attachments_handles_file_video_and_empty_lists() -> None:
    app = FakeApp()
    assert await app.api.messages._upload_attachments(None) == []

    file = File(raw=b"abc", name="doc.txt")
    voice = Voice(raw=b"voice", name="voice.ogg")
    result = await app.api.messages._upload_attachments([file, voice])

    assert result[0].file_id == 30
    assert result[1].type.value == "AUDIO"
    assert app.api.uploads.calls == [("file", file), ("voice", voice)]


@pytest.mark.asyncio
async def test_fetch_history_builds_payload_and_parses_messages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("pymax.api.messages.service.time.time", lambda: 2000.0)
    app = FakeApp(
        [
            frame(
                {
                    MessagePayloadKey.MESSAGES.value: [
                        message_payload(1, 100, "one"),
                        message_payload(2, 100, "two"),
                    ]
                }
            )
        ]
    )

    messages = await app.api.messages.fetch_history(
        100,
        backward=2,
        from_=123,
        item_type=ItemType.DELAYED,
        get_chat=True,
        interactive=True,
    )

    assert [message.id for message in messages or []] == [1, 2]
    assert messages is not None
    assert all(message._actions is app.api.messages for message in messages)
    assert app.calls[0].opcode == Opcode.CHAT_HISTORY
    assert app.calls[0].payload["from"] == 123
    assert app.calls[0].payload["itemType"] == ItemType.DELAYED
    assert app.calls[0].payload["getChat"] is True


@pytest.mark.asyncio
async def test_get_messages_and_get_message_bind_results_and_restore_chat_id() -> None:
    app = FakeApp(
        [
            frame(
                {
                    MessagePayloadKey.MESSAGES.value: [
                        message_payload(
                            116739188629507992,
                            None,
                            "one",
                        ),
                        message_payload(
                            116739188629507993,
                            None,
                            "two",
                        ),
                    ]
                }
            ),
            frame(
                {
                    MessagePayloadKey.MESSAGES.value: [
                        message_payload(
                            116739188629507992,
                            None,
                            "one",
                        )
                    ]
                }
            ),
            frame({MessagePayloadKey.MESSAGES.value: []}),
        ]
    )

    messages = await app.api.messages.get_messages(
        239067070,
        [116739188629507992, 116739188629507993],
    )
    message = await app.api.messages.get_message(
        239067070,
        116739188629507992,
    )
    missing = await app.api.messages.get_message(239067070, 1)

    assert [item.id for item in messages] == [
        116739188629507992,
        116739188629507993,
    ]
    assert all(item.chat_id == 239067070 for item in messages)
    assert all(item._actions is app.api.messages for item in messages)
    assert message is not None
    assert message.id == 116739188629507992
    assert message.chat_id == 239067070
    assert message._actions is app.api.messages
    assert missing is None
    assert app.calls[0].opcode == Opcode.MSG_GET
    assert app.calls[0].payload == {
        "chatId": 239067070,
        "messageIds": [116739188629507992, 116739188629507993],
    }
    assert app.calls[1].payload["messageIds"] == [116739188629507992]


@pytest.mark.asyncio
async def test_edit_message_formats_text_and_parses_bound_message() -> None:
    app = FakeApp(
        [
            frame(
                {
                    MessagePayloadKey.MESSAGE.value: {
                        **message_payload(
                            116739188629507992,
                            None,
                            "edited",
                            status="EDITED",
                        ),
                        "sender": 255000689,
                        "updateTime": 1781298658480,
                        "cid": -1781298654603,
                        "attaches": [],
                    }
                }
            )
        ]
    )

    message = await app.api.messages.edit_message(
        239067070,
        116739188629507992,
        "edited **text**",
    )

    assert message.id == 116739188629507992
    assert message.chat_id == 239067070
    assert message.status == "EDITED"
    assert message._actions is app.api.messages
    assert app.calls[0].opcode == Opcode.MSG_EDIT
    assert app.calls[0].payload == {
        "chatId": 239067070,
        "messageId": 116739188629507992,
        "text": "edited text",
        "elements": [
            {
                "type": "STRONG",
                "from": 7,
                "length": 4,
            }
        ],
        "attachments": [],
    }


@pytest.mark.asyncio
async def test_edit_message_uploads_single_and_multiple_attachments() -> None:
    response_message = {
        MessagePayloadKey.MESSAGE.value: message_payload(
            116739188629507992,
            None,
            "edited",
            status="EDITED",
        )
    }
    app = FakeApp([frame(response_message), frame(response_message)])
    photo = Photo(raw=b"image", name="image.jpg")
    file = File(raw=b"file", name="file.txt")
    video = Video(raw=b"video", name="video.mp4")

    await app.api.messages.edit_message(
        239067070,
        116739188629507992,
        "photo",
        attachments=[photo],
    )
    await app.api.messages.edit_message(
        239067070,
        116739188629507992,
        "files",
        attachments=[file, video],
    )

    assert app.api.uploads.calls == [
        ("photo", photo),
        ("file", file),
        ("video", video),
    ]
    assert app.calls[0].payload["attachments"] == [{"_type": "PHOTO", "photoToken": "photo-token"}]
    assert app.calls[1].payload["attachments"] == [
        {"_type": "FILE", "fileId": 30},
        {
            "_type": "VIDEO",
            "videoId": 20,
            "token": "video-token",
            "videoType": 0,
        },
    ]


@pytest.mark.asyncio
async def test_delete_pin_and_read_message_send_expected_opcodes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("pymax.api.messages.service.time.time", lambda: 3000.0)
    app = FakeApp(
        [
            frame({}),
            frame({}),
            frame({"unread": 0, "mark": 3000000}),
            frame({"unread": 0, "mark": 3000000}),
        ]
    )

    assert await app.api.messages.delete_message(100, [1, 2], for_me=True) is True
    assert await app.api.messages.pin_message(100, 2, notify_pin=False) is True
    read_state = await app.api.messages.read_message(2, 100)
    web_read_state = await app.api.messages.read_message("3", 100)

    assert read_state.mark == 3000000
    assert web_read_state.mark == 3000000
    assert [call.opcode for call in app.calls] == [
        Opcode.MSG_DELETE,
        Opcode.CHAT_UPDATE,
        Opcode.CHAT_MARK,
        Opcode.CHAT_MARK,
    ]
    assert app.calls[0].payload["forMe"] is True
    assert app.calls[1].payload["pinMessageId"] == 2
    assert app.calls[2].payload["messageId"] == 2
    assert app.calls[3].payload["messageId"] == "3"


@pytest.mark.asyncio
async def test_reaction_methods_parse_optional_reaction_info() -> None:
    reaction_info = {
        "totalCount": 1,
        "counters": [{"count": 1, "reaction": "👍"}],
    }
    app = FakeApp(
        [
            frame({MessagePayloadKey.REACTION_INFO.value: reaction_info}),
            frame(
                {
                    MessagePayloadKey.MESSAGES_REACTIONS.value: {
                        "10": reaction_info,
                        "11": {"totalCount": 0, "counters": []},
                    }
                }
            ),
            frame({}),
        ]
    )

    added = await app.api.messages.add_reaction(100, 10, "👍")
    reactions = await app.api.messages.get_reactions(100, [10, 11])
    removed = await app.api.messages.remove_reaction(100, 10)

    assert added is not None
    assert added.total_count == 1
    assert reactions is not None
    assert reactions["10"].counters[0].reaction == "👍"
    assert removed is None
    assert [call.opcode for call in app.calls] == [
        Opcode.MSG_REACTION,
        Opcode.MSG_GET_REACTIONS,
        Opcode.MSG_CANCEL_REACTION,
    ]
    assert app.calls[0].payload["messageId"] == 10
    assert app.calls[1].payload["messageIds"] == [10, 11]
    assert app.calls[2].payload["messageId"] == 10


@pytest.mark.asyncio
async def test_vote_poll_builds_payload_and_parses_state() -> None:
    app = FakeApp(
        [
            frame(
                {
                    "state": {
                        "total": 1,
                        "result": None,
                        "voterPreviewIds": [77],
                    }
                }
            )
        ]
    )

    state = await app.api.messages.vote_poll(100, 10, 42, [3])

    assert state.total == 1
    assert state.voter_preview_ids == [77]
    assert app.calls[0].opcode == Opcode.SEND_VOTE
    assert app.calls[0].payload == {
        "chatId": 100,
        "messageId": 10,
        "pollId": 42,
        "answersIds": [3],
    }


@pytest.mark.asyncio
async def test_get_video_and_file_by_id_parse_request_models() -> None:
    app = FakeApp(
        [
            frame(
                {
                    "cache": True,
                    "FAILOVER_HOSTS": ["maxvd759.okcdn.ru"],
                    "MP4_480": "https://video.test/480",
                    "EXTERNAL": "https://m.ok.ru/video/1",
                    "MP4_720": "https://video.test/720",
                }
            ),
            frame({"unsafe": False, "url": "https://file.test"}),
        ]
    )

    video = await app.api.messages.get_video_by_id(100, 10, 20)
    file = await app.api.messages.get_file_by_id(100, "10", 30)

    assert video is not None
    assert video.url == "https://video.test/720"
    assert video.external == "https://m.ok.ru/video/1"
    assert file is not None
    assert file.url == "https://file.test"
    assert [call.opcode for call in app.calls] == [
        Opcode.VIDEO_PLAY,
        Opcode.FILE_DOWNLOAD,
    ]
    assert app.calls[0].payload == {
        "chatId": 100,
        "messageId": 10,
        "videoId": 20,
    }
    assert app.calls[1].payload == {
        "chatId": 100,
        "messageId": "10",
        "fileId": 30,
    }


def test_video_request_supports_legacy_and_external_only_payloads() -> None:
    legacy = VideoRequest.model_validate(
        {"cache": True, "dynamicUrl": "https://video.test/legacy"}
    )
    external = VideoRequest.model_validate({"cache": True, "EXTERNAL": "https://m.ok.ru/video/1"})

    assert legacy.url == "https://video.test/legacy"
    assert external.url is None
    assert external.external == "https://m.ok.ru/video/1"


def test_next_cid_is_monotonic_when_clock_does_not_move(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("pymax.api.messages.service.time.time", lambda: 10.0)
    app = FakeApp()
    app.api.messages._prev = 10000

    assert app.api.messages._next_cid() == 10001
    assert app.api.messages._next_cid() == 10002
