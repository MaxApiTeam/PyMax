from typing import Any, Literal

from pydantic import Field, model_validator

from pymax.types.domain.base import CamelModel

from .enums import AttachmentType


class VideoAttachment(CamelModel):
    """Видео-вложение сообщения.

    Используйте этот тип для входящих видео в ``Message.attaches``. Временный
    URL для просмотра можно получить через ``client.get_video_by_id``.

    Example:
        .. code-block:: python

           for attach in message.attaches:
               if isinstance(attach, VideoAttachment):
                   video = await client.get_video_by_id(
                       message.chat_id,
                       message.id,
                       attach.video_id,
                   )

    :ivar height: Высота видео.
    :vartype height: int
    :ivar width: Ширина видео.
    :vartype width: int
    :ivar video_id: ID видео.
    :vartype video_id: int
    :ivar duration: Длительность видео.
    :vartype duration: int | None
    :ivar preview_data: Данные превью, если Max их прислал.
    :vartype preview_data: bytes | None
    :ivar type: Тип вложения.
    :vartype type: Literal[AttachmentType.VIDEO]
    :ivar thumbnail: URL миниатюры.
    :vartype thumbnail: str
    :ivar token: Токен видео.
    :vartype token: str
    :ivar video_type: Код типа видео в Max.
    :vartype video_type: int
    """

    height: int
    width: int
    video_id: int
    duration: int | None = None
    preview_data: bytes | None = None
    type: Literal[AttachmentType.VIDEO] = Field(alias="_type")
    thumbnail: str
    token: str
    video_type: int


class VideoRequest(CamelModel):
    """Данные для просмотра видео-вложения.

    :ivar external: Признак или URL внешнего источника видео.
    :vartype external: str | bool | None
    :ivar cache: Использовать ли кеш.
    :vartype cache: bool
    :ivar url: Прямой URL видео или ``None`` для внешнего видео.
    :vartype url: str | None
    """

    external: str | bool | None = Field(default=None, alias="EXTERNAL")
    cache: bool = False  # TODO: idk maybe | None = None better
    url: str | None = None

    @model_validator(mode="before")
    @classmethod
    def select_video_url(cls, value: Any) -> Any:
        """Выбирает прямой URL с максимальным доступным MP4-качеством.

        :param value: Значение, переданное в валидатор модели.
        :type value: Any
        :returns: Данные запроса видео или исходное значение.
        :rtype: Any
        """
        if not isinstance(value, dict) or "url" in value:
            return value

        mp4_urls: list[tuple[int, str]] = []
        for key, url in value.items():
            if not isinstance(key, str) or not isinstance(url, str):
                continue

            normalized_key = key.upper()
            if not normalized_key.startswith("MP4_"):
                continue

            try:
                quality = int(normalized_key.removeprefix("MP4_"))
            except ValueError:
                continue

            if quality > 0:
                mp4_urls.append((quality, url))

        if mp4_urls:
            _, url = max(mp4_urls, key=lambda item: item[0])
            return {**value, "url": url}

        legacy_url = value.get("dynamicUrl", value.get("dynamic_url"))
        if isinstance(legacy_url, str):
            return {**value, "url": legacy_url}

        return value
