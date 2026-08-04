from pydantic import ValidationError

from pymax.logging import get_logger
from pymax.protocol import InboundFrame
from pymax.protocol.enums import Opcode
from pymax.types import AudioUploadSignal, Message
from pymax.types.domain.enums import MessageStatus
from pymax.types.events import FileUploadSignal, VideoUploadSignal

from .enums import EventType

logger = get_logger(__name__)


def resolve_chat(_: InboundFrame) -> EventType | None:
    return EventType.CHAT_UPDATE


def resolve_message_delete(_: InboundFrame) -> EventType | None:
    return EventType.MESSAGE_DELETE


def resolve_message_read(_: InboundFrame) -> EventType | None:
    return EventType.MESSAGE_READ


def resolve_typing(_: InboundFrame) -> EventType | None:
    return EventType.TYPING


def resolve_presence(_: InboundFrame) -> EventType | None:
    return EventType.PRESENCE


def resolve_reaction_update(_: InboundFrame) -> EventType | None:
    return EventType.REACTION_UPDATE


def resolve_attach(frame: InboundFrame) -> EventType | None:
    try:
        FileUploadSignal.model_validate(frame.payload)
        return EventType.FILE_READY
    except ValidationError:
        logger.debug("attach event is not a file upload signal")

    try:
        VideoUploadSignal.model_validate(frame.payload)
        return EventType.VIDEO_READY
    except ValidationError:
        logger.debug("attach event is not a video upload signal")

    try:
        AudioUploadSignal.model_validate(frame.payload)
        return EventType.VOICE_READY
    except ValidationError:
        logger.debug("attach event is not a voice upload signal")

    return None


def resolve_message(frame: InboundFrame) -> EventType | None:
    if frame.opcode not in (Opcode.NOTIF_MESSAGE, Opcode.MSG_EDIT):
        return None

    try:
        model = Message.model_validate(frame.payload)

        if model.status == MessageStatus.EDITED:
            return EventType.MESSAGE_EDIT
        if model.status == MessageStatus.REMOVED:
            return EventType.MESSAGE_DELETE
        else:
            return EventType.MESSAGE_NEW
    except ValidationError:
        logger.debug("failed to resolve message event", exc_info=True)
        return None
