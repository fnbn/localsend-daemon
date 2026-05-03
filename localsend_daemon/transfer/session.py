import asyncio
import secrets
from dataclasses import dataclass, field

from localsend_daemon.models import FileInfo


@dataclass
class SessionFile:
    file_name: str
    size: int
    file_type: str
    token: str = field(default_factory=lambda: secrets.token_urlsafe(16))


@dataclass
class Session:
    session_id: str
    sender_ip: str
    files: dict[str, SessionFile]  # fileId -> SessionFile


class SessionStore:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._session: Session | None = None

    async def create(self, sender_ip: str, files: dict[str, FileInfo]) -> Session | None:
        """Create a new session. Returns None if a session is already active."""
        async with self._lock:
            if self._session is not None:
                return None
            self._session = Session(
                session_id=secrets.token_urlsafe(16),
                sender_ip=sender_ip,
                files={
                    fid: SessionFile(
                        file_name=f.file_name,
                        size=f.size,
                        file_type=f.file_type,
                    )
                    for fid, f in files.items()
                },
            )
            return self._session

    async def get_by_id(self, session_id: str) -> Session | None:
        s = self._session
        return s if s and s.session_id == session_id else None

    async def get_by_ip(self, sender_ip: str) -> Session | None:
        s = self._session
        return s if s and s.sender_ip == sender_ip else None

    async def cancel(
        self, *, session_id: str | None = None, sender_ip: str | None = None
    ) -> Session | None:
        async with self._lock:
            s = self._session
            if s is None:
                return None
            if session_id is not None and s.session_id != session_id:
                return None
            if sender_ip is not None and s.sender_ip != sender_ip:
                return None
            self._session = None
            return s
