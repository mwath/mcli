import uuid
from ctypes import c_uint32, c_uint64
from struct import Struct
from typing import Any, ByteString, Tuple, Union


class Types:
    byte = Struct('>b')
    sshort = Struct('>h')
    ushort = Struct('>H')
    int = Struct('>i')
    long = Struct('>q')
    float = Struct('>f')
    double = Struct('>d')


class ReadPacket:
    def __init__(self, buffer: ByteString):
        self.buffer = buffer
        self.pos = 0

    def __len__(self):
        return len(self.buffer)

    def __repr__(self) -> str:
        return f'<ReadPacket {bytes(self)}>'

    def __bytes__(self) -> bytes:
        return bytes(self.buffer)

    @property
    def remaining(self):
        return len(self) - self.pos

    def readBytes(self, size: int) -> bytearray:
        """Read a number of bytes from the buffer and return a copy."""
        value = self.buffer[self.pos:self.pos + size]
        self.pos = self.pos + size
        return value

    def readStruct(self, fmt: Union[Struct, str, bytes]) -> Tuple:
        st = Struct('>' + fmt) if isinstance(fmt, (str, bytes)) else fmt
        self.pos, offset = self.pos + st.size, self.pos
        return st.unpack_from(self.buffer, offset)

    def readUByte(self) -> int:
        """Read an unsigned byte and return it."""
        value = self.buffer[self.pos]
        self.pos += 1
        return value

    def readSByte(self) -> int:
        """Read a signed byte and return it."""
        return self.readStruct(Types.byte)[0]

    def readBool(self) -> bool:
        return self.readByte() == 1

    def readUShort(self) -> int:
        """Read an unsigned short and return it."""
        return self.readStruct(Types.ushort)[0]

    def readSShort(self) -> int:
        """Read a signed short and return it."""
        return self.readStruct(Types.sshort)[0]

    def readInt(self) -> int:
        """Read a signed int and return it."""
        return self.readStruct(Types.int)[0]

    def readLong(self) -> int:
        """Read a signed long and return it."""
        return self.readStruct(Types.long)[0]

    def readFloat(self) -> float:
        """Read a float and return it."""
        return self.readStruct(Types.float)[0]

    def readDouble(self) -> float:
        """Read a double and return it."""
        return self.readStruct(Types.double)[0]

    def readString(self) -> str:
        """Read a string and return it."""
        return bytes(self.readBytes(self.readVarInt())).decode('utf-8')

    def readVarInt(self) -> int:
        """Read a variable length int and return it."""
        value = 0
        for i in range(5):
            byte = self.buffer[self.pos]
            value |= (byte & 127) << (i * 7)
            self.pos += 1

            if not byte & 0x80:
                break
        else:
            raise ValueError('VarInt is too long!')

        return value

    def readVarLong(self) -> int:
        """Read a variable length long and return it."""
        value = 0
        for i in range(10):
            byte = self.buffer[self.pos]
            value |= (byte & 127) << (i * 7)
            self.pos += 1

            if not byte & 0x80:
                break
        else:
            raise ValueError('VarLong is too long!')

        return value

    def readPosition(self) -> Tuple[int]:
        """Read a position and return it."""
        value = self.readStruct('>H')
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

    def readAngle(self) -> float:
        """Read an angle an return it."""
        return self.readByte() / 256

    def readUUID(self) -> uuid.UUID:
        """Read an UUID an return it."""
        return uuid.UUID(self.readBytes(32))


class WritePacket:
    def __init__(self):
        self.buffer = bytearray()

    def __len__(self):
        return len(self.buffer)

    def __repr__(self) -> str:
        return f'<ReadPacket {bytes(self)}>'

    def __bytes__(self) -> bytes:
        return bytes(self.buffer)

    def writeBytes(self, value: bytearray) -> 'WritePacket':
        """Write a number of bytes into the buffer."""
        self.buffer.extend(value)
        return self

    def writeStruct(self, fmt: Union[Struct, str, bytes], value: Any) -> 'WritePacket':
        st = Struct('>' + fmt) if isinstance(fmt, (str, bytes)) else fmt
        return self.writeBytes(st.pack(value))

    def writeUByte(self, value: int) -> 'WritePacket':
        """Write an unsigned byte."""
        self.buffer.append(value)
        return self

    def writeSByte(self, value: int) -> 'WritePacket':
        """Write a signed byte."""
        return self.writeStruct(Types.byte, value)

    def writeBool(self, value: bool) -> 'WritePacket':
        return self.writeByte(value == 1)

    def writeUShort(self, value: int) -> 'WritePacket':
        """Write an unsigned short."""
        return self.writeStruct(Types.ushort, value)

    def writeSShort(self, value: int) -> 'WritePacket':
        """Write a signed short."""
        return self.writeStruct(Types.sshort, value)

    def writeInt(self, value: int) -> 'WritePacket':
        """Write a signed int."""
        return self.writeStruct(Types.int, value)

    def writeLong(self, value: int) -> 'WritePacket':
        """Write a signed long."""
        return self.writeStruct(Types.long, value)

    def writeFloat(self, value: float) -> 'WritePacket':
        """Write a float."""
        return self.writeStruct(Types.float, value)

    def writeDouble(self, value: float) -> 'WritePacket':
        """Write a double."""
        return self.writeStruct(Types.double, value)

    def writeString(self, value: ByteString) -> 'WritePacket':
        """Write a string."""
        if isinstance(value, str):
            value = value.encode('utf-8')

        return self.writeVarInt(len(value)).writeBytes(value)

    def writeVarInt(self, value: int) -> 'WritePacket':
        """Write a variable length int."""
        value = c_uint32(value).value
        i, remaining = 0, value >> 7

        while remaining != 0:
            self.buffer.append(value & 0x7f | 0x80)
            value = remaining
            remaining >>= 7
            i += 1

            if i >= 5:
                raise ValueError('VarInt too long!')

        self.buffer.append(value & 0x7f)
        return self

    def writeVarLong(self, value: int) -> 'WritePacket':
        """Write a variable length long."""
        value = c_uint64(value).value
        i, remaining = 0, value >> 7

        while remaining != 0:
            self.buffer.append(value & 0x7f | 0x80)
            value = remaining
            remaining >>= 7
            i += 1

            if i >= 10:
                raise ValueError('VarLong too long!')

        self.buffer.append(value & 0x7f)
        return self

    def writePosition(self, value: Tuple[int]) -> 'WritePacket':
        """Write a position."""
        x, y, z = value
        value = ((x & 0x3FFFFFF) << 38) | ((z & 0x3FFFFFF) << 12) | (y & 0xFFF)

        return self.writeStruct('>H', value)

    def writeAngle(self, value: float) -> 'WritePacket':
        """Write an angle."""
        return self.writeByte(int(value * 256) % 256)

    def writeUUID(self, value: uuid.UUID) -> 'WritePacket':
        """Write an UUID."""
        return self.writeBytes(value.bytes)
