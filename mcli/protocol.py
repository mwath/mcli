import asyncio
import os
import zlib
from typing import Union

from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15
from cryptography.hazmat.primitives.ciphers import Cipher, CipherContext, algorithms, modes
from cryptography.hazmat.primitives.serialization import load_der_public_key

from mcli.authentication import Authentication
from mcli.packets import recv, send
from mcli.packets.manager import Manager
from mcli.packets.packet import Packet, ReadPacket, WritePacket
from mcli.utils import minecraft_sha1

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
    __slots__ = ('transport', 'manager', 'buffer', 'reader', '_waiting', 'write_pos', 'decryptor', 'encryptor')

    def __init__(self, manager: Manager, buffer: memoryview = None):
        self.transport: asyncio.Transport = None
        self.manager = manager
        self.buffer = memoryview(bytearray(256 * 1024)) if buffer is None else buffer
        self.reader = ReadPacket(self.buffer)
        self.write_pos: int = 0
        self._waiting: _buffer = None
        self.decryptor: CipherContext = None
        self.encryptor: CipherContext = None

    def connection_made(self, transport: asyncio.Transport):
        self.transport = transport

    def connection_lost(self, exc: Exception):
        print("connection lost:", exc)

    async def init_encryption(self, packet: 'recv.login.EncryptionRequest', auth: Authentication):
        pubkey = load_der_public_key(packet.public_key)
        secret = os.urandom(16)
        token = pubkey.encrypt(bytes(packet.verify_token), PKCS1v15())
        encrypted_secret = pubkey.encrypt(secret, PKCS1v15())
        server_id = minecraft_sha1(packet.server_id, secret, packet.public_key)

        if not await auth.join(server_id):
            raise RuntimeError("Unable to join the server")

        self.send(send.login.EncryptionReponse(encrypted_secret, token))

        cipher = Cipher(algorithms.AES(secret), modes.CFB8(secret))
        self.decryptor = cipher.decryptor()
        self.encryptor = cipher.encryptor()

    def send(self, packet: Union[Packet, bytearray]):
        if isinstance(packet, Packet):
            data = packet.export()
            data = WritePacket().writeVarInt(len(data)).writeBytes(data.buffer).buffer
        else:
            data = packet

        if self.encryptor is not None:
            self.encryptor.update_into(data, data)

        self.transport.write(data)

    def get_buffer(self, sizehint: int) -> bytearray:
        return self.buffer[self.write_pos:]

    def buffer_updated(self, nbytes: int):
        endpos = self.write_pos + nbytes
        if self.decryptor is not None:
            nbytes = self.decryptor.update_into(self.buffer[self.reader.pos:endpos], self.buffer[self.reader.pos:])
            endpos = self.write_pos + nbytes

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
        self.decryptor = protocol.decryptor
        self.encryptor = protocol.encryptor
        protocol.transport.set_protocol(self)

    def handle_packet(self, size: int, packet: ReadPacket):
        if size > 0:
            packet = ReadPacket(zlib.decompress(packet.readBytes(packet.remaining), bufsize=size))

        super().handle_packet(packet.readVarInt(), packet)

    def send(self, packet: Packet):
        data = packet.export().buffer
        length = len(data)

        if length >= self.threshold:
            data = WritePacket().writeVarInt(length).writeBytes(zlib.compress(data)).buffer
            length = len(data)

        super().send(WritePacket().writeVarInt(length).writeBytes(data).buffer)
