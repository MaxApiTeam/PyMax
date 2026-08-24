from enum import Enum


class ChatType(str, Enum):
    """Тип чата."""

    DIALOG = "DIALOG"
    CHAT = "CHAT"
    CHANNEL = "CHANNEL"


class AccessType(str, Enum):
    """Тип доступа к чату."""

    PUBLIC = "PUBLIC"
    PRIVATE = "PRIVATE"
    SECRET = "SECRET"


class MessageStatus(str, Enum):
    """Статус сообщения."""

    EDITED = "EDITED"
    REMOVED = "REMOVED"


class LinkType(str, Enum):
    """Тип связи входящего сообщения с исходным сообщением."""

    REPLY = "REPLY"
    FORWARD = "FORWARD"
