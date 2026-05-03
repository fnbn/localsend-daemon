import asyncio
from contextlib import asynccontextmanager, suppress

import uvicorn
from fastapi import FastAPI

from localsend_daemon.config import Config, load_config
from localsend_daemon.identity import make_identity
from localsend_daemon import info
from localsend_daemon.discovery import register
from localsend_daemon.discovery.multicast import listen, send_announce


@asynccontextmanager
async def lifespan(app: FastAPI):
    identity = app.state.identity
    await send_announce(identity)
    task = asyncio.create_task(listen(identity))
    yield
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task


def create_app(config: Config) -> FastAPI:
    app = FastAPI(title="localsend-daemon", lifespan=lifespan)
    app.state.identity = make_identity(config)
    app.include_router(info.router)
    app.include_router(register.router)
    return app


def run(config_path: str) -> None:
    config = load_config(config_path)
    app = create_app(config)
    uvicorn.run(app, host="0.0.0.0", port=config.port)
