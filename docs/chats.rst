Chats
=====

Что это
-------

``Chat`` описывает диалог, группу или канал Max. У клиента есть кеш чатов из
login/sync, а также методы для загрузки, создания и управления чатами.

Получить чаты
-------------

После ``start`` доступны:

.. code-block:: python

   from pymax import Client

   @client.on_start()
   async def on_start(client: Client) -> None:
       for chat in client.chats or []:
           print(chat.id, chat.title)

Если нужного чата нет в ``client.chats``, запросите его явно:

.. code-block:: python

   chat = await client.get_chat(123456)
   print(chat.title)

Загрузить список чатов с сервера:

.. code-block:: python

   chats = await client.fetch_chats()
   for chat in chats:
       print(chat.id, chat.title)

Почему не видно чаты
--------------------

``client.chats`` - это не гарантированная полная база всех чатов. Это список,
который Max вернул на login с учетом sync-state. На повторном запуске PyMax
отправляет сохраненный ``chats_sync``, и сервер может вернуть только изменения.

Что делать:

* вызовите ``await client.fetch_chats()``;
* запросите конкретный чат через ``await client.get_chat(chat_id)``;
* для следующего login используйте ``SyncOverrides(chats_sync=-1)``;
* проверьте, что вы авторизованы тем аккаунтом и тем файлом сессии.

Создать группу
--------------

.. code-block:: python

   result = await client.create_group(
       name="PyMax test",
       participant_ids=[111, 222],
   )
   if result is not None:
       chat, service_message = result

Пригласить и удалить участников
-------------------------------

.. code-block:: python

   await client.invite_users_to_group(
       chat_id=123456,
       user_ids=[111, 222],
       show_history=True,
   )

   await client.remove_users_from_group(
       chat_id=123456,
       user_ids=[222],
       clean_msg_period=0,
   )

Через объект ``Chat``:

.. code-block:: python

   chat = await client.get_chat(123456)
   await chat.invite([111])
   await chat.answer("Добро пожаловать")

``invite()`` работает только для групп и каналов. Для личного диалога тип чата
не подходит, и метод завершится ошибкой.

Участники и администраторы канала
---------------------------------

``get_chat_members()`` возвращает одну страницу участников и маркер следующей:

.. code-block:: python

   members, marker = await client.get_chat_members(chat_id=123456, count=50)
   for member in members:
       print(member.contact.id)

   if marker:
       next_members, marker = await client.get_chat_members(
           chat_id=123456,
           marker=marker,
           count=50,
       )

Назначить администратора канала можно с явным набором прав:

.. code-block:: python

   from pymax.api.chats import ChannelPermissions

   await client.add_admin(
       chat_id=123456,
       user_id=111,
       permissions=[
           ChannelPermissions.POST_MESSAGE,
           ChannelPermissions.EDIT_MESSAGE,
           ChannelPermissions.DELETE_MESSAGE,
       ],
   )

Настройки и профиль группы
--------------------------

.. code-block:: python

   from pymax import Photo

   await client.change_group_profile(
       chat_id=123456,
       name="Новый заголовок",
       description="Описание группы",
       photo=Photo(path="group.jpg"),
   )

   await client.change_group_settings(
       chat_id=123456,
       only_admin_can_add_member=True,
       only_admin_can_call=True,
   )

``name``, ``description`` и ``photo`` независимы: передавайте только поля,
которые нужно изменить. Значение ``None`` исключает поле из запроса. Перед
обновлением профиля PyMax автоматически загружает ``Photo`` и отправляет Max
полученный photo token.

Через объект ``Chat`` можно менять настройки и перевыпускать invite-ссылку:

.. code-block:: python

   chat = await client.get_chat(123456)
   await chat.update_settings(only_admin_can_add_member=True)
   updated = await chat.rework_invite_link()

История сообщений
-----------------

.. code-block:: python

   chat = await client.get_chat(123456)
   messages = await chat.history(
       backward=50,
       from_time=None,
   )

``from_time`` - точка отсчета в Unix time **в миллисекундах**. Если передать
``None``, PyMax использует текущий момент. ``backward_time`` и
``forward_time`` тоже передаются в миллисекундах и задают временное окно назад
или вперед от ``from_time``.

Выйти из чата
-------------

.. code-block:: python

   chat = await client.get_chat(123456)
   await chat.leave()

``leave()`` зависит от типа чата: для группы вызывает выход из группы, для
канала - выход из канала. Из личного диалога выйти нельзя.

Удалить чат
-----------

.. code-block:: python

   await client.delete_chat(chat_id=123456)

Через объект ``Chat`` PyMax использует ``chat.last_event_time``:

.. code-block:: python

   chat = await client.get_chat(123456)
   await chat.delete(for_all=True)

После успешного удаления чат убирается из локального кеша ``client.chats``.

Invite-ссылки
-------------

.. code-block:: python

   chat = await client.resolve_group_by_link("https://max.ru/join/...")
   joined = await client.join_group("https://max.ru/join/...")
   updated = await client.rework_invite_link(joined.id)

Частые ошибки
-------------

``Cannot leave dialog``
   Из личного диалога нельзя выйти как из группы или канала.

``Unknown chat type``
   Сервер прислал неизвестный тип чата или в объекте нет поля ``type``.

``PyMaxError: Chat not found``
   Сервер не вернул чат. Проверьте ID, права доступа и аккаунт.
