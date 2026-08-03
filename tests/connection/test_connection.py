from __future__ import annotations

import asyncio
from collections import deque

import pytest

from pymax.connection.connection import ConnectionManager
from pymax.connection.pending import PendingRequests
from pymax.protocol import Command, InboundFrame, OutboundFrame


class FakeProtocol:
    version = 1

    def encode(self, frame: OutboundFrame) -> bytes:
        return f"{frame.seq}:{frame.opcode}".encode()

    def decode(self, raw: bytes | str) -> InboundFrame:
        seq_raw, opcode_raw = bytes(raw).decode().split(":")
        return InboundFrame(
            opcode=int(opcode_raw),
            cmd=Command.RESPONSE,
            seq=int(seq_raw),
            payload={"ok": True},
            raw={"ok": True},
        )


class FakeTransport:
    def __init__(self, send_error: Exception | None = None) -> None:
        self.sent: list[bytes | str] = []
        self.connected = False
        self.closed = False
        self.send_error = send_error

    async def connect(self) -> None:
        self.connected = True

    async def close(self) -> None:
        self.closed = True
        self.connected = False

    async def send(self, data: bytes | str) -> None:
        if self.send_error:
            raise self.send_error

        self.sent.append(data)


class QueueReader:
    def __init__(self, items: list[bytes | Exception]) -> None:
        self.items = deque(items)

    async def read(self) -> bytes:
        await asyncio.sleep(0)
        item = self.items.popleft()
        if isinstance(item, Exception):
            raise item
        return item


class BlockingReader:
    async def read(self) -> bytes:
        await asyncio.Event().wait()
        raise AssertionError("unreachable")


@pytest.mark.asyncio
async def test_pending_requests_resolve_reject_discard_and_cancel() -> None:
    pending = PendingRequests()

    first = pending.create(1)
    assert pending.resolve(1, InboundFrame(opcode=1, seq=1, payload={"ok": True}))
    assert (await first).payload == {"ok": True}
    assert not pending.resolve(1, InboundFrame(opcode=1, seq=1))

    second = pending.create(2)
    assert pending.reject(2, RuntimeError("boom"))
    with pytest.raises(RuntimeError, match="boom"):
        await second

    third = pending.create(3)
    pending.discard(3)
    assert third.cancelled()

    fourth = pending.create(4)
    pending.cancel_all(ConnectionError("lost"))
    with pytest.raises(ConnectionError, match="lost"):
        await fourth


@pytest.mark.asyncio
async def test_connection_next_seq_wraps_after_uint16_max() -> None:
    manager = ConnectionManager(
        reader=QueueReader([]),
        transport=FakeTransport(),
        protocol=FakeProtocol(),
    )

    manager._seq = 0xFFFE

    assert manager.next_seq() == 0xFFFF
    assert manager.next_seq() == 0


@pytest.mark.asyncio
async def test_connection_request_resolves_when_matching_response_arrives() -> None:
    transport = FakeTransport()
    manager = ConnectionManager(
        reader=QueueReader([]),
        transport=transport,
        protocol=FakeProtocol(),
    )
    frame = OutboundFrame(ver=1, opcode=99, cmd=Command.REQUEST, seq=7, payload={})

    task = asyncio.create_task(manager.request(frame, timeout=1))
    await asyncio.sleep(0)
    await manager._handle_inbound(
        InboundFrame(opcode=99, cmd=Command.RESPONSE, seq=7, payload={"done": True})
    )

    response = await task

    assert response.payload == {"done": True}
    assert transport.sent == [b"7:99"]


@pytest.mark.asyncio
async def test_connection_request_discards_pending_future_when_send_fails() -> None:
    manager = ConnectionManager(
        reader=QueueReader([]),
        transport=FakeTransport(send_error=ConnectionError("closed")),
        protocol=FakeProtocol(),
    )
    frame = OutboundFrame(ver=1, opcode=99, cmd=Command.REQUEST, seq=7, payload={})

    with pytest.raises(ConnectionError, match="closed"):
        await manager.request(frame, timeout=1)

    assert manager.requests._pending == {}


@pytest.mark.asyncio
async def test_connection_request_discards_pending_future_when_cancelled() -> None:
    manager = ConnectionManager(
        reader=QueueReader([]),
        transport=FakeTransport(),
        protocol=FakeProtocol(),
    )
    frame = OutboundFrame(ver=1, opcode=99, cmd=Command.REQUEST, seq=7, payload={})

    task = asyncio.create_task(manager.request(frame, timeout=10))
    await asyncio.sleep(0)
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    assert manager.requests._pending == {}


@pytest.mark.asyncio
async def test_connection_open_recv_loop_dispatches_events_and_closes() -> None:
    events: list[InboundFrame] = []
    closed: list[Exception | None] = []
    transport = FakeTransport()

    async def on_event(event: InboundFrame) -> None:
        events.append(event)

    manager = ConnectionManager(
        reader=QueueReader([b"5:42", EOFError()]),
        transport=transport,
        protocol=FakeProtocol(),
        on_event=on_event,
        on_close=closed.append,
    )

    await manager.open()
    await asyncio.sleep(0.01)

    with pytest.raises(ConnectionError, match="Connection lost"):
        await manager.wait_closed()

    assert manager.is_open is False
    assert len(closed) == 1
    assert isinstance(closed[0], ConnectionError)
    await manager.close()
    assert transport.closed is True
    assert [event.opcode for event in events] == [42]


@pytest.mark.asyncio
async def test_connection_wait_closed_returns_after_explicit_close() -> None:
    manager = ConnectionManager(
        reader=BlockingReader(),
        transport=FakeTransport(),
        protocol=FakeProtocol(),
    )

    await manager.open()
    waiter = asyncio.create_task(manager.wait_closed())
    await asyncio.sleep(0)

    await manager.close()
    await waiter

    assert manager.is_open is False


@pytest.mark.asyncio
async def test_connection_wait_closed_propagates_external_cancellation() -> None:
    manager = ConnectionManager(
        reader=BlockingReader(),
        transport=FakeTransport(),
        protocol=FakeProtocol(),
    )

    await manager.open()
    waiter = asyncio.create_task(manager.wait_closed())
    await asyncio.sleep(0)
    waiter.cancel()

    with pytest.raises(asyncio.CancelledError):
        await waiter

    await manager.close()


@pytest.mark.asyncio
async def test_send_requires_open_connection() -> None:
    manager = ConnectionManager(
        reader=QueueReader([]),
        transport=FakeTransport(),
        protocol=FakeProtocol(),
    )

    with pytest.raises(ConnectionError, match="Connection is not open"):
        await manager.send(OutboundFrame(ver=1, opcode=1, seq=1, payload={}))
