from typing import Annotated, Any, Literal, TypeAlias

from pydantic import Field

from pymax.types.domain.attachments import AttachmentType
from pymax.types.domain.base import CamelModel

from .enums import ButtonType


class BaseButton(CamelModel):
    text: str


class CallbackButton(BaseButton):
    type: Literal[ButtonType.CALLBACK] = ButtonType.CALLBACK
    text: str
    payload: str
    intent: str


class LinkButton(BaseButton):
    type: Literal[ButtonType.LINK] = ButtonType.LINK
    url: str


class ChatButton(BaseButton):
    type: Literal[ButtonType.CHAT] = ButtonType.CHAT
    payload: str


class GeoLocationButton(BaseButton):
    type: Literal[ButtonType.REQUEST_GEO_LOCATION] = ButtonType.REQUEST_GEO_LOCATION
    quick: bool | None = None


class RequestContactButton(BaseButton):
    type: Literal[ButtonType.REQUEST_CONTACT] = ButtonType.REQUEST_CONTACT


class OpenAppButton(BaseButton):
    type: Literal[ButtonType.OPEN_APP] = ButtonType.OPEN_APP
    contact_id: int | None = None
    payload: str | None = None
    web_app: str | None = None


class MessageButton(BaseButton):
    type: Literal[ButtonType.MESSAGE] = ButtonType.MESSAGE


class ClipboardButton(BaseButton):
    type: Literal[ButtonType.CLIPBOARD] = ButtonType.CLIPBOARD
    payload: str


Button: TypeAlias = Annotated[
    CallbackButton
    | ChatButton
    | LinkButton
    | RequestContactButton
    | GeoLocationButton
    | OpenAppButton
    | MessageButton
    | ClipboardButton,
    Field(discriminator="type"),
]


class InlineKeyboard(CamelModel):
    buttons: list[Button]


class InlineKeyboardAttachment(CamelModel):
    """Вложение inline-клавиатуры.

    :ivar type: Тип вложения.
    :vartype type: Literal[AttachmentType.INLINE_KEYBOARD]
    :ivar keyboard: Данные inline-клавиатуры.
    :vartype keyboard: dict[str, Any]
    """

    type: Literal[AttachmentType.INLINE_KEYBOARD] = Field(alias="_type")
    keyboard: InlineKeyboard
    callback_id: str
