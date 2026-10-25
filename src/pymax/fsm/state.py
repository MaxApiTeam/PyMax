from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pymax.base import BaseClient

from pymax.filters import Filter
from pymax.types import Message


class State(Filter[Message, "BaseClient"]):
    """Состояние FSM и фильтр сообщений по этому состоянию.

    Объявляйте экземпляры атрибутами ``FsmGroup``. Один и тот же экземпляр
    можно передать в ``ctx.storage.set_state()`` и ``router.on_message()``.
    """

    owner: type
    name: str

    def __set_name__(self, owner: type, name: str) -> None:
        self.owner = owner
        self.name = name

    @property
    def full_name(self) -> str:
        """Возвращает полное имя состояния из имени модуля, группы и атрибута."""
        return f"{self.owner.__module__}.{self.owner.__qualname__}:{self.name}"

    def __str__(self) -> str:
        return self.full_name

    async def __call__(
        self,
        event: Message,
        client: BaseClient,
    ) -> bool:
        if event.chat_id is None or event.sender is None:
            return False

        fsm_key = client._app.fsm_storage.resolve_key(client, event)

        if not fsm_key:
            return False

        record = client._app.fsm_storage.records.get(fsm_key)

        if record is None:
            return False

        return await record.get_state() == self.full_name


class FsmGroup:
    """Группа состояний, объявленных атрибутами класса через ``State()``."""

    __states__: dict[str, State] = {}

    def __init_subclass__(cls) -> None:
        super().__init_subclass__()

        inherited: dict[str, State] = {}

        for base in cls.__bases__:
            inherited.update(getattr(base, "__states__", {}))

        own = {name: value for name, value in vars(cls).items() if isinstance(value, State)}

        cls.__states__ = inherited | own
