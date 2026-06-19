from __future__ import annotations

import msgpack
import pytest

from pymax.api.messages.enums import ItemType
from pymax.protocol import Command, InboundFrame, Opcode, OutboundFrame
from pymax.protocol.tcp.compression import Lz4BlockCompression
from pymax.protocol.tcp.framing import TcpPacketFramer
from pymax.protocol.tcp.payload import MsgpackPayloadCodec, TcpPayloadDecoder
from pymax.protocol.tcp.protocol import TcpProtocol
from pymax.protocol.ws.protocol import WsProtocol


def test_websocket_protocol_roundtrip_and_invalid_frames() -> None:
    protocol = WsProtocol()
    outbound = OutboundFrame(
        ver=protocol.version,
        opcode=Opcode.PING,
        cmd=Command.REQUEST,
        seq=7,
        payload={"interactive": True},
    )

    encoded = protocol.encode(outbound)
    decoded = protocol.decode(encoded)

    assert decoded.opcode == Opcode.PING
    assert decoded.payload == {"interactive": True}
    assert protocol.decode("{").opcode == 0
    assert protocol.decode('{"opcode": "bad"}').payload is None


def test_tcp_protocol_roundtrip() -> None:
    protocol = TcpProtocol()
    outbound = OutboundFrame(
        ver=protocol.version,
        opcode=Opcode.CHAT_HISTORY,
        cmd=Command.REQUEST,
        seq=3,
        payload={"chatId": 100, "itemType": ItemType.REGULAR},
    )

    decoded = protocol.decode(protocol.encode(outbound))

    assert decoded == InboundFrame(
        opcode=Opcode.CHAT_HISTORY,
        cmd=Command.REQUEST,
        seq=3,
        payload={"chatId": 100, "itemType": ItemType.REGULAR.value},
        raw={"chatId": 100, "itemType": ItemType.REGULAR.value},
    )


def test_tcp_protocol_keeps_non_dict_payload_in_raw() -> None:
    protocol = TcpProtocol()
    framer = TcpPacketFramer()
    # Сервер может прислать ответ-ошибку голым значением (не map). Раньше это
    # роняло создание InboundFrame с ValidationError и убивало цикл приёма.
    raw = framer.pack(
        ver=protocol.version,
        cmd=Command.ERROR,
        seq=5,
        opcode=Opcode.LOGIN,
        flags=0,
        payload_bytes=msgpack.packb(-12, use_bin_type=True),
    )

    decoded = protocol.decode(raw)

    assert decoded.opcode == Opcode.LOGIN
    assert decoded.cmd == Command.ERROR
    assert decoded.seq == 5
    assert decoded.payload is None
    assert decoded.raw == -12


def test_tcp_protocol_supports_two_byte_sequence_ids() -> None:
    protocol = TcpProtocol()
    outbound = OutboundFrame(
        ver=protocol.version,
        opcode=Opcode.PING,
        cmd=Command.REQUEST,
        seq=0xFFFF,
        payload={"interactive": True},
    )

    decoded = protocol.decode(protocol.encode(outbound))

    assert decoded.seq == 0xFFFF
    assert decoded.opcode == Opcode.PING


def test_tcp_framer_uses_expected_header_layout() -> None:
    framer = TcpPacketFramer()
    packed = framer.pack(
        ver=10,
        cmd=Command.RESPONSE,
        seq=0x0100,
        opcode=Opcode.PING,
        flags=2,
        payload_bytes=b"abc",
    )

    assert framer.HEADER_SIZE == 10
    assert packed[: framer.HEADER_SIZE] == bytes(
        [0x0A, 0x01, 0x01, 0x00, 0x00, 0x01, 0x02, 0x00, 0x00, 0x03]
    )


def test_tcp_framer_handles_short_and_incomplete_packets() -> None:
    framer = TcpPacketFramer()
    packed = framer.pack(
        ver=10,
        cmd=Command.RESPONSE,
        seq=1,
        opcode=Opcode.PING,
        flags=2,
        payload_bytes=b"abc",
    )

    packet = framer.unpack(packed)

    assert framer.unpack(b"short") is None
    assert framer.unpack(packed[:-1]) is None
    assert framer.unpack_header(b"short") is None
    assert framer.unpack_header(packed[: framer.HEADER_SIZE]) == 3
    assert packet is not None
    assert packet.header.cmd == Command.RESPONSE
    assert packet.header.flags == 2
    assert packet.payload_bytes == b"abc"


def test_msgpack_codec_serializes_enums_and_decoder_normalizes_keys() -> None:
    codec = MsgpackPayloadCodec()
    encoded = codec.encode({1: {b"name": ItemType.DELAYED}, "list": [ItemType.REGULAR]})
    decoded = TcpPayloadDecoder(serializer=codec).decode(encoded)

    assert decoded == {
        "1": {"name": ItemType.DELAYED.value},
        "list": [ItemType.REGULAR.value],
    }


def test_msgpack_codec_uses_first_dict_when_stream_has_extra_data() -> None:
    codec = MsgpackPayloadCodec()
    encoded = msgpack.packb({"ok": True}, use_bin_type=True) + msgpack.packb(
        ["ignored"], use_bin_type=True
    )

    assert codec.decode(encoded) == {"ok": True}


def test_lz4_decompresses_literals_and_rejects_invalid_blocks() -> None:
    compression = Lz4BlockCompression()

    assert compression.decompress(bytes([0x50]) + b"hello") == b"hello"

    with pytest.raises(ValueError, match="zero offset"):
        compression.decompress(bytes([0x01, 0x00, 0x00]))
