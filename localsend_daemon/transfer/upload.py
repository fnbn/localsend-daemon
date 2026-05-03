from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response

from localsend_daemon.config import Config
from localsend_daemon.dependencies import get_config, get_session_store
from localsend_daemon.transfer.session import SessionStore

router = APIRouter(prefix="/api/localsend/v2")


def _safe_dest(receive_dir: str, file_name: str) -> Path:
    base = Path(receive_dir)
    name = Path(file_name).name  # strip any directory components
    dest = base / name
    if not dest.exists():
        return dest
    stem = Path(name).stem
    suffix = Path(name).suffix
    counter = 1
    while True:
        candidate = base / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


@router.post("/upload", status_code=200)
async def upload(
    request: Request,
    config: Annotated[Config, Depends(get_config)],
    session_store: Annotated[SessionStore, Depends(get_session_store)],
    session_id: str = Query(alias="sessionId"),
    file_id: str = Query(alias="fileId"),
    token: str = Query(alias="token"),
) -> Response:
    sender_ip = request.client.host if request.client else "unknown"

    session = await session_store.get_by_id(session_id)
    if session is None or session.sender_ip != sender_ip:
        raise HTTPException(status_code=403, detail="Invalid token or IP address")

    session_file = session.files.get(file_id)
    if session_file is None or session_file.token != token:
        raise HTTPException(status_code=403, detail="Invalid token or IP address")

    dest = _safe_dest(config.receive_dir, session_file.file_name)
    dest.parent.mkdir(parents=True, exist_ok=True)

    try:
        with dest.open("wb") as f:
            async for chunk in request.stream():
                f.write(chunk)
    except Exception as e:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="Unknown error by receiver") from e

    await session_store.mark_file_done(session_id, file_id)

    return Response(status_code=200)
