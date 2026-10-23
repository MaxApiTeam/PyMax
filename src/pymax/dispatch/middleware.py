from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, Generic, Protocol, TypeAlias, TypeVar

from .mapping import DispatchEvent

if TYPE_CHECKING:
    from pymax.base import BaseClient


ClientT_contra = TypeVar("ClientT_contra", bound="BaseClient", contravariant=True)

MiddlewareNext: TypeAlias = Callable[[DispatchEvent], Awaitable[Any]]


class Middleware(Protocol, Generic[ClientT_contra]):
    async def __call__(
        self,
        client: ClientT_contra,
        event: DispatchEvent,
        call_next: MiddlewareNext,
    ) -> Any: ...
