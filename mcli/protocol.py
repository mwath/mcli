import asyncio
from mcli import Packet


class UncompressedProtocol(asyncio.Protocol):
    def __init__(self):
        self.buffer = bytearray()
        self.transport: asyncio.Transport = None

    def connection_made(self, transport: asyncio.Transport):
        self.transport = transport

    def connection_lost(self, exc: Exception):
        pass

    def data_received(self, data):
        print(data)

    def datagram_received(self, data, addr):
        self.data_received(data)

    def error_received(self, exc):
        print(exc)

    def eof_received(self):
        pass

    def send(self, packet: Packet):
        self.transport.write(Packet().writeVarInt(len(packet)).buffer + packet.buffer)


class CompressedProtocol(asyncio.Protocol):
    """TODO"""
