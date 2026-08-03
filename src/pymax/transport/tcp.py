import asyncio

from python_socks.async_.asyncio import Proxy

from pymax.logging import get_logger

from .base import Transport

logger = get_logger(__name__)
_CLOSE_TIMEOUT = 5.0


class TCPTransport(Transport):
    def __init__(self, host: str, port: int, proxy: str | None, use_ssl: bool = True) -> None:
        self._host = host
        self._port = port
        self._proxy = proxy
        self._use_ssl = use_ssl
        self._reader = None
        self._writer = None

    async def connect(self) -> None:
        logger.debug(
            "tcp connect host=%s port=%s ssl=%s",
            self._host,
            self._port,
            self._use_ssl,
        )
        if self._proxy:
            logger.debug("tcp connecting via proxy %s", self._proxy)
            proxy = Proxy.from_url(self._proxy)
            sock = await proxy.connect(
                dest_host=self._host,
                dest_port=self._port,
            )
            server_hostname = self._host if self._use_ssl else None
            self._reader, self._writer = await asyncio.open_connection(
                sock=sock,
                ssl=self._use_ssl,
                server_hostname=server_hostname,
            )
            logger.info(
                "tcp connected via proxy %s host=%s port=%s ssl=%s",
                self._proxy,
                self._host,
                self._port,
                self._use_ssl,
            )
        else:
            self._reader, self._writer = await asyncio.open_connection(
                self._host,
                self._port,
                ssl=self._use_ssl,
            )
        logger.info(
            "tcp connected host=%s port=%s ssl=%s",
            self._host,
            self._port,
            self._use_ssl,
        )

    async def close(self) -> None:
        writer = self._writer
        self._reader = None
        self._writer = None

        if writer:
            logger.debug("tcp close")
            writer.close()
            try:
                await asyncio.wait_for(writer.wait_closed(), _CLOSE_TIMEOUT)
            except (OSError, TimeoutError) as e:
                logger.warning("tcp close did not finish cleanly: %s", e)
                writer.transport.abort()
            logger.debug("tcp closed")

    async def send(self, data: bytes | str) -> None:
        if isinstance(data, str):
            data = data.encode()

        if self._writer is None or not self.connected:
            logger.warning("tcp send failed: transport is not connected")
            raise ConnectionError("Not connected to the server")

        logger.debug("tcp send bytes=%s", len(data))
        self._writer.write(data)
        await self._writer.drain()

    async def recv(self, n: int | None = None) -> bytes:
        if self._reader is None or not self.connected:
            logger.warning("tcp recv failed: transport is not connected")
            raise ConnectionError("Not connected to the server")

        if n is None:
            data = await self._reader.readexactly(1024)
        else:
            data = await self._reader.readexactly(n)

        logger.debug("tcp recv bytes=%s requested=%s", len(data), n)
        return data

    @property
    def connected(self) -> bool:
        return bool(self._reader and not self._reader.at_eof())
