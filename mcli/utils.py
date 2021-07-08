import hashlib
import ipaddress
from typing import ByteString, List


def is_valid_ip(host: str) -> bool:
    """Return True if an host is a valid ipv4 or ipv6."""
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def minecraft_sha1(*datas: List[ByteString]) -> str:
    hash_ = hashlib.sha1()
    for data in datas:
        if isinstance(data, str):
            data = data.encode('utf-8')

        hash_.update(data)

    return '{:x}'.format(int.from_bytes(hash_.digest(), byteorder='big', signed=True))
