from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from localsend_daemon.dependencies import get_identity
from localsend_daemon.identity import Identity
from localsend_daemon.models import DeviceInfo, PeerRegistration

router = APIRouter(prefix="/api/localsend/v2")


@router.post("/register")
def post_register(
    peer: PeerRegistration,
    identity: Annotated[Identity, Depends(get_identity)],
) -> JSONResponse:
    body = DeviceInfo(
        alias=identity.alias,
        version=identity.version,
        device_type=identity.device_type,
        fingerprint=identity.fingerprint,
    )
    return JSONResponse(content=body.model_dump(by_alias=True, exclude_none=True))
