from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, Generic, Protocol, TypeAlias, TypeVar

from .mapping import DispatchEvent

if TYPE_CHECKING:
    from pymax.base import BaseClient


ClientT_contra = TypeVar("ClientT_contra", bound="BaseClient", contravariant=True)

MiddlewareNext: TypeAlias = Callable[[DispatchEvent], Awaitable[Any]]
"""Следующий шаг middleware-цепочки, вызываемый как ``await call_next(event)``."""


class Middleware(Protocol, Generic[ClientT_contra]):
    """Асинхронная обертка выбранного обработчика события.

    Реализуйте ``async __call__(client, event, call_next)`` и зарегистрируйте
    экземпляр через ``client.add_middleware()``. Middleware запускаются после
    фильтров в порядке регистрации для обработчиков всех подключенных роутеров.
    Вызов ``await call_next(event)`` продолжает цепочку и возвращает ее результат.
    """

    async def __call__(
        self,
        client: ClientT_contra,
        event: DispatchEvent,
        call_next: MiddlewareNext,
    ) -> Any: ...
