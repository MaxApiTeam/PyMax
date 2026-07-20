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


class ChannelPermissions(int, Enum):
    ADD_REMOVE_MEMBER = 2
    ADD_ADMIN = 4
    CHANGE_CHAT_INFO = 8
    PIN_MESSAGE = 16
    POST_MESSAGE = 256
    EDIT_MESSAGE = 512
    DELETE_MESSAGE = 1024


class PermType(str, Enum):
    ADMIN = "ADMIN"
