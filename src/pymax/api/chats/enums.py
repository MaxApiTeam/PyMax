from enum import Enum


class ControlEvent(str, Enum):
    NEW = "new"


class ChatMemberOperation(str, Enum):
    ADD = "add"
    REMOVE = "remove"


class ChatOption(str, Enum):
    ONLY_OWNER_CAN_CHANGE_ICON_TITLE = "ONLY_OWNER_CAN_CHANGE_ICON_TITLE"
    ALL_CAN_PIN_MESSAGE = "ALL_CAN_PIN_MESSAGE"
    ONLY_ADMIN_CAN_ADD_MEMBER = "ONLY_ADMIN_CAN_ADD_MEMBER"
    ONLY_ADMIN_CAN_CALL = "ONLY_ADMIN_CAN_CALL"
    MEMBERS_CAN_SEE_PRIVATE_LINK = "MEMBERS_CAN_SEE_PRIVATE_LINK"


class ChatPayloadKey(str, Enum):
    CHAT = "chat"
    CHATS = "chats"
    MEMBERS = "members"
    MARKER = "marker"


class ChatLinkPrefix(str, Enum):
    JOIN = "join/"
