from mcli.packets import Packet
from mcli.packets.types import varint


class Handshake(Packet, id=0x00):
    protocol_version: varint
    server_address: str
    server_port: varint
    next_state: varint

