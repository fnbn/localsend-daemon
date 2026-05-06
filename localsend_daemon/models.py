from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

PROTOCOL_VERSION = "2.1"
DEVICE_TYPE = "headless"


class Identity(BaseModel):
    alias: str
    version: str = PROTOCOL_VERSION
    device_type: str = DEVICE_TYPE
    fingerprint: str
    port: int
    protocol: str


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
    """UDP multicast packet — DeviceInfo plus port, protocol, and announce flag."""

    port: int
    protocol: str
    announce: bool


class FileInfo(BaseModel):
    """Metadata for a single file in a prepare-upload request body."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="ignore")

    id: str
    file_name: str
    size: int
    file_type: str
    sha256: str | None = None
    preview: str | None = None


class PrepareRequest(BaseModel):
    """Request body for POST /prepare-upload."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="ignore")

    info: dict = Field(default_factory=dict)
    files: dict[str, FileInfo]


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
