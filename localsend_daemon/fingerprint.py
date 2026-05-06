import asyncio
import hashlib
import logging
import ssl

from fastapi import Request

from localsend_daemon.peers import PeerRegistry

logger = logging.getLogger(__name__)


async def extract_peer_fingerprint(request: Request, peer_registry: PeerRegistry) -> str | None:
    """Return the SHA-256 fingerprint of the peer's TLS cert, or None if unavailable.

    Tries Option A (TLS client cert on the incoming connection) first, then falls back
    to Option C (outbound TLS connection to the peer's own server).  Never reads the
    fingerprint from the request body — that field is unauthenticated and must not be
    trusted.
    """
    logger.debug("fingerprint: starting extraction for %s", request.client)

    fp = _try_option_a(request)
    if fp:
        logger.debug("fingerprint: Option A succeeded: %s", fp)
        return fp
    logger.debug("fingerprint: Option A returned nothing")

    peer_ip = request.client.host if request.client else None
    if peer_ip is None:
        logger.debug("fingerprint: no client IP, giving up")
        return None

    peer_port = peer_registry.get_port(peer_ip)
    if peer_port is None:
        logger.debug("fingerprint: peer %s not in registry, giving up", peer_ip)
        return None

    logger.debug("fingerprint: trying Option C to %s:%d", peer_ip, peer_port)
    result = await _try_option_c(peer_ip, peer_port)
    logger.debug("fingerprint: Option C result: %s", result)
    return result


def _try_option_a(request: Request) -> str | None:
    """Extract fingerprint from a TLS client cert on the incoming connection."""
    transport = request.scope.get("transport")
    logger.debug("fingerprint: Option A transport=%r", transport)
    if transport is None:
        return None
    ssl_obj = transport.get_extra_info("ssl_object")
    logger.debug("fingerprint: Option A ssl_object=%r", ssl_obj)
    if ssl_obj is None:
        return None
    cert_der: bytes | None = ssl_obj.getpeercert(binary_form=True)
    logger.debug("fingerprint: Option A cert_der present=%s", cert_der is not None)
    if not cert_der:
        return None
    return hashlib.sha256(cert_der).hexdigest().upper()


async def _try_option_c(peer_ip: str, peer_port: int) -> str | None:
    """Extract fingerprint by opening an outbound TLS connection to the peer's server."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    logger.debug("fingerprint: Option C opening connection to %s:%d", peer_ip, peer_port)
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(peer_ip, peer_port, ssl=ctx),
            timeout=3.0,
        )
    except Exception as exc:
        logger.debug("fingerprint: Option C connect failed for %s:%d: %s", peer_ip, peer_port, exc)
        return None
    logger.debug("fingerprint: Option C connected, reading cert")
    try:
        ssl_obj = writer.get_extra_info("ssl_object")
        logger.debug("fingerprint: Option C ssl_object=%r", ssl_obj)
        if ssl_obj is None:
            return None
        cert_der: bytes | None = ssl_obj.getpeercert(binary_form=True)
        logger.debug("fingerprint: Option C cert_der present=%s", cert_der is not None)
        if not cert_der:
            return None
        return hashlib.sha256(cert_der).hexdigest().upper()
    finally:
        logger.debug("fingerprint: Option C closing writer")
        writer.close()
        logger.debug("fingerprint: Option C writer closed")
