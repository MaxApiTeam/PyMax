Client
======

Что это
-------

``Client`` и ``WebClient`` - главные объекты библиотеки. Они держат соединение,
авторизацию, локальную сессию, кеш профиля/чатов и методы для API Max.

``Client`` не является обычным HTTP-wrapper-ом на один запрос. После
``await client.start()`` он остается подключенным, слушает события Max,
отвечает на ping и вызывает ваши handler-ы.

Как выбрать клиента
-------------------

``Client``
   TCP-клиент с авторизацией по телефону и SMS-коду. Это основной вариант.
   Поддерживает ``device_type`` ``ANDROID``, ``IOS`` и ``DESKTOP``.

``WebClient``
   WebSocket-клиент с QR-авторизацией. В штатной конфигурации работает как
   ``WEB``-устройство.

Жизненный цикл
--------------

1. Вы создаете ``Client`` или ``WebClient``.
2. Регистрируете handler-ы и подключаете роутеры.
3. Вызываете ``await client.start()``.
4. PyMax открывает соединение, делает handshake и login.
5. После login доступны ``client.me`` и ``client.chats``.
6. Вызывается ``on_start``.
7. Клиент слушает события до закрытия соединения или отмены задачи.

Если ``start()`` запущен отдельной задачей, ``stop()`` штатно закрывает
соединение и завершает эту задачу без ``CancelledError``:

.. code-block:: python

   import asyncio

   task = asyncio.create_task(client.start())
   # ... работа приложения ...
   await client.stop()
   await task

Данные после login
------------------

После успешного login клиент хранит несколько кешей, которые пришли от Max:

``client.me``
   Профиль текущего аккаунта или ``None``, если login еще не завершился.

``client.chats``
   Чаты из login/sync. Это не гарантированно полный список всех чатов.

``client.contacts``
   Контакты из login/sync. Элементы могут быть ``None``, если Max прислал
   неполные данные.

``client.messages``
   Сообщения, которые пришли вместе с login/sync, сгруппированные по ID чата.

Для актуализации используйте явные методы: ``fetch_chats()``, ``get_chat()``,
``get_users()``, ``fetch_users()`` и ``fetch_history()``.

После handshake можно проверить, требует ли Max обновления версии приложения:

.. code-block:: python

   @client.on_start()
   async def on_start(client: Client) -> None:
       if client.is_update_available():
           print("Для выбранной версии приложения доступно обновление")

Создание клиента
----------------

.. code-block:: python

   from pymax import Client, ExtraConfig

   client = Client(
       phone="+79990000000",
       work_dir="cache",
       session_name="account.db",
       extra_config=ExtraConfig(
           log_level="INFO",
           reconnect=True,
           reconnect_delay=3,
       ),
   )

Параметры, которые чаще всего нужны:

``phone``
   Номер телефона для первой авторизации ``Client``.

``work_dir``
   Директория, где PyMax хранит SQLite-файл сессии. Если путь относительный,
   он считается от текущей рабочей директории процесса Python.

``session_name``
   Имя файла сессии внутри ``work_dir``.

``extra_config``
   Настройки соединения, логов, reconnect, token, device/user-agent и sync.

Тип устройства
---------------

``Client`` по умолчанию использует ``DeviceType.ANDROID``. Если нужно
поменять тип устройства, передайте ``device_type`` через ``ExtraConfig``:

.. code-block:: python

   from pymax import Client, ExtraConfig
   from pymax.api.session.enums import DeviceType

   client = Client(
       phone="+79990000000",
       work_dir="cache",
       extra_config=ExtraConfig(device_type=DeviceType.IOS),
   )

Для ``Client`` доступны ``ANDROID``, ``IOS`` и ``DESKTOP``. Практический
нюанс: ``authorize_qr_login()`` подтверждает QR-вход только из mobile-режима,
поэтому для него используйте ``ANDROID`` или ``IOS``. С ``DESKTOP`` этот метод
не работает.

``WebClient`` сам использует ``DeviceType.WEB``. Параметр
``ExtraConfig.device_type`` относится к ``Client`` и не меняет тип устройства
``WebClient``.

Авторизация
-----------

При первом запуске ``Client`` использует ``SmsAuthFlow``. По умолчанию код
запрашивается через консоль. Если на аккаунте включен пароль, можно передать
свой ``password_provider`` или использовать консольный провайдер.

.. code-block:: python

   from pymax import Client, ConsolePasswordProvider

   client = Client(
       phone="+79990000000",
       work_dir="cache",
       password_provider=ConsolePasswordProvider(),
   )

Подробнее про ``SmsCodeProvider``, ``PasswordProvider``, ``QrHandler`` и полный
пользовательский ``AuthFlow`` смотрите в :doc:`auth`.

Если у вас уже есть token, его можно передать через ``ExtraConfig``. Тогда
при отсутствии сохраненной сессии PyMax сохранит этот token и попробует
залогиниться с ним.

.. code-block:: python

   from pymax import Client, ExtraConfig

   client = Client(
       phone="+79990000000",
       work_dir="cache",
       extra_config=ExtraConfig(token="TOKEN"),
   )

Подтверждение QR-входа
----------------------

``Client`` может подтверждать QR-вход по ссылке через
``authorize_qr_login()``. Это полезно, когда QR-ссылку показал другой клиент
или ваш UI получил ее от ``WebClient``:

.. code-block:: python

   async def confirm_qr(client: Client, qr_link: str) -> None:
       ok = await client.authorize_qr_login(qr_link)
       print("QR подтвержден:", ok)

``Client`` для такого подтверждения должен быть уже авторизован. Также
проверьте ``device_type``: используйте ``ANDROID`` или ``IOS``, не
``DESKTOP``.

Если QR создает ``WebClient``, ссылку можно перехватить в своем
``QrHandler`` и подтвердить ее уже запущенным ``Client``:

.. code-block:: python

   from pymax import Client, WebClient


   class ConfirmQrWithClient:
       def __init__(self, client: Client) -> None:
           self.client = client

       async def show_qr(self, qr_url: str) -> None:
           await self.client.authorize_qr_login(qr_url)


   mobile_client = Client(phone="+79990000000", work_dir="cache")
   # mobile_client должен уже пройти start/login в вашей программе.
   web_client = WebClient(
       work_dir="cache",
       session_name="web.db",
       qr_provider=ConfirmQrWithClient(mobile_client),
   )

Сессия и sync-state
-------------------

Сессия хранит:

* token;
* ``device_id``;
* телефон;
* ``mt_instance_id``;
* sync-маркеры ``chats_sync``, ``contacts_sync``, ``drafts_sync``,
  ``presence_sync`` и ``config_hash``.

Файл сессии создается автоматически. При ``work_dir="cache"`` и
``session_name="account.db"`` это будет ``cache/account.db``. Если файл удалить,
PyMax потеряет token и попросит авторизацию снова.

При login PyMax отправляет сохраненные маркеры серверу. Если маркер актуален,
сервер может вернуть только изменения. Поэтому повторный запуск отличается от
первого: первый запуск обычно использует ``-1`` и получает начальный sync,
а последующие запуски продолжают с сохраненного состояния.

Принудительный sync
-------------------

Если нужно попросить Max вернуть больше данных по чатам, можно временно
переопределить sync-маркер:

.. code-block:: python

   from pymax import Client, ExtraConfig, SyncOverrides

   client = Client(
       phone="+79990000000",
       work_dir="cache",
       extra_config=ExtraConfig(
           sync=SyncOverrides(chats_sync=-1),
       ),
   )

Это не удаляет token, но влияет на следующий login. Для полной перезагрузки
сессии можно удалить файл ``work_dir/session_name``; тогда потребуется новая
авторизация.

Повторная авторизация
---------------------

Если нужно сбросить текущую локальную сессию и пройти авторизацию заново,
используйте ``relogin()``:

.. code-block:: python

   await client.relogin()

``relogin()`` удаляет загруженную сессию из store, закрывает текущий runtime и
по умолчанию сразу запускает клиента снова. Если token был передан через
``ExtraConfig(token=...)``, он тоже сбрасывается; это можно отключить через
``drop_config_token=False``.

Reconnect
---------

По умолчанию reconnect включен. Если соединение падает из-за сетевой ошибки,
клиент закрывает текущий runtime, ждет ``reconnect_delay`` секунд, заново
создает соединение и app, затем снова выполняет start/login.

Роутеры после reconnect не теряются: корневой ``Router`` хранится на клиенте,
а новый ``App`` снова получает тот же root router. ``on_start`` вызывается
после каждого успешного reconnect.

Перед повторным подключением можно зарегистрировать ``on_disconnect``:

.. code-block:: python

   @client.on_disconnect()
   async def disconnected(exc: Exception, reconnect: bool, delay: float) -> None:
       print("connection lost:", exc, reconnect, delay)

Отключить reconnect:

.. code-block:: python

   from pymax import Client, ExtraConfig

   client = Client(
       phone="+79990000000",
       extra_config=ExtraConfig(reconnect=False),
   )

Debug-логи
----------

Debug-логи показывают handshake, login, входящие события, API-ошибки,
причины reconnect и детали upload. Начинайте диагностику с них.

.. code-block:: python

   from pymax import Client, ExtraConfig

   client = Client(
       phone="+79990000000",
       extra_config=ExtraConfig(log_level="DEBUG"),
   )

Можно также вызвать ``configure_logging("DEBUG")`` до создания клиента, но
обычно достаточно ``ExtraConfig(log_level="DEBUG")``.

Группы методов клиента
----------------------

Клиент собирает несколько API-направлений:

Сообщения
   ``send_message()``, ``forward_message()``, ``fetch_history()``, ``vote_poll()``,
   ``delete_message()``, ``pin_message()``, ``read_message()``, реакции и
   получение URL для входящих файлов/видео.

Чаты
   ``get_chat()``, ``fetch_chats()``, создание групп, invite-ссылки,
   участники, назначение администраторов, настройки групп, удаление чатов и
   выход из групп/каналов.

Пользователи
   ``get_user()``, ``get_users()``, ``fetch_users()``, ``search_by_phone()``,
   ``add_contact()``, ``remove_contact()``, ``import_contacts()`` и
   ``get_chat_id()``. Подробнее: :doc:`users`.

Аккаунт
   ``change_profile()``, папки чатов, активные сессии, ``logout()`` и
   ``close_all_sessions()``. Подробнее: :doc:`account`.

Auth
   ``set_2fa()``, ``remove_2fa()`` и ``authorize_qr_login()``. Подробнее:
   :doc:`auth`.

Частые ошибки
-------------

``No session available for login``
   Login вызван без сохраненной или новой сессии. Обычно это следствие
   неудачной авторизации.

``Failed to connect and handshake``
   Проверьте сеть, доступность Max, proxy/VPN и настройки ``host``/``port``.

``on_start`` запускает долгую задачу и клиент "зависает"
   Async ``on_start`` запускается как background task. Если внутри бесконечный
   цикл, добавьте ``await asyncio.sleep(...)`` и обрабатывайте отмену.
