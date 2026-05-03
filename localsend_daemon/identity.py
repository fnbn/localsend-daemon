import uuid

from localsend_daemon.config import Config
from localsend_daemon.models import Identity


def make_identity(config: Config, fingerprint: str | None = None) -> Identity:
    return Identity(
        alias=config.alias,
        fingerprint=fingerprint or str(uuid.uuid4()),
        port=config.port,
        protocol=config.protocol,
    )
