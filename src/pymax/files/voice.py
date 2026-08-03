from collections.abc import AsyncGenerator
from pathlib import Path

from .base import BaseFile


class Voice(BaseFile):
    """Голосовое сообщение в формате OGG для отправки.

    Принимает ``path``, ``url`` или ``raw``. Для ``raw`` необходимо явно
    передать имя файла.
    """

    def __init__(
        self,
        raw: bytes | None = None,
        *,
        path: str | None = None,
        url: str | None = None,
        name: str | None = None,
    ) -> None:
        self.name: str = name or ""
        if not self.name and path:
            self.name = Path(path).name
        elif not self.name and url:
            self.name = Path(url).name

        if not self.name:
            raise ValueError("Either name, url or path must be provided.")
        super().__init__(raw=raw, url=url, path=path, name=self.name)

    async def read(self) -> bytes:
        return await super().read()

    async def size(self) -> int:
        return await super().size()

    def iter_chunks(self, size: int) -> AsyncGenerator[bytes, None]:
        return super().iter_chunks(size)
