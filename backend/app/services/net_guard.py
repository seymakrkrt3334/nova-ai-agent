import ipaddress
import socket
from urllib.parse import urlparse

class UnsafeURL(Exception):
    """The URL is not safe to fetch."""


BLOCKED_HOSTS = {
    "localhost",
    "localhost.localdomain",
    "metadata.google.internal",
}


def is_public_ip(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return False
    return not (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    )


def _default_resolve(host: str) -> list[str]:
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise UnsafeURL from exc
    addresses = []
    for info in infos:
        address = info[4][0]
        if address.startswith("::ffff:"):
            address = address.split("::ffff:", 1)[1]
        addresses.append(address)
    return addresses


def validate_public_url(url: str, resolve=None) -> str:
    if not isinstance(url, str):
        raise UnsafeURL
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise UnsafeURL
    if parsed.username or parsed.password:
        raise UnsafeURL
    host = parsed.hostname.lower().rstrip(".")
    if host in BLOCKED_HOSTS or host.endswith(".local") or host.endswith(".internal"):
        raise UnsafeURL
    if _literal_ip(host) is not None:
        if not is_public_ip(host):
            raise UnsafeURL
        return parsed.geturl()
    resolver = resolve or _default_resolve
    addresses = list(resolver(host) or [])
    if not addresses or any(not is_public_ip(address) for address in addresses):
        raise UnsafeURL
    return parsed.geturl()


def citation_url(url: str) -> str | None:
    if not isinstance(url, str):
        return None
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    if parsed.username or parsed.password:
        return None
    host = parsed.hostname.lower().rstrip(".")
    if host in BLOCKED_HOSTS or host.endswith(".local") or host.endswith(".internal"):
        return None
    if _literal_ip(host) is not None and not is_public_ip(host):
        return None
    return parsed.geturl()


def _literal_ip(host: str):
    try:
        return ipaddress.ip_address(host)
    except ValueError:
        return None
