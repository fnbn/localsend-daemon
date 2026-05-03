import logging
import socket

from localsend_daemon.identity import Identity
from localsend_daemon.models import AnnouncePacket

logger = logging.getLogger(__name__)

MULTICAST_GROUP = "224.0.0.167"


def _build_announce(identity: Identity, *, announce: bool) -> bytes:
    packet = AnnouncePacket(
        alias=identity.alias,
        version=identity.version,
        device_type=identity.device_type,
        fingerprint=identity.fingerprint,
        port=identity.port,
        protocol=identity.protocol,
        announce=announce,
    )
    return packet.model_dump_json(by_alias=True, exclude_none=True).encode()


async def send_announce(identity: Identity) -> None:
    data = _build_announce(identity, announce=True)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
    try:
        sock.sendto(data, (MULTICAST_GROUP, identity.port))
        logger.info("Sent multicast announce to %s:%d", MULTICAST_GROUP, identity.port)
    except OSError as e:
        logger.warning("Multicast announce failed: %s", e)
    finally:
        sock.close()
