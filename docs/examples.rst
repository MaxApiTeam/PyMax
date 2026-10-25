Examples
========

Минимальный echo-клиент
-----------------------

.. code-block:: python

   import asyncio

   from pymax import Client, Message
   from pymax.filters import FromMe

   client = Client(phone="+79990000000", work_dir="cache")


   @client.on_message(~FromMe())
   async def echo(message: Message, client: Client) -> None:
       if message.chat_id is None or not message.text:
           return

       await message.answer(f"Вы написали: {message.text}")


   asyncio.run(client.start())

Команды через фильтры
---------------------

.. code-block:: python

   from pymax import Client, ClientRouter, Message
   from pymax.filters import Command

   router = ClientRouter()


   @router.on_message(Command("start"))
   async def start(message: Message, client: Client) -> None:
       await message.answer("Привет")


   @router.on_message(Command("me"))
   async def me(message: Message, client: Client) -> None:
       if client.me:
           await message.answer(f"Ваш ID: {client.me.contact.id}")


   client = Client(phone="+79990000000", work_dir="cache")
   client.include_router(router)

Отправка фото и файла
---------------------

.. code-block:: python

   import asyncio

   from pymax import Client, File, Photo

   client = Client(phone="+79990000000", work_dir="cache")


   @client.on_start()
   async def send_files(client: Client) -> None:
       chat = await client.get_chat(123456)
       await chat.answer(
           text="Материалы",
           attachments=[
               Photo(path="image.jpg"),
               File(path="report.pdf"),
           ],
       )


   asyncio.run(client.start())

Пользователь по телефону
------------------------

.. code-block:: python

   from pymax import Client, Message

   @client.on_message()
   async def find_contact(message: Message, client: Client) -> None:
       if message.text == "/find":
           contact = await client.search_by_phone("+79990000000")
           await message.answer(f"ID: {contact.id}")

Папки чатов
-----------

.. code-block:: python

   from pymax import Client

   @client.on_start()
   async def setup_folder(client: Client) -> None:
       update = await client.create_folder("Работа", [123456])
       print(update.folder_sync)

2FA
---

.. code-block:: python

   from pymax import Client

   @client.on_start()
   async def enable_2fa(client: Client) -> None:
       await client.set_2fa(
           password="strong-password",
           hint="мой пароль",
       )

Загрузка истории при старте
---------------------------

.. code-block:: python

   from pymax import Client, Message

   @client.on_start()
   async def load_history(client: Client) -> None:
       messages = await client.fetch_history(
           chat_id=123456,
           backward=20,
       )
       for message in messages or []:
           print(message.id, message.text)

Raw payload для диагностики
---------------------------

.. code-block:: python

   from pymax import Client
   from pymax.protocol import InboundFrame

   @client.on_raw()
   async def raw(frame: InboundFrame, client: Client) -> None:
       print("opcode:", frame.opcode)
       print("payload:", frame.payload)
