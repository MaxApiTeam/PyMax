PyMax 2.4.0
===========

Версия 2.4.0 добавляет опросы, голосовые сообщения, кружки, настройки
приватности и новые методы управления чатами. Одновременно уточнены контракты
существующих методов и исправлены проблемы с lifecycle клиента, повторной
авторизацией и WebSocket.

Ниже перечислены изменения относительно ``2.3.1``, которые важны при
использовании библиотеки и обновлении существующего кода.

Новый публичный API
-------------------

Опросы
~~~~~~

Добавлены модели ``Poll``, ``PollAnswer`` и ``PollFlags`` для создания
опросов. Опрос отправляется обычным ``send_message()`` и может быть
единственным вложением без текста:

.. code-block:: python

   from pymax.types import Poll, PollAnswer, PollFlags

   message = await client.send_message(
       chat_id=123456,
       attachments=[
           Poll(
               title="Выберите вариант",
               answers=[
                   PollAnswer(text="Первый"),
                   PollAnswer(text="Второй"),
               ],
               settings=PollFlags.FLAG_SETTINGS_REVOTE,
           )
       ],
   )

Для голосования добавлен метод:

``await client.vote_poll(chat_id, message_id, poll_id, answer_ids) -> PollState``

Входящий опрос представлен моделью ``PollAttachment``. Она содержит
``poll_id``, варианты ответа и текущее состояние ``PollState`` с
типизированными результатами и голосами.

Голосовые сообщения и кружки
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Добавлены два типа отправляемых вложений:

``Voice``
   Голосовое сообщение. Принимает только готовый OGG-файл. PyMax не
   перекодирует MP3, WAV и другие форматы.

``VideoNote``
   Круглое видеосообщение. Рекомендуемый формат — MP4 с H.264-видео 480x480,
   30 FPS и AAC-аудио. Длительность передается в миллисекундах через
   ``duration``.

Оба класса экспортируются из ``pymax`` и передаются в ``attachments``:

.. code-block:: python

   from pymax import VideoNote, Voice

   await client.send_message(
       chat_id=123456,
       attachments=[Voice(path="voice.ogg")],
   )
   await client.send_message(
       chat_id=123456,
       attachments=[VideoNote(path="circle.mp4", duration=4200)],
   )

Если ``duration`` для ``VideoNote`` не указан, PyMax может определить его
автоматически с необязательной зависимостью ``video``::

   uv add "maxapi-python[video]"

Чаты и состояние аккаунта
~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: Новые методы
   :header-rows: 1
   :widths: 35 40 25

   * - Метод
     - Назначение
     - Результат
   * - ``get_chat_members(chat_id, marker=None, count=50)``
     - Получить страницу участников чата. Ненулевой ``marker`` передается в
       следующий вызов.
     - ``tuple[list[Member], int]``
   * - ``add_admin(chat_id, user_id, permissions)``
     - Назначить администратора канала с явным списком
       ``ChannelPermissions``.
     - ``None``
   * - ``set_presence(online=...)``
     - Изменить статус, используемый при следующем login или ping.
     - ``None``
   * - ``is_update_available()``
     - Проверить флаг обновления, полученный при handshake.
     - ``bool``

Настройки приватности
~~~~~~~~~~~~~~~~~~~~~

Добавлен метод
``await client.change_profile_settings(settings) -> bool``. Он принимает
``PrivacySettingsUpdate`` и изменяет только заполненные поля:

.. code-block:: python

   from pymax import PrivacyAccess, PrivacySettingsUpdate

   await client.change_profile_settings(
       PrivacySettingsUpdate(
           search_by_phone=PrivacyAccess.CONTACTS,
           incoming_calls=PrivacyAccess.ALL,
           chat_invites=PrivacyAccess.NOBODY,
           phone_number_visibility=PrivacyAccess.CONTACTS,
           hide_online_status=True,
           safe_content_only=True,
       )
   )

Для настроек доступа используются ``PrivacyAccess.ALL``,
``PrivacyAccess.CONTACTS`` и ``PrivacyAccess.NOBODY``. После успешного запроса
PyMax сохраняет новый ``config_hash`` в текущей сессии, поэтому следующая
авторизация продолжает синхронизацию с актуального состояния.

Изменения существующего API
---------------------------

.. list-table:: Изменившиеся контракты
   :header-rows: 1
   :widths: 30 30 40

   * - API
     - Было в 2.3.1
     - Стало в 2.4.0
   * - ``send_message()`` и ``forward_message()``
     - Возвращаемый тип допускал ``Message | None``.
     - Возвращают ``Message``. Если сервер не прислал обязательный объект
       сообщения, вызов завершается ошибкой.
   * - ``Message.reply()``, ``Message.answer()``, ``Message.forward()`` и
       ``Chat.answer()``
     - Bound-методы также имели необязательный возвращаемый тип.
     - Возвращают ``Message`` без лишней проверки на ``None``.
   * - ``send_message()``, ``edit_message()``, ``Message.reply()``,
       ``Message.answer()`` и ``Chat.answer()``
     - Для type checker требовался текст.
     - ``text`` может быть ``None``, если переданы вложения. Если нет ни
       текста, ни вложений, выбрасывается ``ValueError``.
   * - ``fetch_history()``
     - При отсутствии сообщений мог вернуть ``None``.
     - Всегда возвращает ``list[Message]``; пустая история — ``[]``.
   * - ``get_bot_init_data()``
     - ``chat_id`` был обязательным.
     - ``chat_id`` необязателен, поэтому метод можно вызвать вне чата.
   * - ``change_profile()``
     - ``photo`` был типизирован как ``Any``.
     - ``photo`` принимает ``Photo | None``.

Также исправлены типы частичных моделей протокола. В частности,
``StickerAttachment.set_id`` теперь имеет тип ``int | None``, а поля неполных
событий реакций больше не считаются безусловно заполненными.

Breaking changes
----------------

Методы и классы из 2.3.1 не удалялись и не переименовывались. Проверить перед
обновлением нужно два наблюдаемых изменения поведения:

* Код, который отличал ``None`` от пустого списка после ``fetch_history()``,
  должен проверять пустоту списка: ``if not history``.
* Попытка отправить или отредактировать сообщение без текста и без вложений
  теперь сразу завершается ``ValueError``. Сообщения только с вложением
  поддерживаются штатно.

Изменения ``Message | None`` на ``Message`` у методов отправки и пересылки —
уточнение публичного контракта, а не новое успешное значение в runtime.
Пользователи mypy или Pyright могут удалить лишние проверки результата на
``None``. При работе со ``StickerAttachment.set_id`` проверка на ``None``,
наоборот, теперь требуется.

Исправления стабильности и совместимости
----------------------------------------

* Если текущую сессию отозвали с другого устройства, ответы
  ``FAIL_LOGIN_TOKEN`` и ``FAIL_LOGOUT_ALL`` больше не оставляют клиент в
  цикле переподключений. PyMax удаляет недействительный локальный token и
  запускает авторизацию заново. Закрытие TLS-соединения ограничено timeout,
  поэтому зависший shutdown не блокирует клиент бесконечно.
* ``stop()`` штатно завершает ожидающий ``start()``. Внешняя отмена задачи при
  этом не поглощается и продолжает распространяться вызывающему коду.
* WebSocket-клиент использует актуальный endpoint и корректно обрабатывает
  бинарные protocol frames.
* Mobile login поддерживает двухэтапный LOGIN/LOGIN2. Fingerprint устройства
  выбирается автоматически из данных Android-версий от 26.9.1 до 26.25.0.
* Handshake без обязательного ``callsSeed`` завершается контролируемой ошибкой,
  а не оставляет клиент в частично инициализированном состоянии.
* Исправлены очистка ожиданий при ошибках upload, выбор MP4 URL по качеству и
  разбор частичных событий реакций и голосов в опросах.

Базовый набор зависимостей не изменился. Extra ``video`` нужен только для
автоматического определения длительности ``VideoNote``; при явном
``duration`` он не требуется.
