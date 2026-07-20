from __future__ import annotations

from typing import TYPE_CHECKING

from pymax.api.binding import bind_api_model
from pymax.api.response import (
    payload_item,
    payload_keys,
    require_payload_model,
)
from pymax.api.session.enums import DeviceType
from pymax.auth import EmailCodeProvider
from pymax.auth.providers import ConsoleEmailCodeProvider
from pymax.logging import get_logger
from pymax.protocol import Opcode
from pymax.types.domain import Login2Flags, Login2Response
from pymax.types.domain.auth import (
    CheckCodeResponse,
    CheckPasswordResponse,
    CheckQrResponse,
    ConfirmRegistrationResponse,
    RequestQrResponse,
    StartAuthResponse,
)
from pymax.types.domain.login import LoginResponse

from .enums import ProfileOptions, TwoFactorAction
from .payloads import (
    ApproveQrLoginPayload,
    CheckPasswordChallengePayload,
    CheckQrPayload,
    ConfirmQrPayload,
    ConfirmRegistrationPayload,
    CreateAuthTrackPayload,
    Login2Payload,
    MobileUserAgentPayload,
    RemoveTwoFactorPayload,
    RequestCodePayload,
    RequestEmailCodePayload,
    SendCodePayload,
    SendEmailCodePayload,
    SetHintPayload,
    SetPasswordPayload,
    SetTwoFactorPayload,
    SyncPayload,
    WebSyncPayload,
)
from .types import MISSING, Missing

if TYPE_CHECKING:
    from pymax.app import App


logger = get_logger(__name__)


class AuthService:
    def __init__(self, app: App) -> None:
        self.app = app

    async def request_code(self, phone: str) -> StartAuthResponse:
        logger.info("requesting sms code phone_set=%s", bool(phone))

        if not self.app.handshake_response:
            logger.error("request_code requested without handshake response")
            raise RuntimeError("No handshake response available for request_code")

        device_id = (
            self.app.session.device_id if self.app.session else self.app.config.device.device_id
        )

        mode = self.app.fingerprint_generator.generate_fingerprint(
            version=self.app.config.device.user_agent.app_version,
            device_id=device_id,
            calls_seed=self.app.handshake_response.calls_seed,
            arch=self.app.config.device.user_agent.arch or "arm64-v8a",
        )

        frame = RequestCodePayload(phone=phone, mode=mode)
        response = await self.app.invoke(Opcode.AUTH_REQUEST, frame.to_payload())
        logger.debug(
            "sms code request accepted payload_keys=%s",
            payload_keys(response),
        )
        return require_payload_model(response, StartAuthResponse)

    async def send_code(self, token: str, verify_code: str) -> CheckCodeResponse:
        logger.info(
            "sending sms code token_set=%s code_set=%s",
            bool(token),
            bool(verify_code),
        )

        frame = SendCodePayload(
            token=token,
            verify_code=verify_code,
        )
        response = await self.app.invoke(Opcode.AUTH, frame.to_payload())
        logger.debug(
            "sms code response payload_keys=%s",
            payload_keys(response),
        )
        return require_payload_model(response, CheckCodeResponse)

    async def check_password(
        self,
        track_id: str,
        password: str,
    ) -> CheckPasswordResponse:
        logger.info(
            "checking 2fa password track_id_set=%s password_set=%s",
            bool(track_id),
            bool(password),
        )
        frame = CheckPasswordChallengePayload(
            track_id=track_id,
            password=password,
        )
        response = await self.app.invoke(
            Opcode.AUTH_LOGIN_CHECK_PASSWORD,
            frame.to_payload(),
        )
        logger.debug(
            "2fa password response payload_keys=%s",
            payload_keys(response),
        )
        return require_payload_model(response, CheckPasswordResponse)

    async def login(self, user_agent: MobileUserAgentPayload) -> LoginResponse:
        if user_agent.device_type == DeviceType.WEB:
            return await self.web_login()

        return await self.mobile_login()

    async def mobile_login(self) -> LoginResponse:
        session = self.app.session
        if session is None:
            logger.error("login requested without session")
            raise RuntimeError("No session available for login")

        logger.info("logging in")

        if not self.app.handshake_response:
            logger.error("login requested without handshake response")
            raise RuntimeError("No handshake response available for login")

        device_id = (
            self.app.session.device_id if self.app.session else self.app.config.device.device_id
        )

        ccf = self.app.fingerprint_generator.generate_fingerprint(
            version=self.app.config.device.user_agent.app_version,
            device_id=device_id,
            calls_seed=self.app.handshake_response.calls_seed,
            arch=self.app.config.device.user_agent.arch or "arm64-v8a",
        )

        sync = self.app.config.sync.resolve(session.sync)
        frame = SyncPayload.from_sync_state(
            user_agent=self.app.config.device.user_agent,
            token=session.token,
            sync=sync,
            chat_cache_fingerprint=ccf,
            interactive=self.app.config.interactive,
        )
        response = await self.app.invoke(Opcode.LOGIN, frame.to_payload())

        logger.debug("login response payload_keys=%s", payload_keys(response))

        login_response = bind_api_model(
            self.app,
            require_payload_model(response, LoginResponse),
        )
        await self._update_session(login_response)
        return login_response

    async def mobile_login2(self, flags: Login2Flags) -> Login2Response:
        session = self.app.session
        if session is None:
            logger.error("login2 requested without session")
            raise RuntimeError("No session available for login2")

        sync = self.app.config.sync.resolve(session.sync)

        frame = Login2Payload.from_sync_state(
            sync,
            profile_enabled=flags.profile_enabled,
            contact_enabled=flags.contact_enabled,
        )

        response = await self.app.invoke(Opcode.LOGIN2, frame.to_payload())
        logger.debug("login2 response payload_keys=%s", payload_keys(response))

        login2_response = bind_api_model(
            self.app,
            require_payload_model(response, Login2Response),
        )
        await self._update_session(login2_response)
        return login2_response

    async def web_login(self) -> LoginResponse:
        session = self.app.session
        if session is None:
            logger.error("login requested without session")
            raise RuntimeError("No session available for login")

        logger.info("logging in")
        sync = self.app.config.sync.resolve(session.sync)

        frame = WebSyncPayload.from_sync_state(
            token=session.token,
            sync=sync,
            interactive=self.app.config.interactive,
        )
        response = await self.app.invoke(Opcode.LOGIN, frame.to_payload())

        logger.debug("login response payload_keys=%s", payload_keys(response))

        login_response = bind_api_model(
            self.app,
            require_payload_model(response, LoginResponse),
        )
        await self._update_session(login_response)
        return login_response

    async def request_qr(self) -> RequestQrResponse:
        response = await self.app.invoke(Opcode.GET_QR, {})

        return require_payload_model(response, RequestQrResponse)

    async def check_qr(self, track_id: str) -> CheckQrResponse:
        frame = CheckQrPayload(track_id=track_id)

        response = await self.app.invoke(Opcode.GET_QR_STATUS, frame.to_payload())

        return require_payload_model(response, CheckQrResponse)

    async def confirm_qr(self, track_id: str) -> CheckCodeResponse:
        frame = ConfirmQrPayload(track_id=track_id)

        response = await self.app.invoke(Opcode.LOGIN_BY_QR, frame.to_payload())

        return require_payload_model(response, CheckCodeResponse)

    async def _update_session(self, response: LoginResponse | Login2Response) -> None:
        session = self.app.session
        if session is None:
            return

        sync = response.update_sync_state(session.sync)
        updated = session.model_copy(
            update={
                "mt_instance_id": self.app.config.device.mt_instance_id,
                "sync": sync,
            },
        )
        self.app.session = updated
        await self.app.store.save_session(updated)

    async def _get_track_id(self) -> str | None:
        logger.debug("creating auth track")
        frame = CreateAuthTrackPayload()

        response = await self.app.invoke(Opcode.AUTH_CREATE_TRACK, frame.to_payload())

        return payload_item(response, "trackId", str)

    async def _set_email(self, track_id: str, email: str, provider: EmailCodeProvider) -> bool:
        logger.info("setting 2fa email email_set=%s", bool(email))

        frame = RequestEmailCodePayload(
            track_id=track_id,
            email=email,
        )

        await self.app.invoke(Opcode.AUTH_VERIFY_EMAIL, frame.to_payload())

        code = await provider.get_code(email)

        frame = SendEmailCodePayload(
            track_id=track_id,
            verify_code=code,
        )

        await self.app.invoke(Opcode.AUTH_CHECK_EMAIL, frame.to_payload())

        return True

    async def _set_hint(self, track_id: str, hint: str) -> bool:
        logger.info("setting 2fa hint hint_set=%s", bool(hint))

        frame = SetHintPayload(
            track_id=track_id,
            hint=hint,
        )
        await self.app.invoke(Opcode.AUTH_VALIDATE_HINT, frame.to_payload())

        return True

    async def _set_password(self, track_id: str, password: str) -> bool:
        logger.info("setting 2fa password password_set=%s", bool(password))

        frame = SetPasswordPayload(
            track_id=track_id,
            password=password,
        )
        await self.app.invoke(Opcode.AUTH_VALIDATE_PASSWORD, frame.to_payload())

        return True

    async def set_2fa(
        self,
        password: str,
        email: str | Missing = MISSING,
        hint: str | Missing = MISSING,
        email_code_provider: EmailCodeProvider | None = None,
    ) -> bool:
        logger.info(
            "setting 2fa password password_set=%s email_set=%s hint_set=%s",
            bool(password),
            bool(email),
            bool(hint),
        )

        track_id = await self._get_track_id()

        if track_id is None:
            logger.error("missing track_id in auth create track response")
            raise RuntimeError("Failed to create auth track")

        has_hint = False
        has_email = False

        await self._set_password(track_id, password)

        if email is not MISSING:
            provider = email_code_provider or ConsoleEmailCodeProvider()
            await self._set_email(track_id, str(email), provider)
            has_email = True

        if hint is not MISSING:
            await self._set_hint(track_id, str(hint))
            has_hint = True

        expected_capabilities = [TwoFactorAction.SET_PASSWORD]

        if has_hint:
            expected_capabilities.append(TwoFactorAction.HINT)

        if has_email:
            expected_capabilities.append(TwoFactorAction.EMAIL)

        frame = SetTwoFactorPayload(
            track_id=track_id,
            password=password,
            hint=str(hint) if has_hint else None,
            expected_capabilities=expected_capabilities,
        )

        await self.app.invoke(Opcode.AUTH_SET_2FA, frame.to_payload())
        logger.info("2fa password set successfully")
        return True

    async def _check_2fa_password(self, track_id: str, password: str) -> bool:
        logger.info("entering 2fa password password_set=%s", bool(password))

        frame = SetPasswordPayload(
            track_id=track_id,
            password=password,
        )
        await self.app.invoke(Opcode.AUTH_CHECK_PASSWORD, frame.to_payload())

        return True

    async def remove_2fa(self, password: str) -> bool:
        logger.info("removing 2fa password_set=%s", bool(password))

        track_id = await self._get_track_id()

        if track_id is None:
            logger.error("missing track_id in auth create track response")
            raise RuntimeError("Failed to create auth track")

        await self._check_2fa_password(track_id, password)

        frame = RemoveTwoFactorPayload(
            track_id=track_id,
        )

        await self.app.invoke(Opcode.AUTH_SET_2FA, frame.to_payload())

        return True

    async def authorize_qr_login(self, qr_link: str) -> bool:
        logger.info("approving qr login qr_link_set=%s", bool(qr_link))

        frame = ApproveQrLoginPayload(qr_link=qr_link)

        await self.app.invoke(Opcode.AUTH_QR_APPROVE, frame.to_payload())

        return True

    async def check_2fa(self) -> bool:
        if not self.app.me or not self.app.me.profile_options:
            return False

        return ProfileOptions.SECOND_FACTOR_PASSWORD_ENABLED in self.app.me.profile_options

    async def change_password(self, password_old: str, password_new: str) -> bool:
        track_id = await self._get_track_id()

        if not track_id:
            logger.error("missing track_id in auth create track response")
            raise RuntimeError("Failed to create auth track")

        await self._check_2fa_password(track_id, password_old)

        await self._set_password(track_id, password_new)

        expected_capabilities = [TwoFactorAction.UPDATE_PASSWORD]

        frame = SetTwoFactorPayload(
            track_id=track_id,
            password=password_new,
            hint=None,
            expected_capabilities=expected_capabilities,
        )

        await self.app.invoke(Opcode.AUTH_SET_2FA, frame.to_payload())
        logger.info("2fa password set successfully")
        return True

    async def confirm_registration(
        self, first_name: str, last_name: str | None, token: str
    ) -> ConfirmRegistrationResponse:
        frame = ConfirmRegistrationPayload(
            first_name=first_name,
            last_name=last_name,
            token=token,
        )

        response = await self.app.invoke(Opcode.AUTH_CONFIRM, frame.to_payload())

        return require_payload_model(response, ConfirmRegistrationResponse)
