import asyncio
from mcli.protocol import UncompressedProtocol
from mcli.packets.manager import Manager
from mcli.packets.send.handshaking import Handshake
from mcli.packets.send.status import RequestStatus


class Client:
	def __init__(self):
		self.protocol: asyncio.Protocol = None
		self.manager = Manager(self)

	async def query_status(self, host: str, port: int):
		loop = asyncio.get_running_loop()
		_, self.protocol = await loop.create_connection(UncompressedProtocol, host, port)
		self.protocol.send(Handshake(-1, host, port, 1))
		self.protocol.send(RequestStatus())
		await asyncio.sleep(5)

	async def connect(self, host: str, port: int):
		pass

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
