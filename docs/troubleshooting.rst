Troubleshooting
===============

Базовая диагностика
-------------------

Начинайте с debug-логов:

.. code-block:: python

   from pymax import Client, ExtraConfig

   client = Client(
       phone="+79990000000",
       work_dir="cache",
       extra_config=ExtraConfig(log_level="DEBUG"),
   )

Если событие не распознается, добавьте raw-handler:

.. code-block:: python

   from pymax import Client
   from pymax.protocol import InboundFrame

   @client.on_raw()
   async def raw(frame: InboundFrame, client: Client) -> None:
       print(frame.opcode, frame.cmd, frame.payload)

Проблемы запуска
----------------

``Failed to connect and handshake``
   Проверьте сеть, DNS, VPN/proxy и доступность Max. Если reconnect скрывает
   исходное исключение, временно запустите клиент с ``reconnect=False``.

``Authentication failed: no token received``
   Авторизация завершилась без token. Проверьте SMS-код, пароль 2FA и срок
   действия auth-flow.

``Failed to create auth track``
   Ошибка auth-track запроса, чаще всего при работе с 2FA. Проверьте, что
   клиент авторизован и соединение активно.

Снова спрашивает код
   Проверьте путь ``work_dir/session_name``. Относительный ``work_dir`` зависит
   от директории, из которой запущен Python.

Handlers
--------

Если handler не вызывается, проверьте:

* handler зарегистрирован до ``await client.start()``;
* декоратор вызван со скобками;
* функция принимает ``event`` и ``client``;
* фильтры временно отключены или точно возвращают ``True``;
* нужное событие видно через ``on_raw``;
* в debug-логах нет ошибки валидации payload.

Sync и чаты
-----------

``client.chats`` - это данные из login/sync, а не полный список чатов. Для
догрузки используйте:

.. code-block:: python

   chats = await client.fetch_chats()
   chat = await client.get_chat(123456)

Если нужен sync с нуля на следующем login:

.. code-block:: python

   from pymax import ExtraConfig, SyncOverrides

   extra_config = ExtraConfig(sync=SyncOverrides(chats_sync=-1))

Полное удаление файла сессии тоже сбросит состояние, но потребует новую
авторизацию.

Pydantic validation error
-------------------------

Неизвестный тип вложения сохраняется как ``UnknownAttachment``. Validation error
обычно означает, что Max изменил или прислал неполный payload уже известной
модели. Снимите raw payload через ``on_raw`` и не публикуйте token, телефоны,
приватные URL и ID без необходимости.

UploadError
-----------

Для ``Photo`` проверьте расширение, content-type и доступность URL. Для
``File`` и ``Video`` проверьте путь/URL, размер файла и событие готовности:
после HTTP-upload Max должен прислать attach-событие за 60 секунд. Если событие
не приходит, включите ``on_raw`` и посмотрите входящие attach payload-ы.

Reconnect
---------

При reconnect PyMax создает новый runtime, но оставляет тот же root router.
Обработчики остаются зарегистрированными, а ``on_start`` вызывается заново
после успешного login.

2FA
---

``set_2fa()`` с email зависает на вводе кода
   Если передан ``email`` и не указан ``email_code_provider``, PyMax использует
   консольный provider. В UI-приложениях передайте собственный async-provider.

``remove_2fa()`` не отключает пароль
   Метод требует текущий пароль 2FA. Включите ``DEBUG``-логи и проверьте, что
   сервер принял проверку пароля и запрос отключения.
