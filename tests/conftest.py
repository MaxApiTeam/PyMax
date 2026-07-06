from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import pytest

from pymax.api.auth.service import AuthService
from pymax.api.bots.service import BotsService
from pymax.api.chats.service import ChatService
from pymax.api.messages.service import MessageService
from pymax.api.self.service import SelfService
from pymax.api.session.enums import DeviceType
from pymax.api.session.payloads import MobileUserAgentPayload
from pymax.api.session.service import SessionService
from pymax.api.uploads.payloads import (
    AttachFilePayload,
    AttachPhotoPayload,
    VideoAttachPayload,
)
from pymax.api.users.service import UserService
from pymax.config import ClientConfig, DeviceConfig
from pymax.fingerprint.fingerprint import FingerprintGenerator
from pymax.protocol import Command, InboundFrame
from pymax.session.models import SessionInfo
from pymax.types.domain import HandshakeResponse
from pymax.types.domain.sync import SyncOverrides


@dataclass
class InvokeCall:
    opcode: int
    payload: dict[str, Any]
    cmd: int
    timeout: float | None
    compress: bool


class FakeStore:
    def __init__(self) -> None:
        self.saved_sessions: list[SessionInfo] = []
        self.updated_tokens: list[tuple[str, str]] = []
        self.closed = False

    async def save_session(self, session: SessionInfo) -> None:
        self.saved_sessions.append(session)

    async def update_token(self, old_token: str, new_token: str) -> None:
        self.updated_tokens.append((old_token, new_token))

    async def close(self) -> None:
        self.closed = True


class FakeDispatcher:
    def __init__(self) -> None:
        self.internal_handlers: dict[Any, list[Any]] = {}

    def on_internal(self, event: Any, *filters: Any):
        def decorator(handler: Any) -> Any:
            self.internal_handlers.setdefault(event, []).append((handler, filters))
            return handler

        return decorator

    async def stop_startup_tasks(self) -> None:
        return None


class FakeUploads:
    def __init__(self) -> None:
        self.photo_result: AttachPhotoPayload | None = AttachPhotoPayload(
            photo_token="photo-token"
        )
        self.video_result: VideoAttachPayload | None = VideoAttachPayload(
            video_id=20,
            token="video-token",
        )
        self.file_result: AttachFilePayload | None = AttachFilePayload(file_id=30)
        self.calls: list[tuple[str, Any]] = []

    async def upload_photo(self, photo: Any) -> AttachPhotoPayload | None:
        self.calls.append(("photo", photo))
        return self.photo_result

    async def upload_video(self, video: Any) -> VideoAttachPayload | None:
        self.calls.append(("video", video))
        return self.video_result

    async def upload_file(self, file: Any) -> AttachFilePayload | None:
        self.calls.append(("file", file))
        return self.file_result


def mobile_user_agent(
    device_type: DeviceType = DeviceType.ANDROID,
) -> MobileUserAgentPayload:
    kwargs: dict[str, Any] = {
        "device_type": device_type,
        "app_version": "26.14.1",
        "os_version": ("Android 14" if device_type != DeviceType.WEB else "Linux"),
        "timezone": "Europe/Moscow",
        "screen": "1080x2400",
        "locale": "ru",
        "device_name": ("Pixel Test" if device_type != DeviceType.WEB else "Chrome"),
        "device_locale": "ru",
    }
    if device_type != DeviceType.WEB:
        kwargs.update(
            {
                "push_device_type": "GCM",
                "arch": "arm64-v8a",
                "build_number": 6686,
            }
        )
    return MobileUserAgentPayload(**kwargs)


def make_config(device_type: DeviceType = DeviceType.ANDROID) -> ClientConfig:
    return ClientConfig(
        phone="+79990000000",
        work_dir=".",
        session_name="session.db",
        request_timeout=1.0,
        telemetry=False,
        sync=SyncOverrides(),
        device=DeviceConfig(
            mt_instance_id="mt-test",
            device_id="device-test",
            client_session_id=7,
            user_agent=mobile_user_agent(device_type),
        ),
    )


class FakeApp:
    def __init__(
        self,
        responses: list[InboundFrame | Exception] | None = None,
        *,
        device_type: DeviceType = DeviceType.ANDROID,
    ) -> None:
        self.responses = list(responses or [])
        self.calls: list[InvokeCall] = []
        self.config = make_config(device_type)
        self.store = FakeStore()
        self.dispatcher = FakeDispatcher()
        self.connection = SimpleNamespace(is_open=True)

        self.me = None
        self.chats = None
        self.users: dict[int, Any] = {}
        self.contacts: list[Any] = []
        self.messages: dict[int, list[Any]] = {}
        self.session: SessionInfo | None = None
        self.handshake_response: HandshakeResponse | None = HandshakeResponse(calls_seed=123)
        self.started = True
        self.fingerprint_generator = FingerprintGenerator()

        self.api = SimpleNamespace()
        self.api.uploads = FakeUploads()
        self.api.messages = MessageService(self)
        self.api.chats = ChatService(self)
        self.api.users = UserService(self)
        self.api.account = SelfService(self)
        self.api.session = SessionService(self)
        self.api.auth = AuthService(self)
        self.api.bots = BotsService(self)

    async def invoke(
        self,
        opcode: int,
        payload: dict[str, Any],
        cmd: int = Command.REQUEST,
        timeout: float | None = 30.0,
        compress: bool = False,
    ) -> InboundFrame:
        self.calls.append(InvokeCall(opcode, payload, cmd, timeout, compress))
        if not self.responses:
            return frame({})

        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def frame(
    payload: dict[Any, Any] | None,
    *,
    opcode: int = 0,
    cmd: int = Command.RESPONSE,
    seq: int | None = 1,
) -> InboundFrame:
    return InboundFrame(opcode=opcode, cmd=cmd, seq=seq, payload=payload, raw=payload)


def user_payload(user_id: int = 1, name: str = "Test User") -> dict[str, Any]:
    return {"id": user_id, "names": [{"name": name, "type": "NICK"}]}


def profile_payload(user_id: int = 1, options: list[int] | None = None) -> dict[str, Any]:
    return {"contact": user_payload(user_id), "profileOptions": options}


def chat_payload(chat_id: int = 100, chat_type: str = "CHAT") -> dict[str, Any]:
    return {
        "id": chat_id,
        "type": chat_type,
        "status": "ACTIVE",
        "owner": 1,
        "title": f"Chat {chat_id}",
    }


def message_payload(
    message_id: int = 10,
    chat_id: int | None = 100,
    text: str = "hello",
    *,
    status: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": message_id,
        "chatId": chat_id,
        "time": 123456,
        "type": "USER",
        "text": text,
    }
    if status is not None:
        payload["status"] = status
    return payload


def member_payload(user_id: int = 1, status: int = 1) -> dict[str, Any]:
    return {
        "contact": user_payload(user_id),
        "presence": {"seen": 123456, "status": status},
    }


@pytest.fixture
def fake_app() -> FakeApp:
    return FakeApp()
