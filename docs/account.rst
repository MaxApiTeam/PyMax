Account
=======

Что это
-------

Методы аккаунта работают с профилем текущего пользователя, папками чатов,
активными сессиями и выходом из аккаунта. Они доступны напрямую на клиенте.

Профиль
-------

После успешного login профиль текущего аккаунта лежит в ``client.me``:

.. code-block:: python

   @client.on_start()
   async def on_start(client: Client) -> None:
       if client.me is not None:
           print(client.me.contact.id)

Обновить имя, фамилию и описание:

.. code-block:: python

   await client.change_profile(
       first_name="Alex",
       last_name="PyMax",
       description="Testing Max API",
   )

Фотография профиля
------------------

Передайте ``Photo`` в ``change_profile(photo=...)``, чтобы PyMax сам загрузил
файл и применил новый токен фотографии:

.. code-block:: python

   from pymax import Photo

   await client.change_profile(
       first_name="Alex",
       photo=Photo(path="avatar.jpg"),
   )

Если у вас уже есть токен фотографии от API Max, его можно передать напрямую:

.. code-block:: python

   await client.change_profile(
       first_name="Alex",
       photo_token="PHOTO_TOKEN",
   )

Статус присутствия
------------------

``set_presence()`` меняет статус, который будет использован при следующем
login или ping:

.. code-block:: python

   client.set_presence(online=True)

Папки чатов
-----------

Создать папку:

.. code-block:: python

   update = await client.create_folder(
       title="Работа",
       chat_include=[123456, 234567],
   )

Получить список папок:

.. code-block:: python

   folders = await client.get_folders()
   for folder in folders:
       print(folder.id, folder.title)

Обновить и удалить папку:

.. code-block:: python

   await client.update_folder(
       folder_id="folder-id",
       title="Новый заголовок",
       chat_include=[123456],
   )

   await client.delete_folder("folder-id")

``FolderList`` можно итерировать напрямую: он перебирает ``folders`` внутри
ответа.

Сессии и выход
--------------

Получить активные сессии:

.. code-block:: python

   sessions = await client.get_sessions()
   for session in sessions:
       print(session.id, session.device_name, session.current)

Закрыть остальные сессии аккаунта:

.. code-block:: python

   await client.close_all_sessions()

Выйти из текущей сессии Max:

.. code-block:: python

   await client.logout()
   await client.close()

``logout()`` завершает серверную сессию. ``close()`` закрывает локальное
соединение, фоновые задачи и файл сессии.

Частые ошибки
-------------

``client.me`` равен ``None``
   Login еще не завершился. Читайте профиль внутри ``on_start`` или после
   успешного ``await client.connect()``.

Фото профиля не обновилось
   Если переданы и ``photo``, и ``photo_token``, PyMax загрузит ``photo`` и
   использует новый токен загруженной фотографии.

Папка создалась, но список старый
   Используйте ``get_folders()`` после изменения и сохраняйте новый
   ``folder_sync``, если строите собственную синхронизацию папок.
