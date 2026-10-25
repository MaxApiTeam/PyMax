Getting Started
===============

Что это
-------

PyMax - это async-клиент для Max API. Обычный сценарий выглядит так:
создать клиента, один раз пройти авторизацию, повесить обработчики и
запустить бесконечный цикл получения событий.

Установка
---------

Требуется Python 3.10 или новее.

.. code-block:: bash

   pip install -U maxapi-python

или через uv:

.. code-block:: bash

   uv add -U maxapi-python

Первый клиент
-------------

``Client`` авторизуется по номеру телефона и SMS-коду. При первом запуске
PyMax спросит код в консоли и сохранит сессию в SQLite-файл. При следующих
запусках этот файл используется автоматически.

.. code-block:: python

   import asyncio

   from pymax import Client, Message
   from pymax.filters import Command

   client = Client(
       phone="+79990000000",
       work_dir="cache",
       session_name="main.db",
   )


   @client.on_start()
   async def on_start(client: Client) -> None:
       print("Запущен:", client.me.contact.id if client.me else "unknown")
       print("Чатов в первом sync:", len(client.chats or []))


   @client.on_message(Command("start"))
   async def on_message(message: Message, client: Client) -> None:
       print(message.chat_id, message.sender, message.text)

       if message.chat_id is not None:
           await message.answer("Привет от PyMax")


   async def main() -> None:
       await client.start()


   if __name__ == "__main__":
       asyncio.run(main())

Отправьте ``/start``, чтобы вызвать обработчик. О собственных фильтрах и
объединении условий читайте в :doc:`router`.

Что происходит при запуске
--------------------------

1. PyMax подготавливает конфигурацию и загружает сохраненную сессию.
2. ``Client`` открывает TCP-соединение с Max.
3. Выполняется handshake с ``device_id`` из сессии или конфигурации.
4. Если сессии нет, запускается авторизация.
5. Клиент делает login и получает профиль, список чатов и sync-state.
6. Вызываются ``on_start``-обработчики.
7. Клиент слушает входящие события, пока соединение не закрыто.

Повторный запуск
----------------

Повторный запуск обычно не требует SMS-кода: token, ``device_id`` и sync-state
берутся из файла сессии. Если удалить ``work_dir`` или сам ``session_name``,
PyMax потеряет token и устройство, поэтому авторизацию придется пройти заново.

``work_dir`` - это директория для служебных файлов PyMax. Сейчас в ней хранится
SQLite-сессия. Например, при ``work_dir="cache"`` и
``session_name="main.db"`` файл будет ``cache/main.db``.

WebClient и QR
--------------

``WebClient`` использует WebSocket и QR-авторизацию. Он удобен, если нужно
подключаться как web-клиент.

.. code-block:: python

   import asyncio

   from pymax import WebClient

   client = WebClient(work_dir="cache", session_name="web.db")


   @client.on_start()
   async def on_start(client: WebClient) -> None:
       print("Web-клиент запущен")


   async def main() -> None:
       await client.start()


   asyncio.run(main())

Частые ошибки
-------------

``TypeError: handler() takes 1 positional argument but 2 were given``
   Обработчик сообщения должен принимать ``(event, client)``.

``client.chats`` пустой или содержит мало чатов
   Первый login возвращает только то, что отдал sync Max. Для полной подгрузки
   используйте ``fetch_chats()`` или сбросьте sync-маркер чатов, если нужно.

Снова спрашивает SMS
   Проверьте, что не удален ``work_dir/session_name`` и что приложение
   запускается из ожидаемой рабочей директории.
