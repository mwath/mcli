from collections import OrderedDict

import mcli
from mcli.packets.basepacket import ReadPacket, WritePacket
from mcli.packets.manager import Manager, State
from mcli.packets.types import registered as registered_types


class PacketMeta(type):
    def __new__(cls, clsname: str, bases: tuple, classdict: dict, **kwargs):
        if len(bases) == 0:
            return super().__new__(cls, clsname, bases, classdict)

        if 'id' not in kwargs:
            raise ValueError('Packet id is missing.')

        module = classdict['__module__']
        if module.startswith('mcli.packets'):
            state = module.split('.')[3].lower()
            register = module.split('.')[2] == 'recv'
        else:
            if 'state' not in kwargs:
                raise ValueError('Packet state is missing.')

            state = str(kwargs['state']).lower()
            register = kwargs.get('register', False)

        if state not in State.__members__:
            raise ValueError(f'{state!r} is not a valid state.')

        classdict['_id'] = kwargs['id']
        classdict['_state'] = state = State[state]
        classdict['_types'] = types = OrderedDict()

        if '__annotations__' in classdict:
            for name, type_ in classdict['__annotations__'].items():
                if isinstance(type_, type):
                    type_ = type_.__name__

                if type_ not in registered_types:
                    raise TypeError(f'The type {type_} is not supported.')

                types[name] = registered_types[type_]

        klass = super().__new__(cls, clsname, bases, classdict)
        if register:
            Manager._add(state, klass)

        return klass


class Packet(metaclass=PacketMeta):
    def __init__(self, *args, **kwargs):
        for i, name in enumerate(self._types):
            setattr(self, name, kwargs.get(name, args[i]))

    def __repr__(self):
        attr = ' '.join(f'{name}={getattr(self, name)!r}' for name in self._types)
        return f'<{self.__class__.__name__} {attr}>'

    def export(self) -> bytes:
        packet = WritePacket().writeVarInt(self._id)

        for attr, type_ in self._types.items():
            type_.pack(packet, getattr(self, attr))

        return packet

    async def handle(self, client: 'mcli.Client'):
        raise NotImplementedError()

    @classmethod
    def from_bytes(cls, packet: ReadPacket) -> 'Packet':
        try:
            return cls(*(t.unpack(packet) for t in cls._types.values()))
        except Exception:
            raise Exception(f"Unable to parse packet {cls.__name__} (0x{cls._id:x}).")
