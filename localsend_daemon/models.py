from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class DeviceInfo(BaseModel):
    """Wire-format device identity used in /info and /register responses."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    alias: str
    version: str
    device_model: str | None = None
    device_type: str
    fingerprint: str
    download: bool = False


class AnnouncePacket(DeviceInfo):
    """UDP multicast packet — DeviceInfo plus port, protocol, and announce flags."""

    port: int
    protocol: str
    announce: bool
    announcement: bool | None = None  # v1 backward compat, mirrors announce


class PeerRegistration(BaseModel):
    """Incoming peer identity from POST /register."""

    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, extra="ignore"
    )

    alias: str
    version: str
    device_model: str | None = None
    device_type: str | None = None
    fingerprint: str
    port: int | None = None
    protocol: str | None = None
    download: bool = False
