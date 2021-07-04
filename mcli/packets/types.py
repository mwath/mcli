import math

from mcli.packets.basepacket import ReadPacket, WritePacket

__all__ = [
    'registered', 'varint', 'varlong', 'ubyte', 'sbyte', 'ushort', 'sshort', 'long', 'double', 'position', 'angle',
    'uuid', 'constr', 'remaining'
]


class int_type:
    pack = WritePacket.writeInt
    unpack = ReadPacket.readInt


class float_type:
    pack = WritePacket.writeFloat
    unpack = ReadPacket.readFloat


class str_type:
    pack = WritePacket.writeString
    unpack = ReadPacket.readString


class bool_type:
    pack = WritePacket.writeBool
    unpack = ReadPacket.readBool


class bytearray_type:
    @classmethod
    def pack(cls, packet: WritePacket, value: bytearray):
        packet.writeVarInt(len(value))
        packet.writeBytes(value)

    @classmethod
    def unpack(cls, packet: ReadPacket) -> bytearray:
        return packet.readBytes(packet.readVarInt())


registered = {
    'int': int_type,
    'float': float_type,
    'str': str_type,
    'bool': bool_type,
    'bytearray': bytearray_type
}


def register(cls):
    registered[cls.__name__] = cls
    return cls


@register
class varint:
    pack = WritePacket.writeVarInt
    unpack = ReadPacket.readVarInt


@register
class varlong:
    pack = WritePacket.writeVarLong
    unpack = ReadPacket.readVarLong


@register
class ubyte:
    pack = WritePacket.writeUByte
    unpack = ReadPacket.readUByte


@register
class sbyte:
    pack = WritePacket.writeSByte
    unpack = ReadPacket.readSByte


@register
class ushort:
    pack = WritePacket.writeUShort
    unpack = ReadPacket.readUShort


@register
class sshort:
    pack = WritePacket.writeSShort
    unpack = ReadPacket.readSShort


@register
class long:
    pack = WritePacket.writeLong
    unpack = ReadPacket.readLong


@register
class double:
    pack = WritePacket.writeDouble
    unpack = ReadPacket.readDouble


@register
class position:
    pack = WritePacket.writePosition
    unpack = ReadPacket.readPosition


@register
class angle:
    pack = WritePacket.writeAngle
    unpack = ReadPacket.readAngle


@register
class uuid:
    pack = WritePacket.writeUUID
    unpack = ReadPacket.readUUID


@register
class remaining:
    @classmethod
    def pack(cls, packet: WritePacket, value: bytes):
        packet.writeBytes(value)

    @classmethod
    def unpack(cls, packet: ReadPacket) -> bytes:
        return packet.readBytes(packet.remaining)


class Constrain:
    def check(self, value) -> bool:
        raise NotImplementedError()


class constr(Constrain):
    def __init__(self, *, min: int = None, max: int = None):
        if min is None and max is None:
            raise ValueError("At least one argument must be given: min, max")

        self.min = min or 0
        self.max = max or math.inf

    def __repr__(self) -> str:
        max_ = f', max={self.max}' if self.max < math.inf else ''
        return f'constr(min={self.min}{max_})'

    def check(self, value: str) -> bool:
        return self.min <= len(value) <= self.max
