import tomllib
from typing import Literal

from pydantic import BaseModel, Field


class Config(BaseModel):
    alias: str
    port: int = Field(default=53317, ge=1, le=65535)
    receive_dir: str
    pin: str
    protocol: Literal["http", "https"] = "https"


def load_config(path: str) -> Config:
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return Config(**data)
