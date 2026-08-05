from __future__ import annotations

import builtins
from typing import TYPE_CHECKING, Any, TypeVar

from pymax.filters.base import ClientT_contra, Filter, PathResolver
from pymax.filters.refs import FieldRef, NumberFieldRef, TextFieldRef

if TYPE_CHECKING:
    from pymax.base import BaseClient

EventT = TypeVar("EventT")


class MessageContainer(Filter[EventT, ClientT_contra], PathResolver):
    def __init__(
        self,
        expected_type: builtins.type[EventT],
        path: list[str] | None = None,
    ) -> None:
        self.expected_type: type[EventT] = expected_type
        self.path = path or []

    @property
    def text(self) -> TextFieldRef:
        return TextFieldRef(
            path=[*self.path, "text"],
            expected_type=self.expected_type,
        )

    @property
    def id(self) -> NumberFieldRef:
        return NumberFieldRef(
            path=[*self.path, "id"],
            expected_type=self.expected_type,
        )

    @property
    def chat_id(self) -> NumberFieldRef:
        return NumberFieldRef(
            path=[*self.path, "chat_id"],
            expected_type=self.expected_type,
        )

    @property
    def sender(self) -> NumberFieldRef:
        return NumberFieldRef(
            path=[*self.path, "sender"],
            expected_type=self.expected_type,
        )

    @property
    def time(self) -> NumberFieldRef:
        return NumberFieldRef(
            path=[*self.path, "time"],
            expected_type=self.expected_type,
        )

    @property
    def type(self) -> TextFieldRef:
        return TextFieldRef(
            path=[*self.path, "type"],
            expected_type=self.expected_type,
        )

    @property
    def cid(self) -> NumberFieldRef:
        return NumberFieldRef(
            path=[*self.path, "cid"],
            expected_type=self.expected_type,
        )

    @property
    def attaches(self) -> FieldRef:
        return FieldRef(
            path=[*self.path, "attaches"],
            expected_type=self.expected_type,
        )

    @property
    def stats(self) -> FieldRef:
        return FieldRef(
            path=[*self.path, "stats"],
            expected_type=self.expected_type,
        )

    @property
    def status(self) -> TextFieldRef:
        return TextFieldRef(
            path=[*self.path, "status"],
            expected_type=self.expected_type,
        )

    @property
    def reaction_info(self) -> FieldRef:
        return FieldRef(
            path=[*self.path, "reaction_info"],
            expected_type=self.expected_type,
        )

    @property
    def options(self) -> FieldRef:
        return FieldRef(
            path=[*self.path, "options"],
            expected_type=self.expected_type,
        )

    @property
    def prev_message_id(self) -> NumberFieldRef:
        return NumberFieldRef(
            path=[*self.path, "prev_message_id"],
            expected_type=self.expected_type,
        )

    @property
    def ttl(self) -> FieldRef:
        return FieldRef(
            path=[*self.path, "ttl"],
            expected_type=self.expected_type,
        )

    @property
    def unread(self) -> NumberFieldRef:
        return NumberFieldRef(
            path=[*self.path, "unread"],
            expected_type=self.expected_type,
        )

    @property
    def mark(self) -> NumberFieldRef:
        return NumberFieldRef(
            path=[*self.path, "mark"],
            expected_type=self.expected_type,
        )

    @property
    def elements(self) -> FieldRef:
        return FieldRef(
            path=[*self.path, "elements"],
            expected_type=self.expected_type,
        )

    def __call__(self, event: Any, client: ClientT_contra) -> bool:
        if not isinstance(event, self.expected_type):
            return False

        return bool(self.resolve_path(event))
