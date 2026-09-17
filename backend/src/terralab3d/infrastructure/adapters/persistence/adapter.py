"""Persistència local de preferències amb substitució atòmica."""

from __future__ import annotations

import os
import shutil
import time
import uuid
from datetime import datetime, timezone
from abc import ABC, abstractmethod
from pathlib import Path

from terralab3d.infrastructure.app_paths import resolve_preferences_dir


class PersistenceAdapterSpec(ABC):
    @abstractmethod
    def open(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError


class AtomicTextPreferencesAdapter:
    """Implementa PreferencesPort sense exposar rutes arbitràries."""

    def __init__(self, root: Path | None = None) -> None:
        self._root = root or resolve_preferences_dir()

    def load_text(self, key: str) -> str | None:
        path = self._path(key)
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8")

    def save_text(self, key: str, value: str) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(f"{path.suffix}.{uuid.uuid4().hex}.tmp")
        try:
            temporary.write_text(value, encoding="utf-8")
            # Windows may briefly retain a reader/indexer handle on the target.
            # Retrying the same atomic rename is bounded and keeps the old file
            # intact until replacement succeeds.
            for attempt in range(5):
                try:
                    os.replace(temporary, path)
                    return
                except PermissionError:
                    if attempt == 4:
                        raise
                    time.sleep(0.02 * (attempt + 1))
        finally:
            temporary.unlink(missing_ok=True)

    def backup_invalid(self, key: str) -> Path | None:
        """Copia un document invàlid sense alterar-ne l'original."""
        path = self._path(key)
        if not path.exists():
            return None
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = path.with_name(f"{path.stem}.invalid-{timestamp}{path.suffix}")
        counter = 1
        while backup.exists():
            backup = path.with_name(f"{path.stem}.invalid-{timestamp}-{counter}{path.suffix}")
            counter += 1
        shutil.copy2(path, backup)
        return backup

    def _path(self, key: str) -> Path:
        normalized = key.lower()
        if (
            not key
            or key.startswith(".")
            or key.endswith(".")
            or ".." in key
            or any(char not in "abcdefghijklmnopqrstuvwxyz0123456789_.-" for char in normalized)
        ):
            raise ValueError("Clau de preferències no vàlida")
        return self._root / f"{key}.json"
