from fastapi import Request

from localsend_daemon.identity import Identity


def get_identity(request: Request) -> Identity:
    return request.app.state.identity
