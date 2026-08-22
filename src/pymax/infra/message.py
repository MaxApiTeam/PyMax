from pymax.api.messages import DateTimeUnion
from pymax.api.messages.enums import ItemType
from pymax.api.messages.service import SendAttachments
from pymax.types import (
    FileRequest,
    Message,
    PollState,
    ReactionInfo,
    ReadState,
    VideoRequest,
)

from .protocol import IClientProtocol


class MessageMixin(IClientProtocol):
    """Методы клиента для сообщений, истории, реакций и вложений."""

    async def send_message(
        self,
        chat_id: int,
        text: str | None = None,
        reply_to: int | None = None,
        attachments: SendAttachments = None,
        *,
        notify: bool = True,
        send_at: DateTimeUnion | None = None,
    ) -> Message:
        """Отправляет сообщение в чат.

        Args:
            chat_id: ID чата.
            text: Текст сообщения. Можно не передавать при наличии вложений.
            reply_to: ID сообщения для ответа.
            attachments: Файлы, фотографии, видео или опросы для отправки.
            notify: Отправить ли получателям push-уведомление.

        Returns:
            Отправленное сообщение.

        Raises:
            ValueError: Если не переданы ни текст, ни вложения.
        """
        return await self._app.api.messages.send_message(
            chat_id,
            text,
            reply_to,
            attachments,
            notify=notify,
            send_at=send_at,
        )

    async def get_message(
        self,
        chat_id: int,
        message_id: int,
    ) -> Message | None:
        """Возвращает сообщение по ID.

        Args:
            chat_id: ID чата.
            message_id: ID сообщения.

        Returns:
            Сообщение или ``None``, если сервер его не вернул.
        """
        return await self._app.api.messages.get_message(
            chat_id=chat_id,
            message_id=message_id,
        )

    async def forward_message(
        self,
        chat_id: int,
        message_id: int | str,
        source_chat_id: int | None = None,
        *,
        notify: bool = True,
    ) -> Message:
        """Пересылает существующее сообщение в чат.

        Args:
            chat_id: ID целевого чата.
            message_id: ID пересылаемого сообщения.
            source_chat_id: ID исходного чата. Если не указан, используется
                целевой чат.
            notify: Отправить ли получателям push-уведомление.

        Returns:
            Пересланное сообщение.
        """
        return await self._app.api.messages.forward_message(
            chat_id=chat_id,
            message_id=message_id,
            source_chat_id=source_chat_id,
            notify=notify,
        )

    async def get_messages(
        self,
        chat_id: int,
        message_ids: list[int],
    ) -> list[Message]:
        """Возвращает сообщения по ID.

        Args:
            chat_id: ID чата.
            message_ids: ID сообщений.

        Returns:
            Список найденных сообщений.
        """
        return await self._app.api.messages.get_messages(
            chat_id=chat_id,
            message_ids=message_ids,
        )

    async def edit_message(
        self,
        chat_id: int,
        message_id: int,
        text: str | None = None,
        attachments: SendAttachments = None,
    ) -> Message:
        """Редактирует текст и вложения сообщения.

        Args:
            chat_id: ID чата.
            message_id: ID сообщения.
            text: Новый текст сообщения с поддержкой markdown.
            attachments: Новые файлы, фотографии, видео или опросы для сообщения.

        Returns:
            Отредактированное сообщение.
        """
        return await self._app.api.messages.edit_message(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            attachments=attachments,
        )

    async def fetch_history(
        self,
        chat_id: int,
        forward: int = 0,
        backward: int = 40,
        backward_time: DateTimeUnion = 0,
        forward_time: DateTimeUnion = 0,
        from_time: DateTimeUnion | None = None,
        item_type: ItemType = ItemType.REGULAR,
        get_chat: bool = False,
        get_messages: bool = True,
        interactive: bool = False,
    ) -> list[Message]:
        """Загружает историю сообщений чата.

        Args:
            chat_id: ID чата.
            forward: Сколько сообщений загрузить вперед от ``from_time``.
            backward: Сколько сообщений загрузить назад от ``from_time``.
            backward_time: Временное окно назад в миллисекундах.
            forward_time: Временное окно вперед в миллисекундах.
            from_time: Точка отсчета в миллисекундах Unix time. Если
                ``None``, используется текущий момент.
            item_type: Тип элементов истории: обычные или отложенные.
            get_chat: Запросить данные чата вместе с историей.
            get_messages: Запросить сами сообщения.
            interactive: Пометить запрос как интерактивный.

        Returns:
            Список сообщений. Если сервер не вернул сообщения, список пуст.
        """
        return await self._app.api.messages.fetch_history(
            chat_id=chat_id,
            forward=forward,
            backward=backward,
            backward_time=backward_time,
            forward_time=forward_time,
            from_=from_time,
            item_type=item_type,
            get_chat=get_chat,
            get_messages=get_messages,
            interactive=interactive,
        )

    async def delete_message(
        self,
        chat_id: int,
        message_ids: list[int],
        for_me: bool,
    ) -> bool:
        """Удаляет сообщения из чата.

        Args:
            chat_id: ID чата.
            message_ids: ID сообщений.
            for_me: Удалить только для текущего аккаунта.

        Returns:
            ``True``, если сервер принял запрос.
        """
        return await self._app.api.messages.delete_message(
            chat_id=chat_id,
            message_ids=message_ids,
            for_me=for_me,
        )

    async def pin_message(
        self,
        chat_id: int,
        message_id: int,
        notify_pin: bool,
    ) -> bool:
        """Закрепляет сообщение в чате.

        Args:
            chat_id: ID чата.
            message_id: ID сообщения.
            notify_pin: Отправить ли уведомление о закреплении.

        Returns:
            ``True``, если сервер принял запрос.
        """
        return await self._app.api.messages.pin_message(
            chat_id=chat_id,
            message_id=message_id,
            notify_pin=notify_pin,
        )

    async def get_video_by_id(
        self,
        chat_id: int,
        message_id: int | str,
        video_id: int,
    ) -> VideoRequest | None:
        """Возвращает данные для просмотра видео-вложения.

        Args:
            chat_id: ID чата.
            message_id: ID сообщения с видео.
            video_id: ID видео-вложения.

        Returns:
            Данные видео или ``None``, если сервер их не вернул.
        """
        return await self._app.api.messages.get_video_by_id(
            chat_id=chat_id,
            message_id=message_id,
            video_id=video_id,
        )

    async def get_file_by_id(
        self,
        chat_id: int,
        message_id: int | str,
        file_id: int,
    ) -> FileRequest | None:
        """Возвращает данные для скачивания файлового вложения.

        Args:
            chat_id: ID чата.
            message_id: ID сообщения с файлом.
            file_id: ID файлового вложения.

        Returns:
            Данные файла или ``None``, если сервер их не вернул.
        """
        return await self._app.api.messages.get_file_by_id(
            chat_id=chat_id,
            message_id=message_id,
            file_id=file_id,
        )

    async def add_reaction(
        self,
        chat_id: int,
        message_id: int,
        reaction: str,
    ) -> ReactionInfo | None:
        """Добавляет реакцию к сообщению.

        Args:
            chat_id: ID чата.
            message_id: ID сообщения.
            reaction: ID emoji-реакции, поддержанный сервером.

        Returns:
            Обновленные реакции или ``None``, если сервер их не вернул.
        """
        return await self._app.api.messages.add_reaction(
            chat_id=chat_id,
            message_id=message_id,
            reaction=reaction,
        )

    async def get_reactions(
        self,
        chat_id: int,
        message_ids: list[int],
    ) -> dict[str, ReactionInfo] | None:
        """Возвращает реакции для нескольких сообщений.

        Args:
            chat_id: ID чата.
            message_ids: ID сообщений.

        Returns:
            ``{message_id: ReactionInfo}`` или ``None``, если реакций нет в
            ответе сервера.
        """
        return await self._app.api.messages.get_reactions(
            chat_id=chat_id,
            message_ids=message_ids,
        )

    async def remove_reaction(
        self,
        chat_id: int,
        message_id: int,
    ) -> ReactionInfo | None:
        """Удаляет свою реакцию с сообщения.

        Args:
            chat_id: ID чата.
            message_id: ID сообщения.

        Returns:
            Обновленные реакции или ``None``, если сервер их не вернул.
        """
        return await self._app.api.messages.remove_reaction(
            chat_id=chat_id,
            message_id=message_id,
        )

    async def read_message(self, message_id: int | str, chat_id: int) -> ReadState:
        """Отмечает сообщение как прочитанное.

        У Max различается wire-формат ``message_id`` для отметки прочтения:
        TCP-клиент ожидает ``int``, WebSocket-клиент - ``str``.

        Args:
            message_id: ID сообщения. Передавайте ``int`` для ``Client`` и
                ``str`` для ``WebClient``.
            chat_id: ID чата.

        Returns:
            Состояние прочтения.
        """
        return await self._app.api.messages.read_message(
            message_id=message_id,
            chat_id=chat_id,
        )

    async def vote_poll(
        self,
        chat_id: int,
        message_id: int,
        poll_id: int,
        answer_ids: list[int],
    ) -> PollState:
        """Отправляет выбранные ответы в опросе.

        Args:
            chat_id: ID чата с опросом.
            message_id: ID сообщения с опросом.
            poll_id: ID опроса из ``PollAttachment.poll_id``.
            answer_ids: ID выбранных вариантов ответа.

        Returns:
            Обновленное состояние опроса.
        """
        return await self._app.api.messages.vote_poll(
            chat_id=chat_id,
            message_id=message_id,
            poll_id=poll_id,
            answer_ids=answer_ids,
        )
