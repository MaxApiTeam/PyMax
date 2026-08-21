from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Generic, TypeVar
from uuid import uuid4

from pymax.dispatch import ErrorScope, Router
from pymax.dispatch.router import DisconnectDecorator, ErrorDecorator
from pymax.exceptions import ApiError
from pymax.fingerprint.models import ApkBuildFingerprint
from pymax.infra import BaseMixin
from pymax.logging import get_logger

from .app import App
from .config import ClientConfig, DeviceConfig, ExtraConfig

if TYPE_CHECKING:
    from pymax.api.session.payloads import MobileUserAgentPayload
    from pymax.auth import AuthFlow
    from pymax.connection import ConnectionManager
    from pymax.dispatch.router import (
        FilterCallback,
        HandlerDecorator,
        StartDecorator,
    )
    from pymax.protocol import InboundFrame
    from pymax.types import (
        Chat,
        MessageDeleteEvent,
        MessageReadEvent,
        PresenceEvent,
        ReactionUpdateEvent,
        TypingEvent,
        User,
    )
    from pymax.types.domain import Message, Profile

logger = get_logger(__name__)
ClientT = TypeVar("ClientT", bound="BaseClient[Any]")


class BaseClient(BaseMixin, ABC, Generic[ClientT]):
    extra_config: ExtraConfig
    session_name: str
    work_dir: str
    _config: ClientConfig
    _connection: ConnectionManager
    _auth_flow: AuthFlow
    _router: Router[ClientT]
    _app: App[ClientT]

    @property
    def me(self) -> Profile | None:
        """Профиль текущего аккаунта после успешного ``start``."""
        return self._app.me

    @property
    def chats(self) -> list[Chat] | None:
        """Чаты, которые Max вернул на login/sync."""
        return self._app.chats

    @property
    def contacts(self) -> list[User | None]:
        """Контакты, которые Max вернул на login/sync."""
        return self._app.contacts

    @property
    def messages(self) -> dict[int, list[Message]] | None:
        """Сообщения, которые Max вернул на login/sync."""
        return self._app.messages

    def _build_config(
        self,
        *,
        phone: str | None,
        user_agent: MobileUserAgentPayload,
        version: str | None,
        fingerprint: ApkBuildFingerprint | None,
    ) -> ClientConfig:
        logger.debug(
            "building client config token_set=%s",
            bool(self.extra_config.token),
        )
        return ClientConfig(
            phone=phone,
            session_name=self.session_name,
            work_dir=self.work_dir,
            token=self.extra_config.token,
            host=self.extra_config.host,
            port=self.extra_config.port,
            use_ssl=self.extra_config.use_ssl,
            request_timeout=self.extra_config.request_timeout,
            log_level=self.extra_config.log_level,
            telemetry=self.extra_config.telemetry,
            sync=self.extra_config.sync,
            store=self.extra_config.store,
            proxy=self.extra_config.proxy,
            registration_config=self.extra_config.registration_config,
            upload_timeout=self.extra_config.upload_timeout,
            relogin=self.extra_config.relogin,
            app_version=version,
            fingering=fingerprint,
            device=DeviceConfig(
                mt_instance_id=self.extra_config.mt_instance_id,
                device_id=self.extra_config.device_id or str(uuid4()),
                user_agent=user_agent,
            ),
        )

    @abstractmethod
    def _build_connection(self) -> ConnectionManager:

        raise NotImplementedError

    @abstractmethod
    async def _prepare_config(self) -> ClientConfig:
        raise NotImplementedError

    async def _ensure_runtime(self: ClientT) -> None:  # noqa: PYI019
        if getattr(self, "_config", None) is None:
            self._config = await self._prepare_config()
        self._connection = self._build_connection()
        self._app = self._build_app()

    def _init_runtime(self: ClientT, *, auth_flow: AuthFlow) -> None:  # noqa: PYI019
        self._connection = self._build_connection()
        self._auth_flow = auth_flow
        self._router = Router()
        self._app = self._build_app()

    def _build_app(self: ClientT) -> App[ClientT]:  # noqa: PYI019
        app: App[ClientT] = App(
            connection=self._connection,
            config=self._config,
            auth_flow=self._auth_flow,
            root_router=self._router,
        )
        app.dispatcher.bind_client(self)
        return app

    def _reset_runtime(self: ClientT) -> None:  # noqa: PYI019
        self._connection = self._build_connection()
        self._app = self._build_app()

    async def connect(self: ClientT) -> None:  # noqa: PYI019
        try:
            await self._ensure_runtime()
            await self._app.start()
            if not self._app.started:
                await self.close()
                return

            await self._app.dispatcher.emit_start(self)
        except asyncio.CancelledError:
            await self.close()
            raise
        except (ConnectionError, EOFError, OSError, TimeoutError, ApiError) as e:
            await self.close()
            await self._app.dispatcher.emit_disconnect(
                e,
                self.extra_config.reconnect,
                self.extra_config.reconnect_delay,
            )
            raise

    async def start(self: ClientT) -> None:  # noqa: PYI019
        """Запускает клиента и слушает события до закрытия соединения."""
        while True:
            try:
                await self._ensure_runtime()
                await self._app.start()
                if not self._app.started:
                    await self.close()
                    return

                await self._app.dispatcher.emit_start(self)
                await self._connection.wait_closed()
            except asyncio.CancelledError:
                await self.close()
                raise
            except ApiError as e:
                if not self._app._is_invalid_login_token_error(e):
                    await self.close()
                    raise

                logger.warning("login token was revoked; starting authentication again")
                if self.extra_config.relogin:
                    await self.relogin(start=False)
            except (
                ConnectionError,
                EOFError,
                OSError,
                TimeoutError,
            ) as e:
                await self.close()
                await self._app.dispatcher.emit_disconnect(
                    e,
                    self.extra_config.reconnect,
                    self.extra_config.reconnect_delay,
                )

                if not self.extra_config.reconnect:
                    raise

                logger.debug(
                    "client connection failed; reconnecting in %s seconds",
                    self.extra_config.reconnect_delay,
                    exc_info=True,
                )
                await asyncio.sleep(self.extra_config.reconnect_delay)
                self._reset_runtime()
            except Exception:
                await self.close()
                raise
            else:
                await self.close()
                return

    async def close(self) -> None:
        """Закрывает соединение, фоновые задачи и файл сессии."""
        if getattr(self, "_app", None) is None:  # TODO: maybe impl it better way
            return

        await self._app.close()

    async def stop(self) -> None:
        """Останавливает клиента."""
        await self.close()

    async def __aenter__(self: ClientT) -> ClientT:  # noqa: PYI019
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    def on_start(self) -> StartDecorator[ClientT]:
        """Регистрирует обработчик успешного запуска."""
        return self._router.on_start()

    def on_message(
        self,
        *filters: FilterCallback[Message],
    ) -> HandlerDecorator[Message, ClientT]:
        """Регистрирует обработчик новых сообщений."""
        return self._router.on_message(*filters)

    def on_message_edit(
        self,
        *filters: FilterCallback[Message],
    ) -> HandlerDecorator[Message, ClientT]:
        """Регистрирует обработчик редактирования сообщений."""
        return self._router.on_message_edit(*filters)

    def on_message_delete(
        self,
        *filters: FilterCallback[MessageDeleteEvent],
    ) -> HandlerDecorator[MessageDeleteEvent, ClientT]:
        """Регистрирует обработчик удаления сообщений."""
        return self._router.on_message_delete(*filters)

    def on_message_read(
        self,
        *filters: FilterCallback[MessageReadEvent],
    ) -> HandlerDecorator[MessageReadEvent, ClientT]:
        """Регистрирует обработчик изменения отметки прочтения."""
        return self._router.on_message_read(*filters)

    def on_typing(
        self,
        *filters: FilterCallback[TypingEvent],
    ) -> HandlerDecorator[TypingEvent, ClientT]:
        """Регистрирует обработчик набора текста."""
        return self._router.on_typing(*filters)

    def on_presence(
        self,
        *filters: FilterCallback[PresenceEvent],
    ) -> HandlerDecorator[PresenceEvent, ClientT]:
        """Регистрирует обработчик изменения присутствия пользователя."""
        return self._router.on_presence(*filters)

    def on_reaction_update(
        self,
        *filters: FilterCallback[ReactionUpdateEvent],
    ) -> HandlerDecorator[ReactionUpdateEvent, ClientT]:
        """Регистрирует обработчик обновления реакций сообщения."""
        return self._router.on_reaction_update(*filters)

    def on_chat_update(
        self,
        *filters: FilterCallback[Chat],
    ) -> HandlerDecorator[Chat, ClientT]:
        """Регистрирует обработчик обновления чата."""
        return self._router.on_chat_update(*filters)

    def on_raw(
        self,
        *filters: FilterCallback[InboundFrame],
    ) -> HandlerDecorator[InboundFrame, ClientT]:
        """Регистрирует обработчик исходных входящих frame-ов."""
        return self._router.on_raw(*filters)

    def on_error(self, scope: ErrorScope = ErrorScope.GLOBAL) -> ErrorDecorator[ClientT]:
        """Регистрирует обработчик ошибок dispatch-а и запуска клиента."""
        return self._router.on_error(scope)

    def on_disconnect(self) -> DisconnectDecorator:
        """Регистрирует обработчик сетевого отключения перед reconnect."""
        return self._router.on_disconnect()

    def include_router(self, router: Router[ClientT]) -> None:
        """Подключает дочерний router к root router клиента."""
        self._router.include_router(router)

    async def relogin(self: ClientT, drop_config_token: bool = True, start: bool = True) -> None:  # noqa: PYI019
        """Удаляет текущую локальную сессию и запускает авторизацию заново.

        Args:
            drop_config_token: Сбросить token, переданный через ``ExtraConfig``.
            start: Сразу запустить клиента после сброса runtime.
        """
        store = self._app.store
        session = self._app.session

        if session is None:
            raise RuntimeError("Cannot relogin before session is loaded")

        await store.delete_session(session.token)
        await self.close()

        if drop_config_token:
            self.extra_config.token = None
            self._config.token = None

        self._reset_runtime()

        if start:
            await self.start()
