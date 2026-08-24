from __future__ import annotations

import time
from types import SimpleNamespace

import pytest

from pymax.auth.qr import QrAuthFlow
from pymax.auth.sms import SmsAuthFlow
from pymax.config import RegistrationConfig
from pymax.types.domain.auth import (
    CheckCodeResponse,
    CheckPasswordResponse,
    CheckQrResponse,
    RequestQrResponse,
    StartAuthResponse,
)


class StaticCodeProvider:
    def __init__(self, code: str = "111111") -> None:
        self.code = code
        self.phones: list[str] = []

    async def get_code(self, phone: str) -> str:
        self.phones.append(phone)
        return self.code


class SequencePasswordProvider:
    def __init__(self, passwords: list[str]) -> None:
        self.passwords = list(passwords)
        self.hints: list[str | None] = []

    async def get_password(self, hint: str | None = None) -> str:
        self.hints.append(hint)
        return self.passwords.pop(0)


class SmsAuthApi:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple]] = []

    async def request_code(self, phone: str):
        self.calls.append(("request_code", (phone,)))
        return StartAuthResponse.model_validate(
            {
                "token": "sms-token",
                "codeLength": 6,
                "requestMaxDuration": 60,
                "requestCountLeft": 1,
                "altActionDuration": 0,
            }
        )

    async def send_code(self, token: str, code: str):
        self.calls.append(("send_code", (token, code)))
        return CheckCodeResponse.model_validate(
            {"passwordChallenge": {"trackId": "track-1", "hint": "hint"}}
        )

    async def check_password(self, track_id: str, password: str):
        self.calls.append(("check_password", (track_id, password)))
        return CheckPasswordResponse.model_validate(
            {"tokenAttrs": {"LOGIN": {"token": "2fa-token"}}}
        )


@pytest.mark.asyncio
async def test_sms_auth_flow_requests_code_and_completes_2fa() -> None:
    auth_api = SmsAuthApi()
    app = SimpleNamespace(
        config=SimpleNamespace(
            phone="+79990000000",
            password_max_attempts=None,
        ),
        api=SimpleNamespace(auth=auth_api),
    )
    code_provider = StaticCodeProvider()
    password_provider = SequencePasswordProvider(["", "secret"])
    flow = SmsAuthFlow(code_provider, password_provider)

    result = await flow.authenticate(app)

    assert result.token == "2fa-token"
    assert code_provider.phones == ["+79990000000"]
    assert password_provider.hints == ["hint", "hint"]
    assert auth_api.calls == [
        ("request_code", ("+79990000000",)),
        ("send_code", ("sms-token", "111111")),
        ("check_password", ("track-1", "secret")),
    ]


@pytest.mark.asyncio
async def test_sms_auth_flow_requires_phone() -> None:
    flow = SmsAuthFlow(StaticCodeProvider())
    app = SimpleNamespace(config=SimpleNamespace(phone=None))

    with pytest.raises(RuntimeError, match="Phone is required"):
        await flow.authenticate(app)


class RegistrationAuthApi:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple]] = []

    async def request_code(self, phone: str):
        self.calls.append(("request_code", (phone,)))
        return StartAuthResponse.model_validate(
            {
                "token": "sms-token",
                "codeLength": 6,
                "requestMaxDuration": 60,
                "requestCountLeft": 1,
                "altActionDuration": 0,
            }
        )

    async def send_code(self, token: str, code: str):
        self.calls.append(("send_code", (token, code)))
        return CheckCodeResponse.model_validate(
            {"tokenAttrs": {"REGISTER": {"token": "register-token"}}}
        )

    async def confirm_registration(
        self,
        first_name: str,
        last_name: str | None,
        token: str,
    ):
        self.calls.append(("confirm_registration", (first_name, last_name, token)))
        return SimpleNamespace(token="registered-token")


@pytest.mark.asyncio
async def test_sms_auth_flow_confirms_new_account_registration() -> None:
    auth_api = RegistrationAuthApi()
    app = SimpleNamespace(
        config=SimpleNamespace(
            phone="+79990000000",
            registration_config=RegistrationConfig(
                first_name="Max",
                last_name="User",
            ),
        ),
        api=SimpleNamespace(auth=auth_api),
    )

    result = await SmsAuthFlow(StaticCodeProvider()).authenticate(app)

    assert result.token == "registered-token"
    assert auth_api.calls[-1] == (
        "confirm_registration",
        ("Max", "User", "register-token"),
    )


@pytest.mark.asyncio
async def test_sms_auth_flow_requires_registration_config_for_new_account() -> None:
    auth_api = RegistrationAuthApi()
    app = SimpleNamespace(
        config=SimpleNamespace(
            phone="+79990000000",
            registration_config=None,
        ),
        api=SimpleNamespace(auth=auth_api),
    )

    with pytest.raises(RuntimeError, match="RegistrationConfig is required"):
        await SmsAuthFlow(StaticCodeProvider()).authenticate(app)


class QrProvider:
    def __init__(self) -> None:
        self.links: list[str] = []

    async def show_qr(self, qr_url: str) -> None:
        self.links.append(qr_url)


class QrAuthApi:
    def __init__(self) -> None:
        self.statuses = [False, True]
        self.calls: list[tuple[str, tuple]] = []

    async def request_qr(self):
        self.calls.append(("request_qr", ()))
        return RequestQrResponse.model_validate(
            {
                "expiresAt": int((time.time() + 5) * 1000),
                "pollingInterval": 0,
                "qrLink": "max://qr",
                "trackId": "qr-track",
                "ttl": 5000,
            }
        )

    async def check_qr(self, track_id: str):
        self.calls.append(("check_qr", (track_id,)))
        return CheckQrResponse.model_validate(
            {
                "status": {
                    "expiresAt": int((time.time() + 5) * 1000),
                    "loginAvailable": self.statuses.pop(0),
                }
            }
        )

    async def confirm_qr(self, track_id: str):
        self.calls.append(("confirm_qr", (track_id,)))
        return CheckCodeResponse.model_validate({"tokenAttrs": {"LOGIN": {"token": "qr-token"}}})


@pytest.mark.asyncio
async def test_qr_auth_flow_shows_qr_polls_until_available_and_confirms() -> None:
    provider = QrProvider()
    auth_api = QrAuthApi()
    app = SimpleNamespace(api=SimpleNamespace(auth=auth_api))
    flow = QrAuthFlow(provider)

    result = await flow.authenticate(app)

    assert result.token == "qr-token"
    assert provider.links == ["max://qr"]
    assert auth_api.calls == [
        ("request_qr", ()),
        ("check_qr", ("qr-track",)),
        ("check_qr", ("qr-track",)),
        ("confirm_qr", ("qr-track",)),
    ]
