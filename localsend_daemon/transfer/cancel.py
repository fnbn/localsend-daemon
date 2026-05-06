from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from localsend_daemon.dependencies import get_session_store
from localsend_daemon.transfer.session import SessionStore

router = APIRouter(prefix="/api/localsend/v2")


@router.post("/cancel", status_code=200)
async def cancel(
    session_store: Annotated[SessionStore, Depends(get_session_store)],
    session_id: str = Query(alias="sessionId"),
) -> Response:
    session = await session_store.cancel(session_id=session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    for sf in session.files.values():
        if sf.dest_path is not None:
            sf.dest_path.unlink(missing_ok=True)

    return Response(status_code=200)
