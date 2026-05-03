from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from localsend_daemon.config import Config
from localsend_daemon.dependencies import get_config, get_session_store
from localsend_daemon.models import PrepareRequest
from localsend_daemon.transfer.session import SessionStore

router = APIRouter(prefix="/api/localsend/v2")


def _sender_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.post("/prepare-upload")
async def prepare_upload(
    body: PrepareRequest,
    request: Request,
    config: Annotated[Config, Depends(get_config)],
    session_store: Annotated[SessionStore, Depends(get_session_store)],
    pin: str | None = Query(default=None),
) -> JSONResponse:
    if pin != config.pin:
        detail = "PIN required" if pin is None else "Invalid PIN"
        raise HTTPException(status_code=401, detail=detail)

    session = await session_store.create(_sender_ip(request), body.files)
    if session is None:
        raise HTTPException(status_code=409, detail="Blocked by another session")

    return JSONResponse({
        "sessionId": session.session_id,
        "files": {fid: sf.token for fid, sf in session.files.items()},
    })
