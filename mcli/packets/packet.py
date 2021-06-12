from collections import OrderedDict
from mcli.packets.basepacket import ReadPacket, WritePacket
from mcli.packets import types


class PacketMeta(type):
    def __new__(cls, clsname: str, bases: tuple, classdict: dict, **kwds):
        if '__annotations__' in classdict:
            if 'id' not in kwds:
                raise ValueError('Packet id is missing.')

            classdict['_id'] = kwds['id']
            classdict['_types'] = _types = OrderedDict()

            for name, type_ in classdict['__annotations__'].items():
                if isinstance(type_, type):
                    type_ = type_.__name__

                if type_ not in types.registered:
                    raise TypeError(f'The type {type_} is not supported.')

                _types[name] = types.registered[type_]

        return super().__new__(cls, clsname, bases, classdict)


class Packet(metaclass=PacketMeta):
    def __init__(self, *args, **kwargs):
        for i, name in enumerate(self._types):
            setattr(self, name, kwargs.get(name, args[i]))

    def __repr__(self):
        attr = ' '.join(f'{name}={getattr(self, name)!r}' for name in self._types)
        return f'<{self.__class__.__name__} {attr}>'

    @property
    def export(self) -> bytes:
        packet = WritePacket().writeVarInt(self._id)

        for attr, type_ in self._types.items():
            type_.pack(packet, getattr(self, attr))

        return packet

    @classmethod
    def from_bytes(cls, packet: ReadPacket) -> 'Packet':
        return cls(*(t.unpack(packet) for t in cls._types.values()))
