from typing import Annotated, Literal, TypeAlias

from pydantic import Field

from .attachments.enums import AttachmentType
from .base import CamelModel


class StoryCoordinates(CamelModel):
    """Положение слоя сторис в долях ширины и высоты кадра."""

    x: float
    y: float
    w: float
    h: float
    rotation: float = 0


class StoryClickableLink(CamelModel):
    """Ссылка слоя сторис и результат ее проверки сервером."""

    url: str
    check_result: int | None = None


class StoryLayer(CamelModel):
    """Слой сторис со ссылкой и координатами."""

    type: int = 0
    coordinates: StoryCoordinates
    clickable_link: StoryClickableLink


class StoryPhotoMedia(CamelModel):
    """Фото сторис, полученное от Max, без обязательного токена загрузки."""

    base_url: str
    height: int
    width: int
    photo_id: int
    preview_data: bytes | None = None
    type: Literal[AttachmentType.PHOTO] = Field(alias="_type")


class StoryVideoMedia(CamelModel):
    """Видео сторис, полученное от Max.

    В отличие от ``VideoAttachment``, не требует токен загрузки и
    ``video_type``, которые используются при публикации.
    """

    height: int
    width: int
    video_id: int
    duration: int | None = None
    preview_data: bytes | None = None
    type: Literal[AttachmentType.VIDEO] = Field(alias="_type")
    thumbnail: str


StoryMedia: TypeAlias = Annotated[
    StoryPhotoMedia | StoryVideoMedia,
    Field(discriminator="type"),
]


class Story(CamelModel):
    """Сторис, возвращенная после публикации или при чтении.

    :ivar id: ID сторис.
    :ivar cid: Идентификатор публикации, сформированный клиентом.
    :ivar media: Фото или видео сторис.
    :ivar layers: Слои поверх кадра.
    :ivar settings: Настройки сторис в формате Max.
    :ivar expiration: Время жизни сторис в миллисекундах.
    """

    id: int
    cid: int | None = None
    media: StoryMedia
    layers: list[StoryLayer] = Field(default_factory=list)
    settings: int
    expiration: int


class StoryOwner(CamelModel):
    """Владелец сторис.

    :ivar owner_id: ID владельца, а не отдельной сторис.
    :ivar type: Числовой тип владельца из Max. ``0`` — пользователь.
    """

    owner_id: int
    type: int = 0


class StoryPreview(CamelModel):
    """Сводная информация о сторис владельца в ленте и обновлениях.

    ID отдельных сторис в превью нет. Для их получения передайте
    ``owner.owner_id`` и ``owner.type`` в ``client.get_stories()``.

    :ivar owner: Владелец сторис.
    :ivar total_count: Общее количество сторис владельца.
    :ivar read_count: Количество просмотренных сторис владельца.
    """

    owner: StoryOwner
    total_count: int = 0
    read_count: int = 0
    last_story_expiration_time: int = 0
    settings: int = 0
    update_time: int = 0


class StoryDetailedStats(CamelModel):
    """Запись подробной статистики просмотра или реакции на сторис.

    Типизировано только ``user_id``. Дополнительные поля доступны в
    ``model_extra`` с исходными именами ответа Max, без преобразования
    camelCase. Поле ``reaction``, если оно пришло, остается словарем.

    :ivar user_id: ID пользователя.
    """

    user_id: int
