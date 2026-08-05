from __future__ import annotations

import builtins
from typing import TYPE_CHECKING, Any, TypeVar

from pymax.filters.base import ClientT_contra, Filter, PathResolver
from pymax.filters.refs import FieldRef, NumberFieldRef, TextFieldRef

from .message import MessageContainer

if TYPE_CHECKING:
    from pymax.base import BaseClient

EventT = TypeVar("EventT")


class ChatContainer(Filter[EventT, ClientT_contra], PathResolver):
    def __init__(
        self,
        expected_type: builtins.type[EventT],
        path: list[str] | None = None,
    ) -> None:
        self.expected_type: type[EventT] = expected_type
        self.path = path or []

    @property
    def id(self) -> NumberFieldRef:
        return NumberFieldRef(
            path=[*self.path, "id"],
            expected_type=self.expected_type,
        )

    @property
    def type(self) -> TextFieldRef:
        return TextFieldRef(
            path=[*self.path, "type"],
            expected_type=self.expected_type,
        )

    @property
    def status(self) -> TextFieldRef:
        return TextFieldRef(
            path=[*self.path, "status"],
            expected_type=self.expected_type,
        )

    @property
    def owner(self) -> NumberFieldRef:
        return NumberFieldRef(
            path=[*self.path, "owner"],
            expected_type=self.expected_type,
        )

    @property
    def participants(self) -> FieldRef:
        return FieldRef(
            path=[*self.path, "participants"],
            expected_type=self.expected_type,
        )

    @property
    def title(self) -> TextFieldRef:
        return TextFieldRef(
            path=[*self.path, "title"],
            expected_type=self.expected_type,
        )

    @property
    def base_raw_icon_url(self) -> TextFieldRef:
        return TextFieldRef(
            path=[*self.path, "base_raw_icon_url"],
            expected_type=self.expected_type,
        )

    @property
    def base_icon_url(self) -> TextFieldRef:
        return TextFieldRef(
            path=[*self.path, "base_icon_url"],
            expected_type=self.expected_type,
        )

    @property
    def last_message(self) -> MessageContainer:
        return MessageContainer(
            path=[*self.path, "last_message"],
            expected_type=self.expected_type,
        )

    @property
    def last_event_time(self) -> NumberFieldRef:
        return NumberFieldRef(
            path=[*self.path, "last_event_time"],
            expected_type=self.expected_type,
        )

    @property
    def last_delayed_update_time(self) -> NumberFieldRef:
        return NumberFieldRef(
            path=[*self.path, "last_delayed_update_time"],
            expected_type=self.expected_type,
        )

    @property
    def last_fire_delayed_error_time(self) -> NumberFieldRef:
        return NumberFieldRef(
            path=[*self.path, "last_fire_delayed_error_time"],
            expected_type=self.expected_type,
        )

    @property
    def created(self) -> NumberFieldRef:
        return NumberFieldRef(
            path=[*self.path, "created"],
            expected_type=self.expected_type,
        )

    @property
    def new_messages(self) -> NumberFieldRef:
        return NumberFieldRef(
            path=[*self.path, "new_messages"],
            expected_type=self.expected_type,
        )

    @property
    def link(self) -> TextFieldRef:
        return TextFieldRef(
            path=[*self.path, "link"],
            expected_type=self.expected_type,
        )

    @property
    def access(self) -> TextFieldRef:
        return TextFieldRef(
            path=[*self.path, "access"],
            expected_type=self.expected_type,
        )

    @property
    def restrictions(self) -> NumberFieldRef:
        return NumberFieldRef(
            path=[*self.path, "restrictions"],
            expected_type=self.expected_type,
        )

    @property
    def pinned_message(self) -> MessageContainer:
        return MessageContainer(
            path=[*self.path, "pinned_message"],
            expected_type=self.expected_type,
        )

    @property
    def participants_count(self) -> NumberFieldRef:
        return NumberFieldRef(
            path=[*self.path, "participants_count"],
            expected_type=self.expected_type,
        )

    @property
    def description(self) -> TextFieldRef:
        return TextFieldRef(
            path=[*self.path, "description"],
            expected_type=self.expected_type,
        )

    @property
    def options(self) -> FieldRef:
        return FieldRef(
            path=[*self.path, "options"],
            expected_type=self.expected_type,
        )

    @property
    def join_time(self) -> NumberFieldRef:
        return NumberFieldRef(
            path=[*self.path, "join_time"],
            expected_type=self.expected_type,
        )

    @property
    def invited_by(self) -> NumberFieldRef:
        return NumberFieldRef(
            path=[*self.path, "invited_by"],
            expected_type=self.expected_type,
        )

    @property
    def modified(self) -> NumberFieldRef:
        return NumberFieldRef(
            path=[*self.path, "modified"],
            expected_type=self.expected_type,
        )

    @property
    def messages_count(self) -> NumberFieldRef:
        return NumberFieldRef(
            path=[*self.path, "messages_count"],
            expected_type=self.expected_type,
        )

    @property
    def has_bots(self) -> FieldRef:
        return FieldRef(
            path=[*self.path, "has_bots"],
            expected_type=self.expected_type,
        )

    @property
    def prev_message_id(self) -> NumberFieldRef:
        return NumberFieldRef(
            path=[*self.path, "prev_message_id"],
            expected_type=self.expected_type,
        )

    @property
    def admin_participants(self) -> FieldRef:
        return FieldRef(
            path=[*self.path, "admin_participants"],
            expected_type=self.expected_type,
        )

    @property
    def admins(self) -> FieldRef:
        return FieldRef(
            path=[*self.path, "admins"],
            expected_type=self.expected_type,
        )

    @property
    def cid(self) -> NumberFieldRef:
        return NumberFieldRef(
            path=[*self.path, "cid"],
            expected_type=self.expected_type,
        )

    def __call__(self, event: Any, client: ClientT_contra) -> bool:
        if not isinstance(event, self.expected_type):
            return False

        return bool(self.resolve_path(event))
