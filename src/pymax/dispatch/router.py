from __future__ import annotations

from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    Concatenate,
    Generic,
    ParamSpec,
    Protocol,
    TypeAlias,
    TypeVar,
)

from pymax.filters import Filter
from pymax.types import MessageDeleteEvent

from .enums import EventType

if TYPE_CHECKING:
    from pymax.base import BaseClient
    from pymax.client import Client
    from pymax.dispatch.middleware import Middleware
    from pymax.protocol import InboundFrame
    from pymax.types import Chat, StoryPreview
    from pymax.types.domain import Message
    from pymax.types.events import (
        MessageReadEvent,
        PresenceEvent,
        ReactionUpdateEvent,
        TypingEvent,
    )


class ErrorScope(str, Enum):
    """Область действия error-handler-а."""

    GLOBAL = "global"
    LOCAL = "local"


_EventT = TypeVar("_EventT")
ClientT = TypeVar("ClientT", bound="BaseClient")
_P = ParamSpec("_P")

HandlerCallback: TypeAlias = Callable[
    [_EventT, ClientT],
    Awaitable[Any] | Any,
]
# HandlerDecorator: TypeAlias = Callable[
#     [HandlerCallback[_EventT, ClientT]],
#     HandlerCallback[_EventT, ClientT],
# ]

HandlerResult: TypeAlias = Awaitable[Any] | Any


class HandlerDecorator(Protocol, Generic[_EventT, ClientT]):
    def __call__(
        self,
        handler: Callable[
            Concatenate[_EventT, ClientT, _P],
            HandlerResult,
        ],
    ) -> Callable[
        Concatenate[_EventT, ClientT, _P],
        HandlerResult,
    ]: ...


StartCallback: TypeAlias = Callable[
    [ClientT],
    Awaitable[Any] | Any,
]
StartDecorator: TypeAlias = Callable[
    [StartCallback[ClientT]],
    StartCallback[ClientT],
]


@dataclass(slots=True)
class ErrorContext(Generic[ClientT]):
    """Контекст ошибки, передаваемый в ``on_error`` callback."""

    client: ClientT
    event_type: EventType
    event: Any
    handler: HandlerEntry[Any, ClientT] | StartCallback | None
    router: Router[ClientT]


ErrorCallback: TypeAlias = Callable[
    [Exception, ErrorContext[ClientT]],
    Awaitable[Any] | Any,
]

ErrorDecorator: TypeAlias = Callable[
    [ErrorCallback[ClientT]],
    ErrorCallback[ClientT],
]

DisconnectCallback: TypeAlias = Callable[
    [Exception, bool, float],
    Awaitable[Any] | Any,
]

DisconnectDecorator: TypeAlias = Callable[
    [DisconnectCallback],
    DisconnectCallback,
]


@dataclass(slots=True)
class HandlerEntry(Generic[_EventT, ClientT]):
    callback: HandlerCallback[_EventT, ClientT]
    filters: tuple[Filter, ...] = ()


@dataclass(slots=True)
class ErrorEntry(Generic[ClientT]):
    callback: ErrorCallback[ClientT]
    scope: ErrorScope = ErrorScope.GLOBAL


ErrorSource: TypeAlias = HandlerEntry[Any, ClientT] | StartCallback[ClientT]


class Router(Generic[ClientT]):
    """Контейнер обработчиков событий PyMax.

    Роутер хранит обработчики и фильтры. Когда приходит событие, dispatcher
    проверяет обработчики в порядке регистрации и вызывает первый подходящий
    в каждом роутере, затем обходит его дочерние роутеры. Первые два аргумента
    обработчика — ``event`` и ``client``; дополнительные обязательные параметры
    разрешаются по аннотациям типов через DI.

    Example:
        .. code-block:: python

           from pymax import Client, Message, Router
           from pymax.filters import Command

           router = Router[Client]()

           @router.on_message(Command("start"))
           async def start(message: Message, client: Client) -> None:
               await message.answer("Привет")

           client = Client(phone="+79990000000")
           client.include_router(router)
    """

    def __init__(self) -> None:
        self.handlers: dict[
            EventType,
            list[HandlerEntry[Any, ClientT]],
        ] = defaultdict(list)

        self.children: list[Router[ClientT]] = []
        self.middlewares: list[Middleware[ClientT]] = []
        self.on_start_handlers: list[StartCallback[ClientT]] = []
        self.error_handlers: list[ErrorEntry[ClientT]] = []
        self.disconnect_handlers: list[DisconnectCallback] = []

    def on_error(
        self,
        scope: ErrorScope = ErrorScope.GLOBAL,
    ) -> ErrorDecorator[ClientT]:
        """Регистрирует обработчик ошибок для текущего router-а.

        ``GLOBAL``-handler видит ошибки всего дерева подключенных router-ов.
        ``LOCAL``-handler видит только ошибки своего router-а.
        Callback получает ``handler(exception, context)``. При обработке
        событий сюда передаются ошибки фильтров, middleware и handler-ов.
        """
        scope = ErrorScope(scope)

        def decorator(callback: ErrorCallback[ClientT]) -> ErrorCallback[ClientT]:
            self.error_handlers.append(ErrorEntry(callback=callback, scope=scope))
            return callback

        return decorator

    def on_disconnect(self) -> DisconnectDecorator:
        """Регистрирует обработчик потери соединения.

        Callback вызывается как ``handler(exception, reconnect, delay)``:
        исходная ошибка, будет ли reconnect и задержка перед ним.
        """

        def decorator(callback: DisconnectCallback) -> DisconnectCallback:
            self.disconnect_handlers.append(callback)
            return callback

        return decorator

    def on(
        self,
        event: EventType,
        /,
        *filters: Filter[_EventT, ClientT],
    ) -> HandlerDecorator[_EventT, ClientT]:
        """Регистрирует обработчик события по ``EventType``.

        Args:
            event: Тип события.
            *filters: Экземпляры ``Filter``, вызываемые как
                ``filter(event, client)``. Все фильтры должны вернуть ``True``;
                async-результаты ожидаются автоматически.

        Returns:
            Декоратор для ``handler(event, client)``.

        Example:
            .. code-block:: python

               from pymax import Client, EventType
               from pymax.protocol import InboundFrame

               @router.on(EventType.RAW)
               async def raw(frame: InboundFrame, client: Client) -> None:
                   print(frame.payload)
        """

        def decorator(
            handler: Callable[
                Concatenate[_EventT, ClientT, _P],
                HandlerResult,
            ],
        ) -> Callable[
            Concatenate[_EventT, ClientT, _P],
            HandlerResult,
        ]:
            self.handlers[event].append(
                HandlerEntry(
                    callback=handler,
                    filters=filters,
                )
            )
            return handler

        return decorator

    def include_router(self, router: Router[ClientT]) -> None:
        """Подключает дочерний роутер.

        Args:
            router: Router, обработчики которого нужно добавить в дерево.

        Returns:
            ``None``.
        """
        self.children.append(router)

    def on_start(self) -> StartDecorator:
        """Регистрирует обработчик старта клиента.

        Returns:
            Декоратор для ``handler(client)``.
        """

        def decorator(handler: StartCallback) -> StartCallback:
            self.on_start_handlers.append(handler)
            return handler

        return decorator

    def on_message(
        self,
        *filters: Filter[Message, ClientT],
    ) -> HandlerDecorator[Message, ClientT]:
        """Регистрирует обработчик новых сообщений.

        Args:
            *filters: Фильтры для ``Message``.

        Returns:
            Декоратор для ``handler(message, client)``.
        """
        return self.on(EventType.MESSAGE_NEW, *filters)

    def on_message_edit(
        self,
        *filters: Filter[Message, ClientT],
    ) -> HandlerDecorator[Message, ClientT]:
        """Регистрирует обработчик редактирования сообщений.

        Args:
            *filters: Фильтры для ``Message``.

        Returns:
            Декоратор для ``handler(message, client)``.
        """
        return self.on(EventType.MESSAGE_EDIT, *filters)

    def on_message_delete(
        self,
        *filters: Filter[MessageDeleteEvent, ClientT],
    ) -> HandlerDecorator[MessageDeleteEvent, ClientT]:
        """Регистрирует обработчик удаления сообщений.

        Args:
            *filters: Фильтры для ``MessageDeleteEvent``.

        Returns:
            Декоратор для ``handler(event, client)``.
        """
        return self.on(EventType.MESSAGE_DELETE, *filters)

    def on_message_read(
        self,
        *filters: Filter[MessageReadEvent, ClientT],
    ) -> HandlerDecorator[MessageReadEvent, ClientT]:
        """Регистрирует обработчик изменения отметки прочтения."""
        return self.on(EventType.MESSAGE_READ, *filters)

    def on_typing(
        self,
        *filters: Filter[TypingEvent, ClientT],
    ) -> HandlerDecorator[TypingEvent, ClientT]:
        """Регистрирует обработчик набора текста."""
        return self.on(EventType.TYPING, *filters)

    def on_presence(
        self,
        *filters: Filter[PresenceEvent, ClientT],
    ) -> HandlerDecorator[PresenceEvent, ClientT]:
        """Регистрирует обработчик изменения присутствия пользователя."""
        return self.on(EventType.PRESENCE, *filters)

    def on_reaction_update(
        self,
        *filters: Filter[ReactionUpdateEvent, ClientT],
    ) -> HandlerDecorator[ReactionUpdateEvent, ClientT]:
        """Регистрирует обработчик ``ReactionUpdateEvent``.

        Получает обновления счетчиков реакций и реакции текущего пользователя.
        """
        return self.on(EventType.REACTION_UPDATE, *filters)

    def on_chat_update(
        self,
        *filters: Filter[Chat, ClientT],
    ) -> HandlerDecorator[Chat, ClientT]:
        """Регистрирует обработчик обновления чата.

        Args:
            *filters: Фильтры для ``Chat``.

        Returns:
            Декоратор для ``handler(chat, client)``.
        """
        return self.on(EventType.CHAT_UPDATE, *filters)

    def on_story_update(
        self,
        *filters: Filter[StoryPreview, ClientT],
    ) -> HandlerDecorator[StoryPreview, ClientT]:
        """Регистрирует обработчик обновления ``StoryPreview`` владельца.

        Первый аргумент handler-а содержит сводное превью, а не ``Story``.
        """
        return self.on(EventType.STORY_UPDATE, *filters)

    def on_raw(
        self,
        *filters: Filter[InboundFrame, ClientT],
    ) -> HandlerDecorator[InboundFrame, ClientT]:
        """Регистрирует обработчик исходных frame-ов.

        Вызывается после типизированной обработки, даже если тип события
        неизвестен или его обработка завершилась ошибкой.

        Args:
            *filters: Фильтры для ``InboundFrame``.

        Returns:
            Декоратор для ``handler(frame, client)``.
        """
        return self.on(EventType.RAW, *filters)


ClientRouter: TypeAlias = Router["Client"]
