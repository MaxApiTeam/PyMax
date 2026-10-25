Stories
=======

Что это
-------

Методы сторис доступны у ``Client`` и ``WebClient``: публикация фото и видео,
лента владельцев, получение отдельных историй, отметка просмотра, реакции и
подробная статистика. Полная история представлена моделью ``Story``, а элемент
ленты и событие обновления — моделью ``StoryPreview``.

Примеры ниже выполняются после запуска клиента, например в ``on_start()``.
Описание моделей находится на странице :doc:`types/story`.

Опубликовать фото или видео
---------------------------

.. code-block:: python

   from pymax import Photo, Video

   photo_story = await client.send_story(
       Photo(path="image.jpg"),
       link="https://example.com/",
   )
   video_story = await client.send_story(
       Video(path="clip.mp4"),
       duration=12_000,
   )
   print(photo_story.id, video_story.id)

``send_story()`` публикует одну историю на 48 часов и возвращает ``Story``.
``link`` необязателен: при его передаче PyMax добавляет ссылку в нижней части
кадра. Настроить срок публикации или положение ссылки через этот метод нельзя.

Для ``Video`` обязательно передайте в ``send_story()`` отдельный аргумент
``duration`` — положительную длительность в миллисекундах. Автоматического
определения длительности для сторис нет; установка extra ``video`` этого не
меняет. Без ``duration`` или при значении ``0`` и меньше метод поднимет
``ValueError`` до загрузки видео.

``Photo`` и ``Video`` принимают ``path``, ``url`` или ``raw``. Для байтов
нужно указать ``name``. Подробнее об источниках данных: :doc:`files`.

Лента и получение историй
-------------------------

``get_stories_feed()`` возвращает пару ``(previews, next_cursor)``.
По умолчанию запрашивается первая страница с ``cursor="0"`` и ``count=15``.
Каждый ``StoryPreview`` описывает владельца и количество его историй, но
не содержит ID отдельных историй. Получите их через ``get_stories()``:

.. code-block:: python

   cursor = "0"
   while True:
       previews, cursor = await client.get_stories_feed(cursor=cursor, count=15)
       for preview in previews:
           owner = preview.owner
           stories = await client.get_stories(
               owner_id=owner.owner_id,
               owner_type=owner.type,
           )
           for story in stories:
               print(owner.owner_id, story.id, story.media)

       if not cursor:
           break

Передавайте возвращенный курсор в следующий запрос. Пустая строка означает
конец ленты. ``owner_id`` — ID владельца, а ``story.id`` — ID конкретной
истории: это разные аргументы API.

``owner_type=0`` означает пользователя и используется по умолчанию. Для
владельца из ленты передавайте ``preview.owner.type`` без изменения.

Если ID историй уже известны, используйте ``get_stories_by_id()``. Ему также
нужны ID и тип владельца:

.. code-block:: python

   stories = await client.get_stories(owner_id=123)
   if stories:
       selected = await client.get_stories_by_id(
           owner_id=123,
           story_ids=[stories[0].id],
           owner_type=0,
       )

Оба метода получения возвращают ``list[Story]``. Если подходящих историй нет,
список пустой.

Отметка просмотра и реакции
---------------------------

Получение истории само по себе не вызывает ``read_story()``. Чтобы отправить
отметку просмотра, передайте ID истории и ее владельца:

.. code-block:: python

   stories = await client.get_stories(owner_id=123)
   if stories:
       story_id = stories[0].id
       await client.read_story(story_id=story_id, owner_id=123)
       added = await client.add_story_reaction(
           owner_id=123,
           story_id=story_id,
           reaction="👍",
       )
       removed = await client.remove_story_reaction(
           owner_id=123,
           story_id=story_id,
       )

``add_story_reaction()`` добавляет или заменяет свою реакцию. По умолчанию
``reaction_type=0`` означает эмодзи; для строкового ID реакции передайте
``reaction_type=1``. ``remove_story_reaction()`` снимает свою реакцию.
Оба метода возвращают булево значение ``success`` из ответа Max.

Для владельца из ленты во все три метода передавайте также
``owner_type=preview.owner.type``. ``read_story()`` возвращает ``True``, если
запрос завершился без API-ошибки; отдельного подтверждения изменения состояния
на сервере метод не проверяет.

Изменить настройки и удалить
----------------------------

``edit_story(story_id, settings)`` меняет настройки опубликованной истории
и возвращает обновленную ``Story``. ``settings`` — числовая битовая маска
в формате Max; именованных флагов для нее в публичном API нет. Метод не
меняет медиа или ссылку.

Удаление принимает ID истории:

.. code-block:: python

   await client.delete_story(story_id=photo_story.id)

``delete_story()`` возвращает ``True``, если запрос завершился без API-ошибки.

Подробная статистика
--------------------

``get_story_detailed_stats()`` возвращает пару ``(stats, next_marker)``.
Выберите фильтр из ``pymax.api.stories``:

* ``StoryStatsFilter.VIEWS`` (``0``) — просмотры;
* ``StoryStatsFilter.REACTIONS`` (``1``) — реакции.

Первая страница запрашивается с ``marker=0``. Возвращенный ненулевой маркер
передайте в следующий запрос; ``0`` означает конец списка:

.. code-block:: python

   from pymax.api.stories import StoryStatsFilter

   marker = 0
   while True:
       stats, marker = await client.get_story_detailed_stats(
           story_id=photo_story.id,
           filter=StoryStatsFilter.VIEWS,
           marker=marker,
       )
       for stat in stats:
           print(stat.user_id, stat.model_extra)

       if marker == 0:
           break

В ``StoryDetailedStats`` типизировано только поле ``user_id``. Дополнительные
поля ответа доступны в ``model_extra`` с исходными именами Max, включая
camelCase. Например, ``reaction``, если оно пришло, сохраняется как исходный
словарь, а не отдельная типизированная модель. Аналогично счетчики просмотров
и реакций не объявлены полями ``Story``: проверяйте дополнительные данные
конкретного ответа, если они нужны.

Обновления сторис
-----------------

``on_story_update()`` передает в обработчик ``StoryPreview`` владельца,
а не отдельную ``Story``. Чтобы получить сами истории после обновления,
запросите их по ``preview.owner``:

.. code-block:: python

   from pymax import Client, StoryPreview

   @client.on_story_update()
   async def on_story_update(preview: StoryPreview, client: Client) -> None:
       owner = preview.owner
       stories = await client.get_stories(
           owner_id=owner.owner_id,
           owner_type=owner.type,
       )
       print(owner.owner_id, [story.id for story in stories])

Такой же декоратор доступен у ``Router``.

Методы клиента
--------------

Полные сигнатуры методов доступны в API reference для
:doc:`api/client-client` и :doc:`api/client-web`.
