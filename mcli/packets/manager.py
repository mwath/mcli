import asyncio
import warnings
from enum import IntEnum
from typing import Callable, Optional

import mcli


class State(IntEnum):
    handshaking = 0
    status = 1
    login = 2
    play = 3


class Manager:
    packets = {}

    def __init__(self, client: 'mcli.Client'):
        self.client = client

    @classmethod
    def _add(cls, state: State, packet: 'mcli.Packet'):
        key = (state, packet._id)
        if key in cls.packets:
            warnings.warn(f'Packet id 0x{packet._id:x} ({packet.__name__}) is already registered in state {state!r}!')
        else:
            cls.packets[key] = packet

    @classmethod
    def register(cls, state: State) -> Callable[['mcli.Packet'], 'mcli.Packet']:
        def wrapper(pkt: 'mcli.Packet') -> 'mcli.Packet':
            cls._add(state, pkt)
            return pkt

        return wrapper

    def get(self, packet_id: int) -> Optional['mcli.Packet']:
        # return self.clientbound.get(packet_id, version=self.client.protocol.version)
        return self.packets.get((self.client.state, packet_id))

    def handle(self, packet_id: int, packet: 'mcli.ReadPacket'):
        """Handle a single packet."""
        factory = self.get(packet_id)
        if factory is None:
            # TODO: add debug logging
            return

        pkt = factory.from_bytes(packet)

        if pkt.__class__.handle != mcli.Packet.handle:
            asyncio.create_task(pkt.handle(self.client))

        self.client.dispatch(pkt)

        # TODO: add external handlers
