Story
=====

``Story`` содержит отдельную историю. ``StoryPreview`` содержит сводку по
владельцу в ленте или событии ``on_story_update()``; ID отдельных историй
нужно получать через ``get_stories()``. Примеры работы: :doc:`../stories`.

.. autoclass:: pymax.types.domain.story.Story
   :members:
   :show-inheritance:

StoryMedia
----------

``StoryMedia`` — объединение ``StoryPhotoMedia`` и ``StoryVideoMedia``.
PyMax выбирает модель по полю ``type``, которому во входящих данных
соответствует ``_type``. Эти модели описывают полученное медиа: поля
``photoToken`` и ``token`` для их создания не обязательны.

.. autoclass:: pymax.types.domain.story.StoryPhotoMedia
   :members:
   :show-inheritance:

.. autoclass:: pymax.types.domain.story.StoryVideoMedia
   :members:
   :show-inheritance:

Слои
----

.. autoclass:: pymax.types.domain.story.StoryLayer
   :members:
   :show-inheritance:

.. autoclass:: pymax.types.domain.story.StoryCoordinates
   :members:
   :show-inheritance:

.. autoclass:: pymax.types.domain.story.StoryClickableLink
   :members:
   :show-inheritance:

Владелец и превью
-----------------

.. autoclass:: pymax.types.domain.story.StoryOwner
   :members:
   :show-inheritance:

.. autoclass:: pymax.types.domain.story.StoryPreview
   :members:
   :show-inheritance:

Статистика
----------

.. autoclass:: pymax.types.domain.story.StoryDetailedStats
   :members:
   :show-inheritance:

.. autoclass:: pymax.api.stories.StoryStatsFilter
   :members:
