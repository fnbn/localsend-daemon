from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from localsend_daemon.dependencies import get_identity
from localsend_daemon.identity import Identity
from localsend_daemon.models import DeviceInfo

router = APIRouter()


class V1InfoResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    alias: str
    device_model: str | None = None
    device_type: str


@router.get("/api/localsend/v1/info")
def get_info_v1(identity: Annotated[Identity, Depends(get_identity)]) -> JSONResponse:
    body = V1InfoResponse(alias=identity.alias, device_type=identity.device_type)
    return JSONResponse(content=body.model_dump(by_alias=True, exclude_none=True))


@router.get("/api/localsend/v2/info")
def get_info(identity: Annotated[Identity, Depends(get_identity)]) -> JSONResponse:
    body = DeviceInfo(
        alias=identity.alias,
        version=identity.version,
        device_type=identity.device_type,
        fingerprint=identity.fingerprint,
    )
    return JSONResponse(content=body.model_dump(by_alias=True, exclude_none=True))
