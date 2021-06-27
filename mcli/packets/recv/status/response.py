from mcli.packets import Packet
from mcli.packets.types import long


class ResponseStatus(Packet, id=0x00):
    response: str


class Pong(Packet, id=0x01):
    payload: long
