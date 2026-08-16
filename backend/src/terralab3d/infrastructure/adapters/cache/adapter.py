"""Byte-governed LRU and Persistent Cache for terrain and surface resources.

Keeps memory usage strictly bounded while avoiding re-sampling when
switching styles (BASE <-> CATEGORICAL_ORIGINAL) or re-visiting chunks.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import tempfile
import threading
from collections import OrderedDict
from pathlib import Path
from typing import Callable, Generic, TypeVar

log = logging.getLogger("terralab3d.cache")

T = TypeVar("T")


class ByteLRUCache(Generic[T]):
    """In-memory LRU cache strictly bounded by byte length.

    Evicts the least recently used entries when the byte budget is exceeded.
    """

    def __init__(
        self,
        max_bytes: int,
        byte_sizer: Callable[[T], int],
        *,
        name: str = "byte_lru_cache",
    ) -> None:
        self._max_bytes = max(1024, int(max_bytes))
        self._byte_sizer = byte_sizer
        self._name = name
        self._cache: OrderedDict[str, T] = OrderedDict()
        self._current_bytes = 0
        self._peak_bytes = 0
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._lock = threading.Lock()

    @property
    def current_bytes(self) -> int:
        return self._current_bytes

    @property
    def max_bytes(self) -> int:
        return self._max_bytes

    @property
    def entry_count(self) -> int:
        return len(self._cache)

    def get(self, key: str) -> T | None:
        with self._lock:
            val = self._cache.pop(key, None)
            if val is not None:
                self._cache[key] = val
                self._hits += 1
                return val
            self._misses += 1
            return None

    def put(self, key: str, value: T) -> None:
        val_bytes = self._byte_sizer(value)
        with self._lock:
            if key in self._cache:
                old = self._cache.pop(key)
                self._current_bytes -= self._byte_sizer(old)
            self._cache[key] = value
            self._current_bytes += val_bytes
            if self._current_bytes > self._peak_bytes:
                self._peak_bytes = self._current_bytes

            # Evict oldest until under budget
            while self._current_bytes > self._max_bytes and self._cache:
                _, oldest = self._cache.popitem(last=False)
                self._current_bytes -= self._byte_sizer(oldest)
                self._evictions += 1

    def remove(self, key: str) -> bool:
        with self._lock:
            old = self._cache.pop(key, None)
            if old is not None:
                self._current_bytes -= self._byte_sizer(old)
                return True
            return False

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            self._current_bytes = 0

    def metrics(self) -> dict[str, int | float]:
        with self._lock:
            total = self._hits + self._misses
            hit_ratio = float(self._hits / total) if total > 0 else 0.0
            return {
                f"{self._name}_currentBytes": self._current_bytes,
                f"{self._name}_peakBytes": self._peak_bytes,
                f"{self._name}_maxBytes": self._max_bytes,
                f"{self._name}_entryCount": len(self._cache),
                f"{self._name}_hits": self._hits,
                f"{self._name}_misses": self._misses,
                f"{self._name}_hitRatio": hit_ratio,
                f"{self._name}_evictions": self._evictions,
            }


class PersistentDiskCache:
    """Disk-backed persistent cache with atomic writes and byte budget."""

    def __init__(
        self,
        directory: Path,
        max_bytes: int = 512 * 1024 * 1024,
        *,
        version_tag: str = "v1",
    ) -> None:
        self._directory = directory
        self._max_bytes = max(1024 * 1024, int(max_bytes))
        self._version_tag = version_tag
        self._lock = threading.Lock()
        self._directory.mkdir(parents=True, exist_ok=True)

    def read_bytes(self, key: str) -> bytes | None:
        file_path = self._key_to_path(key)
        if not file_path.is_file():
            return None
        try:
            with self._lock:
                return file_path.read_bytes()
        except OSError as exc:
            log.warning("MGP: [persistent_cache] [read failed key=%s error=%s]", key, exc)
            return None

    def write_bytes(self, key: str, payload: bytes) -> bool:
        file_path = self._key_to_path(key)
        try:
            with self._lock:
                # Atomic write: write to temp file then rename
                temp_file = self._directory / f".tmp_{os.getpid()}_{hashlib.blake2b(key.encode(), digest_size=6).hexdigest()}"
                temp_file.write_bytes(payload)
                temp_file.replace(file_path)
                self._trim_disk_budget()
                return True
        except OSError as exc:
            log.warning("MGP: [persistent_cache] [write failed key=%s error=%s]", key, exc)
            return False

    def clear(self) -> None:
        with self._lock:
            for item in self._directory.glob("*.bin"):
                try:
                    item.unlink(missing_ok=True)
                except OSError:
                    pass

    def _key_to_path(self, key: str) -> Path:
        hashed = hashlib.blake2b(f"{self._version_tag}:{key}".encode(), digest_size=20).hexdigest()
        return self._directory / f"{hashed}.bin"

    def _trim_disk_budget(self) -> None:
        try:
            files = list(self._directory.glob("*.bin"))
            total_bytes = sum(f.stat().st_size for f in files)
            if total_bytes <= self._max_bytes:
                return
            # Sort by mtime ascending (oldest first)
            sorted_files = sorted(files, key=lambda f: f.stat().st_mtime)
            for f in sorted_files:
                if total_bytes <= self._max_bytes:
                    break
                sz = f.stat().st_size
                f.unlink(missing_ok=True)
                total_bytes -= sz
        except OSError as exc:
            log.debug("MGP: [persistent_cache] [trim failed error=%s]", exc)
