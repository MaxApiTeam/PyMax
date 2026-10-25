from pymax import Router

try:
    from dishka import AsyncContainer
    from dishka.integrations.base import is_dishka_injected, wrap_injection
except ImportError as e:
    raise RuntimeError(
        "Dishka integration requires the 'dishka' extra. "
        "Install it with `uv add 'maxapi-python[dishka]'`"
    ) from e

from collections.abc import Callable, Generator
from typing import Any, ParamSpec, TypeVar
from weakref import WeakKeyDictionary

from pymax.base import BaseClient

P = ParamSpec("P")
T = TypeVar("T")

_containers: WeakKeyDictionary[BaseClient[Any], AsyncContainer] = WeakKeyDictionary()
ClientT = TypeVar("ClientT", bound=BaseClient)


def _get_client(
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> BaseClient[Any]:
    client = kwargs.get("client")

    if isinstance(client, BaseClient):
        return client

    for arg in reversed(args):
        if isinstance(arg, BaseClient):
            return arg

    raise RuntimeError("Cannot resolve PyMax client for Dishka injection")


def _get_container(
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> AsyncContainer:
    client = _get_client(args, kwargs)

    try:
        return _containers[client]
    except KeyError:
        raise RuntimeError(
            "Dishka is not configured for this client. Call setup_dishka(container, client)."
        ) from None


def inject(func: Callable[P, T]) -> Callable[P, T]:
    """Внедряет параметры ``FromDishka[T]`` в обработчик события.

    Размещайте ``@inject`` под декоратором регистрации обработчика,
    например ``@router.on_message()``. Контейнер для переданного в обработчик
    клиента должен быть зарегистрирован через ``setup_dishka()``.
    """
    return wrap_injection(
        func=func,
        is_async=True,
        container_getter=_get_container,
    )


def inject_router(router: Router[ClientT]) -> None:
    """Оборачивает уже зарегистрированные обработчики роутера и его детей.

    Пропускает обработчики, уже обернутые через ``inject``. Не затрагивает
    ``on_start``, ``on_error``, ``on_disconnect`` и последующие регистрации.
    """
    for current_router in _iter_routers(router):
        for entries in current_router.handlers.values():
            for entry in entries:
                if not is_dishka_injected(entry.callback):
                    entry.callback = inject(entry.callback)


def _iter_routers(router: Router[ClientT]) -> Generator[Router[ClientT] | Any, Any, None]:
    yield router

    for child in router.children:
        yield from _iter_routers(child)


def setup_dishka(
    container: AsyncContainer,
    client: BaseClient[Any],
    *,
    auto_inject: bool = False,
) -> None:
    """Привязывает контейнер Dishka к клиенту.

    Args:
        container: Контейнер, из которого обработчики получают зависимости.
        client: Клиент, для которого включается интеграция.
        auto_inject: Обернуть уже зарегистрированные обработчики всего дерева
            роутеров клиента. По умолчанию используется явный ``@inject``.

    Интеграция не открывает отдельный scope для события, не добавляет событие
    или клиента в контекст Dishka и не закрывает контейнер автоматически.
    """
    _containers[client] = container

    if auto_inject:
        inject_router(client._router)
