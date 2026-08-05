from __future__ import annotations

import asyncio
import inspect
from contextlib import suppress
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from pymax.filters import Filter
from pymax.logging import get_logger
from pymax.protocol import InboundFrame
from pymax.types import Chat, MessageDeleteEvent
from pymax.types.domain import Message
from pymax.types.events import (
    MessageReadEvent,
    PresenceEvent,
    ReactionUpdateEvent,
    TypingEvent,
)

from .enums import EventType
from .mapping import EventMapper, EventResolver
from .router import (
    DisconnectCallback,
    DisconnectDecorator,
    ErrorContext,
    ErrorDecorator,
    ErrorEntry,
    ErrorScope,
    ErrorSource,
    HandlerCallback,
    HandlerDecorator,
    HandlerEntry,
    Router,
    StartCallback,
    StartDecorator,
)

if TYPE_CHECKING:
    from collections.abc import Generator

    from pymax.app import App
    from pymax.base import BaseClient


logger = get_logger(__name__)

ClientT = TypeVar("ClientT", bound="BaseClient")
EventT = TypeVar("EventT")


class Dispatcher(Generic[ClientT]):
    def __init__(self, app: App, root_router: Router[ClientT] | None = None) -> None:
        self.root_router: Router[ClientT] = root_router or Router()
        self.internal_router: Router[ClientT] = Router()
        self.resolver = EventResolver()
        self.mapper = EventMapper(app)
        self.startup_tasks: list[asyncio.Task[Any]] = []
        self.client: ClientT | None = None

    def bind_client(self, client: ClientT) -> None:
        self.client = client

    def include_router(self, router: Router[ClientT]) -> None:
        self.root_router.include_router(router)
        logger.debug(
            "router included handlers=%s children=%s",
            len(router.handlers),
            len(router.children),
        )

    def on_internal(
        self,
        event: EventType,
        *filters: Filter[Any, ClientT],
    ) -> HandlerDecorator[Any, ClientT]:
        logger.debug(
            "registering internal handler event=%s filters=%s",
            event,
            len(filters),
        )
        return self.internal_router.on(event, *filters)

    def on(
        self,
        event: EventType,
        *filters: Filter[Any, ClientT],
    ) -> HandlerDecorator[Any, ClientT]:
        logger.debug("registering handler event=%s filters=%s", event, len(filters))
        return self.root_router.on(event, *filters)

    def on_error(self, scope: ErrorScope = ErrorScope.GLOBAL) -> ErrorDecorator[ClientT]:
        return self.root_router.on_error(scope)

    def on_disconnect(self) -> DisconnectDecorator:
        """Регистрирует обработчик сетевого отключения на root router."""
        return self.root_router.on_disconnect()

    def on_message(
        self,
        *filters: Filter[Message, ClientT],
    ) -> HandlerDecorator[Message, ClientT]:
        logger.debug("registering message handler filters=%s", len(filters))
        return self.root_router.on_message(*filters)

    def on_message_edit(
        self,
        *filters: Filter[Message, ClientT],
    ) -> HandlerDecorator[Message, ClientT]:
        logger.debug("registering message edit handler filters=%s", len(filters))
        return self.root_router.on_message_edit(*filters)

    def on_message_delete(
        self,
        *filters: Filter[MessageDeleteEvent, ClientT],
    ) -> HandlerDecorator[MessageDeleteEvent, ClientT]:
        return self.root_router.on_message_delete(*filters)

    def on_message_read(
        self,
        *filters: Filter[MessageReadEvent, ClientT],
    ) -> HandlerDecorator[MessageReadEvent, ClientT]:
        return self.root_router.on_message_read(*filters)

    def on_typing(
        self,
        *filters: Filter[TypingEvent, ClientT],
    ) -> HandlerDecorator[TypingEvent, ClientT]:
        return self.root_router.on_typing(*filters)

    def on_presence(
        self,
        *filters: Filter[PresenceEvent, ClientT],
    ) -> HandlerDecorator[PresenceEvent, ClientT]:
        return self.root_router.on_presence(*filters)

    def on_reaction_update(
        self,
        *filters: Filter[ReactionUpdateEvent, ClientT],
    ) -> HandlerDecorator[ReactionUpdateEvent, ClientT]:
        return self.root_router.on_reaction_update(*filters)

    def on_chat_update(
        self,
        *filters: Filter[Chat, ClientT],
    ) -> HandlerDecorator[Chat, ClientT]:
        return self.root_router.on_chat_update(*filters)

    def on_raw(
        self,
        *filters: Filter[InboundFrame, ClientT],
    ) -> HandlerDecorator[InboundFrame, ClientT]:
        return self.root_router.on_raw(*filters)

    def on_start(self) -> StartDecorator[ClientT]:
        return self.root_router.on_start()

    def iter_routers(self) -> Generator[Router[ClientT], Any, None]:
        yield from self._iter_router(self.root_router)

    def _iter_router(self, router: Router[ClientT]) -> Generator[Router[ClientT], Any, None]:
        yield router

        for child in router.children:
            yield from self._iter_router(child)

    def iter_error_entries(
        self,
    ) -> Generator[tuple[Router[ClientT], ErrorEntry[ClientT]], Any, None]:
        for router in self.iter_routers():
            for entry in router.error_handlers:
                yield router, entry

    def iter_disconnect_handlers(self) -> Generator[DisconnectCallback, Any, None]:
        """Итерирует обработчики disconnect по root router и его детям."""
        for router in self.iter_routers():
            yield from router.disconnect_handlers

    def iter_error_handlers(
        self,
        failed_router: Router[ClientT],
    ) -> Generator[ErrorEntry[ClientT], Any, None]:
        for owner_router, entry in self.iter_error_entries():
            if entry.scope is ErrorScope.LOCAL and owner_router is not failed_router:
                continue

            yield entry

    async def emit_start(self, client: ClientT) -> None:
        tasks: list[asyncio.Task[Any]] = []

        for router in self.iter_routers():  # TODO: create iter_on_start_handlers
            for handler in router.on_start_handlers:
                task = asyncio.create_task(self._run_start_handler(router, handler, client))
                task.add_done_callback(_log_task_error)
                tasks.append(task)

        self.startup_tasks.extend(tasks)

    async def _run_start_handler(
        self,
        router: Router[ClientT],
        handler: StartCallback[ClientT],
        client: ClientT,
    ) -> None:
        try:
            result = handler(client)

            if inspect.isawaitable(result):
                await result

        except Exception as e:
            handled = await self.emit_error(
                e,
                EventType.ON_START,
                None,
                router,
                handler,
            )

            if not handled:
                raise

    async def stop_startup_tasks(self) -> None:
        if not self.startup_tasks:
            return

        for task in self.startup_tasks:
            if not task.done():
                task.cancel()

        for task in self.startup_tasks:
            with suppress(asyncio.CancelledError, Exception):
                await task

        self.startup_tasks = []

    async def dispatch(self, frame: InboundFrame) -> None:
        event_type = self.resolver.resolve(frame)

        if event_type is not None:
            logger.debug("dispatching event type=%s", event_type)
            event = self.mapper.map(event_type, frame)
            await self._dispatch_to_router(self.internal_router, event_type, event)
            await self._dispatch_to_router(self.root_router, event_type, event)
        else:
            logger.debug(
                "dispatching raw event only opcode=%s cmd=%s",
                frame.opcode,
                frame.cmd,
            )

        await self._dispatch_to_router(self.root_router, EventType.RAW, frame)

    async def _dispatch_to_router(
        self,
        router: Router[ClientT],
        event_type: EventType,
        event: Any,
    ) -> None:
        for entry in router.handlers.get(event_type, []):
            try:
                if await self._matches(entry, event):
                    logger.debug(
                        "calling handler event=%s callback=%s",
                        event_type,
                        _callback_name(entry.callback),
                    )
                    await self._call(entry.callback, event)
            except Exception as e:  # noqa: PERF203
                handled = await self.emit_error(e, event_type, event, router, entry)
                if not handled:
                    raise

        for child in router.children:
            await self._dispatch_to_router(child, event_type, event)

    async def _matches(
        self,
        entry: HandlerEntry[Any, ClientT],
        event: Any,
    ) -> bool:
        for flt in entry.filters:
            if not self.client:
                return False
            filter_match = flt(event, self.client)
            result = await flt.resolve_filter_result(filter_match)

            if not result:
                logger.debug(
                    "handler skipped by filter callback=%s",
                    _callback_name(entry.callback),
                )
                return False
        return True

    async def _call(self, callback: HandlerCallback[Any, ClientT], event: Any) -> Any:
        if self.client is None:
            raise RuntimeError("client is not bound")

        result = callback(event, self.client)

        if inspect.isawaitable(result):
            return await result

        return result

    async def emit_error(
        self,
        exception: Exception,
        event_type: EventType,
        event: Any,
        router: Router[ClientT],
        handler: ErrorSource[ClientT] | None,
    ) -> bool:
        client = self.client
        handled = False

        if client is None:
            raise RuntimeError("client is not bound to dispatcher")

        ctx = ErrorContext[ClientT](
            client=client,
            event_type=event_type,
            event=event,
            router=router,
            handler=handler,
        )
        for entry in self.iter_error_handlers(router):
            handled = True
            try:
                result = entry.callback(exception, ctx)

                if inspect.isawaitable(result):
                    await result
            except Exception as e:
                logger.exception("Error while error handling: %s", e)
                return False

        return handled

    async def emit_disconnect(
        self,
        exception: Exception,
        reconnect: bool,
        delay: float,
    ) -> None:
        """Вызывает обработчики потери соединения.

        Ошибки внутри disconnect-handler-ов логируются и не прерывают reconnect.
        """

        if self.client is None:
            raise RuntimeError("client is not bound to dispatcher")

        for handler in self.iter_disconnect_handlers():
            try:
                result = handler(exception, reconnect, delay)

                if inspect.isawaitable(result):
                    await result
            except Exception as e:
                logger.exception("Error during disconnect handling: %s", e)


def _callback_name(callback: Any) -> str:
    return getattr(
        callback,
        "__qualname__",
        getattr(callback, "__name__", repr(callback)),
    )


def _log_task_error(task: asyncio.Task[Any]) -> None:
    try:
        task.result()
    except asyncio.CancelledError:
        pass
    except Exception:
        logger.exception("startup task failed")
