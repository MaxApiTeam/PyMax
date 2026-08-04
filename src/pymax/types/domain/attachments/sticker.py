from typing import Literal

from pydantic import Field

from pymax.types.domain.base import CamelModel

from .enums import AttachmentType


class StickerAttachment(CamelModel):
    """Стикер-вложение сообщения.

    :ivar author_type: Тип автора стикера, если Max его прислал.
    :vartype author_type: str | None
    :ivar lottie_url: URL Lottie-анимации.
    :vartype lottie_url: str | None
    :ivar url: URL стикера.
    :vartype url: str
    :ivar sticker_id: ID стикера.
    :vartype sticker_id: int
    :ivar tags: Теги стикера.
    :vartype tags: list[str] | None
    :ivar width: Ширина стикера.
    :vartype width: int
    :ivar set_id: ID набора стикеров.
    :vartype set_id: int
    :ivar time: Время или версия стикера в данных Max.
    :vartype time: int
    :ivar sticker_type: Тип стикера.
    :vartype sticker_type: str
    :ivar audio: Есть ли аудио.
    :vartype audio: bool
    :ivar height: Высота стикера.
    :vartype height: int
    :ivar type: Тип вложения.
    :vartype type: Literal[AttachmentType.STICKER]
    """

    author_type: str | None = None
    lottie_url: str | None = None
    url: str
    sticker_id: int
    tags: list[str] | None = None
    width: int
    set_id: int | None = None
    time: int
    sticker_type: str
    audio: bool
    height: int
    type: Literal[AttachmentType.STICKER] = Field(alias="_type")
