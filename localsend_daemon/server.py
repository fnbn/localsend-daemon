import asyncio
import tempfile
from contextlib import asynccontextmanager, suppress
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from localsend_daemon.config import Config, load_config
from localsend_daemon.identity import make_identity
from localsend_daemon import info
from localsend_daemon.discovery import register
from localsend_daemon.discovery.multicast import listen, send_announce
from localsend_daemon.tls import cert_fingerprint, generate_cert


@asynccontextmanager
async def lifespan(app: FastAPI):
    identity = app.state.identity
    await send_announce(identity)
    task = asyncio.create_task(listen(identity))
    yield
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task


def create_app(config: Config, fingerprint: str | None = None) -> FastAPI:
    app = FastAPI(title="localsend-daemon", lifespan=lifespan)
    app.state.identity = make_identity(config, fingerprint)
    app.include_router(info.router)
    app.include_router(register.router)
    return app


def run(config_path: str) -> None:
    config = load_config(config_path)

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
            )
    else:
        app = create_app(config)
        uvicorn.run(app, host="0.0.0.0", port=config.port)
