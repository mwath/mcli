import mcli
import warnings


class Manager:
    register = {}

    def __init__(self, client: 'mcli.Client'):
        self.client = client

    def add(self, cls):
        if cls._id in self.register:
            warnings.warn(f'Packet id 0x{cls._id:x} ({cls.__name__}) is already registered!')
        else:
            self.register[cls._id] = cls

    def get(self, packet_id: int):
        # return self.recv.get(packet_id, version=self.client.protocol.version)
        return self.register.get(packet_id)
