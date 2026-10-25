from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, AsyncGenerator

from pymax.fsm.context import FSMContext, FSMKey
from pymax.types.domain.message import Message

from .protocol import FSMStorage
from .state import State

if TYPE_CHECKING:
    from pymax.base import BaseClient
    from pymax.dispatch import DispatchEvent


class InMemoryFSMStorage:
    def __init__(self) -> None:
        self.records: dict[FSMKey, InMemoryFSM] = {}
        self.locks: dict[FSMKey, asyncio.Lock] = {}

    def resolve_key(
        self,
        client: BaseClient,
        event: DispatchEvent,
    ) -> FSMKey | None:
        if not isinstance(event, Message):
            return None

        if event.chat_id is None or event.sender is None:
            return None

        return FSMKey(
            client_id=hash(client),
            user_id=event.sender,
            chat_id=event.chat_id,
        )

    def get_context(
        self,
        client: BaseClient,
        event: Message,
    ) -> FSMContext | None:
        if not event.chat_id or not event.sender:
            return None

        key = self.resolve_key(client, event)

        if not key:
            return None

        record = self.records.get(key)
        if record is None:
            record = InMemoryFSM()
            self.records[key] = record

        return FSMContext(storage=record, key=key)

    @asynccontextmanager
    async def isolate(
        self,
        client: BaseClient,
        event: DispatchEvent,
    ) -> AsyncGenerator[None]:
        key = self.resolve_key(client, event)

        if key is None:
            yield
            return

        lock = self.locks.setdefault(key, asyncio.Lock())

        async with lock:
            yield


@dataclass
class FsmState:
    value: str | None = None
    created_at: datetime = datetime.now()
    ttl: int | None = None


class InMemoryFSM(FSMStorage):
    """Состояние и данные одного FSM-контекста в памяти процесса.

    В обработчике это хранилище доступно как ``ctx.storage``.
    """

    def __init__(self) -> None:
        self.state: FsmState = FsmState()
        self.data: dict[str, Any] = {}
        self.lock = asyncio.Lock()

    async def get_state(self) -> str | None:
        """Возвращает имя состояния или ``None``, если оно не задано или истек TTL.

        Истечение TTL сбрасывает только состояние, сохраняя данные контекста.
        """
        async with self.lock:
            if self.state.ttl is None:
                return self.state.value

            expires_at = self.state.created_at.timestamp() + self.state.ttl

            if datetime.now().timestamp() >= expires_at:
                self.state = FsmState()
                return None

            return self.state.value

    async def set_state(self, state: str | State | None, ttl: int | None = None) -> None:
        """Устанавливает состояние, сохраняя данные контекста.

        Args:
            state: Состояние, его строковое имя или ``None`` для сброса.
            ttl: Срок действия в секундах с момента установки.
                ``None`` означает отсутствие срока действия.
        """
        async with self.lock:
            if state is None:
                self.state = FsmState()
                return

            self.state.value = str(state)
            self.state.ttl = ttl
            self.state.created_at = datetime.now()

    async def get_data(self) -> dict[str, Any]:
        """Возвращает поверхностную копию словаря данных контекста."""
        async with self.lock:
            return self.data.copy()

    async def set_data(self, key: str, value: Any) -> None:
        """Записывает одно значение, сохраняя остальные ключи данных."""
        async with self.lock:
            self.data[key] = value

    async def update_data(self, **data: Any) -> None:
        """Добавляет или перезаписывает переданные ключи данных."""
        async with self.lock:
            self.data.update(data)

    async def clear(self) -> None:
        """Сбрасывает состояние и удаляет все данные текущего контекста."""
        async with self.lock:
            self.state = FsmState()
            self.data.clear()
