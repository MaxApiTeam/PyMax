Router
======

Что это
-------

Роутер хранит обработчики. Когда приходит новое событие, PyMax определяет его
тип, проверяет фильтры и вызывает подходящие handler-ы.

Зачем нужен
-----------

Можно писать обработчики прямо на клиенте:

.. code-block:: python

   from pymax import Client, Message

   client = Client(phone="+79990000000", work_dir="cache")


   @client.on_message()
   async def any_message(message: Message, client: Client) -> None:
       print(message.text)

А можно разнести логику по роутерам:

.. code-block:: python

   from pymax import Client, ClientRouter, Message
   from pymax.filters import Command

   router = ClientRouter()


   @router.on_message(Command("start"))
   async def start_command(message: Message, client: Client) -> None:
       await message.answer("Готово")


   client = Client(phone="+79990000000", work_dir="cache")
   client.include_router(router)

``Router``, ``ClientRouter`` и ``WebRouter``
--------------------------------------------

В PyMax есть один настоящий класс роутера: ``Router``. В
``src/pymax/routers.py`` дополнительно объявлены два alias-а типов:

.. code-block:: python

   ClientRouter = Router[Client]
   WebRouter = Router[WebClient]

Это не отдельные реализации и не разные режимы dispatch. Alias нужен, чтобы
подсказки типов понимали, какой клиент придет вторым аргументом handler-а.

Для ``Client`` можно писать так:

.. code-block:: python

   from pymax import Client, ClientRouter, Message

   router = ClientRouter()


   @router.on_message()
   async def handle(message: Message, client: Client) -> None:
       await message.answer("ok")

Для ``WebClient`` аналогично:

.. code-block:: python

   from pymax import Message, WebClient, WebRouter

   router = WebRouter()


   @router.on_message()
   async def handle(message: Message, client: WebClient) -> None:
       await message.answer("ok")

Корневой и вложенные роутеры
----------------------------

Root router
   Внутренний роутер клиента. Декораторы ``client.on_message()`` и
   ``client.on_start()`` регистрируют обработчики именно в нем. Его не нужно
   создавать руками.

Подключаемый router
   Отдельный ``Router``/``ClientRouter``/``WebRouter``, который вы создаете
   сами и подключаете через ``client.include_router(router)``.

Вложенный router
   Router, подключенный к другому router через ``router.include_router(child)``.
   Dispatch проходит по root router, затем по подключенным роутерам и их детям.

В каждом роутере обработчики одного типа события проверяются в порядке
регистрации. После первого подходящего обработчика остальные обработчики
этого типа в том же роутере пропускаются. Затем событие передается дочерним
роутерам: обработчик в родительском роутере не останавливает их обход.
Обработчик без фильтров подходит всегда, поэтому общий fallback регистрируйте
после более конкретных обработчиков.

Фильтры
-------

Фильтры наследуются от ``pymax.filters.Filter``. Их ``__call__`` получает
``event`` и ``client`` и возвращает ``bool`` или awaitable с результатом
``bool``. Для обычных проверок доступны готовые фильтры:

* ``Command("start")`` — команда ``/start``, в том числе с аргументами;
* ``Reply()`` и ``Forwarded()`` — ответ и пересланное сообщение;
* ``FromMe()`` — сообщение текущего пользователя;
* ``HasAttachment(PhotoAttachment)`` — наличие вложения указанного типа
  из ``pymax.types``. Можно передать несколько типов.

У ``Command`` можно задать другой префикс, например
``Command("start", prefix="!")`` или ``prefix=("/", "!")``.

Свой фильтр:

.. code-block:: python

   from pymax import Client, ClientRouter, Message
   from pymax.filters import Filter

   router = ClientRouter()


   class HasText(Filter[Message, Client]):
       def __call__(self, message: Message, client: Client) -> bool:
           return bool(message.text)


   @router.on_message(HasText())
   async def handle(message: Message, client: Client) -> None:
       await message.answer("Текст получил")

Метод ``__call__`` также может быть ``async def``. Обычную функцию вместо
экземпляра ``Filter`` передавать не нужно.

Несколько фильтров в декораторе работают как AND: все должны вернуть ``True``.
При первом ``False`` проверка этого обработчика прекращается. Фильтры можно
объединять операторами ``&`` (AND), ``|`` (OR) и ``~`` (NOT):

.. code-block:: python

   from pymax.filters import Command, FromMe, Reply

   @router.on_message((Command("start") | Command("help")) & ~FromMe(), Reply())
   async def command_reply(message: Message, client: Client) -> None:
       await message.answer("Команда в ответе")

Magic-фильтры
~~~~~~~~~~~~~

``F`` из ``pymax.filters`` строит проверки полей ``Message`` и ``Chat``:

.. code-block:: python

   from pymax.filters import F

   @router.on_message((F.message.sender == 123456) & F.message.text.contains("привет"))
   async def greeting(message: Message, client: Client) -> None:
       await message.answer("Привет")

Сравнения при объединении берите в скобки. Используйте ``&``, ``|`` и ``~``,
а не Python-операторы ``and``, ``or`` и ``not``.

Ссылка на поле без сравнения проверяет его истинность, например
``F.message.text`` — непустой текст. Для текстовых полей доступны
``contains()``, ``startswith()`` и ``endswith()`` с параметром
``ignore_case=True``; для числовых — сравнения и ``between(minimum, maximum)``.
``is_none()`` проверяет ``None``, ``is_empty()`` — пустой список:

.. code-block:: python

   no_attachments = F.message.attaches.is_empty()
   unknown_sender = F.message.sender.is_none()
   private_chat = F.chat.type == "DIALOG"

Фильтр проверяет и тип события: ``F.message`` применяется к ``Message``,
``F.chat`` — к ``Chat``. Например, ``F.chat.last_message.text`` проверяет
текст последнего сообщения чата.

Dispatcher сам ожидает async-результат. При ручном вызове составного фильтра
тоже нужен ``await``:

.. code-block:: python

   text_from_sender = (F.message.sender == 123456) & F.message.text
   matched = await text_from_sender(message, client)

Middleware
----------

``client.add_middleware()`` добавляет middleware в общую цепочку обработчиков
клиента, включая подключенные роутеры. Регистрировать middleware можно до
``connect()`` или ``start()``; регистрация сохраняется при reconnect.

.. code-block:: python

   from typing import Any

   from pymax import Client
   from pymax.dispatch import DispatchEvent, Middleware, MiddlewareNext

   client = Client(phone="+79990000000")


   class LoggingMiddleware(Middleware[Client]):
       async def __call__(
           self,
           client: Client,
           event: DispatchEvent,
           call_next: MiddlewareNext,
       ) -> Any:
           print(type(event).__name__)
           return await call_next(event)


   client.add_middleware(LoggingMiddleware())

Middleware выполняются после фильтров, перед подходящим handler-ом. Первое
зарегистрированное middleware входит первым, а выходит последним. Чтобы
продолжить цепочку, вызовите ``await call_next(event)``. Внутренние обработчики
готовности загрузок выполняются отдельно и через пользовательскую цепочку
не проходят.

Middleware оборачивает каждый выбранный обработчик. Если событие подходит
обработчикам в нескольких роутерах, цепочка вызывается для каждого из них.
Если middleware не вызывает ``call_next``, оставшаяся цепочка и выбранный
обработчик не запускаются.

Почему handler принимает event и client
---------------------------------------

Первые два аргумента handler-а всегда ``event`` и ``client``. Это сделано, чтобы
один и тот же router можно было подключить к разным клиентам, а внутри handler
всегда был доступ к API-методам клиента.

.. code-block:: python

   from pymax import Client, Message

   @client.on_message()
   async def on_message(message: Message, client: Client) -> None:
       await message.answer("ok")

Handler может быть синхронным или асинхронным. Дополнительные обязательные
параметры разрешаются по аннотации типа: встроенный ``FSMContext`` описан
в :doc:`fsm`, подключение зависимостей через Dishka — в :doc:`di`.
У ``on_start``, ``on_error`` и ``on_disconnect`` свои сигнатуры, показанные ниже.

``on_start``
------------

``on_start`` вызывается после успешного подключения, авторизации и login,
когда уже доступны ``client.me`` и ``client.chats``.

.. code-block:: python

   from pymax import Client

   @client.on_start()
   async def started(client: Client) -> None:
       print(client.me)

Если включен reconnect, ``on_start`` будет вызван после каждого успешного
переподключения. На одном клиенте или роутере можно зарегистрировать несколько
``on_start``-обработчиков; PyMax запустит каждый из них.

Ошибки handler-ов
-----------------

``on_error`` получает ошибки из фильтров, middleware, обработчиков событий
и ``on_start``. Ошибки распознавания и преобразования входящего frame-а
в типизированное событие возникают до этой границы обработки.

.. code-block:: python

   from pymax import Client, ClientRouter
   from pymax.dispatch import ErrorContext, ErrorScope

   client = Client(phone="+79990000000", work_dir="cache")


   @client.on_error(scope=ErrorScope.GLOBAL)
   async def on_err(e: Exception, ctx: ErrorContext[Client]) -> None:
       print(ctx.event_type, ctx.router, e)


   router = ClientRouter()


   @router.on_error(scope=ErrorScope.LOCAL)
   async def router_error(e: Exception, ctx: ErrorContext[Client]) -> None:
       print("router failed:", e)


   client.include_router(router)

``ErrorScope.GLOBAL`` получает ошибки из всего дерева подключенных роутеров.
``ErrorScope.LOCAL`` получает только ошибки того router-а, на котором
зарегистрирован error-handler.

PyMax вызывает все подходящие error-handler-ы в порядке обхода роутеров.
Если они завершились успешно, исходная ошибка считается обработанной.
Если ни одного error-handler-а нет или один из них сам упал, исходная ошибка
продолжит распространяться.

Отключение
----------

``on_disconnect`` вызывается при сетевой ошибке перед reconnect или перед
пробросом ошибки, если reconnect отключен.

.. code-block:: python

   @client.on_disconnect()
   async def disconnected(exc: Exception, reconnect: bool, delay: float) -> None:
       print(exc, reconnect, delay)

Raw events
----------

``on_raw`` получает исходный ``InboundFrame`` для каждого входящего frame-а,
переданного в dispatch. Он вызывается после типизированной обработки, в том
числе когда тип события неизвестен или его распознавание, преобразование либо
обработка завершились ошибкой.

.. code-block:: python

   from pymax import Client
   from pymax.protocol import InboundFrame

   @client.on_raw()
   async def raw(frame: InboundFrame, client: Client) -> None:
       print(frame.opcode, frame.payload)

Другие события
--------------

Декоратор определяет тип первого аргумента handler-а:

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Декоратор
     - Событие
   * - ``on_message()``, ``on_message_edit()``
     - ``Message``
   * - ``on_message_delete()``
     - ``MessageDeleteEvent``
   * - ``on_message_read()``
     - ``MessageReadEvent``
   * - ``on_typing()``
     - ``TypingEvent``
   * - ``on_presence()``
     - ``PresenceEvent``
   * - ``on_reaction_update()``
     - ``ReactionUpdateEvent``
   * - ``on_chat_update()``
     - ``Chat``
   * - ``on_story_update()``
     - ``StoryPreview``
   * - ``on_raw()``
     - ``InboundFrame``

Все они принимают экземпляры ``Filter`` и используют первые два аргумента
``handler(event, client)``. ``on_reaction_update()`` получает как обновления
счетчиков реакций, так и уведомления о реакции текущего пользователя
(opcode 155 и 156). ``on_story_update()`` получает сводное превью сторис
владельца, а не отдельную ``Story``.

Частые ошибки
-------------

Забыли скобки у декоратора
   Нужно писать ``@client.on_message()``, а не ``@client.on_message``.

Handler принимает один аргумент
   Используйте ``async def handler(message: Message, client: Client) -> None: ...``.

Фильтр падает с ошибкой
   Handler не будет вызван. Ошибка передается подходящим ``on_error``;
   без них она продолжает распространяться.
