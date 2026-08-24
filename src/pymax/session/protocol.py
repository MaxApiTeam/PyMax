from typing import Protocol, runtime_checkable

from .models import SessionInfo


@runtime_checkable
class StoreProtocol(Protocol):
    """Асинхронный контракт пользовательского хранилища сессии.

    PyMax использует переданный ``ExtraConfig.store`` только при
    ``persist_session=True`` и вызывает :meth:`close` при закрытии runtime.
    """

    async def save_session(self, session_info: SessionInfo) -> None:
        """Сохраняет или полностью заменяет данные сессии."""
        ...

    async def update_token(self, old_token: str, new_token: str, /) -> None:
        """Заменяет ``old_token`` у соответствующей сессии."""
        ...

    async def load_session(self) -> SessionInfo | None:
        """Возвращает сессию для запуска клиента или ``None``."""
        ...

    async def load_session_by_device_id(self, device_id: str) -> SessionInfo | None:
        """Ищет сессию по device ID."""
        ...

    async def load_session_by_phone(self, phone: str) -> SessionInfo | None:
        """Ищет сессию по номеру телефона."""
        ...

    async def delete_session(self, token: str, /) -> None:
        """Удаляет сессию с переданным token, если она существует."""
        ...

    async def close(self) -> None:
        """Освобождает ресурсы хранилища при закрытии runtime."""
        ...
