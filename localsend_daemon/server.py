import asyncio
import logging
import tempfile
from contextlib import asynccontextmanager, suppress
from pathlib import Path

import uvicorn
from fastapi import FastAPI

logger = logging.getLogger(__name__)

from localsend_daemon.config import Config, load_config
from localsend_daemon.identity import make_identity
from localsend_daemon import info
from localsend_daemon.discovery import register
from localsend_daemon.discovery.multicast import listen, send_announce
from localsend_daemon.tls import cert_fingerprint, generate_cert
from localsend_daemon.transfer import cancel, prepare, upload
from localsend_daemon.transfer.session import SessionStore


@asynccontextmanager
async def lifespan(app: FastAPI):
    identity = app.state.identity
    await send_announce(identity)
    task = asyncio.create_task(listen(identity))
    task.add_done_callback(
        lambda t: logger.error("Multicast listener stopped: %s", t.exception(), exc_info=t.exception())
        if not t.cancelled() and t.exception() else None
    )
    yield
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task


def create_app(config: Config, fingerprint: str | None = None) -> FastAPI:
    app = FastAPI(title="localsend-daemon", lifespan=lifespan)
    app.state.config = config
    app.state.identity = make_identity(config, fingerprint)
    app.state.session_store = SessionStore()
    app.include_router(info.router)
    app.include_router(register.router)
    app.include_router(prepare.router)
    app.include_router(upload.router)
    app.include_router(cancel.router)
    return app


def run(config_path: str, log_level: str = "ERROR") -> None:
    config = load_config(config_path)
    uvicorn_log_level = log_level.lower()

    if config.protocol == "https":
        cert_pem, key_pem, cert_der = generate_cert()
        fingerprint = cert_fingerprint(cert_der)
        with tempfile.TemporaryDirectory() as tmpdir:
            cert_path = Path(tmpdir) / "cert.pem"
            key_path = Path(tmpdir) / "key.pem"
            cert_path.write_bytes(cert_pem)
            key_path.write_bytes(key_pem)
            app = create_app(config, fingerprint)
            uvicorn.run(
                app,
                host="0.0.0.0",
                port=config.port,
                ssl_certfile=str(cert_path),
                ssl_keyfile=str(key_path),
                log_level=uvicorn_log_level,
            )
    else:
        app = create_app(config)
        uvicorn.run(app, host="0.0.0.0", port=config.port, log_level=uvicorn_log_level)
