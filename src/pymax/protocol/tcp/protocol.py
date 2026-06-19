from pymax.logging import get_logger
from pymax.protocol import InboundFrame, OutboundFrame
from pymax.protocol.base import BaseProtocol

from .framing import TcpPacketFramer
from .payload import (
    Lz4BlockCompression,
    MsgpackPayloadCodec,
    TcpPayloadDecoder,
)

logger = get_logger(__name__)


class TcpProtocol(BaseProtocol):
    version = 10

    def __init__(self) -> None:
        super().__init__()
        self.framer = TcpPacketFramer()
        self.serializer = MsgpackPayloadCodec()
        self.compression = Lz4BlockCompression()
        self.payload_decoder = TcpPayloadDecoder(
            serializer=self.serializer, compression=self.compression
        )

    def encode(self, frame: OutboundFrame) -> bytes:
        payload_bytes = self.serializer.encode(frame.payload) if frame.payload is not None else b""

        flags = 0

        # if frame.compress and payload_bytes:
        #     payload_bytes = self.compression.compress(payload_bytes)
        #     flags = 0x01

        return self.framer.pack(
            ver=self.version,
            cmd=frame.cmd,
            seq=frame.seq,
            opcode=frame.opcode,
            flags=flags,
            payload_bytes=payload_bytes,
        )

    def decode(self, raw: bytes | str) -> InboundFrame:
        if isinstance(raw, str):
            raw = raw.encode("utf-8")

        packed_packet = self.framer.unpack(raw)
        if not packed_packet:
            return InboundFrame(opcode=0, cmd=0, seq=None, payload=None, raw=None)

        logger.debug(
            "tcp frame decoded header ver=%s cmd=%s seq=%s opcode=%s flags=%s payload_len=%s",
            packed_packet.header.ver,
            packed_packet.header.cmd,
            packed_packet.header.seq,
            packed_packet.header.opcode,
            packed_packet.header.flags,
            packed_packet.header.payload_len,
        )
        decoded = self.payload_decoder.decode(
            packed_packet.payload_bytes, flags=packed_packet.header.flags
        )

        # Не каждый фрейм несёт map: например, ответ-ошибка приходит голым
        # значением (числовым кодом). payload оставляем строго dict|None — его
        # так читают консьюмеры, — а исходное значение кладём в raw, чтобы не
        # терять данные и не ронять весь приём кадров на ValidationError.
        payload = decoded if isinstance(decoded, dict) else None
        if payload is None and decoded is not None:
            logger.debug(
                "non-dict tcp payload opcode=%s cmd=%s type=%s value=%r",
                packed_packet.header.opcode,
                packed_packet.header.cmd,
                type(decoded).__name__,
                decoded,
            )

        return InboundFrame(
            opcode=packed_packet.header.opcode,
            cmd=packed_packet.header.cmd,
            seq=packed_packet.header.seq,
            payload=payload,
            raw=decoded,
        )
