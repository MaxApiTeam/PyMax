from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Annotated, Any, TypeAlias

from pydantic import Field, PrivateAttr, model_validator

from pymax.files import File, Photo, Video, VideoNote, Voice
from pymax.types.domain import (
    AudioAttachment,
    CallAttachment,
    ContactAttachment,
    ControlAttachment,
    FileAttachment,
    InlineKeyboardAttachment,
    PhotoAttachment,
    Poll,
    PollAttachment,
    ShareAttachment,
    StickerAttachment,
    UnknownAttachment,
    VideoAttachment,
)

from .base import CamelModel
from .element import Element
from .enums import MessageStatus

if TYPE_CHECKING:
    from pymax.api.messages.service import MessageService


KnownAttachment: TypeAlias = Annotated[
    PhotoAttachment
    | VideoAttachment
    | FileAttachment
    | ContactAttachment
    | StickerAttachment
    | AudioAttachment
    | ControlAttachment
    | InlineKeyboardAttachment
    | ShareAttachment
    | CallAttachment
    | PollAttachment,
    Field(discriminator="type"),
]
Attachment: TypeAlias = KnownAttachment | UnknownAttachment
SendAttachment: TypeAlias = Photo | File | Video | Poll | Voice | VideoNote
SendAttachments: TypeAlias = Sequence[SendAttachment] | None


class ReactionCounter(CamelModel):
    """Счетчик одной реакции на сообщение.

    :ivar count: Количество таких реакций.
    :vartype count: int
    :ivar reaction: ID emoji-реакции.
    :vartype reaction: str
    """

    count: int
    reaction: str


class ReactionInfo(CamelModel):
    """Сводная информация о реакциях на сообщение.

    :ivar total_count: Общее количество реакций.
    :vartype total_count: int
    :ivar counters: Счетчики по каждому типу реакции.
    :vartype counters: list[ReactionCounter]
    :ivar your_reaction: Реакция текущего пользователя, если она есть.
    :vartype your_reaction: str | None
    """

    total_count: int = 0
    counters: list[ReactionCounter] = Field(default_factory=list)
    your_reaction: str | None = None


class ReadState(CamelModel):
    """Состояние прочтения после отметки сообщения прочитанным.

    :ivar unread: Количество непрочитанных сообщений.
    :vartype unread: int
    :ivar mark: Текущая отметка прочтения.
    :vartype mark: int
    """

    unread: int
    mark: int


class Message(CamelModel):
    """Сообщение Max с методами для действий над ним.

    Сообщения, полученные через клиент, обычно уже привязаны к сервису
    сообщений. После этого можно вызывать удобные методы объекта:
    :meth:`reply`, :meth:`answer`, :meth:`forward`, :meth:`edit`, :meth:`pin`,
    :meth:`delete`, :meth:`read`, :meth:`react`, :meth:`unreact` и
    :meth:`get_reactions`.

    Используйте ``Message`` в обработчиках ``on_message`` и при работе с
    историей. Некоторые поля могут быть ``None``, потому что Max присылает
    разные payload-ы для разных событий.

    Example:
        .. code-block:: python

           from pymax import Client

           @client.on_message()
           async def on_message(message: Message, client: Client) -> None:
               if message.chat_id is None:
                   return

               await message.answer("Получил сообщение")

    :ivar id: ID сообщения.
    :vartype id: int
    :ivar chat_id: ID чата, если он есть в данных сообщения.
    :vartype chat_id: int | None
    :ivar sender: ID отправителя.
    :vartype sender: int | None
    :ivar text: Текст сообщения.
    :vartype text: str
    :ivar time: Время сообщения в формате Unix time.
    :vartype time: int
    :ivar type: Тип сообщения.
    :vartype type: str
    :ivar cid: Клиентский ID сообщения, если он есть в payload-е.
    :vartype cid: int | None
    :ivar attaches: Вложения сообщения.
    :vartype attaches: list[Attachment]
    :ivar stats: Дополнительная статистика сообщения от Max.
    :vartype stats: dict[str, Any] | None
    :ivar status: Статус доставки сообщения.
    :vartype status: MessageStatus | None
    :ivar reaction_info: Информация о реакциях на сообщение.
    :vartype reaction_info: ReactionInfo | None
    :ivar options: Дополнительные параметры сообщения от Max.
    :vartype options: int | dict[str, Any] | None
    :ivar prev_message_id: ID предыдущего сообщения.
    :vartype prev_message_id: int | str | None
    :ivar ttl: Признак сообщения с ограниченным временем жизни.
    :vartype ttl: bool | None
    :ivar unread: Количество непрочитанных сообщений.
    :vartype unread: int | None
    :ivar mark: Текущая отметка прочтения.
    :vartype mark: int | None
    :ivar elements: Форматированные элементы текста сообщения.
    :vartype elements: list[Element]
    """

    id: int
    chat_id: int | None = None
    sender: int | None = None
    text: str = ""
    time: int
    type: str
    cid: int | None = None
    attaches: list[Attachment] = Field(default_factory=list)
    stats: dict[str, Any] | None = None
    status: MessageStatus | None = None
    reaction_info: ReactionInfo | None = None
    options: int | dict[str, Any] | None = None
    prev_message_id: int | str | None = None
    ttl: bool | None = None
    unread: int | None = None
    mark: int | None = None
    elements: list[Element] = Field(default_factory=list)

    _actions: MessageService | None = PrivateAttr(default=None)

    def bind(self, actions: MessageService) -> Message:
        """Привязывает сервис сообщений к объекту сообщения.

        :param actions: Сервис сообщений для выполнения действий с сообщением.
        :type actions: MessageService
        :returns: Это же сообщение с привязанным сервисом.
        :rtype: Message
        """
        self._actions = actions
        return self

    async def reply(
        self,
        text: str | None = None,
        attachments: SendAttachments = None,
        *,
        notify: bool = True,
    ) -> Message:
        """Отправляет ответ на это сообщение в тот же чат.

        :param text: Текст сообщения.
        :type text: str | None
        :param attachments: Файлы, фотографии или видео для отправки.
        :type attachments: SendAttachments
        :param notify: Отправить ли получателям push-уведомление.
        :type notify: bool
        :returns: Отправленное сообщение.
        :rtype: Message
        :raises RuntimeError: Если сообщение не привязано к сервису или не
            содержит ``chat_id``.
        """
        actions, chat_id = self._bound()

        return await actions.send_message(
            chat_id=chat_id,
            text=text,
            reply_to=self.id,
            attachments=attachments,
            notify=notify,
        )

    async def answer(
        self,
        text: str | None = None,
        reply_to: int | None = None,
        attachments: SendAttachments = None,
        *,
        notify: bool = True,
    ) -> Message:
        """Отправляет сообщение в тот же чат.

        :param text: Текст сообщения.
        :type text: str | None
        :param reply_to: ID сообщения для ответа.
        :type reply_to: int | None
        :param attachments: Файлы, фотографии или видео для отправки.
        :type attachments: SendAttachments
        :param notify: Отправить ли получателям push-уведомление.
        :type notify: bool
        :returns: Отправленное сообщение.
        :rtype: Message
        :raises RuntimeError: Если сообщение не привязано к сервису или не
            содержит ``chat_id``.
        """
        actions, chat_id = self._bound()

        return await actions.send_message(
            chat_id=chat_id,
            text=text,
            reply_to=reply_to,
            attachments=attachments,
            notify=notify,
        )

    async def forward(
        self,
        chat_id: int,
        *,
        notify: bool = True,
    ) -> Message:
        """Пересылает это сообщение в другой чат.

        :param chat_id: ID целевого чата.
        :type chat_id: int
        :param notify: Отправить ли получателям push-уведомление.
        :type notify: bool
        :returns: Пересланное сообщение.
        :rtype: Message
        :raises RuntimeError: Если сообщение не привязано к сервису или не
            содержит ``chat_id``.
        """
        actions, source_chat_id = self._bound()

        return await actions.forward_message(
            chat_id=chat_id,
            message_id=self.id,
            source_chat_id=source_chat_id,
            notify=notify,
        )

    async def pin(self, notify_pin: bool = True) -> bool:
        """Закрепляет это сообщение в чате.

        :param notify_pin: Отправить ли уведомление о закреплении.
        :type notify_pin: bool
        :returns: ``True``, если сервер принял запрос.
        :rtype: bool
        :raises RuntimeError: Если сообщение не привязано к сервису или не
            содержит ``chat_id``.
        """
        actions, chat_id = self._bound()

        return await actions.pin_message(
            chat_id=chat_id,
            message_id=self.id,
            notify_pin=notify_pin,
        )

    async def edit(
        self,
        text: str | None = None,
        attachments: SendAttachments = None,
    ) -> Message:
        """Редактирует текст и вложения этого сообщения.

        :param text: Новый текст сообщения с поддержкой markdown.
        :type text: str | None
        :param attachments: Новые файлы, фотографии или видео для сообщения.
        :type attachments: SendAttachments
        :returns: Отредактированное сообщение.
        :rtype: Message
        :raises RuntimeError: Если сообщение не привязано к сервису или не
            содержит ``chat_id``.
        """
        actions, chat_id = self._bound()

        return await actions.edit_message(
            chat_id=chat_id,
            message_id=self.id,
            text=text,
            attachments=attachments,
        )

    async def delete(self, for_me: bool = False) -> bool:
        """Удаляет это сообщение.

        :param for_me: Удалить сообщение только для текущего аккаунта.
        :type for_me: bool
        :returns: ``True``, если сервер принял запрос.
        :rtype: bool
        :raises RuntimeError: Если сообщение не привязано к сервису или не
            содержит ``chat_id``.
        """
        actions, chat_id = self._bound()

        return await actions.delete_message(
            chat_id=chat_id,
            message_ids=[self.id],
            for_me=for_me,
        )

    async def read(self) -> ReadState:
        """Отмечает это сообщение как прочитанное.

        :returns: Состояние прочтения.
        :rtype: ReadState
        :raises RuntimeError: Если сообщение не привязано к сервису или не
            содержит ``chat_id``.
        """
        actions, chat_id = self._bound()

        return await actions.read_message(
            message_id=self.id,
            chat_id=chat_id,
        )

    async def react(self, reaction: str) -> ReactionInfo | None:
        """Добавляет или заменяет свою реакцию на этом сообщении.

        :param reaction: ID emoji-реакции, поддержанный сервером.
        :type reaction: str
        :returns: Обновленные реакции или ``None``, если сервер их не вернул.
        :rtype: ReactionInfo | None
        :raises RuntimeError: Если сообщение не привязано к сервису или не
            содержит ``chat_id``.
        """
        actions, chat_id = self._bound()

        return await actions.add_reaction(
            chat_id=chat_id,
            message_id=str(self.id),  # :C
            reaction=reaction,
        )

    async def unreact(self) -> ReactionInfo | None:
        """Удаляет свою реакцию с этого сообщения.

        :returns: Обновленные реакции или ``None``, если сервер их не вернул.
        :rtype: ReactionInfo | None
        :raises RuntimeError: Если сообщение не привязано к сервису или не
            содержит ``chat_id``.
        """
        actions, chat_id = self._bound()

        return await actions.remove_reaction(
            chat_id=chat_id,
            message_id=str(self.id),  # :C x2
        )

    async def get_reactions(self) -> dict[str, ReactionInfo] | None:
        """Возвращает реакции для этого сообщения.

        :returns: ``{message_id: ReactionInfo}`` или ``None``, если реакций
            нет в ответе сервера.
        :rtype: dict[str, ReactionInfo] | None
        :raises RuntimeError: Если сообщение не привязано к сервису или не
            содержит ``chat_id``.
        """
        actions, chat_id = self._bound()

        return await actions.get_reactions(
            chat_id=chat_id,
            message_ids=[str(self.id)],  # :C x3
        )

    def _bound(self) -> tuple[MessageService, int]:
        if self._actions is None:
            raise RuntimeError("Message is not bound to a client.")

        if self.chat_id is None:
            raise RuntimeError("Message does not contain chat_id.")

        return self._actions, self.chat_id

    @model_validator(mode="before")
    @classmethod
    def _unwrap_message_event(cls, value: Any) -> Any:
        """Преобразует данные события сообщения в данные сообщения.

        :param value: Значение, переданное в валидатор модели.
        :type value: Any
        :returns: Данные сообщения или исходное значение, если преобразование
            не требуется.
        :rtype: Any
        """
        if not isinstance(value, dict):
            return value

        message = value.get("message")
        if not isinstance(message, dict):
            return value

        return {
            **message,
            "chatId": value.get("chatId"),
            "prevMessageId": value.get("prevMessageId"),
            "ttl": value.get("ttl"),
            "unread": value.get("unread"),
            "mark": value.get("mark"),
        }
