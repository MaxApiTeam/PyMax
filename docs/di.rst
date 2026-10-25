Внедрение зависимостей
======================

Встроенная передача ``FSMContext`` описана в разделе :doc:`fsm` и работает без
дополнительных пакетов. Для собственных сервисов и других зависимостей
можно подключить Dishka.

Установка
---------

.. code-block:: bash

   pip install -U 'maxapi-python[dishka]'

или через uv:

.. code-block:: bash

   uv add 'maxapi-python[dishka]'

Подключение Dishka
------------------

Создайте ``AsyncContainer`` и свяжите его с клиентом через
``setup_dishka(container, client)``. Параметры, которые должен заполнить
контейнер, помечаются ``FromDishka[T]``. Событие и клиент остаются первыми
двумя аргументами обработчика.

.. code-block:: python

   import asyncio

   from dishka import FromDishka, Provider, Scope, make_async_container, provide

   from pymax import Client, ClientRouter, Message
   from pymax.filters import Command
   from pymax.integrations.dishka import inject, setup_dishka


   class GreetingService:
       def text(self) -> str:
           return "Привет от сервиса!"


   class AppProvider(Provider):
       @provide(scope=Scope.APP)
       def greetings(self) -> GreetingService:
           return GreetingService()


   router = ClientRouter()


   @router.on_message(Command("hello"))
   @inject
   async def hello(
       message: Message,
       client: Client,
       greetings: FromDishka[GreetingService],
   ) -> None:
       await message.answer(greetings.text())


   async def main() -> None:
       container = make_async_container(AppProvider())
       client = Client(phone="+79990000000", work_dir="cache")
       client.include_router(router)
       setup_dishka(container, client)

       try:
           await client.start()
       finally:
           await container.close()


   if __name__ == "__main__":
       asyncio.run(main())

``@inject`` находится под ``@router.on_message(...)``: сначала создается
обертка Dishka, затем роутер регистрирует ее. Одна аннотация
``GreetingService`` без ``FromDishka`` не включает внедрение зависимости.

В примере сервис имеет ``Scope.APP`` и повторно используется в пределах
созданного контейнера. Контейнер привязан к конкретному экземпляру клиента.
Если один роутер подключен к нескольким клиентам, вызовите ``setup_dishka``
для каждого из них с нужным контейнером.

Автоматическое оборачивание обработчиков
----------------------------------------

Вместо ``@inject`` у каждого обработчика можно включить ``auto_inject``:

.. code-block:: python

   client.include_router(router)
   setup_dishka(container, client, auto_inject=True)

Сначала зарегистрируйте обработчики и подключите роутеры, затем вызовите
``setup_dishka``. Интеграция обойдет текущее дерево роутеров клиента и обернет
уже зарегистрированные обработчики событий. Обработчики, у которых уже есть
``@inject``, повторно не оборачиваются.

Если нужно обернуть только отдельный роутер и его детей, используйте
``inject_router``:

.. code-block:: python

   from pymax.integrations.dishka import inject_router

   inject_router(router)

Этот вызов не заменяет ``setup_dishka``: контейнер по-прежнему нужно связать
с клиентом. Оба способа оборачивают только существующие регистрации; новые
обработчики и позже подключенные роутеры автоматически не обрабатываются.
Для них используйте ``@inject`` или повторите оборачивание после регистрации.

Автоматическое оборачивание относится к обработчикам событий, например
``on_message`` и ``on_raw``. Оно не затрагивает ``on_start``, ``on_error``
и ``on_disconnect``.

Scope и завершение работы
-------------------------

Интеграция получает зависимости непосредственно из контейнера, переданного
в ``setup_dishka``. Отдельный ``Scope.REQUEST`` для каждого события не
открывается. При обычном контейнере со ``Scope.APP`` зависимости уровня
``Scope.REQUEST`` автоматически недоступны.

PyMax также не добавляет ``Message``, ``Client`` или ``FSMContext`` в контекст
Dishka. Событие и клиент передаются самим PyMax, а ``FSMContext`` можно
добавить отдельным обязательным параметром с этой аннотацией.

Созданием, выбором scope и закрытием контейнера управляет приложение.
``client.close()`` не закрывает контейнер Dishka. В примере это делает
``await container.close()`` в ``finally`` после завершения работы клиента.

API reference
-------------

.. autofunction:: pymax.integrations.dishka.inject

.. autofunction:: pymax.integrations.dishka.inject_router

.. autofunction:: pymax.integrations.dishka.setup_dishka
