from __future__ import annotations

from abc import ABC, abstractmethod
from inspect import isawaitable
from typing import TYPE_CHECKING, Any, Generic, TypeVar

if TYPE_CHECKING:
    from collections.abc import Awaitable

    from pymax.base import BaseClient


MISSING = object()

EventT = TypeVar("EventT")
ClientT_contra = TypeVar("ClientT_contra", bound="BaseClient", contravariant=True)


class Filter(ABC, Generic[EventT, ClientT_contra]):
    @abstractmethod
    def __call__(
        self,
        event: EventT,
        client: ClientT_contra,
        /,
    ) -> bool | Awaitable[bool]: ...
    def __and__(self, other: Filter[EventT, ClientT_contra]) -> AndFilter:
        return AndFilter(self, other)

    def __or__(self, value: Filter[EventT, ClientT_contra]) -> OrFilter:
        return OrFilter(self, value)

    def __invert__(self) -> NotFilter:
        return NotFilter(self)

    async def resolve_filter_result(
        self,
        result: bool | Awaitable[bool],
    ) -> bool:
        if isawaitable(result):
            return await result

        return result


class PathResolver:
    def __init__(self, path: list[str]) -> None:
        self.path = path

    def resolve_path(self, event: Any) -> Any | None:
        value = event

        for attr in self.path:
            value = getattr(value, attr, MISSING)

            if value is MISSING:
                return MISSING

        return value


class IsNoneFilter(Filter[EventT, ClientT_contra], PathResolver):
    def __init__(
        self,
        path: list[str],
        expected_type: type[EventT],
    ) -> None:
        super().__init__(path)
        self.expected_type = expected_type
        self.path = path

    def __call__(self, event: EventT, _: ClientT_contra) -> bool:
        if not isinstance(event, self.expected_type):
            return False

        value = self.resolve_path(event)

        if value is MISSING:
            return False

        return value is None


class IsEmptyFilter(Filter[EventT, ClientT_contra], PathResolver):
    def __init__(
        self,
        path: list[str],
        expected_type: type[EventT],
    ) -> None:
        super().__init__(path)
        self.expected_type = expected_type
        self.path = path

    def __call__(self, event: EventT, _: ClientT_contra) -> bool:
        if not isinstance(event, self.expected_type):
            return False

        value = self.resolve_path(event)

        return value == []


class FieldRef(Filter[EventT, ClientT_contra], PathResolver):
    def __init__(self, path: list[str], expected_type: type[EventT]) -> None:
        super().__init__(path)
        self.expected_type: type[EventT] = expected_type
        self.path = path

    def __eq__(self, value: object) -> EqFilter:  # pyright: ignore[reportIncompatibleMethodOverride] # ty: ignore[invalid-method-override]
        return EqFilter(self.path, self.expected_type, value)

    def __ne__(self, value: object) -> NeFilter:  # pyright: ignore[reportIncompatibleMethodOverride] # ty: ignore[invalid-method-override]
        return NeFilter(self.path, self.expected_type, value)

    def is_none(self) -> IsNoneFilter:
        return IsNoneFilter(self.path, expected_type=self.expected_type)

    def is_empty(self) -> IsEmptyFilter:
        return IsEmptyFilter(self.path, expected_type=self.expected_type)

    def __call__(self, event: EventT, _: ClientT_contra, /) -> bool:
        if not isinstance(event, self.expected_type):
            return False

        value = self.resolve_path(event)

        if value is MISSING:
            return False

        return bool(value)


class BinaryFilter(Filter[EventT, ClientT_contra]):
    def __init__(
        self, left: Filter[EventT, ClientT_contra], right: Filter[EventT, ClientT_contra]
    ) -> None:
        self.left = left
        self.right = right


class NotFilter(Filter[EventT, ClientT_contra]):
    def __init__(self, filter_instance: Filter[EventT, ClientT_contra]) -> None:
        self.filter = filter_instance

    async def __call__(self, event: EventT, client: ClientT_contra) -> bool:
        return not await self.resolve_filter_result(self.filter(event, client))


class NeFilter(Filter[EventT, ClientT_contra], PathResolver):
    def __init__(
        self,
        path: list[str],
        expected_type: type[EventT],
        expected: object,
    ) -> None:
        self.path: list[str] = path
        self.expected_type = expected_type
        self.expected: object = expected

    def __call__(self, event: EventT, _: ClientT_contra) -> bool:
        if not isinstance(event, self.expected_type):
            return False

        value = self.resolve_path(event)

        if value is MISSING:
            return False

        return value != self.expected


class AndFilter(BinaryFilter[EventT, ClientT_contra]):
    async def __call__(self, event: EventT, client: ClientT_contra) -> bool:
        left = await self.resolve_filter_result(self.left(event, client))

        if not left:
            return False

        return await self.resolve_filter_result(self.right(event, client))


class OrFilter(BinaryFilter[EventT, ClientT_contra]):
    async def __call__(self, event: EventT, client: ClientT_contra) -> bool:
        left = await self.resolve_filter_result(self.left(event, client))

        if left:
            return True

        return await self.resolve_filter_result(self.right(event, client))


class EqFilter(Filter[EventT, ClientT_contra], PathResolver):
    def __init__(
        self,
        path: list[str],
        expected_type: type[EventT],
        expected: object,
    ) -> None:
        self.path: list[str] = path
        self.expected_type = expected_type
        self.expected: object = expected

    def __call__(self, event: EventT, _: ClientT_contra) -> bool:
        if not isinstance(event, self.expected_type):
            return False

        value = self.resolve_path(event)

        if value is MISSING:
            return False

        return value == self.expected
