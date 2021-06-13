from mcli.packets import Packet
from mcli.packets.types import varint, uuid


class DisconnectLogin(Packet, id=0x00):
    reason: str


class EncryptionRequest(Packet, id=0x01):
    server_id: str
    public_key: bytearray
    verify_token :bytearray
    pass


class LoginSuccess(Packet, id=0x02):
    uuid: uuid
    username: str


class SetCompression(Packet, id=0x03):
    threshold: varint


class LoginPluginRequest(Packet, id=0x04):
    message_id: varint
    channel: str
    #data: bytearray
    pass
