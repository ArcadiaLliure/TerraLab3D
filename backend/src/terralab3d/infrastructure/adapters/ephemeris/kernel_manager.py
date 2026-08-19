"""Deterministic lifecycle and provenance for the process-global SPICE pool."""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

log = logging.getLogger("terralab3d.spice.kernels")


class KernelManifestError(RuntimeError):
    code = "KERNEL_MANIFEST_ERROR"


@dataclass(frozen=True, slots=True)
class ActiveKernel:
    kernel_id: str
    file_name: str
    path: Path
    kernel_type: str
    priority: int
    body_ids: tuple[int, ...]


class SpiceKernelManager:
    """Owns one explicitly ordered SPICE kernel generation.

    CSPICE keeps a process-global kernel pool. The manager serializes all
    access, clears pre-existing test state at the boundary, loads each file
    once, and clears only when the owning adapter closes.
    """

    _pool_lock = threading.RLock()

    def __init__(self, manifest_path: Path) -> None:
        self.manifest_path = manifest_path.resolve()
        self._payload = self._read_manifest()
        self.generation = str(self._payload["kernelGeneration"])
        self.aberration_policy = str(self._payload.get("aberrationPolicy", "LT+S"))
        self._kernels = self._resolve_kernels()
        self._handle_to_kernel: dict[int, ActiveKernel] = {}
        self._open = False
        self.load_count = 0

    @property
    def lock(self) -> threading.RLock:
        return self._pool_lock

    @property
    def kernels(self) -> tuple[ActiveKernel, ...]:
        return self._kernels

    def open(self) -> None:
        if self._open:
            return
        spice = _spice()
        with self._pool_lock:
            spice.kclear()
            try:
                for kernel in self._kernels:
                    spice.furnsh(str(kernel.path))
                    self.load_count += 1
                    log.debug(
                        "MGP: [KernelManager.py] [load] "
                        "[Kernel carregat type=%s file=%s generation=%s]",
                        kernel.kernel_type,
                        kernel.file_name,
                        self.generation,
                    )
                self._index_handles(spice)
                self._open = True
            except Exception as exc:
                spice.kclear()
                self._handle_to_kernel.clear()
                self.load_count = 0
                raise KernelManifestError(
                    f"Cannot load SPICE generation {self.generation}: {exc}"
                ) from exc

    def close(self) -> None:
        if not self._open:
            return
        spice = _spice()
        with self._pool_lock:
            spice.kclear()
            self._handle_to_kernel.clear()
            self._open = False
            log.debug(
                "MGP: [KernelManager.py] [close] [Kernel pool net generation=%s]",
                self.generation,
            )

    def active_kernel_id(self, body_id: int, et: float) -> str | None:
        spice = _spice()
        with self._pool_lock:
            try:
                result = spice.spksfs(body_id, et, 128)
                if len(result) == 4:
                    handle, _, _, found = result
                    if not found:
                        return None
                else:
                    handle = result[0]
                kernel = self._handle_to_kernel.get(int(handle))
                return kernel.kernel_id if kernel is not None else None
            except Exception:
                return None

    def _read_manifest(self) -> dict[str, Any]:
        try:
            with self.manifest_path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            raise KernelManifestError(f"Cannot read {self.manifest_path}: {exc}") from exc
        if not payload.get("kernelGeneration") or not isinstance(payload.get("kernels"), list):
            raise KernelManifestError("Kernel manifest lacks generation or kernels")
        return payload

    def _resolve_kernels(self) -> tuple[ActiveKernel, ...]:
        kernels_root = self.manifest_path.parent.parent.resolve()
        sky_root = kernels_root.parent.parent.resolve()
        records: list[ActiveKernel] = []
        for raw in self._payload["kernels"]:
            if not raw.get("installed"):
                continue
            base = sky_root if raw.get("relativeBase") == "sky" else kernels_root
            path = (base / str(raw["relativePath"])).resolve()
            if sky_root not in path.parents or not path.is_file():
                raise KernelManifestError(f"Kernel is missing or outside data_root: {path}")
            records.append(
                ActiveKernel(
                    kernel_id=str(raw["kernelId"]),
                    file_name=str(raw["fileName"]),
                    path=path,
                    kernel_type=str(raw["kernelType"]),
                    priority=int(raw["priority"]),
                    body_ids=tuple(int(item) for item in raw.get("bodyIds", ())),
                )
            )
        type_order = {"LSK": 0, "PCK": 1, "FK": 2, "SPK": 3}
        records.sort(key=lambda item: (type_order.get(item.kernel_type, 9), item.priority))
        if not any(item.kernel_type == "LSK" for item in records):
            raise KernelManifestError("No LSK installed")
        if not any(item.kernel_type == "PCK" for item in records):
            raise KernelManifestError("No PCK installed")
        if not any(item.kernel_type == "SPK" for item in records):
            raise KernelManifestError("No SPK installed")
        return tuple(records)

    def _index_handles(self, spice: Any) -> None:
        count = int(spice.ktotal("ALL"))
        by_path = {str(item.path).casefold(): item for item in self._kernels}
        for index in range(count):
            result = spice.kdata(index, "ALL")
            if len(result) == 5:
                file_name, _, _, handle, found = result
                if not found:
                    continue
            else:
                file_name, _, _, handle = result
            kernel = by_path.get(str(Path(file_name).resolve()).casefold())
            if kernel is not None:
                self._handle_to_kernel[int(handle)] = kernel


def _spice() -> Any:
    try:
        import spiceypy as spice
    except ImportError as exc:
        raise KernelManifestError("spiceypy is not installed") from exc
    return spice
