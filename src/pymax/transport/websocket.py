from websockets import ClientConnection, Origin
from websockets.asyncio import client

from pymax.logging import get_logger

from .base import Transport

logger = get_logger(__name__)


class WebSocketTransport(Transport):
    def __init__(self, url: str, proxy: str | None) -> None:
        self.url = url
        self.proxy = proxy
        self.ws: ClientConnection | None = None

    async def connect(self) -> None:
        if self.proxy:
            self.ws = await client.connect(
                self.url, origin=Origin("https://web.max.ru"), proxy=self.proxy
            )
        else:
            self.ws = await client.connect(
                self.url, origin=Origin("https://web.max.ru")
            )  # TODO: origin should be configurable

    async def close(self) -> None:
        if self.ws:
            ws = self.ws
            await ws.close()
            await ws.wait_closed()
            self.ws = None

    async def send(self, data: bytes | str) -> None:
        if self.ws is None or not self.connected:
            raise ConnectionError("Not connected to the server")
        logger.debug("sending %s", data)
        await self.ws.send(data)

    async def recv(self, n: int | None = None) -> bytes | str:
        if self.ws is None or not self.connected:
            raise ConnectionError("Not connected to the server")

        return await self.ws.recv(decode=False)

    @property
    def connected(self) -> bool:
        return bool(self.ws and self.ws.close_code is None)
