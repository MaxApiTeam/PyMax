from enum import Enum


class ItemType(str, Enum):
    REGULAR = "REGULAR"
    DELAYED = "DELAYED"


class ReadAction(str, Enum):
    READ_MESSAGE = "READ_MESSAGE"
    READ_REACTION = "READ_REACTION"


class MessagePayloadKey(str, Enum):
    MESSAGE = "message"
    MESSAGES = "messages"
    REACTION_INFO = "reactionInfo"
    MESSAGES_REACTIONS = "messagesReactions"
    COMMENTS_INFO_UPDATES = "commentsInfoUpdates"
