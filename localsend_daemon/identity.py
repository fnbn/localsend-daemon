import uuid
from pydantic import BaseModel

from localsend_daemon.config import Config

PROTOCOL_VERSION = "2.0"
DEVICE_TYPE = "headless"
PROTOCOL = "http"


class Identity(BaseModel):
    alias: str
    version: str = PROTOCOL_VERSION
    device_type: str = DEVICE_TYPE
    fingerprint: str
    port: int
    protocol: str = PROTOCOL


def make_identity(config: Config) -> Identity:
    return Identity(
        alias=config.alias,
        fingerprint=str(uuid.uuid4()),
        port=config.port,
    )
