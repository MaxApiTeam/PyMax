from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar

from .base import ClientT_contra, Filter, PathResolver

if TYPE_CHECKING:
    from pymax.base import BaseClient

EventT = TypeVar("EventT")


class ContainsFilter(Filter[EventT, ClientT_contra], PathResolver):
    def __init__(
        self,
        path: list[str],
        expected_type: type[EventT],
        text: str,
        ignore_case: bool,
    ) -> None:
        self.path = path
        self.expected_type = expected_type
        self.text = text
        self.ignore_case = ignore_case

    def __call__(self, event: EventT, _: ClientT_contra) -> bool:
        if not isinstance(event, self.expected_type):
            return False

        value = self.resolve_path(event)

        if not isinstance(value, str):
            return False

        if self.ignore_case:
            return self.text.casefold() in value.casefold()

        return self.text in value


class StartsWithFilter(Filter[EventT, ClientT_contra], PathResolver):
    def __init__(
        self,
        path: list[str],
        expected_type: type[EventT],
        text: str,
        ignore_case: bool,
    ) -> None:
        self.path = path
        self.expected_type = expected_type
        self.text = text
        self.ignore_case = ignore_case

    def __call__(self, event: EventT, _: ClientT_contra) -> bool:
        if not isinstance(event, self.expected_type):
            return False

        value = self.resolve_path(event)

        if not isinstance(value, str):
            return False

        if self.ignore_case:
            return value.casefold().startswith(self.text.casefold())

        return value.startswith(self.text)


class EndsWithFilter(Filter[EventT, ClientT_contra], PathResolver):
    def __init__(
        self,
        path: list[str],
        expected_type: type[EventT],
        text: str,
        ignore_case: bool,
    ) -> None:
        self.path = path
        self.expected_type = expected_type
        self.text = text
        self.ignore_case = ignore_case

    def __call__(self, event: EventT, _: ClientT_contra) -> bool:
        if not isinstance(event, self.expected_type):
            return False

        value = self.resolve_path(event)

        if not isinstance(value, str):
            return False

        if self.ignore_case:
            return value.casefold().endswith(self.text.casefold())

        return value.endswith(self.text)


class LessThanFilter(Filter[EventT, ClientT_contra], PathResolver):
    def __init__(
        self,
        path: list[str],
        expected_type: type[EventT],
        expected: float,
    ) -> None:
        self.path = path
        self.expected_type = expected_type
        self.expected = expected

    def __call__(self, event: EventT, _: ClientT_contra) -> bool:
        if not isinstance(event, self.expected_type):
            return False

        value = self.resolve_path(event)

        if not isinstance(value, int | float) or isinstance(value, bool):
            return False

        return value < self.expected


class LessThanOrEqualFilter(Filter[EventT, ClientT_contra], PathResolver):
    def __init__(
        self,
        path: list[str],
        expected_type: type[EventT],
        expected: float,
    ) -> None:
        self.path = path
        self.expected_type = expected_type
        self.expected = expected

    def __call__(self, event: EventT, _: ClientT_contra) -> bool:
        if not isinstance(event, self.expected_type):
            return False

        value = self.resolve_path(event)

        if not isinstance(value, int | float) or isinstance(value, bool):
            return False

        return value <= self.expected


class GreaterThanFilter(Filter[EventT, ClientT_contra], PathResolver):
    def __init__(
        self,
        path: list[str],
        expected_type: type[EventT],
        expected: float,
    ) -> None:
        self.path = path
        self.expected_type = expected_type
        self.expected = expected

    def __call__(self, event: EventT, _: ClientT_contra) -> bool:
        if not isinstance(event, self.expected_type):
            return False

        value = self.resolve_path(event)

        if not isinstance(value, int | float) or isinstance(value, bool):
            return False

        return value > self.expected


class GreaterThanOrEqualFilter(Filter[EventT, ClientT_contra], PathResolver):
    def __init__(
        self,
        path: list[str],
        expected_type: type[EventT],
        expected: float,
    ) -> None:
        self.path = path
        self.expected_type = expected_type
        self.expected = expected

    def __call__(self, event: EventT, _: ClientT_contra) -> bool:
        if not isinstance(event, self.expected_type):
            return False

        value = self.resolve_path(event)

        if not isinstance(value, int | float) or isinstance(value, bool):
            return False

        return value >= self.expected


class BetweenFilter(Filter[EventT, ClientT_contra], PathResolver):
    def __init__(
        self,
        path: list[str],
        expected_type: type[EventT],
        minimum: float,
        maximum: float,
    ) -> None:
        self.path = path
        self.expected_type = expected_type
        self.minimum = minimum
        self.maximum = maximum

    def __call__(self, event: EventT, _: ClientT_contra) -> bool:
        if not isinstance(event, self.expected_type):
            return False

        value = self.resolve_path(event)

        if not isinstance(value, int | float) or isinstance(value, bool):
            return False

        return self.minimum <= value <= self.maximum
