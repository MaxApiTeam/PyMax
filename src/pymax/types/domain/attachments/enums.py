from enum import Enum, IntFlag


class AttachmentType(str, Enum):
    """Тип вложения сообщения."""

    PHOTO = "PHOTO"
    VIDEO = "VIDEO"
    FILE = "FILE"
    STICKER = "STICKER"
    AUDIO = "AUDIO"
    CONTROL = "CONTROL"
    CONTACT = "CONTACT"
    CALL = "CALL"
    SHARE = "SHARE"
    INLINE_KEYBOARD = "INLINE_KEYBOARD"
    POLL = "POLL"
    UNKNOWN = "UNKNOWN"


class TranscriptionStatus(str, Enum):
    """Статус транскрибации аудио."""

    FAILED = "FAILED"
    MEDIA_NOT_READY = "MEDIA_NOT_READY"
    NOT_SUPPORTED = "NOT_SUPPORTED"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    UNKNOWN = "UNKNOWN"


class PollFlags(IntFlag):
    """Настройки опроса, представленные битовой маской.

    Несколько настроек объединяются оператором ``|``. Числовые значения,
    полученные от Max, автоматически преобразуются в ``PollFlags``.
    """

    FLAG_SETTINGS_ANONYMOUS = 1
    FLAG_SETTINGS_MULTISELECT = 2
    FLAG_SETTINGS_REVOTE = 4
    FLAG_SETTINGS_CLOSED = 8
    FLAG_SETTINGS_QUIZ = 16
    FLAG_SETTINGS_CAN_FORWARD = 32


class CallType(str, Enum):
    """Тип звонка во входящем ``CallAttachment``."""

    AUDIO = "AUDIO"
    VIDEO = "VIDEO"


class HangupType(str, Enum):
    """Причина завершения звонка во входящем ``CallAttachment``."""

    MISSED = "MISSED"
    REJECTED = "REJECTED"
    CANCELED = "CANCELED"
    HUNGUP = "HUNGUP"
