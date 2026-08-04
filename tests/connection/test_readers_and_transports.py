from __future__ import annotations

import asyncio

import pytest

from pymax.connection.readers.tcp import TCPReader
from pymax.connection.readers.ws import WSReader
from pymax.protocol import Command, Opcode
from pymax.protocol.tcp.framing import TcpPacketFramer
from pymax.transport.tcp import TCPTransport
from pymax.transport.websocket import WebSocketTransport


class ChunkTransport:
    def __init__(self, chunks: list[bytes]) -> None:
        self.chunks = list(chunks)
        self.requests: list[int] = []

    async def recv(self, n: int | None = None) -> bytes:
        self.requests.append(n or 0)
        return self.chunks.pop(0)


@pytest.mark.asyncio
async def test_tcp_reader_reads_header_then_payload() -> None:
    framer = TcpPacketFramer()
    packet = framer.pack(
        ver=10,
        cmd=Command.REQUEST,
        seq=1,
        opcode=Opcode.PING,
        flags=0,
        payload_bytes=b"abc",
    )
    transport = ChunkTransport([packet[: framer.HEADER_SIZE], packet[framer.HEADER_SIZE :]])
    reader = TCPReader(transport, framer)

    assert await reader.read() == packet
    assert transport.requests == [framer.HEADER_SIZE, 3]


@pytest.mark.asyncio
async def test_ws_reader_returns_transport_message() -> None:
    class Transport:
        async def recv(self):
            return "message"

    assert await WSReader(Transport()).read() == "message"


class FakeStreamReader:
    def __init__(self) -> None:
        self.eof = False

    async def readexactly(self, n: int) -> bytes:
        return b"x" * n

    def at_eof(self) -> bool:
        return self.eof


class FakeStreamWriter:
    def __init__(self) -> None:
        self.writes: list[bytes] = []
        self.closed = False
        self.transport = FakeStreamTransport()

    def write(self, data: bytes) -> None:
        self.writes.append(data)

    async def drain(self) -> None:
        return None

    def close(self) -> None:
        self.closed = True

    async def wait_closed(self) -> None:
        return None


class FakeStreamTransport:
    def __init__(self) -> None:
        self.aborted = False

    def abort(self) -> None:
        self.aborted = True


@pytest.mark.asyncio
async def test_tcp_transport_connect_send_recv_and_close(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reader = FakeStreamReader()
    writer = FakeStreamWriter()

    async def open_connection(*args, **kwargs):
        return reader, writer

    monkeypatch.setattr("pymax.transport.tcp.asyncio.open_connection", open_connection)
    transport = TCPTransport("example.test", 443, proxy=None, use_ssl=True)

    await transport.connect()
    await transport.send("hi")
    data = await transport.recv(3)
    await transport.close()

    assert transport.connected is False
    assert writer.writes == [b"hi"]
    assert data == b"xxx"
    assert writer.closed is True


@pytest.mark.asyncio
async def test_tcp_transport_ignores_tls_close_error() -> None:
    writer = FakeStreamWriter()

    async def wait_closed() -> None:
        raise OSError("SSL shutdown failed")

    writer.wait_closed = wait_closed
    transport = TCPTransport("example.test", 443, proxy=None, use_ssl=True)
    transport._writer = writer

    await transport.close()

    assert writer.closed is True
    assert writer.transport.aborted is True


@pytest.mark.asyncio
async def test_tcp_transport_proxy_ssl_passes_server_hostname(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reader = FakeStreamReader()
    writer = FakeStreamWriter()
    sock = object()
    proxy_connect_kwargs = {}
    open_connection_kwargs = {}

    class FakeProxy:
        async def connect(self, **kwargs):
            proxy_connect_kwargs.update(kwargs)
            return sock

    async def open_connection(*args, **kwargs):
        open_connection_kwargs.update(kwargs)
        return reader, writer

    monkeypatch.setattr(
        "pymax.transport.tcp.Proxy.from_url",
        lambda proxy_url: FakeProxy(),
    )
    monkeypatch.setattr("pymax.transport.tcp.asyncio.open_connection", open_connection)

    transport = TCPTransport(
        "example.test",
        443,
        proxy="socks5://localhost:9050",
        use_ssl=True,
    )

    await transport.connect()

    assert proxy_connect_kwargs == {
        "dest_host": "example.test",
        "dest_port": 443,
    }
    assert open_connection_kwargs == {
        "sock": sock,
        "ssl": True,
        "server_hostname": "example.test",
    }


class FakeWebSocket:
    def __init__(self) -> None:
        self.close_code = None
        self.sent: list[bytes | str] = []
        self.closed = False
        self.recv_decode: bool | None = None

    async def send(self, data: bytes | str) -> None:
        self.sent.append(data)

    async def recv(self, decode=True):
        self.recv_decode = decode
        return "incoming"

    async def close(self) -> None:
        self.closed = True
        self.close_code = 1000

    async def wait_closed(self) -> None:
        return None


@pytest.mark.asyncio
async def test_websocket_transport_connect_send_recv_and_close(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ws = FakeWebSocket()

    async def connect(*args, **kwargs):
        return ws

    monkeypatch.setattr("pymax.transport.websocket.client.connect", connect)
    transport = WebSocketTransport("wss://example.test", proxy=None)

    await transport.connect()
    await transport.send("hello")
    incoming = await transport.recv()
    await transport.close()

    assert ws.sent == ["hello"]
    assert incoming == "incoming"
    assert ws.recv_decode is False
    assert transport.connected is False
