Files
=====

Что это
-------

Для отправки вложений PyMax использует пять основных классов:

``Photo``
   Фото. Проверяет расширение и MIME-тип.

``Video``
   Видео. Загружается чанками и ждет событие готовности от Max.

``File``
   Обычный файл. Тоже загружается чанками и ждет событие готовности.

``Voice``
   Голосовое сообщение в формате OGG.

``VideoNote``
   Круглое видеосообщение. Можно передать длительность вручную или установить
   extra ``video`` для автоматического определения.

Как отправить файл
------------------

.. code-block:: python

   import asyncio

   from pymax import Client, File, Photo, Video, VideoNote, Voice

   client = Client(phone="+79990000000", work_dir="cache")


   @client.on_start()
   async def send_files(client: Client) -> None:
       chat = await client.get_chat(123456)

       await chat.answer(
           text="Фото",
           attachments=[Photo(path="image.jpg")],
       )

       await chat.answer(
           text="Документ",
           attachments=[File(path="report.pdf")],
       )

       await chat.answer(
           text="Видео",
           attachments=[Video(path="clip.mp4")],
       )

       await chat.answer(attachments=[Voice(path="voice.ogg")])
       await chat.answer(
           attachments=[VideoNote(path="circle.mp4", duration=4200)]
       )


   asyncio.run(client.start())

Источники данных
----------------

Можно передать ровно один источник:

.. code-block:: python

   Photo(path="image.jpg")
   File(url="https://example.com/report.pdf")
   Video(raw=b"...", name="clip.mp4")
   Voice(path="voice.ogg")
   VideoNote(path="circle.mp4", duration=4200)

Для ``raw`` обязательно указывайте ``name``. Для ``File``, ``Video``,
``Voice`` и ``VideoNote`` имя берется из ``path`` или ``url``, если не
передано явно.

Если длительность ``VideoNote`` не передана, установите дополнительную
зависимость:

.. code-block:: console

   uv add "maxapi-python[video]"

Как работает upload
-------------------

1. PyMax запрашивает у Max временный upload URL.
2. Читает файл из ``path``, ``url`` или ``raw``.
3. Загружает данные HTTP-запросом.
4. Для ``File``, ``Video``, ``Voice`` и ``VideoNote`` ждет служебное событие
   готовности до 60 секунд.
5. Подставляет token/file_id/video_id в отправляемое сообщение.

Фото проходит проще: после HTTP-upload PyMax сразу достает token из ответа.

Скачать входящий файл
---------------------

``FileAttachment`` содержит ID, но для скачивания нужен временный URL:

.. code-block:: python

   from pymax import Client, Message
   from pymax.types.domain import FileAttachment

   @client.on_message()
   async def on_message(message: Message, client: Client) -> None:
       if message.chat_id is None:
           return

       for attach in message.attaches:
           if isinstance(attach, FileAttachment):
               info = await client.get_file_by_id(
                   chat_id=message.chat_id,
                   message_id=message.id,
                   file_id=attach.file_id,
               )
               print(info.url if info else "URL не получен")

Частые ошибки
-------------

``ValueError: Only one of raw, url or path must be provided``
   Передайте только один источник файла.

``ValueError: Name must be provided for raw data``
   Для bytes укажите имя: ``File(raw=data, name="file.bin")``.

``Invalid photo extension``
   ``Photo`` принимает ``.jpg``, ``.jpeg``, ``.png``, ``.gif``, ``.webp`` и
   ``.bmp``.

``UploadError``
   Upload-сервис не получил нужный ответ от Max. Включите ``DEBUG``-логи:
   часто причина в недоступном URL, неверном размере файла, timeout или в том,
   что событие готовности файла не пришло за 60 секунд.

``Automatic video duration detection requires the 'video' extra``
   Передайте ``duration`` в миллисекундах или установите
   ``maxapi-python[video]``.
