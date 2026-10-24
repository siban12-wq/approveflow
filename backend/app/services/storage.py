from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from pathlib import Path

from app.core.config import get_settings

ALLOWED_TYPES = {"application/pdf", "image/jpeg", "image/png"}
ALLOWED_EXT = {".pdf", ".jpg", ".jpeg", ".png"}


class StorageBackend(ABC):
    @abstractmethod
    def save(self, filename: str, data: bytes) -> str: ...

    @abstractmethod
    def path_for(self, key: str) -> Path: ...


class LocalStorage(StorageBackend):
    def __init__(self) -> None:
        self.root = Path(get_settings().upload_dir).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, filename: str, data: bytes) -> str:
        dest = self.root / filename
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return str(dest)

    def path_for(self, key: str) -> Path:
        return Path(key)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def virus_scan_placeholder(_data: bytes) -> bool:
    """Hook for a real scanner. Demo always returns clean."""
    return True


storage = LocalStorage()
