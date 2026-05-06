import asyncio
import secrets
from dataclasses import dataclass, field
from pathlib import Path

from localsend_daemon.models import FileInfo


@dataclass
class SessionFile:
    file_name: str
    size: int
    file_type: str
    token: str = field(default_factory=lambda: secrets.token_urlsafe(16))
    dest_path: Path | None = None  # set by upload handler before writing


@dataclass
class Session:
    session_id: str
    sender_ip: str
    files: dict[str, SessionFile]  # fileId -> SessionFile
    received_files: set[str] = field(default_factory=set)
    cancel_event: asyncio.Event = field(default_factory=asyncio.Event)


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

    async def mark_file_done(self, session_id: str, file_id: str) -> bool:
        """Mark file received. Returns True and clears session when all files are done."""
        async with self._lock:
            s = self._session
            if s is None or s.session_id != session_id:
                return False
            s.received_files.add(file_id)
            if s.received_files >= s.files.keys():
                self._session = None
            return True

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
            s.cancel_event.set()
            self._session = None
            return s
