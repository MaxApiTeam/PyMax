from __future__ import annotations

import pytest

from pymax.api.auth.enums import ProfileOptions, TwoFactorAction
from pymax.api.session.enums import DeviceType
from pymax.protocol import Opcode
from pymax.session.models import SessionInfo
from pymax.types.domain.sync import SyncState
from tests.conftest import (
    FakeApp,
    chat_payload,
    frame,
    message_payload,
    mobile_user_agent,
    profile_payload,
    user_payload,
)


class StaticEmailProvider:
    def __init__(self, code: str = "123456") -> None:
        self.code = code
        self.emails: list[str] = []

    async def get_code(self, email: str) -> str:
        self.emails.append(email)
        return self.code


@pytest.mark.asyncio
async def test_request_and_send_code_parse_auth_responses() -> None:
    app = FakeApp(
        [
            frame(
                {
                    "token": "sms-token",
                    "codeLength": 6,
                    "requestMaxDuration": 60,
                    "requestCountLeft": 2,
                    "altActionDuration": 5,
                }
            ),
            frame({"tokenAttrs": {"LOGIN": {"token": "login-token"}}}),
        ]
    )

    start = await app.api.auth.request_code("+79990000000")
    result = await app.api.auth.send_code(start.token, "111111")

    assert start.token == "sms-token"
    assert result.login_token == "login-token"
    assert [call.opcode for call in app.calls] == [
        Opcode.AUTH_REQUEST,
        Opcode.AUTH,
    ]
    assert app.calls[0].payload["phone"] == "+79990000000"
    assert app.calls[0].payload["mode"] == app.fingerprint_generator.generate_fingerprint(
        version=app.config.device.user_agent.app_version,
        device_id=app.config.device.device_id,
        calls_seed=123,
    )
    assert app.calls[1].payload["verifyCode"] == "111111"


@pytest.mark.asyncio
async def test_mobile_login_sends_sync_payload_and_persists_updated_session() -> None:
    app = FakeApp(
        [
            frame(
                {
                    "profile": profile_payload(42),
                    "chats": [
                        {
                            **chat_payload(100),
                            "pinnedMessage": message_payload(10, 100),
                        }
                    ],
                    "messages": {"100": [message_payload(11, 100)]},
                    "contacts": [user_payload(43)],
                    "token": "server-token",
                    "time": 777,
                    "config": {"hash": "cfg-hash"},
                }
            )
        ]
    )
    app.session = SessionInfo(
        token="local-token",
        device_id="device-test",
        phone="+79990000000",
        sync=SyncState(chats_sync=1, contacts_sync=2, drafts_sync=3, presence_sync=4),
    )

    response = await app.api.auth.mobile_login()

    assert response.token == "server-token"
    assert app.calls[0].opcode == Opcode.LOGIN
    assert app.calls[0].payload["token"] == "local-token"
    assert app.calls[0].payload["userAgent"]["deviceType"] == DeviceType.ANDROID
    assert app.calls[0].payload[
        "chatCacheFingerprint"
    ] == app.fingerprint_generator.generate_fingerprint(
        version=app.config.device.user_agent.app_version,
        device_id=app.config.device.device_id,
        calls_seed=123,
    )
    assert app.session is not None
    assert app.session.mt_instance_id == "mt-test"
    assert app.session.sync.chats_sync == 777
    assert app.session.sync.contacts_sync == 777
    assert app.session.sync.drafts_sync == 777
    assert app.session.sync.presence_sync == 777
    assert app.session.sync.config_hash == "cfg-hash"
    assert app.store.saved_sessions == [app.session]
    assert response.profile.contact._actions is app.api.users
    assert response.chats[0]._message_actions is app.api.messages
    assert response.chats[0].pinned_message is not None
    assert response.chats[0].pinned_message._actions is app.api.messages
    assert response.messages[100][0]._actions is app.api.messages
    assert response.contacts[0] is not None
    assert response.contacts[0]._actions is app.api.users


@pytest.mark.asyncio
async def test_login_uses_web_payload_for_web_user_agent() -> None:
    app = FakeApp(
        [frame({"profile": profile_payload(42), "token": "web-token"})],
        device_type=DeviceType.WEB,
    )
    app.session = SessionInfo(
        token="web-local-token",
        device_id="device-test",
        phone="",
    )

    response = await app.api.auth.login(mobile_user_agent(DeviceType.WEB))

    assert response.token == "web-token"
    assert app.calls[0].opcode == Opcode.LOGIN
    assert app.calls[0].payload["token"] == "web-local-token"
    assert "userAgent" not in app.calls[0].payload
    assert app.calls[0].payload["chatsCount"] == 40


@pytest.mark.asyncio
async def test_login_without_session_raises_runtime_error() -> None:
    app = FakeApp()

    with pytest.raises(RuntimeError, match="No session available"):
        await app.api.auth.mobile_login()

    assert app.calls == []


@pytest.mark.asyncio
async def test_set_2fa_runs_password_email_hint_and_final_commit() -> None:
    provider = StaticEmailProvider()
    app = FakeApp(
        [
            frame({"trackId": "track-1"}),
            frame({}),
            frame({}),
            frame({}),
            frame({}),
            frame({}),
        ]
    )

    result = await app.api.auth.set_2fa(
        "secret",
        email="user@example.com",
        hint="hint",
        email_code_provider=provider,
    )

    assert result is True
    assert provider.emails == ["user@example.com"]
    assert [call.opcode for call in app.calls] == [
        Opcode.AUTH_CREATE_TRACK,
        Opcode.AUTH_VALIDATE_PASSWORD,
        Opcode.AUTH_VERIFY_EMAIL,
        Opcode.AUTH_CHECK_EMAIL,
        Opcode.AUTH_VALIDATE_HINT,
        Opcode.AUTH_SET_2FA,
    ]
    assert app.calls[-1].payload["trackId"] == "track-1"
    assert app.calls[-1].payload["hint"] == "hint"
    assert app.calls[-1].payload["expectedCapabilities"] == [
        TwoFactorAction.SET_PASSWORD,
        TwoFactorAction.HINT,
        TwoFactorAction.EMAIL,
    ]


@pytest.mark.asyncio
async def test_set_2fa_requires_track_id() -> None:
    app = FakeApp([frame({})])

    with pytest.raises(RuntimeError, match="Failed to create auth track"):
        await app.api.auth.set_2fa("secret")

    assert [call.opcode for call in app.calls] == [Opcode.AUTH_CREATE_TRACK]


@pytest.mark.asyncio
async def test_remove_2fa_checks_password_then_removes_factor() -> None:
    app = FakeApp([frame({"trackId": "track-1"}), frame({}), frame({})])

    assert await app.api.auth.remove_2fa("secret") is True

    assert [call.opcode for call in app.calls] == [
        Opcode.AUTH_CREATE_TRACK,
        Opcode.AUTH_CHECK_PASSWORD,
        Opcode.AUTH_SET_2FA,
    ]
    assert app.calls[2].payload["remove2fa"] is True
    assert app.calls[2].payload["expectedCapabilities"] == [TwoFactorAction.REMOVE_2FA]


@pytest.mark.asyncio
async def test_qr_auth_service_methods_send_expected_payloads() -> None:
    app = FakeApp(
        [
            frame(
                {
                    "expiresAt": 1000,
                    "pollingInterval": 100,
                    "qrLink": "max://qr",
                    "trackId": "track",
                    "ttl": 900,
                }
            ),
            frame({"status": {"expiresAt": 1000, "loginAvailable": True}}),
            frame({"tokenAttrs": {"LOGIN": {"token": "login-token"}}}),
            frame({}),
        ]
    )

    requested = await app.api.auth.request_qr()
    checked = await app.api.auth.check_qr("track")
    confirmed = await app.api.auth.confirm_qr("track")
    approved = await app.api.auth.authorize_qr_login("max://qr")

    assert requested.track_id == "track"
    assert checked.status.login_available is True
    assert confirmed.login_token == "login-token"
    assert approved is True
    assert [call.opcode for call in app.calls] == [
        Opcode.GET_QR,
        Opcode.GET_QR_STATUS,
        Opcode.LOGIN_BY_QR,
        Opcode.AUTH_QR_APPROVE,
    ]
    assert app.calls[1].payload == {"trackId": "track"}
    assert app.calls[3].payload == {"qrLink": "max://qr"}


@pytest.mark.asyncio
async def test_confirm_registration_sends_profile_and_parses_token() -> None:
    app = FakeApp(
        [
            frame(
                {
                    "userToken": 42,
                    "profile": profile_payload(42),
                    "tokenType": "REGISTER",
                    "token": "registered-token",
                }
            )
        ]
    )

    result = await app.api.auth.confirm_registration(
        first_name="Max",
        last_name="User",
        token="register-token",
    )

    assert result.token == "registered-token"
    assert result.profile.contact.id == 42
    assert app.calls[0].opcode == Opcode.AUTH_CONFIRM
    assert app.calls[0].payload == {
        "firstName": "Max",
        "lastName": "User",
        "token": "register-token",
        "tokenType": "REGISTER",
    }


@pytest.mark.asyncio
async def test_check_2fa_reads_profile_options() -> None:
    app = FakeApp()

    assert await app.api.auth.check_2fa() is False

    app.me = None
    assert await app.api.auth.check_2fa() is False

    from pymax.types.domain import Profile

    app.me = Profile.model_validate(
        profile_payload(1, [ProfileOptions.SECOND_FACTOR_PASSWORD_ENABLED])
    )
    assert await app.api.auth.check_2fa() is True
