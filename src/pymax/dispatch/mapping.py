from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from pymax.api.binding import bind_api_model
from pymax.protocol import InboundFrame, Opcode
from pymax.protocol.enums import Command
from pymax.types import AudioUploadSignal, Chat, MessageDeleteEvent
from pymax.types.domain import Message
from pymax.types.events import (
    FileUploadSignal,
    MessageReadEvent,
    PresenceEvent,
    ReactionUpdateEvent,
    TypingEvent,
    VideoUploadSignal,
)

from .enums import EventType
from .resolvers import (
    resolve_attach,
    resolve_chat,
    resolve_message,
    resolve_message_delete,
    resolve_message_read,
    resolve_presence,
    resolve_reaction_update,
    resolve_typing,
)

if TYPE_CHECKING:
    from pymax.app import App

Resolver = Callable[[InboundFrame], EventType | None]

EVENT_MAP: dict[Opcode, Resolver] = {
    Opcode.NOTIF_MESSAGE: resolve_message,
    Opcode.MSG_EDIT: resolve_message,
    Opcode.NOTIF_CHAT: resolve_chat,
    Opcode.NOTIF_MSG_DELETE: resolve_message_delete,
    Opcode.NOTIF_ATTACH: resolve_attach,
    Opcode.NOTIF_TYPING: resolve_typing,
    Opcode.NOTIF_MARK: resolve_message_read,
    Opcode.NOTIF_PRESENCE: resolve_presence,
    Opcode.NOTIF_MSG_REACTIONS_CHANGED: resolve_reaction_update,
}


class EventResolver:
    def resolve(self, frame: InboundFrame) -> EventType | None:
        if frame.cmd != Command.REQUEST:
            return None

        try:
            opcode = Opcode(frame.opcode)
        except ValueError:
            return None

        handler = EVENT_MAP.get(opcode)

        if handler:
            return handler(frame)
        return None


class EventMapper:
    def __init__(self, app: App) -> None:
        self.app = app

    def map(self, event_type: EventType, frame: InboundFrame):
        if frame.cmd != Command.REQUEST:
            return None

        if frame.payload:
            if event_type in (EventType.MESSAGE_NEW, EventType.MESSAGE_EDIT):
                return bind_api_model(
                    self.app,
                    Message.model_validate(frame.payload),
                )
            elif event_type == EventType.CHAT_UPDATE:
                return bind_api_model(
                    self.app,
                    Chat.model_validate(frame.payload["chat"]),
                )
            elif event_type == EventType.MESSAGE_DELETE:
                return bind_api_model(
                    self.app,
                    MessageDeleteEvent.model_validate(frame.payload),
                )
            elif event_type == EventType.MESSAGE_READ:
                return MessageReadEvent.model_validate(frame.payload)
            elif event_type == EventType.TYPING:
                return TypingEvent.model_validate(frame.payload)
            elif event_type == EventType.PRESENCE:
                return PresenceEvent.model_validate(frame.payload)
            elif event_type == EventType.REACTION_UPDATE:
                return ReactionUpdateEvent.model_validate(frame.payload)
            elif event_type == EventType.VIDEO_READY:
                return VideoUploadSignal.model_validate(frame.payload)
            elif event_type == EventType.FILE_READY:
                return FileUploadSignal.model_validate(frame.payload)
            elif event_type == EventType.VOICE_READY:
                return AudioUploadSignal.model_validate(frame.payload)
        return frame
