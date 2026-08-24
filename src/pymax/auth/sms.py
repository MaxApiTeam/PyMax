from __future__ import annotations

from typing import TYPE_CHECKING

from pymax.auth.base import AuthFlow
from pymax.exceptions import ApiError
from pymax.logging import get_logger

from .exceptions import PasswordAttemptsExceededError
from .models import AuthResult
from .providers import (
    ConsolePasswordProvider,
    PasswordProvider,
    SmsCodeProvider,
)

if TYPE_CHECKING:
    from pymax.app import App


logger = get_logger(__name__)


class SmsAuthFlow(AuthFlow):
    """Стандартная SMS-авторизация ``Client``.

    Flow запрашивает SMS-код, отправляет его в Max, при необходимости проходит
    пароль 2FA и возвращает token для сохранения в сессии.

    Args:
        code_provider: Provider, который возвращает SMS-код.
        password_provider: Provider пароля 2FA. Если не передан, используется
            ``ConsolePasswordProvider``.

    Example:
        .. code-block:: python

           from pymax import Client, ConsoleSmsCodeProvider, SmsAuthFlow

           flow = SmsAuthFlow(ConsoleSmsCodeProvider())
           client = Client(
               phone="+79990000000",
               auth_flow=flow,
           )
    """

    def __init__(
        self,
        code_provider: SmsCodeProvider,
        password_provider: PasswordProvider | None = None,
    ) -> None:
        self.code_provider = code_provider
        self.password_provider = password_provider or ConsolePasswordProvider()

    async def authenticate(self, app: App) -> AuthResult:
        """Проходит SMS/2FA-авторизацию.

        Args:
            app: Внутренний runtime PyMax.

        Returns:
            ``AuthResult`` с token.

        Raises:
            RuntimeError: Если у клиента нет телефона.
        """
        phone = app.config.phone
        if not phone:
            logger.error("sms authentication requested without phone")
            raise RuntimeError("Phone is required for SMS authentication")

        logger.info("starting sms authentication")
        start = await app.api.auth.request_code(phone)
        logger.debug("sms token received token_set=%s", bool(start.token))
        code = await self.code_provider.get_code(phone)
        logger.debug("sms code provider returned code_set=%s", bool(code))
        result = await app.api.auth.send_code(start.token, code)

        if result.login_token:
            token = result.login_token
        elif not result.login_token and result.password_challenge:
            token = await self._authenticate_with_password(
                app,
                track_id=result.password_challenge.track_id,
                hint=result.password_challenge.hint,
            )
        elif result.register_token:
            if not app.config.registration_config:
                raise RuntimeError("RegistrationConfig is required to register a new account")
            else:
                registration_config = app.config.registration_config
                response = await app.api.auth.confirm_registration(
                    first_name=registration_config.first_name,
                    last_name=registration_config.last_name,
                    token=result.register_token,
                )
                token = response.token
        else:
            logger.error(
                "Authentication failed: server returned no login token, "
                "password challenge, or registration token"
            )
            token = None

        logger.info(
            "sms authentication completed token_set=%s",
            bool(token),
        )
        return AuthResult(
            token=token,
        )

    async def _authenticate_with_password(
        self,
        app: App,
        track_id: str,
        hint: str | None,
    ) -> str:
        logger.info("starting 2fa password authentication")
        attempt = 0
        while (
            app.config.password_max_attempts is None or app.config.password_max_attempts > attempt
        ):
            password = await self.password_provider.get_password(hint)
            logger.debug(
                "2fa password provider returned password_set=%s",
                bool(password),
            )
            if not password:
                logger.warning("2fa password is empty; retrying")
                attempt += 1
                continue

            try:
                response = await app.api.auth.check_password(track_id, password)
            except ApiError as e:
                logger.error("2fa password check failed: %s", e)
                attempt += 1
                continue

            if response.error:
                logger.error("2fa password check failed error=%s", response.error)
                attempt += 1
                continue

            if response.login_token:
                logger.info("2fa password authentication completed")
                return response.login_token

            logger.error("2fa password response did not contain login token; retrying")
            attempt += 1

        raise PasswordAttemptsExceededError
