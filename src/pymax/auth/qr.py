from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING

from pymax.auth.base import AuthFlow
from pymax.auth.exceptions import PasswordAttemptsExceededError
from pymax.exceptions import ApiError
from pymax.logging import get_logger

from .models import AuthResult
from .providers import ConsolePasswordProvider, PasswordProvider, QrHandler

if TYPE_CHECKING:
    from pymax.app import App
    from pymax.types.domain.auth import RequestQrResponse


logger = get_logger(__name__)


class QrAuthFlow(AuthFlow):
    """Стандартная QR-авторизация ``WebClient``.

    Flow получает QR-ссылку, передает ее в ``QrHandler``, ждет подтверждения и
    возвращает token для сохранения в сессии.

    Args:
        qr_provider: Handler, который показывает QR пользователю.
        password_provider: Provider пароля 2FA. Если не передан, используется
            ``ConsolePasswordProvider``.

    Example:
        .. code-block:: python

           from pymax import ConsoleQrHandler, QrAuthFlow, WebClient

           flow = QrAuthFlow(ConsoleQrHandler())
           client = WebClient(auth_flow=flow)
    """

    def __init__(
        self,
        qr_provider: QrHandler,
        password_provider: PasswordProvider | None = None,
    ) -> None:
        self.qr_provider = qr_provider
        self.password_provider = password_provider or ConsolePasswordProvider()

    async def authenticate(self, app: App) -> AuthResult:
        """Проходит QR-авторизацию.

        Args:
            app: Внутренний runtime PyMax.

        Returns:
            ``AuthResult`` с token.

        Raises:
            RuntimeError: Если QR истек до подтверждения.
        """
        logger.info("starting qr authentication")

        qr_info = await app.api.auth.request_qr()

        logger.debug("got qr track_id=%s", qr_info.track_id)

        await self.qr_provider.show_qr(qr_info.qr_link)

        confirmed = await self._poll_qr(app, qr_info)

        if not confirmed:
            raise RuntimeError("QR authentication expired")

        result = await app.api.auth.confirm_qr(qr_info.track_id)

        token = result.login_token
        if not token and result.password_challenge:
            token = await self._authenticate_with_password(
                app,
                track_id=result.password_challenge.track_id,
                hint=result.password_challenge.hint,
            )

        return AuthResult(
            token=token,
        )

    async def _poll_qr(self, app: App, qr_info: RequestQrResponse) -> bool:
        interval = qr_info.polling_interval / 1000
        expires_at = qr_info.expires_at / 1000

        while time.time() < expires_at:
            response = await app.api.auth.check_qr(qr_info.track_id)

            if response.status.login_available:
                return True

            await asyncio.sleep(interval)

        return False

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
