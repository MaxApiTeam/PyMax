from __future__ import annotations

from typing import TypeVar

from .base import MISSING, ClientT_contra, FieldRef
from .filters import (
    BetweenFilter,
    ContainsFilter,
    EndsWithFilter,
    GreaterThanFilter,
    GreaterThanOrEqualFilter,
    LessThanFilter,
    LessThanOrEqualFilter,
    StartsWithFilter,
)

EventT = TypeVar("EventT")


class TextFieldRef(FieldRef[EventT, ClientT_contra]):
    def contains(self, text: str, *, ignore_case: bool = False) -> ContainsFilter:
        return ContainsFilter(self.path, self.expected_type, text, ignore_case)

    def startswith(self, text: str, *, ignore_case: bool = False) -> StartsWithFilter:
        return StartsWithFilter(self.path, self.expected_type, text, ignore_case)

    def endswith(self, text: str, *, ignore_case: bool = False) -> EndsWithFilter:
        return EndsWithFilter(self.path, self.expected_type, text, ignore_case)

    def __call__(self, event: EventT, _: ClientT_contra) -> bool:
        if not isinstance(event, self.expected_type):
            return False

        value = self.resolve_path(event)

        if value is MISSING:
            return False

        return bool(value)


class NumberFieldRef(FieldRef[EventT, ClientT_contra]):
    def __lt__(self, value: float) -> LessThanFilter:
        return LessThanFilter(self.path, self.expected_type, value)

    def __le__(self, value: float) -> LessThanOrEqualFilter:
        return LessThanOrEqualFilter(self.path, self.expected_type, value)

    def __gt__(self, value: float) -> GreaterThanFilter:
        return GreaterThanFilter(self.path, self.expected_type, value)

    def __ge__(self, value: float) -> GreaterThanOrEqualFilter:
        return GreaterThanOrEqualFilter(self.path, self.expected_type, value)

    def between(self, minimum: float, maximum: float) -> BetweenFilter:
        return BetweenFilter(self.path, self.expected_type, minimum, maximum)
