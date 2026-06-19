from typing import Any

from pydantic import BaseModel


class OutboundFrame(BaseModel):
    ver: int
    opcode: int
    cmd: int = 0
    seq: int
    payload: dict[Any, Any] | None = None


class InboundFrame(BaseModel):
    opcode: int
    cmd: int = 0
    seq: int | None = None
    payload: dict[Any, Any] | None = None
    # Не каждый фрейм несёт map: ответ-ошибка может прийти голым значением
    # (например, числовым кодом), поэтому raw хранит исходный payload как есть.
    raw: Any = None


class TcpPacketHeader(BaseModel):
    ver: int
    cmd: int
    seq: int
    opcode: int
    flags: int = 0
    payload_len: int = 0


class PackedPacket(BaseModel):
    header: TcpPacketHeader
    payload_bytes: bytes
