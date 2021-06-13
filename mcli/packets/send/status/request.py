from mcli.packets import Packet
from mcli.packets.types import long

class RequestStatus(Packet, id=0x00):
	pass


class Ping(Packet, id=0x01):
	payload: long
	pass