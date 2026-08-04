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
   Голосовое сообщение. Поддерживается только формат OGG; PyMax не
   конвертирует другие аудиоформаты.

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

Формат Voice и VideoNote
------------------------

Для ``Voice`` используйте готовый OGG-файл. Простого переименования MP3, WAV
или другого аудиофайла в ``.ogg`` недостаточно: PyMax загружает исходные байты
без перекодирования.

``VideoNote`` также не перекодирует видео. Для совместимости с официальным
клиентом 26.21.1 рекомендуется следующий формат:

* контейнер MP4;
* видео H.264/AVC, 480x480, 30 FPS и bitrate около 1 024 000 bit/s;
* pixel format ``yuv420p`` при подготовке через FFmpeg;
* ключевой кадр примерно раз в секунду, то есть GOP около 30 кадров;
* аудио AAC в том же MP4-контейнере;
* длительность до 60 секунд.

Официальный клиент задает квадратное разрешение, фиксированные 30 FPS и
максимальную длительность через server config. Нижняя граница в одну секунду
не является подтвержденным ограничением upload API, поэтому PyMax ее не
проверяет.

Поворот лучше физически применить при перекодировании и убрать rotation
metadata: так файл меньше зависит от того, как конкретный клиент обработает
orientation hint. H.264 profile и level специально фиксировать не требуется.
``faststart`` официальный recorder явно не включает; при самостоятельной
подготовке файла его можно использовать, но для PyMax это не обязательное
условие.

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
