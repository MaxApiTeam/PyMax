from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import Field, PrivateAttr

from .base import CamelModel
from .enums import AccessType, ChatType
from .message import Message, SendAttachments

if TYPE_CHECKING:
    from pymax.api.chats import ChatService
    from pymax.api.messages import MessageService
    from pymax.api.messages.enums import ItemType


class Chat(CamelModel):
    """Чат, группа, канал или диалог Max.

    Объекты чатов, полученные через клиент, обычно уже привязаны к сервисам
    сообщений и чатов. После этого можно вызывать удобные методы объекта:
    :meth:`answer`, :meth:`history`, :meth:`get_message`,
    :meth:`get_messages`, :meth:`leave`, :meth:`delete`, :meth:`invite`,
    :meth:`remove_users`, :meth:`pin_message`, :meth:`update_settings` и
    :meth:`rework_invite_link`.

    Используйте ``Chat`` для работы с конкретным диалогом, группой или каналом.
    ``client.chats`` содержит чаты из login/sync, а недостающие чаты можно
    загрузить через ``client.get_chat`` или ``client.fetch_chats``.

    Example:
        .. code-block:: python

           chat = await client.get_chat(123456)
           await chat.answer("Привет")
           history = await chat.history(backward=20)

    :ivar id: ID чата.
    :vartype id: int
    :ivar type: Тип чата.
    :vartype type: ChatType | str
    :ivar status: Статус чата.
    :vartype status: str
    :ivar owner: ID владельца чата.
    :vartype owner: int
    :ivar participants: Участники чата.
    :vartype participants: dict[int, int]
    :ivar title: Название чата.
    :vartype title: str | None
    :ivar base_raw_icon_url: Исходный URL иконки чата.
    :vartype base_raw_icon_url: str | None
    :ivar base_icon_url: URL иконки чата.
    :vartype base_icon_url: str | None
    :ivar last_message: Последнее сообщение чата.
    :vartype last_message: Message | None
    :ivar last_event_time: Время последнего события в формате Unix time.
    :vartype last_event_time: int
    :ivar last_delayed_update_time: Время последнего отложенного обновления.
    :vartype last_delayed_update_time: int
    :ivar last_fire_delayed_error_time: Время последней ошибки отложенного
        события.
    :vartype last_fire_delayed_error_time: int
    :ivar created: Время создания чата в формате Unix time.
    :vartype created: int
    :ivar new_messages: Количество новых сообщений.
    :vartype new_messages: int
    :ivar link: Invite-ссылка чата.
    :vartype link: str | None
    :ivar access: Тип доступа к чату.
    :vartype access: AccessType | str | None
    :ivar restrictions: Битовая маска или код ограничений чата.
    :vartype restrictions: int | None
    :ivar pinned_message: Закрепленное сообщение.
    :vartype pinned_message: Message | None
    :ivar participants_count: Количество участников.
    :vartype participants_count: int
    :ivar description: Описание чата.
    :vartype description: str | None
    :ivar options: Дополнительные флаги и настройки чата от Max.
    :vartype options: dict[str, bool] | int | None
    :ivar join_time: Время вступления в чат в формате Unix time.
    :vartype join_time: int
    :ivar invited_by: ID пользователя, который пригласил текущий аккаунт.
    :vartype invited_by: int | None
    :ivar modified: Время последнего изменения в формате Unix time.
    :vartype modified: int
    :ivar messages_count: Количество сообщений.
    :vartype messages_count: int
    :ivar has_bots: Есть ли в чате боты, если Max прислал этот признак.
    :vartype has_bots: bool | None
    :ivar prev_message_id: ID предыдущего сообщения.
    :vartype prev_message_id: int | None
    :ivar admin_participants: Данные администраторов по ID пользователя.
    :vartype admin_participants: dict[int, dict[Any, Any]]
    :ivar admins: ID администраторов чата.
    :vartype admins: list[int]
    :ivar cid: Клиентский ID, если он есть в payload-е Max.
    :vartype cid: int | None
    """

    id: int
    type: ChatType | str
    status: str
    owner: int
    participants: dict[int, int] = Field(default_factory=dict)
    title: str | None = None
    base_raw_icon_url: str | None = None
    base_icon_url: str | None = None
    last_message: Message | None = None
    last_event_time: int = 0
    last_delayed_update_time: int = 0
    last_fire_delayed_error_time: int = 0
    created: int = 0
    new_messages: int = 0
    link: str | None = None
    access: AccessType | str | None = None
    restrictions: int | None = None
    pinned_message: Message | None = None
    participants_count: int = 0
    description: str | None = None
    options: dict[str, bool] | int | None = None
    join_time: int = 0
    invited_by: int | None = None
    modified: int = 0
    messages_count: int = 0
    has_bots: bool | None = None
    prev_message_id: int | None = None
    admin_participants: dict[int, dict[Any, Any]] = Field(default_factory=dict)
    admins: list[int] = Field(default_factory=list)
    cid: int | None = None

    _message_actions: MessageService | None = PrivateAttr(default=None)
    _chat_actions: ChatService | None = PrivateAttr(default=None)

    def bind(
        self,
        message_actions: MessageService,
        chat_actions: ChatService,
    ) -> Chat:
        """Привязывает сервисы сообщений и чатов к объекту чата.

        :param message_actions: Сервис сообщений для действий с сообщениями.
        :type message_actions: MessageService
        :param chat_actions: Сервис чатов для действий с чатами.
        :type chat_actions: ChatService
        :returns: Этот же чат с привязанными сервисами.
        :rtype: Chat
        """
        self._message_actions = message_actions
        self._chat_actions = chat_actions
        if self.last_message is not None:
            self.last_message.bind(message_actions)
        if self.pinned_message is not None:
            self.pinned_message.bind(message_actions)
        return self

    async def answer(
        self,
        text: str | None = None,
        reply_to: int | None = None,
        attachments: SendAttachments = None,
        *,
        notify: bool = True,
    ) -> Message:
        """Отправляет сообщение в этот чат.

        :param text: Текст сообщения.
        :type text: str
        :param reply_to: ID сообщения для ответа.
        :type reply_to: int | None
        :param attachments: Файлы, фотографии или видео для отправки.
        :type attachments: SendAttachments
        :param notify: Отправить ли получателям push-уведомление.
        :type notify: bool
        :returns: Отправленное сообщение или ``None``, если сервер не вернул
            его.
        :rtype: Message | None
        :raises RuntimeError: Если чат не привязан к клиенту.
        """
        actions, _ = self._bound()

        return await actions.send_message(
            chat_id=self.id,
            text=text,
            reply_to=reply_to,
            attachments=attachments,
            notify=notify,
        )

    async def history(
        self,
        forward: int = 0,
        backward: int = 40,
        backward_time: int = 0,
        forward_time: int = 0,
        from_time: int | None = None,
        item_type: ItemType | None = None,
        get_chat: bool = False,
        get_messages: bool = True,
        interactive: bool = False,
    ) -> list[Message]:
        """Загружает историю сообщений этого чата.

        ``from_time``, ``backward_time`` и ``forward_time`` передаются в
        миллисекундах Unix time. Если ``from_time`` равен ``None``, PyMax
        использует текущий момент.

        :param forward: Сколько сообщений загрузить вперед от ``from_time``.
        :type forward: int
        :param backward: Сколько сообщений загрузить назад от ``from_time``.
        :type backward: int
        :param backward_time: Временное окно назад в миллисекундах.
        :type backward_time: int
        :param forward_time: Временное окно вперед в миллисекундах.
        :type forward_time: int
        :param from_time: Точка отсчета в миллисекундах Unix time. Если
            ``None``, используется текущий момент.
        :type from_time: int | None
        :param item_type: Тип элементов истории: обычные или отложенные.
        :type item_type: ItemType | None
        :param get_chat: Запросить данные чата вместе с историей.
        :type get_chat: bool
        :param get_messages: Запросить сами сообщения.
        :type get_messages: bool
        :param interactive: Пометить запрос как интерактивный.
        :type interactive: bool
        :returns: Сообщения или ``None``, если сервер не вернул список.
        :rtype: list[Message] | None
        :raises RuntimeError: Если чат не привязан к клиенту.
        """
        actions, _ = self._bound()
        if item_type is None:
            from pymax.api.messages.enums import ItemType

            item_type = ItemType.REGULAR

        return await actions.fetch_history(
            chat_id=self.id,
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

    async def get_message(self, message_id: int) -> Message | None:
        """Возвращает сообщение этого чата по ID.

        :param message_id: ID сообщения.
        :type message_id: int
        :returns: Сообщение или ``None``, если сервер его не вернул.
        :rtype: Message | None
        :raises RuntimeError: Если чат не привязан к клиенту.
        """
        actions, _ = self._bound()

        return await actions.get_message(
            chat_id=self.id,
            message_id=message_id,
        )

    async def get_messages(self, message_ids: list[int]) -> list[Message]:
        """Возвращает сообщения этого чата по ID.

        :param message_ids: ID сообщений.
        :type message_ids: list[int]
        :returns: Список найденных сообщений.
        :rtype: list[Message]
        :raises RuntimeError: Если чат не привязан к клиенту.
        """
        actions, _ = self._bound()

        return await actions.get_messages(
            chat_id=self.id,
            message_ids=message_ids,
        )

    async def leave(self) -> None:
        """Выходит из группы или канала.

        Метод зависит от типа чата: для ``ChatType.CHAT`` вызывает выход из
        группы, для ``ChatType.CHANNEL`` - выход из канала. Для личного диалога
        ``ChatType.DIALOG`` выход не поддерживается.

        :returns: ``None``.
        :rtype: None
        :raises RuntimeError: Если чат не привязан к клиенту или является
            личным диалогом.
        :raises ValueError: Если тип чата неизвестен.
        """
        _, chat_actions = self._bound()

        if self.type == ChatType.DIALOG:
            raise RuntimeError("Cannot leave dialog")

        if self.type == ChatType.CHAT:
            return await chat_actions.leave_group(self.id)

        if self.type == ChatType.CHANNEL:
            return await chat_actions.leave_channel(self.id)

        raise ValueError("Unknown chat type=%s", self.type)

    async def delete(self, *, for_all: bool = True) -> None:
        """Удаляет этот чат.

        Для ``last_event_time`` используется значение ``Chat.last_event_time``.

        :param for_all: Удалить чат для всех участников, если сервер
            поддерживает такой режим.
        :type for_all: bool
        :returns: ``None``.
        :rtype: None
        :raises RuntimeError: Если чат не привязан к клиенту.
        """
        _, chat_actions = self._bound()

        return await chat_actions.delete_chat(
            self.id,
            last_event_time=self.last_event_time,
            for_all=for_all,
        )

    async def invite(
        self,
        user_ids: list[int],
        show_history: bool = True,
    ) -> Chat | None:
        """Приглашает пользователей в группу или канал.

        Метод зависит от типа чата: для ``ChatType.CHAT`` вызывает приглашение
        в группу, для ``ChatType.CHANNEL`` - приглашение в канал. Для других
        типов чатов будет ошибка.

        :param user_ids: ID пользователей, которых нужно пригласить.
        :type user_ids: list[int]
        :param show_history: Показать ли новым участникам историю сообщений.
        :type show_history: bool
        :returns: Обновленный чат или ``None``, если сервер не вернул его.
        :rtype: Chat | None
        :raises RuntimeError: Если чат не привязан к клиенту.
        :raises ValueError: Если тип чата неизвестен.
        """
        _, chat_actions = self._bound()

        if self.type == ChatType.CHAT:
            return await chat_actions.invite_users_to_group(
                self.id,
                user_ids,
                show_history,
            )
        if self.type == ChatType.CHANNEL:
            return await chat_actions.invite_users_to_channel(
                self.id,
                user_ids,
                show_history,
            )

        raise ValueError("Unknown chat type=%s", self.type)

    async def remove_users(
        self,
        user_ids: list[int],
        clean_msg_period: int = 0,
    ) -> bool:
        """Удаляет пользователей из группы.

        :param user_ids: ID пользователей, которых нужно удалить.
        :type user_ids: list[int]
        :param clean_msg_period: Период удаления сообщений пользователей.
        :type clean_msg_period: int
        :returns: ``True``, если сервер принял запрос.
        :rtype: bool
        :raises RuntimeError: Если чат не привязан к клиенту.
        """
        _, chat_actions = self._bound()

        return await chat_actions.remove_users_from_group(
            self.id,
            user_ids,
            clean_msg_period,
        )

    async def pin_message(
        self,
        message_id: int,
        notify_pin: bool = True,
    ) -> bool:
        """Закрепляет сообщение в этом чате.

        :param message_id: ID сообщения.
        :type message_id: int
        :param notify_pin: Отправить ли уведомление о закреплении.
        :type notify_pin: bool
        :returns: ``True``, если сервер принял запрос.
        :rtype: bool
        :raises RuntimeError: Если чат не привязан к клиенту.
        """
        message_actions, _ = self._bound()

        return await message_actions.pin_message(
            self.id,
            message_id,
            notify_pin,
        )

    async def update_settings(
        self,
        all_can_pin_message: bool | None = None,
        only_owner_can_change_icon_title: bool | None = None,
        only_admin_can_add_member: bool | None = None,
        only_admin_can_call: bool | None = None,
        members_can_see_private_link: bool | None = None,
    ) -> None:
        """Обновляет настройки группы.

        :param all_can_pin_message: Разрешить всем участникам закреплять
            сообщения.
        :type all_can_pin_message: bool | None
        :param only_owner_can_change_icon_title: Разрешить менять аватар и
            название только владельцу.
        :type only_owner_can_change_icon_title: bool | None
        :param only_admin_can_add_member: Разрешить добавлять участников
            только администраторам.
        :type only_admin_can_add_member: bool | None
        :param only_admin_can_call: Разрешить звонки только администраторам.
        :type only_admin_can_call: bool | None
        :param members_can_see_private_link: Разрешить участникам видеть
            приватную invite-ссылку.
        :type members_can_see_private_link: bool | None
        :returns: ``None``.
        :rtype: None
        :raises RuntimeError: Если чат не привязан к клиенту.
        """
        _, chat_actions = self._bound()

        return await chat_actions.change_group_settings(
            self.id,
            all_can_pin_message=all_can_pin_message,
            only_owner_can_change_icon_title=only_owner_can_change_icon_title,
            only_admin_can_add_member=only_admin_can_add_member,
            only_admin_can_call=only_admin_can_call,
            members_can_see_private_link=members_can_see_private_link,
        )

    async def rework_invite_link(self) -> Chat:
        """Перевыпускает приватную invite-ссылку группы.

        :returns: Обновленный чат с новой invite-ссылкой.
        :rtype: Chat
        :raises RuntimeError: Если чат не привязан к клиенту.
        """
        _, chat_actions = self._bound()

        return await chat_actions.rework_invite_link(self.id)

    def _bound(self) -> tuple[MessageService, ChatService]:
        if self._message_actions is None:
            raise RuntimeError("Chat is not bound to a client.")

        if self._chat_actions is None:
            raise RuntimeError("Chat is not bound to a client.")

        return self._message_actions, self._chat_actions

    @property
    def is_dialog(self) -> bool:
        """``True``, если чат является личным диалогом."""
        return self.type == ChatType.DIALOG

    @property
    def is_group(self) -> bool:
        """``True``, если чат является группой."""
        return self.type == ChatType.CHAT

    @property
    def is_channel(self) -> bool:
        """``True``, если чат является каналом."""
        return self.type == ChatType.CHANNEL
