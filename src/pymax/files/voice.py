from collections.abc import AsyncGenerator
from pathlib import Path

from .base import TimedMediaFile


class Voice(TimedMediaFile):
    """Голосовое сообщение в формате OGG для отправки.

    Принимает ``path``, ``url`` или ``raw``. Для ``raw`` необходимо явно
    передать имя файла. Длительность задается в миллисекундах; если она не
    передана, требуется extra ``video`` для автоматического определения.

    Args:
        raw: Байты голосового сообщения.
        path: Локальный путь к OGG-файлу.
        url: URL OGG-файла.
        name: Имя файла. Обязательно для ``raw``.
        duration: Длительность в миллисекундах. ``None`` включает
            автоматическое определение через extra ``video``.

    Raises:
        RuntimeError: При определении длительности без extra ``video``.
    """

    def __init__(
        self,
        raw: bytes | None = None,
        *,
        path: str | None = None,
        url: str | None = None,
        name: str | None = None,
        duration: int | None = None,
    ) -> None:
        self.name: str = name or ""
        self.duration = duration
        if not self.name and path:
            self.name = Path(path).name
        elif not self.name and url:
            self.name = Path(url).name

        if not self.name:
            raise ValueError("Either name, url or path must be provided.")
        super().__init__(raw=raw, url=url, path=path, name=self.name, duration=self.duration)

    async def read(self) -> bytes:
        return await super().read()

    async def size(self) -> int:
        return await super().size()

    def iter_chunks(self, size: int) -> AsyncGenerator[bytes, None]:
        return super().iter_chunks(size)
