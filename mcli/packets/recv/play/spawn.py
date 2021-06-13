from mcli.packets import Packet
from mcli.packets.types import varint, uuid, double, angle, position


class SpawnEntity(Packet, id=0x00):
    entity_id: varint
    object_uuid: uuid
    type: varint
    x: double
    y: double
    z: double
    pitch: angle
    yaw: angle
    data: int
    # velocity_x: short
    # velocity_y: short
    # velocity_z: short


class SpawnExperienceOrb(Packet, id=0x01):
    entity_id: varint
    x: double
    y: double
    z: double
    # count: short


class SpawnLivingEntity(Packet, id=0x02):
    entity_id: varint
    object_uuid: uuid
    type: varint
    x: double
    y: double
    z: double
    yaw: angle
    pitch: angle
    data: int
    # velocity_x: short
    # velocity_y: short
    # velocity_z: short


class SpawnPainting(Packet, id=0x03):
    entity_id: varint
    entity_uuid: uuid
    motive: varint
    location: position
    # direction: Byte Enum


class SpawnPlayer(Packet, id=0x04):
    entity_id: varint
    player_uuid: uuid
    x: double
    y: double
    z: double
    yaw: angle
    pitch: angle
