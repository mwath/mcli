import asyncio
import zlib

from mcli.packets.manager import Manager
from mcli.packets.packet import Packet, ReadPacket, WritePacket

__all__ = ['UncompressedProtocol', 'CompressedProtocol']


class UncompressedProtocol(asyncio.Protocol):
    __slots__ = ('transport', 'manager', 'buffer', 'length', 'pos')

    def __init__(self, manager: Manager):
        self.transport: asyncio.Transport = None
        self.manager = manager
        self.buffer = bytearray()
        self.length = 0
        self.pos = 0

    def connection_made(self, transport: asyncio.Transport):
        self.transport = transport

    def connection_lost(self, exc: Exception):
        print("connection lost:", exc)

    def send(self, packet: Packet):
        data = packet.export()
        self.transport.write(WritePacket().writeVarInt(len(data)).buffer + data.buffer)

    def data_received(self, data):
        # TCP can split a single packet into several segments.
        self.buffer.extend(data)

        while len(self.buffer) > self.length:
            if self.length == 0:
                for i in range(5):
                    byte = self.buffer[self.pos]
                    self.length |= (byte & 127) << (i * 7)
                    self.pos += 1

                    if not byte & 0x80:
                        break
                else:
                    raise ValueError('VarInt is too long!')

            if len(self.buffer) >= self.length:
                endpos = self.pos + self.length
                packet = ReadPacket(self.buffer[self.pos:endpos])
                self.handle_packet(packet.readVarInt(), packet)

                del self.buffer[:endpos]
                self.length = self.pos = 0

    def handle_packet(self, id_: int, packet: ReadPacket):
        print(id_, self.manager.client.state, packet)
        self.manager.handle(id_, packet)

    def eof_received(self):
        print("eof received")


class CompressedProtocol(UncompressedProtocol):
    def __init__(self, manager: Manager, threshold: int):
        self.threshold = threshold
        super().__init__(manager)

    def handle_packet(self, size: int, packet: ReadPacket):
        if size > self.threshold:
            raise Exception("Wrong threshold!")

        packet = ReadPacket(zlib.decompress(packet.readBytes(packet.remaining), bufsize=size))
        super().handle_packet(packet.readVarInt(), packet)

    def send(self, packet: Packet):
        data = packet.export().buffer
        length = len(data)

        if length >= self.threshold:
            data = WritePacket().writeVarInt(length).buffer + zlib.compress(data)
            length = len(data)

        self.transport.write(WritePacket().writeVarInt(length).buffer + data)
