from __future__ import annotations

from pymax.auth.base import AuthFlow
from pymax.auth.providers import ConsoleQrHandler, QrHandler
from pymax.auth.qr import QrAuthFlow
from pymax.connection import ConnectionManager
from pymax.connection.readers import WSReader
from pymax.logging import configure_logging, get_logger
from pymax.protocol.tcp import TcpProtocol
from pymax.transport.websocket import WebSocketTransport

from .base import BaseClient
from .config import ExtraConfig

logger = get_logger(__name__)


class WebClient(BaseClient["WebClient"]):
    """WebSocket-клиент PyMax с QR-авторизацией.

    Используйте ``WebClient``, когда нужен web-режим Max: клиент открывает
    WebSocket, показывает QR через ``qr_provider`` и после подтверждения
    сохраняет сессию в ``work_dir/session_name``.

    Args:
        session_name: Имя SQLite-файла сессии внутри ``work_dir``.
        work_dir: Директория для файла сессии.
        extra_config: Настройки URL, логов, reconnect, device и sync.
        auth_flow: Пользовательский QR auth-flow.
        qr_provider: Обработчик, который показывает QR пользователю.
    """

    def __init__(
        self,
        session_name: str = "session.db",
        work_dir: str = ".",
        extra_config: ExtraConfig | None = None,
        auth_flow: AuthFlow | None = None,
        qr_provider: QrHandler | None = None,
    ) -> None:
        self.extra_config = extra_config or ExtraConfig()
        self.session_name = session_name
        self.work_dir = work_dir

        configure_logging(self.extra_config.log_level)
        logger.debug(
            "creating web client session=%s work_dir=%s proxy_set=%s reconnect=%s",
            self.session_name,
            self.work_dir,
            bool(self.extra_config.proxy),
            self.extra_config.reconnect,
        )

        self._config = self._build_config(
            phone=None,
            user_agent=(
                self.extra_config.user_agent or self.extra_config.generate_web_user_agent()
            ),
        )

        if auth_flow is None:
            auth_flow = QrAuthFlow(qr_provider or ConsoleQrHandler())
        self._init_runtime(auth_flow=auth_flow)

        logger.debug(
            "web client created transport=ws url=%s",
            self.extra_config.url,
        )

    def _build_connection(self) -> ConnectionManager:
        logger.debug(
            "building websocket connection url=%s",
            self.extra_config.url,
        )
        transport = WebSocketTransport(
            url=self.extra_config.url,
            proxy=self.extra_config.proxy,
        )
        reader = WSReader(transport=transport)
        return ConnectionManager(
            reader=reader,
            transport=transport,
            protocol=TcpProtocol(),
        )
