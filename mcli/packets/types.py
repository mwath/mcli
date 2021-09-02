import math
from uuid import UUID

from mcli.packets.basepacket import ReadPacket, WritePacket

__all__ = [
    'registered', 'varint', 'varlong', 'ubyte', 'sbyte', 'ushort', 'sshort', 'long', 'double', 'position', 'angle',
    'uuid', 'constr', 'remaining'
]


class int_type:
    pack = WritePacket.writeInt
    unpack = ReadPacket.readInt
    hint = 'i'


class float_type:
    pack = WritePacket.writeFloat
    unpack = ReadPacket.readFloat
    hint = 'f'


class str_type:
    pack = WritePacket.writeString
    unpack = ReadPacket.readString
    hint = '-'


class bool_type:
    pack = WritePacket.writeBool
    unpack = ReadPacket.readBool
    hint = 'B'
    hint_read = bool
    hint_write = int


class bytearray_type:
    hint = '-'

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
    hint = '-'


@register
class varlong:
    pack = WritePacket.writeVarLong
    unpack = ReadPacket.readVarLong
    hint = '-'


@register
class ubyte:
    pack = WritePacket.writeUByte
    unpack = ReadPacket.readUByte
    hint = 'B'


@register
class sbyte:
    pack = WritePacket.writeSByte
    unpack = ReadPacket.readSByte
    hint = 'b'


@register
class ushort:
    pack = WritePacket.writeUShort
    unpack = ReadPacket.readUShort
    hint = 'H'


@register
class sshort:
    pack = WritePacket.writeSShort
    unpack = ReadPacket.readSShort
    hint = 'h'


@register
class long:
    pack = WritePacket.writeLong
    unpack = ReadPacket.readLong
    hint = 'q'


@register
class double:
    pack = WritePacket.writeDouble
    unpack = ReadPacket.readDouble
    hint = 'd'


@register
class position:
    pack = WritePacket.writePosition
    unpack = ReadPacket.readPosition
    hint = 'H'

    @classmethod
    def hint_read(value):
        x = value >> 38
        y = value & 0xFFF
        z = (value >> 12) & 0x3ffffff

        if x >= 2**25:
            x -= 2**26
        if y >= 2**11:
            y -= 2**12
        if z >= 2**25:
            z -= 2**26

        return (x, y, z)

    @classmethod
    def hint_write(value):
        x, y, z = value
        return ((x & 0x3FFFFFF) << 38) | ((z & 0x3FFFFFF) << 12) | (y & 0xFFF)


@register
class angle:
    pack = WritePacket.writeAngle
    unpack = ReadPacket.readAngle
    hint = 'B'

    @classmethod
    def hint_read(value):
        return value / 256

    @classmethod
    def hint_write(value):
        return int(value * 256) % 256


@register
class uuid:
    pack = WritePacket.writeUUID
    unpack = ReadPacket.readUUID
    hint = '16s'

    @classmethod
    def hint_read(value):
        return UUID(bytes=bytes(value))

    @classmethod
    def hint_write(value):
        return value.bytes


@register
class remaining:
    @classmethod
    def pack(cls, packet: WritePacket, value: bytes):
        packet.writeBytes(value)

    @classmethod
    def unpack(cls, packet: ReadPacket) -> bytes:
        return packet.readBytes(packet.remaining)

    hint = '-'


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
