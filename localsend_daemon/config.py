import tomllib
from pydantic import BaseModel


class Config(BaseModel):
    alias: str
    port: int = 53317
    receive_dir: str
    pin: str
    protocol: str = "https"


def load_config(path: str) -> Config:
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return Config(**data)
