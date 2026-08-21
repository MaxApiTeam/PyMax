from __future__ import annotations

from pymax.auth import (
    AuthFlow,
    ConsoleSmsCodeProvider,
    PasswordProvider,
    SmsAuthFlow,
    SmsCodeProvider,
)
from pymax.config import ClientConfig
from pymax.connection import ConnectionManager
from pymax.connection.readers import TCPReader
from pymax.dispatch import Router
from pymax.logging import configure_logging, get_logger
from pymax.protocol.tcp import TcpProtocol
from pymax.protocol.tcp.framing import TcpPacketFramer
from pymax.transport.tcp import TCPTransport
from pymax.versions.catalog import VersionCatalog

from .base import BaseClient
from .config import ExtraConfig

logger = get_logger(__name__)


class Client(BaseClient["Client"]):
    """TCP-клиент PyMax с SMS-авторизацией.

    Используйте ``Client`` как основной long-running клиент: он открывает
    соединение, проходит авторизацию, хранит сессию в ``work_dir``.
    Клиент вызывает роутеры и предоставляет методы для сообщений, чатов,
    пользователей и профиля.

    Args:
        phone: Номер телефона для первой авторизации.
        session_name: Имя SQLite-файла сессии внутри ``work_dir``.
        work_dir: Директория для файла сессии и служебного cache.
        extra_config: Дополнительные настройки соединения, логов, reconnect
            и sync.
        auth_flow: Полностью пользовательский сценарий авторизации.
        sms_code_provider: Провайдер SMS-кода для стандартного ``SmsAuthFlow``.
        password_provider: Провайдер пароля 2FA, если аккаунт его требует.
    """

    def __init__(  # noqa: PLR0913
        self,
        phone: str,
        session_name: str = "session.db",
        work_dir: str = ".",
        extra_config: ExtraConfig | None = None,
        auth_flow: AuthFlow | None = None,
        sms_code_provider: SmsCodeProvider | None = None,
        password_provider: PasswordProvider | None = None,
        app_version: str = VersionCatalog.RECOMMENDED_APP_VERSION,
        catalog: VersionCatalog | None = None,
    ) -> None:

        self.phone = phone
        self.extra_config = extra_config or ExtraConfig()
        self.session_name = session_name
        self.work_dir = work_dir
        self.app_version = app_version
        self.catalog = catalog or VersionCatalog()

        configure_logging(self.extra_config.log_level)
        logger.debug(
            "creating client phone_set=%s session=%s work_dir=%s proxy_set=%s reconnect=%s",
            bool(phone),
            self.session_name,
            self.work_dir,
            bool(self.extra_config.proxy),
            self.extra_config.reconnect,
        )

        if auth_flow is None:
            auth_flow = SmsAuthFlow(
                sms_code_provider or ConsoleSmsCodeProvider(),
                password_provider,
            )
        self._auth_flow = auth_flow
        self._router = Router()

        logger.debug(
            "client created transport=tcp host=%s port=%s",
            self.extra_config.host,
            self.extra_config.port,
        )

    async def _prepare_config(self) -> ClientConfig:
        catalog = await self.catalog.load()
        fingerprint = catalog.resolve(self.app_version)

        user_agent = self.extra_config.user_agent or self.extra_config.generate_user_agent(
            self.app_version, fingerprint.build_number
        )

        return self._build_config(
            phone=self.phone,
            user_agent=user_agent,
            version=self.app_version,
            fingerprint=fingerprint,
        )

    def _build_connection(self) -> ConnectionManager:
        logger.debug(
            "building tcp connection host=%s port=%s ssl=%s",
            self.extra_config.host,
            self.extra_config.port,
            self.extra_config.use_ssl,
        )
        transport = TCPTransport(
            port=self.extra_config.port,
            host=self.extra_config.host,
            use_ssl=self.extra_config.use_ssl,
            proxy=self.extra_config.proxy,
        )
        reader = TCPReader(
            transport=transport,
            framer=TcpPacketFramer(),
        )
        return ConnectionManager(
            reader=reader,
            transport=transport,
            protocol=TcpProtocol(),
        )
