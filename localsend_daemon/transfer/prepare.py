import logging
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from localsend_daemon.config import Config
from localsend_daemon.dependencies import get_config, get_peer_registry, get_session_store, get_trust_store
from localsend_daemon.fingerprint import extract_peer_fingerprint
from localsend_daemon.models import PrepareRequest
from localsend_daemon.peers import PeerRegistry
from localsend_daemon.transfer.session import SessionStore
from localsend_daemon.trust import TrustStore

router = APIRouter(prefix="/api/localsend/v2")
logger = logging.getLogger(__name__)


def _sender_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.post("/prepare-upload")
async def prepare_upload(
    body: PrepareRequest,
    request: Request,
    config: Annotated[Config, Depends(get_config)],
    session_store: Annotated[SessionStore, Depends(get_session_store)],
    peer_registry: Annotated[PeerRegistry, Depends(get_peer_registry)],
    trust_store: Annotated[TrustStore | None, Depends(get_trust_store)],
    pin: str | None = Query(default=None),
) -> JSONResponse:
    sender_ip = _sender_ip(request)

    need_fp = trust_store is not None or config.trust_on_first_pin
    peer_fp = await extract_peer_fingerprint(request, peer_registry) if need_fp else None

    if (
        config.protocol == "https"
        and trust_store is not None
        and peer_fp is not None
        and trust_store.contains(peer_fp)
    ):
        logger.info("PIN bypass for trusted fingerprint %s from %s", peer_fp, sender_ip)
    else:
        if pin != config.pin:
            detail = "PIN required" if pin is None else "Invalid PIN"
            raise HTTPException(status_code=401, detail=detail)
        if (
            config.trust_on_first_pin
            and config.protocol == "https"
            and trust_store is not None
            and peer_fp is not None
        ):
            trust_store.add(
                peer_fp,
                comment=f"auto-added {datetime.now(UTC):%Y-%m-%d} from {sender_ip}",
            )
            logger.warning("Auto-trusted new fingerprint %s from %s after PIN", peer_fp, sender_ip)

    session = await session_store.create(sender_ip, body.files)
    if session is None:
        raise HTTPException(status_code=409, detail="Blocked by another session")

    return JSONResponse({
        "sessionId": session.session_id,
        "files": {fid: sf.token for fid, sf in session.files.items()},
    })
