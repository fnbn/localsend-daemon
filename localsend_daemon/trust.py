import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

_HEX64 = re.compile(r"^[0-9A-F]{64}$")


def _normalize(fp: str) -> str:
    return fp.replace(":", "").upper()


def _is_valid(fp: str) -> bool:
    return bool(_HEX64.match(fp))


def _parse_file(path: Path) -> set[str]:
    if not path.exists():
        return set()
    trusted: set[str] = set()
    for lineno, raw in enumerate(path.read_text().splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        fp = _normalize(line.split()[0])
        if _is_valid(fp):
            trusted.add(fp)
        else:
            logger.warning("trust: invalid fingerprint on line %d: %r", lineno, line)
    return trusted


def _atomic_append(path: Path, fp: str, comment: str | None) -> None:
    entry = f"{fp}  # {comment}" if comment else fp
    existing = path.read_text() if path.exists() else ""
    if existing and not existing.endswith("\n"):
        existing += "\n"
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(existing + entry + "\n")
    tmp.chmod(0o600)
    tmp.replace(path)
    path.chmod(0o600)


class TrustStore:
    """In-memory trusted-fingerprint set backed by a file, loaded at construction."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._trusted: set[str] = _parse_file(path)

    def contains(self, fingerprint: str) -> bool:
        return _normalize(fingerprint) in self._trusted

    def add(self, fingerprint: str, comment: str | None = None) -> None:
        fp = _normalize(fingerprint)
        if not _is_valid(fp):
            logger.warning("trust: refusing to add invalid fingerprint %r", fp)
            return
        if fp in self._trusted:
            return
        self._trusted.add(fp)
        _atomic_append(self._path, fp, comment)
