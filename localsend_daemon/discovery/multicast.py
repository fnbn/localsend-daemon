import asyncio
import logging
import socket
import struct
import time

import httpx

from localsend_daemon.models import Identity
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


def _register_body(identity: Identity) -> dict:
    packet = AnnouncePacket(
        alias=identity.alias,
        version=identity.version,
        device_type=identity.device_type,
        fingerprint=identity.fingerprint,
        port=identity.port,
        protocol=identity.protocol,
        announce=False,
    )
    return packet.model_dump(by_alias=True, exclude_none=True, exclude={"announce"})


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


class _AnnounceListener(asyncio.DatagramProtocol):
    def __init__(self, identity: Identity) -> None:
        self.identity = identity
        self._last_response: dict[str, float] = {}
        self.transport: asyncio.DatagramTransport | None = None

    def connection_made(self, transport: asyncio.DatagramTransport) -> None:
        self.transport = transport

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        asyncio.create_task(self._handle(data, addr))

    async def _handle(self, data: bytes, addr: tuple[str, int]) -> None:
        logger.info('HAAAA')
        try:
            packet = AnnouncePacket.model_validate_json(data)
        except Exception:
            logger.warning('Received multicast packet, but cannot parse announcement.')
            return

        if not packet.announce:
            return
        if packet.fingerprint == self.identity.fingerprint:
            return  # skip self

        now = time.monotonic()
        if now - self._last_response.get(packet.fingerprint, 0) < 1.0:
            return
        self._last_response[packet.fingerprint] = now

        sender_ip, _ = addr
        logger.info("Received announce from %s:%d (%s)", sender_ip, packet.port, packet.alias)

        # UDP response — works for peers that can't accept incoming TCP (e.g. iOS)
        if self.transport:
            self.transport.sendto(
                _build_announce(self.identity, announce=False),
                (MULTICAST_GROUP, self.identity.port),
            )

        # HTTP POST — primary response for peers that accept incoming connections
        url = f"{packet.protocol}://{sender_ip}:{packet.port}/api/localsend/v2/register"
        try:
            async with httpx.AsyncClient(timeout=5, verify=False) as client:
                await client.post(url, json=_register_body(self.identity))
        except Exception as e:
            logger.debug("POST /register to %s failed: %s", url, e)


def _make_listen_socket(port: int) -> socket.socket:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    except AttributeError:
        pass
    sock.bind(("", port))
    mreq = struct.pack("4sL", socket.inet_aton(MULTICAST_GROUP), socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    sock.setblocking(False)
    return sock


async def listen(identity: Identity) -> None:
    loop = asyncio.get_running_loop()
    sock = _make_listen_socket(identity.port)
    transport, _ = await loop.create_datagram_endpoint(
        lambda: _AnnounceListener(identity),
        sock=sock,
    )
    try:
        await asyncio.Future()
    finally:
        transport.close()
