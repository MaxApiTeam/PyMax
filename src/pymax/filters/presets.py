from __future__ import annotations

from typing import TYPE_CHECKING

from pymax.types import LinkType, Message

from .base import Filter

if TYPE_CHECKING:
    from pymax.base import BaseClient
    from pymax.types.domain.message import Attachment


class Command(Filter[Message, "BaseClient"]):
    def __init__(self, command: str, prefix: str | tuple[str, ...] = "/") -> None:
        self.prefixes = (prefix,) if isinstance(prefix, str) else prefix

        for prefix_ in self.prefixes:
            self.command = command.removeprefix(prefix_)

    def __call__(self, message: Message, _: BaseClient) -> bool:
        if not message.text:
            return False

        for prefix in self.prefixes:
            dirty_command = message.text.split(maxsplit=1)[0]

            if message.text.startswith(prefix) and dirty_command[len(prefix) :] == self.command:
                return True

        return False


class Reply(Filter[Message, "BaseClient"]):
    def __call__(self, message: Message, _: BaseClient) -> bool:
        if not message.link:
            return False

        return message.link.type == LinkType.REPLY


class Forwarded(Filter[Message, "BaseClient"]):
    def __call__(self, message: Message, _: BaseClient) -> bool:
        if not message.link:
            return False

        return message.link.type == LinkType.FORWARD


class FromMe(Filter[Message, "BaseClient"]):
    def __call__(self, message: Message, client: BaseClient) -> bool:
        if not message.sender or not client.me:
            return False

        return message.sender == client.me.contact.id


class HasAttachment(Filter[Message, "BaseClient"]):
    def __init__(self, *attachment_types: type[Attachment]) -> None:
        self.expected_types = attachment_types

    def __call__(self, message: Message, _: BaseClient) -> bool:
        return any(isinstance(attach, self.expected_types) for attach in message.attaches)
