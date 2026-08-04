from typing import Any, Literal

from pydantic import Field

from pymax.api.models import CamelModel
from pymax.api.uploads.payloads import (
    AttachFilePayload,
    AttachPhotoPayload,
    VideoAttachPayload,
)
from pymax.types.domain import Poll

from .enums import ItemType, ReadAction


class GetMessagesPayload(CamelModel):
    chat_id: int
    message_ids: list[int]


class EditMessagePayload(CamelModel):
    chat_id: int
    message_id: int
    text: str | None = None
    elements: list[Any]
    attachments: list[AttachPhotoPayload | VideoAttachPayload | AttachFilePayload | Poll] = Field(
        default_factory=list
    )


class ReplyLink(CamelModel):
    type: str = "REPLY"  # TODO: enum?
    message_id: int


class SendMessagePayloadMessage(CamelModel):
    text: str | None = None
    cid: int
    elements: list[Any]
    attaches: list[AttachPhotoPayload | VideoAttachPayload | AttachFilePayload | Poll]
    link: ReplyLink | None = None


class SendMessagePayload(CamelModel):
    chat_id: int
    message: SendMessagePayloadMessage
    notify: bool = False


class ForwardLink(CamelModel):
    type: Literal["FORWARD"] = "FORWARD"
    message_id: str
    chat_id: int


class ForwardMessagePayloadMessage(CamelModel):
    cid: int
    link: ForwardLink
    attaches: list[AttachPhotoPayload | VideoAttachPayload | AttachFilePayload] = Field(
        default_factory=list
    )


class ForwardMessagePayload(CamelModel):
    chat_id: int
    message: ForwardMessagePayloadMessage
    notify: bool = True


class ChatHistoryPayload(CamelModel):
    chat_id: int
    forward: int
    backward: int = 40
    backward_time: int = 0
    forward_time: int = 0
    get_chat: bool = False
    from_: int = Field(serialization_alias="from")
    item_type: ItemType = ItemType.REGULAR
    get_messages: bool = True
    interactive: bool = False


class DeleteMessagePayload(CamelModel):
    chat_id: int
    message_ids: list[int]
    for_me: bool = False


class PinMessagePayload(CamelModel):
    chat_id: int
    notify_pin: bool
    pin_message_id: int


class GetVideoPayload(CamelModel):
    chat_id: int
    message_id: int | str
    video_id: int


class GetFilePayload(CamelModel):
    chat_id: int
    message_id: int | str
    file_id: int


class ReactionInfoPayload(CamelModel):
    reaction_type: str = "EMOJI"
    id: str


class AddReactionPayload(CamelModel):
    chat_id: int
    message_id: str
    reaction: ReactionInfoPayload


class GetReactionsPayload(CamelModel):
    chat_id: int
    message_ids: list[str]


class RemoveReactionPayload(CamelModel):
    chat_id: int
    message_id: str


class ReadMessagesPayload(CamelModel):
    type: ReadAction
    chat_id: int
    message_id: str | int  # Сокет просит int а вс str
    mark: int


class VotePollPayload(CamelModel):
    chat_id: int
    message_id: int
    poll_id: int
    answers_ids: list[int]
