from mcli.packets import Packet
from mcli.packets.types import varint


class LoginStart(Packet, id=0x00):
    name: str


class EncryptionReponse(Packet, id=0x01):
    shared_secret: bytearray
    verify_token: bytearray


class LoginPluginResponse(Packet, id=0x02):
    message_id: varint
    successful: bool
    #data: bytearray
