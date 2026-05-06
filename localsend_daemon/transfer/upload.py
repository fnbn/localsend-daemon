from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response

from localsend_daemon.config import Config
from localsend_daemon.dependencies import get_config, get_session_store
from localsend_daemon.transfer.session import SessionStore

router = APIRouter(prefix="/api/localsend/v2")


def _open_dest(receive_dir: str, name: str):
    """Atomically create a uniquely-named file. Returns (path, open file object)."""
    base = Path(receive_dir)
    base.mkdir(parents=True, exist_ok=True)
    stem = Path(name).stem
    suffix = Path(name).suffix
    try:
        path = base / name
        return path, path.open("xb")
    except FileExistsError:
        pass
    counter = 1
    while True:
        path = base / f"{stem} ({counter}){suffix}"
        try:
            return path, path.open("xb")
        except FileExistsError:
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

    name = Path(session_file.file_name).name
    if not name or name in (".", ".."):
        raise HTTPException(status_code=400, detail="Invalid file name")

    dest, f = _open_dest(config.receive_dir, name)
    session_file.dest_path = dest

    try:
        with f:
            async for chunk in request.stream():
                f.write(chunk)
    except Exception as e:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="Unknown error by receiver") from e

    await session_store.mark_file_done(session_id, file_id)

    return Response(status_code=200)
