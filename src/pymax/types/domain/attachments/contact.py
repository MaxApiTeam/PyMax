from typing import Literal

from pydantic import Field

from pymax.types.domain.base import CamelModel

from .enums import AttachmentType


class ContactAttachment(CamelModel):
    """Контактное вложение сообщения.

    :ivar contact_id: ID контакта, если Max его прислал.
    :vartype contact_id: int | None
    :ivar first_name: Имя контакта.
    :vartype first_name: str | None
    :ivar last_name: Фамилия контакта.
    :vartype last_name: str | None
    :ivar name: Отображаемое имя контакта.
    :vartype name: str | None
    :ivar photo_url: URL фотографии контакта.
    :vartype photo_url: str | None
    :ivar type: Тип вложения.
    :vartype type: Literal[AttachmentType.CONTACT]
    """

    contact_id: int | None = None
    first_name: str | None = None
    last_name: str | None = None
    name: str | None = None
    photo_url: str | None = None
    type: Literal[AttachmentType.CONTACT] = Field(alias="_type")
