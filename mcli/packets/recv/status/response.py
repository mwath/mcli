from mcli.packets import Packet
from mcli.packets.types import long

class ResponseStatus(Packet, id=0x00):
    json_response: str
    pass

class Pong(Packet, id=0x01):
    Payload: long
    pass