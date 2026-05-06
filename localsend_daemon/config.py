import tomllib
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class Config(BaseModel):
    alias: str
    port: int = Field(default=53317, ge=1, le=65535)
    receive_dir: str
    pin: str
    protocol: Literal["http", "https"] = "https"
    trusted_fingerprints_path: str | None = None
    trust_on_first_pin: bool = False

    @model_validator(mode="after")
    def _validate_trust_config(self) -> "Config":
        if self.trust_on_first_pin and self.trusted_fingerprints_path is None:
            raise ValueError("trust_on_first_pin=true requires trusted_fingerprints_path to be set")
        return self


def load_config(path: str) -> Config:
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return Config(**data)
