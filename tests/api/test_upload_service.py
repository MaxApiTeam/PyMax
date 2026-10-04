from __future__ import annotations

import pytest

from pymax.api.uploads.payloads import UploadPayload
from pymax.api.uploads.service import UploadService
from pymax.exceptions import UploadError
from pymax.files import File, Photo, Video, Voice
from pymax.protocol import Opcode
from pymax.types import AttachmentType
from pymax.types.events import AudioUploadSignal, FileUploadSignal, VideoUploadSignal
from tests.conftest import FakeApp, frame


class FakeHttpResponse:
    def __init__(self, status: int, json_data: dict | None = None, on_enter=None) -> None:
        self.status = status
        self.json_data = json_data or {}
        self.on_enter = on_enter

    async def __aenter__(self):
        if self.on_enter is not None:
            self.on_enter()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def json(self) -> dict:
        return self.json_data


class FakeHttpSession:
    posts: list[dict] = []
    response = FakeHttpResponse(200, {"photos": {"photo-1": {"token": "uploaded"}}})

    def __init__(self, *args, **kwargs) -> None:
        self.args = args
        self.kwargs = kwargs

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def post(self, **kwargs):
        self.posts.append(kwargs)
        return self.response


def test_upload_payload_uses_regular_video_defaults() -> None:
    assert UploadPayload().to_payload() == {
        "count": 1,
        "type": 0,
        "uploaderType": 0,
        "profile": False,
    }


@pytest.mark.asyncio
async def test_upload_photo_requests_url_posts_file_and_returns_attach_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The URL MAX returns today carries no photo id at all -- it is a one-shot
    `uploadImage?r=<token>` -- and the result is keyed by position ("0"), so the
    token must not be looked up by a `photoIds` query parameter."""
    app = FakeApp([frame({"url": "https://iu.oneme.ru/uploadImage?r=TOKEN1"})])
    service = UploadService(app)
    monkeypatch.setattr(
        "pymax.api.uploads.service.aiohttp.ClientSession",
        FakeHttpSession,
    )
    FakeHttpSession.posts = []
    FakeHttpSession.response = FakeHttpResponse(
        200,
        {"photos": {"0": {"token": "uploaded"}}},
    )

    result = await service.upload_photo(Photo(raw=b"image-bytes", name="image.jpg"))

    assert result.photo_token == "uploaded"
    assert app.calls[0].opcode == Opcode.PHOTO_UPLOAD
    assert FakeHttpSession.posts[0]["url"] == "https://iu.oneme.ru/uploadImage?r=TOKEN1"


@pytest.mark.asyncio
async def test_upload_photo_reads_the_token_from_a_result_keyed_by_photo_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keying is not guaranteed to stay "0": anything keyed works as long as the
    response holds exactly one photo."""
    app = FakeApp([frame({"url": "https://iu.oneme.ru/uploadImage?r=TOKEN1"})])
    service = UploadService(app)
    monkeypatch.setattr(
        "pymax.api.uploads.service.aiohttp.ClientSession",
        FakeHttpSession,
    )
    FakeHttpSession.posts = []
    FakeHttpSession.response = FakeHttpResponse(
        200,
        {"photos": {"photo-1": {"token": "uploaded"}}},
    )

    result = await service.upload_photo(Photo(raw=b"image-bytes", name="image.jpg"))

    assert result.photo_token == "uploaded"


@pytest.mark.asyncio
async def test_upload_photo_refuses_an_ambiguous_multi_photo_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without a photo id in the URL there is no way to tell which entry is
    ours, so a batched result must fail rather than attach the wrong photo."""
    app = FakeApp([frame({"url": "https://iu.oneme.ru/uploadImage?r=TOKEN1"})])
    service = UploadService(app)
    monkeypatch.setattr(
        "pymax.api.uploads.service.aiohttp.ClientSession",
        FakeHttpSession,
    )
    FakeHttpSession.posts = []
    FakeHttpSession.response = FakeHttpResponse(
        200,
        {"photos": {"0": {"token": "a"}, "1": {"token": "b"}}},
    )

    with pytest.raises(UploadError, match="expected 1"):
        await service.upload_photo(Photo(raw=b"image-bytes", name="image.jpg"))


@pytest.mark.asyncio
async def test_upload_photo_refuses_an_empty_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An empty result is as unusable as an ambiguous one -- there is no photo to
    attach -- so it must fail rather than be reported as a success."""
    app = FakeApp([frame({"url": "https://iu.oneme.ru/uploadImage?r=TOKEN1"})])
    service = UploadService(app)
    monkeypatch.setattr(
        "pymax.api.uploads.service.aiohttp.ClientSession",
        FakeHttpSession,
    )
    FakeHttpSession.posts = []
    FakeHttpSession.response = FakeHttpResponse(200, {"photos": {}})

    with pytest.raises(UploadError, match="expected 1"):
        await service.upload_photo(Photo(raw=b"image-bytes", name="image.jpg"))


@pytest.mark.asyncio
async def test_each_photo_of_an_album_is_uploaded_separately(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A multi-photo message is N independent `count: 1` uploads -- N distinct
    URLs, N POSTs, N results -- and the tokens are then sent together in one
    message. The url's photo id was never what tied a result to its photo."""
    app = FakeApp(
        [
            frame({"url": "https://iu.oneme.ru/uploadImage?r=TOKEN1"}),
            frame({"url": "https://iu.oneme.ru/uploadImage?r=TOKEN2"}),
        ]
    )
    service = UploadService(app)
    monkeypatch.setattr(
        "pymax.api.uploads.service.aiohttp.ClientSession",
        FakeHttpSession,
    )
    FakeHttpSession.posts = []
    FakeHttpSession.response = FakeHttpResponse(200, {"photos": {"0": {"token": "t"}}})

    first = await service.upload_photo(Photo(raw=b"one", name="one.jpg"))
    FakeHttpSession.response = FakeHttpResponse(200, {"photos": {"0": {"token": "t2"}}})
    second = await service.upload_photo(Photo(raw=b"two", name="two.jpg"))

    assert (first.photo_token, second.photo_token) == ("t", "t2")
    assert [call.opcode for call in app.calls] == [Opcode.PHOTO_UPLOAD] * 2
    assert [post["url"] for post in FakeHttpSession.posts] == [
        "https://iu.oneme.ru/uploadImage?r=TOKEN1",
        "https://iu.oneme.ru/uploadImage?r=TOKEN2",
    ]
    # One upload per photo, always: that is what makes a single-entry result
    # unambiguous.
    for call in app.calls:
        assert call.payload["count"] == 1


@pytest.mark.asyncio
async def test_upload_waiters_resolve_processing_signals() -> None:
    app = FakeApp()
    service = UploadService(app)
    loop = __import__("asyncio").get_running_loop()
    video_future = loop.create_future()
    file_future = loop.create_future()
    voice_future = loop.create_future()
    service.video_upload_waiters[1] = video_future
    service.file_upload_waiters[2] = file_future
    service.voice_upload_waiters[3] = voice_future

    await service.on_video_attach(VideoUploadSignal(video_id=1), None)
    await service.on_file_attach(FileUploadSignal(file_id=2), None)
    await service.on_voice_attach(AudioUploadSignal(audio_id=3), None)

    assert video_future.result().video_id == 1
    assert file_future.result().file_id == 2
    assert voice_future.result().audio_id == 3
    assert service.video_upload_waiters == {}
    assert service.file_upload_waiters == {}
    assert service.voice_upload_waiters == {}


@pytest.mark.asyncio
async def test_upload_video_posts_chunks_waits_for_processing_and_cleans_waiter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = FakeApp(
        [
            frame(
                {
                    "info": [
                        {
                            "url": "https://upload.test/video",
                            "videoId": 10,
                            "token": "video-token",
                        }
                    ]
                }
            )
        ]
    )
    service = UploadService(app)

    def resolve_processing() -> None:
        service.video_upload_waiters[10].set_result(VideoUploadSignal(video_id=10))

    FakeHttpSession.posts = []
    FakeHttpSession.response = FakeHttpResponse(200, on_enter=resolve_processing)
    monkeypatch.setattr(
        "pymax.api.uploads.service.aiohttp.ClientSession",
        FakeHttpSession,
    )

    result = await service.upload_video(Video(raw=b"video", name="clip.mp4"))

    assert result.video_id == 10
    assert result.token == "video-token"
    assert service.video_upload_waiters == {}
    assert FakeHttpSession.posts[0]["headers"]["Content-Range"] == "bytes 0-4/5"
    assert FakeHttpSession.posts[0]["url"] == "https://upload.test/video"


@pytest.mark.asyncio
async def test_upload_voice_posts_chunks_and_builds_attachment_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = FakeApp(
        [
            frame(
                {
                    "info": [
                        {
                            "url": "https://upload.test/voice",
                            "videoId": 12,
                            "token": "voice-token",
                        }
                    ]
                }
            )
        ]
    )
    service = UploadService(app)

    FakeHttpSession.posts = []
    FakeHttpSession.response = FakeHttpResponse(200)
    monkeypatch.setattr(
        "pymax.api.uploads.service.aiohttp.ClientSession",
        FakeHttpSession,
    )

    result = await service.upload_voice(Voice(raw=b"voice", name="voice.ogg", duration=1_000))

    assert result.type == AttachmentType.AUDIO
    assert result.video_id == 12
    assert result.token == "voice-token"
    assert result.duration == 1_000
    assert result.wave == b"\x00" * 80
    assert app.calls[0].payload == {
        "count": 1,
        "type": 2,
        "uploaderType": 1,
        "profile": False,
    }
    assert service.voice_upload_waiters == {}
    assert FakeHttpSession.posts[0]["headers"]["Content-Range"] == "bytes 0-4/5"
    assert FakeHttpSession.posts[0]["url"] == "https://upload.test/voice"


@pytest.mark.asyncio
async def test_upload_file_posts_chunks_waits_for_processing_and_cleans_waiter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = FakeApp(
        [
            frame(
                {
                    "info": [
                        {
                            "url": "https://upload.test/file",
                            "fileId": 11,
                            "token": "file-token",
                        }
                    ]
                }
            )
        ]
    )
    service = UploadService(app)

    def resolve_processing() -> None:
        service.file_upload_waiters[11].set_result(FileUploadSignal(file_id=11))

    FakeHttpSession.posts = []
    FakeHttpSession.response = FakeHttpResponse(200, on_enter=resolve_processing)
    monkeypatch.setattr(
        "pymax.api.uploads.service.aiohttp.ClientSession",
        FakeHttpSession,
    )

    result = await service.upload_file(File(raw=b"file", name="doc.txt"))

    assert result.file_id == 11
    assert service.file_upload_waiters == {}
    assert FakeHttpSession.posts[0]["headers"]["Content-Range"] == "0-3/4"
    assert FakeHttpSession.posts[0]["url"] == "https://upload.test/file"
