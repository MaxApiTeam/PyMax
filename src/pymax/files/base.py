import os
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from io import BytesIO

import aiofiles
import aiohttp

try:
    from tinytag import TinyTag
except ImportError:
    TinyTag = None


class BaseFile(ABC):
    def __init__(
        self,
        raw: bytes | None = None,
        *,
        path: str | None,
        url: str | None,
        name: str | None,
    ) -> None:
        self.path = path
        self.url = url
        self.raw = raw
        self.name = name

        if raw is None and not url and not path:
            raise ValueError("Path or Url or Raw must be provided")

        if raw is not None and not name:
            raise ValueError("Name must be provided for raw data")

        sources = sum(source is not None for source in (raw, url, path))
        if sources > 1:
            raise ValueError("Only one of raw, url or path must be provided.")

    @abstractmethod
    async def read(self) -> bytes:
        if self.raw:
            return self.raw

        if self.path:
            async with aiofiles.open(self.path, "rb") as f:
                return await f.read()
        elif self.url:
            async with aiohttp.ClientSession() as session:  # noqa: SIM117
                async with session.get(self.url) as resp:
                    resp.raise_for_status()
                    return await resp.read()
        else:
            raise ValueError("Path or Url must be provided")

    @abstractmethod
    async def size(self) -> int:
        if self.raw:
            return len(self.raw)

        if self.path:
            return os.path.getsize(self.path)

        if self.url:
            async with aiohttp.ClientSession() as session:  # noqa: SIM117
                async with session.head(self.url, allow_redirects=True) as resp:
                    return int(resp.headers["Content-Length"])
        else:
            raise ValueError("Path or Url must be provided")

    @abstractmethod
    async def iter_chunks(self, size: int) -> AsyncGenerator[bytes, None]:
        if size <= 0:
            raise ValueError("size must be greater than zero")

        if self.raw:
            for i in range(0, len(self.raw), size):
                yield self.raw[i : i + size]

        if self.path:
            async with aiofiles.open(self.path, "rb") as f:
                while True:
                    data = await f.read(size)

                    if not data:
                        break
                    yield data

        if self.url:
            async with aiohttp.ClientSession() as session:  # noqa: SIM117
                async with session.get(self.url) as resp:
                    resp.raise_for_status()
                    async for chunk in resp.content.iter_chunked(size):
                        yield chunk


class TimedMediaFile(BaseFile):
    def __init__(
        self,
        raw: bytes | None = None,
        *,
        path: str | None,
        url: str | None,
        name: str | None,
        duration: int | None,
    ) -> None:
        self.duration = duration
        super().__init__(raw, path=path, url=url, name=name)

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
        elif self.path:
            tag = TinyTag.get(
                filename=self.path,
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
