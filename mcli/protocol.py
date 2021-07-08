import asyncio
import zlib

from mcli.packets.manager import Manager
from mcli.packets.packet import Packet, ReadPacket, WritePacket

__all__ = ['UncompressedProtocol', 'CompressedProtocol']


class _buffer:
    __slots__ = ('data', 'length')

    def __init__(self, data: memoryview, length: int):
        self.data = bytearray(data)
        self.length = length

    @property
    def remaining(self):
        return self.length - len(self.data)


class UncompressedProtocol(asyncio.BufferedProtocol):
    __slots__ = ('transport', 'manager', 'buffer', 'reader', '_waiting', 'write_pos')

    def __init__(self, manager: Manager, buffer: memoryview = None):
        self.transport: asyncio.Transport = None
        self.manager = manager
        self.buffer = memoryview(bytearray(256 * 1024)) if buffer is None else buffer
        self.reader = ReadPacket(self.buffer)
        self.write_pos: int = 0
        self._waiting: _buffer = None

    def connection_made(self, transport: asyncio.Transport):
        self.transport = transport

    def connection_lost(self, exc: Exception):
        print("connection lost:", exc)

    def send(self, packet: Packet):
        data = packet.export()
        self.transport.write(WritePacket().writeVarInt(len(data)).buffer + data.buffer)

    def get_buffer(self, sizehint: int) -> bytearray:
        return self.buffer[self.write_pos:]

    def buffer_updated(self, nbytes: int):
        if self._waiting is not None:
            remaining = self._waiting.remaining
            if remaining <= nbytes:
                packet = ReadPacket(self._waiting.data)
                packet.buffer.extend(self.buffer[:remaining])
                self.reader.pos = remaining
                self.handle_packet(packet.readVarInt(), packet)
                self._waiting = None
                return

            self._waiting.data.extend(self.buffer)
            return

        endpos = self.reader.pos + nbytes

        while self.reader.pos < endpos:
            startpos = self.reader.pos
            length = self.reader.readVarInt()

            if self.reader.pos + length <= endpos:
                packet = ReadPacket(self.reader.readBytes(length))
                self.handle_packet(packet.readVarInt(), packet)
            elif self.reader.pos + length > len(self.buffer):
                self._waiting = _buffer(self.buffer, length)
                break
            else:
                self.write_pos = endpos
                self.reader.pos = startpos
                return

        self.reader.pos = 0
        self.write_pos = 0

    def handle_packet(self, id_: int, packet: ReadPacket):
        self.manager.handle(id_, packet)

    def eof_received(self):
        print("eof received")


class CompressedProtocol(UncompressedProtocol):
    def __init__(self, threshold: int, protocol: UncompressedProtocol):
        super().__init__(protocol.manager, buffer=protocol.buffer)
        self.threshold = threshold
        self._waiting = protocol._waiting
        self.reader = protocol.reader
        protocol.transport.set_protocol(self)

    def handle_packet(self, size: int, packet: ReadPacket):
        if size > self.threshold:
            packet = ReadPacket(zlib.decompress(packet.readBytes(packet.remaining), bufsize=size))

        super().handle_packet(packet.readVarInt(), packet)

    def send(self, packet: Packet):
        data = packet.export().buffer
        length = len(data)

        if length >= self.threshold:
            data = WritePacket().writeVarInt(length).buffer + zlib.compress(data)
            length = len(data)

        self.transport.write(WritePacket().writeVarInt(length).buffer + data)
