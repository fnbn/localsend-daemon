from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from localsend_daemon.dependencies import get_identity, get_peer_registry
from localsend_daemon.models import DeviceInfo, Identity, PeerRegistration
from localsend_daemon.peers import PeerRegistry

router = APIRouter(prefix="/api/localsend/v2")


@router.post("/register")
async def post_register(
    peer: PeerRegistration,
    request: Request,
    identity: Annotated[Identity, Depends(get_identity)],
    peer_registry: Annotated[PeerRegistry, Depends(get_peer_registry)],
) -> JSONResponse:
    sender_ip = request.client.host if request.client else None
    if sender_ip is not None and peer.port is not None:
        peer_registry.register(sender_ip, peer.port)
    body = DeviceInfo(
        alias=identity.alias,
        version=identity.version,
        device_type=identity.device_type,
        fingerprint=identity.fingerprint,
    )
    return JSONResponse(content=body.model_dump(by_alias=True, exclude_none=True))
