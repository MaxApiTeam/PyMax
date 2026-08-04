from collections.abc import AsyncGenerator
from io import BytesIO
from pathlib import Path

from .base import BaseFile

try:
    from tinytag import TinyTag
except ImportError:
    TinyTag = None


class Video(BaseFile):
    """Видео для отправки в сообщение.

    ``Video`` принимает ``path``, ``url`` или ``raw``. При отправке PyMax
    загружает видео чанками и ждет от Max событие готовности обработки.

    Args:
        raw: Байты видео.
        url: URL видео.
        path: Локальный путь к видео.
        name: Имя файла. Обязательно для ``raw``.

    Example:
        .. code-block:: python

           from pymax import Video

           await client.send_message(
               chat_id=123,
               text="Видео",
               attachments=[Video(path="clip.mp4")],
           )
    """

    def __init__(
        self,
        raw: bytes | None = None,
        *,
        url: str | None = None,
        path: str | None = None,
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
        """Читает видео целиком в память.

        Returns:
            Байты видео.
        """
        return await super().read()

    async def size(self) -> int:
        """Возвращает размер видео в байтах.

        Returns:
            Размер видео.
        """
        return await super().size()

    def iter_chunks(self, size: int) -> AsyncGenerator[bytes, None]:
        """Итерирует видео чанками.

        Args:
            size: Размер чанка в байтах.

        Returns:
            Async generator с байтами.
        """
        return super().iter_chunks(size)


class VideoNote(Video):
    """Круглое видеосообщение для отправки.

    Принимает те же источники, что и ``Video``. Длительность задается в
    миллисекундах. Если она не передана, требуется extra ``video`` для
    автоматического определения длительности.
    """

    def __init__(
        self,
        raw: bytes | None = None,
        *,
        url: str | None = None,
        path: str | None = None,
        name: str | None = None,
        duration: int | None = None,
    ) -> None:
        self.duration = duration
        super().__init__(raw, url=url, path=path, name=name)

    async def get_duration(self) -> int:
        if self.duration is not None:
            return self.duration

        if not TinyTag:
            raise RuntimeError(
                "Automatic video duration detection requires the 'video' extra. "
                "Install it with `uv add 'maxapi-python[video]'` "
                "or pass duration manually."
            )

        if self.raw:
            tag = TinyTag.get(
                filename=self.name,
                file_obj=BytesIO(self.raw),
                tags=False,
                duration=True,
            )
        else:
            tag = TinyTag.get(
                filename=self.name,
                file_obj=BytesIO(await self.read()),
                tags=False,
                duration=True,
            )

        if tag.duration is None:
            raise ValueError("Failed to determine video duration.")

        return round(tag.duration * 1000)
