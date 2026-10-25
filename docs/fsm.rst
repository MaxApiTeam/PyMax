FSM
===

FSM хранит состояние диалога и данные между сообщениями. Например, можно
сначала спросить имя, затем город и обработать каждый ответ своим handler-ом.
Состояние и данные разделены по клиенту, пользователю и чату: один пользователь
может независимо проходить сценарий в разных чатах.

Состояния и контекст
--------------------

Импортируйте ``FSMContext``, ``FsmGroup`` и ``State`` из ``pymax.fsm``.
Состояния объявляются атрибутами класса ``FsmGroup``. Экземпляр ``State``
используется и для установки состояния, и как фильтр обработчика.

Добавьте после ``message`` и ``client`` обязательный параметр с аннотацией
``FSMContext``. PyMax подставит контекст автоматически; имя параметра может
быть любым. Для этого не нужна установка Dishka.

``ctx.storage``
   Хранилище состояния и данных текущего контекста. Все операции выполняются
   через него: например, ``await ctx.storage.set_state(Form.name)``.

``ctx.key``
   Ключ текущего контекста, связывающий клиента, пользователя и чат.

Аннотация параметра должна быть ``FSMContext`` без значения по умолчанию.
Автоматическая передача контекста доступна для событий ``Message``, когда
известны отправитель и чат; для других типов событий FSM не поддерживается.

Пример диалога
--------------

.. code-block:: python

   import asyncio

   from pymax import Client, ClientRouter, Message
   from pymax.filters import Command
   from pymax.fsm import FSMContext, FsmGroup, State

   router = ClientRouter()


   class Form(FsmGroup):
       name = State()
       city = State()


   @router.on_message(Command("form"))
   async def begin(message: Message, client: Client, ctx: FSMContext) -> None:
       await ctx.storage.clear()
       await ctx.storage.set_state(Form.name, ttl=300)
       await message.answer("Как вас зовут?")


   @router.on_message(Form.name)
   async def save_name(message: Message, client: Client, ctx: FSMContext) -> None:
       if not message.text:
           await message.answer("Отправьте имя текстом")
           return

       await ctx.storage.set_data("name", message.text)
       await ctx.storage.set_state(Form.city, ttl=300)
       await message.answer("Из какого вы города?")


   @router.on_message(Form.city)
   async def save_city(message: Message, client: Client, ctx: FSMContext) -> None:
       if not message.text:
           await message.answer("Отправьте город текстом")
           return

       await ctx.storage.update_data(city=message.text)
       data = await ctx.storage.get_data()
       await ctx.storage.clear()
       await message.answer(f"{data['name']}, город: {data['city']}")


   client = Client(phone="+79990000000", work_dir="cache")
   client.include_router(router)


   async def main() -> None:
       await client.start()


   if __name__ == "__main__":
       asyncio.run(main())

Отправьте ``/form``, затем имя и город. Повторная команда ``/form`` очищает
предыдущие данные и начинает диалог заново. В примере каждый шаг действует
пять минут с момента перехода в него.

Порядок обработчиков
--------------------

В одном роутере вызывается первый обработчик, у которого совпали все фильтры.
Поэтому команда начала диалога зарегистрирована перед обработчиками состояний,
а общий обработчик без фильтров следует размещать после них.

После первого совпадения PyMax продолжает обход дочерних роутеров. Если
обработчик родителя изменил состояние, фильтр дочернего роутера уже увидит
новое значение на том же сообщении. В примере все шаги находятся в одном
роутере, поэтому сообщение с командой не обрабатывается сразу как имя.

Операции с состоянием и данными
-------------------------------

Все методы ``ctx.storage`` асинхронные:

``get_state()``
   Возвращает строковое имя состояния или ``None``. Для ``State`` используется
   полное имя из модуля, класса группы и имени атрибута.

``set_state(state, ttl=None)``
   Принимает ``State``, строку или ``None``. ``None`` сбрасывает состояние.
   ``ttl`` задается в секундах; без него состояние действует до следующего
   изменения. Переход и сброс состояния сохраняют данные.

``get_data()``
   Возвращает поверхностную копию словаря. Изменение ключей этой копии
   не меняет хранилище, но вложенные изменяемые значения остаются общими.

``set_data(key, value)``
   Записывает одно значение по ключу, сохраняя остальные данные.

``update_data(**data)``
   Добавляет или перезаписывает несколько ключей, сохраняя остальные данные.

``clear()``
   Сбрасывает состояние и удаляет все данные текущего контекста.

Хранение и TTL
--------------

Сейчас используется ``InMemoryFSM``: состояние и данные живут в памяти
процесса. Они сохраняются при reconnect того же экземпляра клиента и теряются
после перезапуска процесса. У нового экземпляра клиента отдельное хранилище.

TTL проверяется при чтении состояния, в том числе фильтром ``State``.
Истечение срока сбрасывает только состояние, без удаления данных и без
вызова отдельного обработчика. Для полного сброса используйте ``clear()``.

Фильтры и обычные обработчики ``Message`` для одного клиента, пользователя и
чата выполняются последовательно, включая переходы состояния.

API reference
-------------

.. autoclass:: pymax.fsm.FSMContext

.. autoclass:: pymax.fsm.State
   :members: full_name
   :exclude-members: owner, name

.. autoclass:: pymax.fsm.FsmGroup

.. autoclass:: pymax.fsm.InMemoryFSM
   :members: get_state, set_state, get_data, set_data, update_data, clear
