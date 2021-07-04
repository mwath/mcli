import asyncio
import json
import time
from typing import Dict, List, Tuple

from mcli.packets.manager import Manager, State
from mcli.packets.packet import Packet, ReadPacket
from mcli.packets.recv.status.response import Pong, ResponseStatus
from mcli.packets.send.handshaking import Handshake
from mcli.packets.send.status import RequestStatus
from mcli.packets.send.status.request import Ping
from mcli.protocol import UncompressedProtocol
from mcli.utils import is_valid_ip


class Client:
    def __init__(self):
        self.protocol: UncompressedProtocol = None
        self.manager = Manager(self)
        self.state = State.handshaking
        self.__listeners: Dict[type, List[asyncio.Future]] = {}

    async def query_status(self, host: str, port: int) -> Tuple[dict, int]:
        await self._connect(host, port, State.status)

        self.protocol.send(RequestStatus())
        status = await self.wait_for(ResponseStatus)

        self.protocol.send(Ping(int(time.perf_counter() * 1000)))
        ping = await self.wait_for(Pong)
        ping = int(time.perf_counter() * 1000) - ping.payload

        return json.loads(status.response), ping

    async def connect(self, host: str, port: int, version: int = -1):
        if version == -1:
            # Discover the server's version
            status, _ = await self.query_status(host, port)
            version = status['version']['protocol']
        
        await self._connect(host, port, State.login, version)

    async def _connect(self, host: str, port: int, next_state: State, version: int = -1):
        if not is_valid_ip(host):
            # TODO: Check for SRV record
            pass

        loop = asyncio.get_running_loop()
        _, self.protocol = await loop.create_connection(lambda: UncompressedProtocol(self.manager), host, port)

        self.protocol.send(Handshake(version, host, port, int(next_state)))
        self.state = next_state

    async def login(self, username: str, password: str):
        pass

    async def disconnect(self):
        pass

    def dispatch(self, packet: ReadPacket):
        """Dispatch a packet. Resume any wait_for() waiting for the given packet."""
        klass = packet.__class__
        if klass in self.__listeners:
            for listener in self.__listeners[klass]:
                if not listener.done():
                    listener.set_result(packet)

            del self.__listeners[klass]

    async def wait_for(self, packet: type, timeout: float = None) -> ReadPacket:
        """Wait for a packet. The coroutine will resume once the packet has been received and dispatched."""
        fut = asyncio.Future()

        if packet not in self.__listeners:
            self.__listeners[packet] = [fut]
        else:
            self.__listeners[packet].append(fut)

        return await asyncio.wait_for(fut, timeout)

    @property
    def is_connected(self):
        return self.protocol is not None and not self.protocol.transport.is_closing()

    @property
    def is_logged(self):
        return False
