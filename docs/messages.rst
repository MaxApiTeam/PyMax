Messages
========

Что это
-------

``Message`` - объект сообщения Max. Он содержит текст, ID чата, отправителя,
вложения и удобные методы: ``answer()``, ``reply()``, ``pin()``, ``delete()``,
``read()``, ``react()`` и ``unreact()``.

Принимать сообщения
-------------------

.. code-block:: python

   from pymax import Client, Message, MessageDeleteEvent

   client = Client(phone="+79990000000", work_dir="cache")


   @client.on_message()
   async def on_message(message: Message, client: Client) -> None:
       print(message.text)


   @client.on_message_edit()
   async def on_edit(message: Message, client: Client) -> None:
       print("edited:", message.text)


   @client.on_message_delete()
   async def on_delete(event: MessageDeleteEvent, client: Client) -> None:
       print("deleted in chat:", event.chat_id)

Получать и редактировать сообщения
----------------------------------

.. code-block:: python

   message = await client.get_message(
       chat_id=123456,
       message_id=987654,
   )
   messages = await client.get_messages(
       chat_id=123456,
       message_ids=[987654, 987655],
   )

   if message is not None:
       await message.edit("Обновленный текст")

Через клиент то же редактирование доступно как
``client.edit_message(chat_id, message_id, text, ...)``.
Новые вложения передаются через ``attachments``.

Отправлять сообщения
--------------------

Через клиент:

.. code-block:: python

   await client.send_message(chat_id=123456, text="Привет")

Через сообщение из handler-а:

.. code-block:: python

   @client.on_message()
   async def on_message(message: Message, client: Client) -> None:
       await message.answer("Ответ в тот же чат")
       await message.reply("Ответ реплаем")
       await message.forward(chat_id=654321)

Переслать сообщение напрямую через клиент можно с указанием исходного и
целевого чатов:

.. code-block:: python

   await client.forward_message(
       chat_id=654321,
       message_id=987654,
       source_chat_id=123456,
   )

Reply и forward во входящем сообщении
-------------------------------------

Если сообщение является reply или forward, поле ``message.link`` содержит
исходное ``message`` и его ``chat_id``. Для forward Max также может прислать
``chat_name``, ``chat_link``, ``chat_access_type`` и ``chat_icon_url``; для
скрытого источника эти поля равны ``None``. У обычного сообщения ``link`` равен
``None``.

.. code-block:: python

   @client.on_message()
   async def on_message(message: Message, client: Client) -> None:
       if message.link is not None:
           print("source:", message.link.chat_id, message.link.message.id)

Отложенная отправка
-------------------

``client.send_message()``, ``message.answer()`` и ``message.reply()`` принимают
``send_at`` трех видов:

* ``datetime`` - абсолютное время отправки;
* ``timedelta`` - задержка относительно текущего локального времени;
* ``int`` - Unix time в секундах.

.. code-block:: python

   from datetime import datetime, timedelta, timezone

   await client.send_message(
       chat_id=123456,
       text="Через пять минут",
       send_at=timedelta(minutes=5),
   )

   await client.send_message(
       chat_id=123456,
       text="В назначенное время",
       send_at=datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc),
       notify=False,
   )

``None`` и ``0`` означают немедленную отправку. Значение ``notify`` также
используется сервером при срабатывании отложенного сообщения.

У полученного отложенного сообщения поле ``delayed_attributes`` содержит
``time_to_fire`` в миллисекундах и флаги уведомлений. Для обычного сообщения
оно равно ``None``. Получить отложенные сообщения можно через
``fetch_history(item_type=ItemType.DELAYED)``.

Опросы
------

Опрос можно отправить без текста. Настройки объединяются оператором ``|``:

.. code-block:: python

   from pymax.types import Poll, PollAnswer, PollFlags

   await client.send_message(
       chat_id=123456,
       attachments=[
           Poll(
               title="Какой вариант выбрать?",
               answers=[
                   PollAnswer(text="Первый"),
                   PollAnswer(text="Второй"),
               ],
               settings=(
                   PollFlags.FLAG_SETTINGS_ANONYMOUS
                   | PollFlags.FLAG_SETTINGS_REVOTE
               ),
           )
       ],
   )

Для голосования нужны ID сообщения, опроса и вариантов из входящего
``PollAttachment``:

.. code-block:: python

   from pymax import Message
   from pymax.types import PollAttachment

   @client.on_message()
   async def vote(message: Message, client: Client) -> None:
       if message.chat_id is None:
           return

       for attach in message.attaches:
           if isinstance(attach, PollAttachment):
               answer_id = attach.answers[0].answer_id
               if answer_id is not None:
                   state = await client.vote_poll(
                       chat_id=message.chat_id,
                       message_id=message.id,
                       poll_id=attach.poll_id,
                       answer_ids=[answer_id],
                   )
                   print(state.total)

Ответ, реакции, удаление и прочтение
------------------------------------

.. code-block:: python

   @client.on_message()
   async def on_message(message: Message, client: Client) -> None:
       if message.text == "/pin":
           await message.pin()
       elif message.text == "/read":
           await message.read()
       elif message.text == "/like":
           await message.react("👍")
       elif message.text == "/reactions":
           reactions = await message.get_reactions()
           print(reactions)
       elif message.text == "/delete":
           await message.delete(for_me=False)

.. note::

   У низкоуровневого ``client.read_message(...)`` есть особенность Max:
   для отметки прочтения TCP-клиент ожидает ``message_id`` как ``int``, а
   WebSocket-клиент - как ``str``. Если вызываете метод напрямую, выбирайте
   тип по клиенту.

Методы ``add_reaction()``, ``get_reactions()`` и ``remove_reaction()``
принимают ID сообщений только как ``int``. При этом ``get_reactions()``
возвращает словарь со строковыми ключами, потому что именно так ID приходят в
ответе Max.

Служебные события
-----------------

Начиная с ``2.2.0`` доступны отдельные обработчики набора текста, присутствия,
прочтения и реакций:

.. code-block:: python

   from pymax import (
       Client,
       MessageReadEvent,
       PresenceEvent,
       ReactionUpdateEvent,
       TypingEvent,
   )

   @client.on_typing()
   async def typing(event: TypingEvent, client: Client) -> None:
       print(event.chat_id, event.user_id)

   @client.on_presence()
   async def presence(event: PresenceEvent, client: Client) -> None:
       print(event.user_id, event.presence.status)

   @client.on_message_read()
   async def read(event: MessageReadEvent, client: Client) -> None:
       print(event.chat_id, event.mark)

   @client.on_reaction_update()
   async def reactions(event: ReactionUpdateEvent, client: Client) -> None:
       print(event.message_id, event.total_count)

История сообщений
-----------------

.. code-block:: python

   history = await client.fetch_history(chat_id=123456, backward=50)
   for message in history:
       print(message.id, message.text)

``fetch_history()`` принимает ``item_type``. По умолчанию используются обычные
сообщения; для отложенных сообщений передайте ``ItemType.DELAYED`` из
``pymax.api.messages.enums``.

Почему поля бывают None
-----------------------

Max присылает разные формы событий. Некоторые payload-ы содержат полный объект
сообщения, а некоторые - только часть данных. Поэтому ``Message.chat_id``,
``sender``, ``attaches``, ``reaction_info``, ``status`` и другие поля могут
быть пустыми.

Практическое правило: перед действиями, которым нужен чат, проверяйте
``message.chat_id``.

.. code-block:: python

   @client.on_message()
   async def on_message(message: Message, client: Client) -> None:
       if message.chat_id is None:
           return

       await message.answer("ok")

Вложения
--------

Входящие вложения лежат в ``message.attaches``. Тип вложения определяется по
полю ``type``: фото, видео, файл, стикер, аудио, опрос, контакт, звонок, share
или inline-клавиатура.

Неизвестный ``_type`` не отклоняет все сообщение: PyMax возвращает
``UnknownAttachment``, сохраняет исходный тип в ``type``, а остальные поля - в
``model_extra``. Это позволяет принять payload нового типа до добавления его
отдельной модели в библиотеку.

.. code-block:: python

   from pymax import Client, Message
   from pymax.types.domain import FileAttachment, PhotoAttachment, UnknownAttachment

   @client.on_message()
   async def on_message(message: Message, client: Client) -> None:
       if message.chat_id is None:
           return

       for attach in message.attaches:
           if isinstance(attach, PhotoAttachment):
               print("photo:", attach.photo_id, attach.base_url)
           elif isinstance(attach, FileAttachment):
               file_info = await client.get_file_by_id(
                   chat_id=message.chat_id,
                   message_id=message.id,
                   file_id=attach.file_id,
               )
               print(file_info.url if file_info else "no url")
           elif isinstance(attach, UnknownAttachment):
               print("unknown:", attach.type, attach.model_extra)

Частые ошибки
-------------

``Message is not bound to a client``
   Методы ``message.answer()`` и похожие работают на сообщениях, полученных
   через клиент. Если вы создали ``Message`` вручную через Pydantic, он не
   знает, каким клиентом выполнить действие.

``Message does not contain chat_id``
   В событии нет ID чата. Используйте ``client.send_message(...)`` только если
   знаете ``chat_id`` из другого источника.

Pydantic validation error на attachments
   Неизвестный ``_type`` обрабатывается через ``UnknownAttachment``, но
   поврежденный или неполный payload уже известного типа все еще может не пройти
   валидацию. Включите debug-логи, посмотрите raw payload через ``on_raw`` и
   обновите PyMax или добавьте обработку нового формата.
