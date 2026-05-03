from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from localsend_daemon.identity import Identity

router = APIRouter(prefix='/api/localsend/v2')


class InfoResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    alias: str
    version: str
    device_model: str | None = None
    device_type: str
    fingerprint: str
    download: bool = False


def _get_identity(request: Request) -> Identity:
    return request.app.state.identity


@router.get("/info")
def get_info(identity: Annotated[Identity, Depends(_get_identity)]) -> JSONResponse:
    body = InfoResponse(
        alias=identity.alias,
        version=identity.version,
        device_type=identity.device_type,
        fingerprint=identity.fingerprint,
    )
    return JSONResponse(content=body.model_dump(by_alias=True, exclude_none=True))
