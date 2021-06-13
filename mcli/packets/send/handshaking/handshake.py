from mcli.packets import Packet
from mcli.packets.types import varint, ushort


class Handshake(Packet, id=0x00):
    protocol_version: varint
    server_address: str
    server_port: ushort
    next_state: varint

