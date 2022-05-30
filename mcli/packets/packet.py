import struct
from collections import OrderedDict

import mcli
from mcli.packets.basepacket import ReadPacket, WritePacket
from mcli.packets.manager import Manager, State
from mcli.packets.types import Constrain
from mcli.packets.types import registered as registered_types

VALIDATION_CODE = """
    if not all(constrain.check(value) for value, (name, constrain) in zip({args2check}, self._validators.items())):
        raise ValueError("Invalid value %r for attribute %r. Constrain: %s." % (value, name, str(constrain)))
"""

PACKET_DYNAMIC = """
def __init__(self, {args_typing}):{validation}
    {attributes}

def export(self) -> bytes:
    packet = WritePacket().writeVarInt({id})
    {export_data}
    return packet

@classmethod
def from_bytes(cls, packet: ReadPacket) -> 'Packet':
    try:
        return cls({import_data})
    except Exception:
        raise Exception("Unable to parse packet %s (0x{id:x})." % (cls.__name__))
"""


def _convert_write(_G: dict, name: str, type_: type):
    if hasattr(type_, 'hint_write'):
        _G[f'convert_{name}'] = type_.hint_write
        return f"convert_{name}(self.{name})"
    return f'self.{name}'


def _add_pack(pack: list[str, type], _G: dict, export_data: list[str], import_data: list[str]):
    fmt = ''.join(t.hint for _, t in pack)
    values = ', '.join(_convert_write(_G, n, t) for n, t in pack)
    export_data.append(f'packet.writeBytes(struct.pack(">{fmt}", {values}))')
    # TODO: convert values for the import
    import_data.append(f'*struct.unpack(">{fmt}", packet.readBytes({struct.calcsize(fmt)}))')


class PacketMeta(type):
    def __new__(cls, clsname: str, bases: tuple, classdict: dict, **kwargs):
        if len(bases) == 0:
            return super().__new__(cls, clsname, bases, classdict)

        if 'id' not in kwargs:
            raise ValueError('Packet id is missing.')

        module = classdict['__module__']
        if module.startswith('mcli.packets'):
            state = module.split('.')[3].lower()
            register = module.split('.')[2] == 'clientbound'
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
        classdict['_validators'] = validators = {}

        if '__annotations__' in classdict:
            for name, type_ in classdict['__annotations__'].items():
                if isinstance(type_, type):
                    type_ = type_.__name__

                if type_ not in registered_types:
                    raise TypeError(f'The type {type_} is not supported.')

                if name in classdict and isinstance(classdict[name], Constrain):
                    validators[name] = classdict[name]

                types[name] = (registered_types[type_], classdict.pop(name, None))

        classdict['__slots__'] = tuple(types)
        if len(types) > 0:
            _G = globals().copy()  # holds functions to convert types
            pack, export_data, import_data = [], [], []

            # Gather types with fixed-size together and use a single struct.(un)pack function call.
            # It improves performances significantly.
            for name, (type_, _) in types.items():
                # We use the the type's hint to get the struct format.
                # "-" means the type doesn't have a struct format equivalent.
                if type_.hint == '-':
                    if len(pack) > 0:
                        _add_pack(pack, _G, export_data, import_data)
                        pack.clear()

                    export_data.append(f'packet.{type_.pack.__name__}(self.{name})')
                    import_data.append(f'packet.{type_.unpack.__name__}()')
                else:
                    pack.append((name, type_))

            if len(pack) > 0:
                _add_pack(pack, _G, export_data, import_data)

            # Check for constrains in constructor
            validation = ''
            if len(validators) > 0:
                validation = VALIDATION_CODE.format(args2check=tuple(validators))

            # Create the code, execute it and store it in classdict
            code = PACKET_DYNAMIC.format(
                id=kwargs['id'],
                args_typing=', '.join(types),
                validation=validation,
                attributes='\n    '.join(f'self.{name} = {name}' for name in types),
                export_data=', '.join(export_data),
                import_data=', '.join(import_data)
            )
            exec(compile(code, f"<packet-{clsname}-src>", 'exec', optimize=2), _G, classdict)

            # Replace qualname into something more useful. Do not apply on export_bytes since it's a classmethod.
            for name in ('export', '__init__'):
                classdict[name].__qualname__ = clsname + '.' + classdict[name].__name__

        klass = super().__new__(cls, clsname, bases, classdict)
        if register:
            Manager._add(state, klass)

        return klass


class Packet(metaclass=PacketMeta):
    def __init__(self, *args, **kwargs):
        for i, (name, (_, checker)) in enumerate(self._types.items()):
            value = kwargs.get(name, args[i])
            if checker is not None and not checker.check(value):
                raise ValueError(f"Invalid value {value!r} for attribute {name!r}. Constrain: {checker}.")

            setattr(self, name, value)

    def __repr__(self):
        attr = ' '.join(f'{name}={getattr(self, name)!r}' for name in self._types)
        return f'<{self.__class__.__name__} {attr}>'

    def export(self) -> bytes:
        packet = WritePacket().writeVarInt(self._id)

        for attr, (type_, _) in self._types.items():
            type_.pack(packet, getattr(self, attr))

        return packet

    async def handle(self, client: 'mcli.Client'):
        raise NotImplementedError()

    @classmethod
    def from_bytes(cls, packet: ReadPacket) -> 'Packet':
        try:
            return cls(*(t.unpack(packet) for t, _ in cls._types.values()))
        except Exception:
            raise Exception(f"Unable to parse packet {cls.__name__} (0x{cls._id:x}).")
