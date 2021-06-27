import asyncio

from mcli.packets.manager import Manager
from mcli.packets.packet import Packet, ReadPacket, WritePacket


class UncompressedProtocol(asyncio.Protocol):
    def __init__(self, manager: Manager):
        self.buffer = bytearray()
        self.length = 0
        self.pos = 0
        self.transport: asyncio.Transport = None
        self.manager = manager

    def connection_made(self, transport: asyncio.Transport):
        self.transport = transport

    def connection_lost(self, exc: Exception):
        pass

    def data_received(self, data):
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
                packet = ReadPacket(self.buffer[self.pos:self.pos+self.length])
                self.manager.handle(packet.readVarInt(), packet)

                del self.buffer[:self.pos+self.length]
                self.length = self.pos = 0

    def datagram_received(self, data, addr):
        self.data_received(data)

    def error_received(self, exc):
        print(exc)

    def eof_received(self):
        pass

    def send(self, packet: Packet):
        data = packet.export()
        self.transport.write(WritePacket().writeVarInt(len(data)).buffer + data.buffer)


class CompressedProtocol(asyncio.Protocol):
    """TODO"""
