from enum import Enum


class EventType(str, Enum):
    MESSAGE_NEW = "message_new"
    MESSAGE_EDIT = "message_edit"
    MESSAGE_DELETE = "message_delete"
    MESSAGE_READ = "message_read"
    TYPING = "typing"
    PRESENCE = "presence"
    REACTION_UPDATE = "reaction_update"
    CHAT_UPDATE = "chat_update"
    USER_UPDATE = "user_update"
    VIDEO_READY = "video_ready"
    FILE_READY = "file_ready"
    VOICE_READY = "voice_ready"
    RAW = "raw"
    ON_START = "on_start"
