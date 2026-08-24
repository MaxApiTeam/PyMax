Auth
====

Что это
-------

Auth-flow - это объект, который получает доступ к низкоуровневому ``App`` и
возвращает token для новой сессии. Обычно писать свой полный flow не нужно:
достаточно заменить provider, который получает SMS-код, пароль 2FA или
показывает QR.

Как работает стандартная авторизация
------------------------------------

``Client`` использует ``SmsAuthFlow``:

1. запрашивает SMS-код у Max;
2. просит код у ``SmsCodeProvider``;
3. отправляет код в Max;
4. если Max требует пароль, просит его у ``PasswordProvider``;
5. возвращает token, который PyMax сохраняет в ``work_dir/session_name``.

``WebClient`` использует ``QrAuthFlow``:

1. запрашивает QR-ссылку;
2. передает ссылку в ``QrHandler``;
3. опрашивает Max до подтверждения или истечения QR;
4. подтверждает QR и сохраняет token.

Кастомный SMS provider
----------------------

Provider нужен, когда код приходит не из консоли: например, из UI, очереди,
секретного хранилища или тестового стенда.

.. code-block:: python

   import asyncio

   from pymax import Client


   class MemorySmsCodeProvider:
       def __init__(self) -> None:
           self._queue = asyncio.Queue[str]()

       async def set_code(self, code: str) -> None:
           await self._queue.put(code)

       async def get_code(self, phone: str) -> str:
           return await self._queue.get()


   sms_provider = MemorySmsCodeProvider()
   client = Client(
       phone="+79990000000",
       work_dir="cache",
       sms_code_provider=sms_provider,
   )

Метод ``get_code`` должен вернуть строку с кодом. Если он зависнет, зависнет и
первичная авторизация.

Кастомный 2FA password provider
-------------------------------

``PasswordProvider`` вызывается только если Max сообщил, что аккаунту нужен
дополнительный пароль.

.. code-block:: python

   import os

   from pymax import Client


   class EnvPasswordProvider:
       async def get_password(self, hint: str | None = None) -> str:
           return os.environ["MAX_2FA_PASSWORD"]


   client = Client(
       phone="+79990000000",
       work_dir="cache",
       password_provider=EnvPasswordProvider(),
   )

Если provider вернет пустую строку или Max отклонит пароль, ``SmsAuthFlow``
попросит пароль снова.

Количество попыток можно ограничить через ``ExtraConfig``:

.. code-block:: python

   from pymax import Client, ExtraConfig, PasswordAttemptsExceededError

   client = Client(
       phone="+79990000000",
       password_provider=EnvPasswordProvider(),
       extra_config=ExtraConfig(password_max_attempts=3),
   )

   try:
       await client.connect()
   except PasswordAttemptsExceededError:
       print("Пароль 2FA не принят")

``password_max_attempts=None`` означает неограниченное число попыток и
сохраняет прежнее поведение. Пустой пароль, ``ApiError``, ошибка в ответе Max
и ответ без login token расходуют одну попытку. При ``0`` или отрицательном
значении provider не вызывается, а ``PasswordAttemptsExceededError``
возникает сразу. Исключение наследуется напрямую от ``Exception``, поэтому
его нужно перехватывать отдельно от ``PyMaxError``.

Кастомный QR handler
--------------------

Обычно ``QrHandler`` не подтверждает QR сам. Его задача - показать ссылку
пользователю: вывести в терминал, отправить в web UI или положить в лог.

.. code-block:: python

   from pymax import WebClient


   class PrintQrUrl:
       async def show_qr(self, qr_url: str) -> None:
           print("Откройте QR:", qr_url)


   client = WebClient(
       work_dir="cache",
       session_name="web.db",
       qr_provider=PrintQrUrl(),
   )

Если у вас уже есть запущенный и авторизованный ``Client``, QR-ссылку можно
подтвердить программно через ``authorize_qr_login()``. Это удобно, когда
``WebClient`` получает QR, а основной mobile-клиент должен разрешить вход:

.. code-block:: python

   from pymax import Client, WebClient


   class ConfirmQrWithClient:
       def __init__(self, client: Client) -> None:
           self.client = client

       async def show_qr(self, qr_url: str) -> None:
           await self.client.authorize_qr_login(qr_url)


   mobile_client = Client(phone="+79990000000", work_dir="cache")
   # mobile_client должен уже пройти start/login в вашей программе.
   web_client = WebClient(qr_provider=ConfirmQrWithClient(mobile_client))

``mobile_client`` должен быть уже авторизован к моменту вызова
``show_qr()``. Для такого подтверждения используйте ``Client`` с
``device_type`` ``ANDROID`` или ``IOS``; при ``DESKTOP`` метод
``authorize_qr_login()`` не работает. ``WebClient`` в штатной конфигурации
всегда использует ``WEB``.

Полный кастомный AuthFlow
-------------------------

Полный ``AuthFlow`` нужен редко: например, если вы хотите получить token из
внешней системы, реализовать нестандартную авторизацию или полностью заменить
SMS/QR-сценарий.

Flow должен иметь async-метод ``authenticate(app)`` и вернуть ``AuthResult``.
``app`` - внутренний runtime PyMax; через него доступны низкоуровневые
``app.api.auth.*`` методы. Это advanced API, поэтому старайтесь сначала
решить задачу через provider-ы.

.. code-block:: python

   from pymax import Client
   from pymax.app import App
   from pymax.auth.models import AuthResult


   class StaticTokenFlow:
       def __init__(self, token: str) -> None:
           self.token = token

       async def authenticate(self, app: App) -> AuthResult:
           return AuthResult(token=self.token)


   client = Client(
       phone="+79990000000",
       work_dir="cache",
       auth_flow=StaticTokenFlow("TOKEN"),
   )

Если вам нужно только передать готовый token, проще использовать
``ExtraConfig(token="TOKEN")``. Тогда custom flow не нужен.

Регистрация нового аккаунта
---------------------------

Если номер ещё не зарегистрирован в Max, после SMS-кода сервер возвращает
токен регистрации. Чтобы стандартный ``SmsAuthFlow`` завершил создание
аккаунта, передайте имя через ``RegistrationConfig``:

.. code-block:: python

   from pymax import Client, ExtraConfig, RegistrationConfig

   client = Client(
       phone="+79990000000",
       extra_config=ExtraConfig(
           registration_config=RegistrationConfig(
               first_name="Max",
               last_name="User",
           )
       ),
   )

Для уже существующего аккаунта эта настройка не используется. Если Max
вернул токен регистрации, а ``registration_config`` не задан, авторизация
завершится с ``RuntimeError``.

Управление 2FA
--------------

После авторизации можно установить или удалить пароль 2FA текущего аккаунта.
Методы доступны на ``Client`` и ``WebClient``:

.. code-block:: python

   await client.set_2fa(
       password="strong-password",
       hint="мой пароль",
   )

   await client.remove_2fa(password="strong-password")

``set_2fa()`` сначала создает auth-track, затем проверяет пароль, при
необходимости привязывает email и подсказку, после чего включает 2FA.
``remove_2fa()`` создает auth-track, проверяет текущий пароль и отключает 2FA.

Если нужно привязать email, передайте ``email``. Max отправит код на почту.
Без ``email_code_provider`` PyMax запросит код в консоли:

.. code-block:: python

   await client.set_2fa(
       password="strong-password",
       email="user@example.com",
       hint="мой пароль",
   )

Для UI, очереди или тестового стенда можно передать собственный provider:

.. code-block:: python

   import asyncio

   from pymax.auth import EmailCodeProvider


   class QueueEmailCodeProvider:
       def __init__(self) -> None:
           self._queue = asyncio.Queue[str]()

       async def set_code(self, code: str) -> None:
           await self._queue.put(code)

       async def get_code(self, email: str) -> str:
           return await self._queue.get()


   provider: EmailCodeProvider = QueueEmailCodeProvider()

   await client.set_2fa(
       password="strong-password",
       email="user@example.com",
       email_code_provider=provider,
   )

``email`` и ``hint`` отличаются от ``None``-полей в обычных моделях: если
параметр не передан, PyMax не трогает соответствующую часть настройки 2FA.
Передавайте строку только для тех частей, которые хотите установить.

Частые ошибки
-------------

Provider не вызывается
   Сессия уже есть в ``work_dir/session_name``. Provider нужен только при
   новой авторизации.

Снова спрашивает SMS
   Потерян файл сессии или запускается другой ``work_dir``.

QR истек
   ``QrAuthFlow`` ждет подтверждения до ``expires_at`` от сервера. Запустите
   клиент заново и покажите новый QR.

Полный AuthFlow ломается после обновления PyMax
   Это возможно: полный flow использует внутренний ``App``. Provider-ы
   стабильнее и безопаснее для обычного кода.

2FA email-код не запрашивается
   ``email_code_provider`` используется только если вы передали ``email`` в
   ``set_2fa()``.
