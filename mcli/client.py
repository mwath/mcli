import asyncio

from mcli.packets.manager import Manager, State
from mcli.packets.send.handshaking import Handshake
from mcli.packets.send.status import RequestStatus
from mcli.protocol import UncompressedProtocol
from mcli.protocol import CommonProtocol, TCPProtocol
from mcli.utils import is_valid_ip


class Client:
    def __init__(self):
        self.protocol: CommonProtocol = None
        self.manager = Manager(self)
        self.state = State.handshaking

    async def query_status(self, host: str, port: int):
        await self.connect(host, port, 1)
        self.protocol.send(RequestStatus())
        await asyncio.sleep(5)

    async def connect(self, host: str, port: int, next_state: State, version: int = -1):
        loop = asyncio.get_running_loop()
        if not is_valid_ip(host):
            # TODO: Check for SRV record
            pass
        _, self.protocol = await loop.create_connection(lambda: UncompressedProtocol(self.manager), host, port)

        self.protocol.send(Handshake(version, host, port, int(next_state)))
        self.state = State.status

    async def login(self, username: str, password: str):
        pass

    async def disconnect(self):
        pass

    @property
    def is_connected(self):
        return False

    @property
    def is_logged(self):
        return False
