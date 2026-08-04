from __future__ import annotations

from pymax.types.domain import (
    AudioAttachment,
    Message,
    PollAttachment,
    UnknownAttachment,
    VideoAttachment,
)
from tests.conftest import message_payload


def test_message_accepts_unsupported_attachment_type() -> None:
    payload = message_payload(1, 100)
    payload["attaches"] = [
        {
            "_type": "UNSUPPORTED",
            "duration": 259544,
            "token": "voice-token",
        }
    ]

    message = Message.model_validate(payload)

    attach = message.attaches[0]
    assert isinstance(attach, UnknownAttachment)
    assert attach.type == "UNSUPPORTED"
    assert attach.model_extra == {
        "duration": 259544,
        "token": "voice-token",
    }


def test_message_accepts_future_unknown_attachment_type() -> None:
    payload = message_payload(1, 100)
    payload["attaches"] = [
        {
            "_type": "VOICE_TRANSCRIPTION",
            "token": "future-token",
        }
    ]

    message = Message.model_validate(payload)

    attach = message.attaches[0]
    assert isinstance(attach, UnknownAttachment)
    assert attach.type == "VOICE_TRANSCRIPTION"
    assert attach.model_extra == {"token": "future-token"}


def test_audio_attachment_accepts_missing_server_fields() -> None:
    payload = message_payload(1, 100)
    payload["attaches"] = [
        {
            "_type": "AUDIO",
            "token": "audio-token",
        }
    ]

    message = Message.model_validate(payload)

    attach = message.attaches[0]
    assert isinstance(attach, AudioAttachment)
    assert attach.duration is None
    assert attach.audio_id is None
    assert attach.token == "audio-token"


def test_video_attachment_accepts_missing_duration() -> None:
    payload = message_payload(1, 100)
    payload["attaches"] = [
        {
            "_type": "VIDEO",
            "height": 720,
            "width": 1280,
            "videoId": 42,
            "previewData": b"preview",
            "thumbnail": "https://example.test/thumb.jpg",
            "token": "video-token",
            "videoType": 0,
        }
    ]

    message = Message.model_validate(payload)

    attach = message.attaches[0]
    assert isinstance(attach, VideoAttachment)
    assert attach.duration is None
    assert attach.video_id == 42


def test_poll_attachment_parses_vote_details() -> None:
    payload = message_payload(1, 100)
    payload["attaches"] = [
        {
            "_type": "POLL",
            "title": "Question",
            "answers": [{"text": "Answer", "answerId": 1}],
            "settings": 0,
            "pollId": 42,
            "version": 1,
            "state": {
                "total": 1,
                "result": [
                    {
                        "answerId": 1,
                        "voteCount": 1,
                        "votes": [{"timestamp": 123456, "userId": 77}],
                        "rate": 100,
                        "options": 0,
                    }
                ],
                "voterPreviewIds": [77],
            },
        }
    ]

    message = Message.model_validate(payload)

    attach = message.attaches[0]
    assert isinstance(attach, PollAttachment)
    assert attach.state.result is not None
    assert attach.state.result[0].votes[0].user_id == 77
    assert attach.state.result[0].votes[0].timestamp == 123456


def test_message_elements_accept_missing_length_and_attribute_url() -> None:
    payload = message_payload(1, 100)
    payload["elements"] = [
        {
            "type": "ANIMOJI",
            "attributes": {},
        }
    ]

    message = Message.model_validate(payload)

    element = message.elements[0]
    assert element.length is None
    assert element.attributes is not None
    assert element.attributes.url is None
