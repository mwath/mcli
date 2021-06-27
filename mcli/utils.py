import ipaddress


def is_valid_ip(host: str) -> bool:
    """Return True if an host is a valid ipv4 or ipv6."""
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False
