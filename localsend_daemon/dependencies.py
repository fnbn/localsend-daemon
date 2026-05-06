from fastapi import Request

from localsend_daemon.config import Config
from localsend_daemon.models import Identity
from localsend_daemon.peers import PeerRegistry
from localsend_daemon.transfer.session import SessionStore
from localsend_daemon.trust import TrustStore


def get_config(request: Request) -> Config:
    return request.app.state.config


def get_identity(request: Request) -> Identity:
    return request.app.state.identity


def get_session_store(request: Request) -> SessionStore:
    return request.app.state.session_store


def get_peer_registry(request: Request) -> PeerRegistry:
    return request.app.state.peer_registry


def get_trust_store(request: Request) -> TrustStore | None:
    return getattr(request.app.state, "trust_store", None)
