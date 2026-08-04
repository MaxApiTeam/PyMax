Types
=====

Что это
-------

Типы PyMax - это Pydantic-модели для данных Max: сообщения, чаты, контакты,
профиль, папки, вложения и sync-state. Обычно вы не создаете их вручную:
клиент возвращает уже готовые объекты.

Зачем нужны
-----------

Типы помогают писать понятный код:

.. code-block:: python

   from pymax import Client, Message
   from pymax.types.domain import PhotoAttachment

   async def handler(message: Message, client: Client) -> None:
       for attach in message.attaches:
           if isinstance(attach, PhotoAttachment):
               print(attach.photo_id, attach.base_url)

Главные типы
------------

``Message``
   Сообщение Max. Может отвечать, отправлять reply, ставить реакции,
   закрепляться, удаляться и отмечаться прочитанным.

``Chat``
   Диалог, группа или канал. Может отправлять сообщения, загружать историю,
   приглашать пользователей, выходить из группы/канала и менять настройки.

``User`` и ``Profile``
   Пользователи и профиль текущего аккаунта.

``ContactInfo``
   Контакт телефонной книги для ``import_contacts()``.

``PhotoAttachment``, ``VideoAttachment``, ``FileAttachment``, ``PollAttachment`` и другие
   Входящие вложения в ``message.attaches``.

``SyncState`` и ``SyncOverrides``
   Состояние синхронизации login. Пользователь чаще работает только с
   ``SyncOverrides`` через ``ExtraConfig``.

Почему поля бывают None
-----------------------

Max не всегда присылает полный объект. Например, событие редактирования,
удаления или служебное событие может содержать только часть полей. Поэтому
многие поля описаны как ``None``-able. Это нормально: проверяйте поле перед
использованием.

Bound и unbound объекты
-----------------------

Сообщения и чаты, которые пришли из ``Client`` или ``WebClient``, уже связаны
с клиентом. Поэтому у них работают удобные методы:

.. code-block:: python

   await message.answer("ok")
   await chat.answer("ok")

Если вы создали ``Message`` или ``Chat`` вручную через Pydantic, это просто
данные. Такой объект не знает, каким клиентом отправлять сообщения или менять
чат, поэтому методы действий могут завершиться ошибкой. В обычном коде не
нужно вручную привязывать объекты: берите их из handler-ов, ``get_chat()``,
``fetch_chats()`` или ``fetch_history()``.

Pydantic validation error
-------------------------

Вложения распознаются по discriminator-полю ``_type``. Если Max прислал новый
тип или неполный payload, Pydantic может выбросить validation error. Для
диагностики включите ``DEBUG`` и посмотрите ``on_raw``.

API reference
-------------

.. toctree::
   :maxdepth: 1

   chat
   message
   message_delete_event
   message_read_event
   typing_event
   presence_event
   reaction_update_event
   reaction_counter
   reaction_info
   read_state
   element
   name
   user
   contact_info
   profile
   session
   folder
   folder_update
   folder_list
   sync_state
   sync_overrides
   audio_attachment
   call_attachment
   contact_attachment
   control_attachment
   file_attachment
   photo_attachment
   poll
   poll_attachment
   share_attachment
   sticker_attachment
   video_attachment
   inline_keyboard_attachment
