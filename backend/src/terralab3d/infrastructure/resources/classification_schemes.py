"""Atomic persistence for user-authored external classification schemes."""

from __future__ import annotations

import json
import os
from pathlib import Path
from threading import RLock
from typing import Any

from terralab3d.domain.surface.tlst import SourceScheme, TlstValidationError
from terralab3d.infrastructure.adapters.surface.tlst_catalog import (
    LandCoverSchemeRegistry,
    parse_source_scheme,
    source_scheme_to_payload,
)
from terralab3d.infrastructure.app_paths import resolve_data_root


class UserClassificationSchemeRepository:
    SCHEMA_VERSION = 1

    def __init__(
        self,
        registry: LandCoverSchemeRegistry,
        path: Path | None = None,
    ) -> None:
        self._registry = registry
        self.path = path or (
            resolve_data_root() / "config" / "classification_schemes.json"
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._document: dict[str, Any] = {
            "schemaVersion": self.SCHEMA_VERSION,
            "schemes": [],
        }
        self.load()

    def load(self) -> None:
        with self._lock:
            if self.path.exists():
                payload = json.loads(self.path.read_text(encoding="utf-8"))
                if not isinstance(payload, dict) or not isinstance(payload.get("schemes", []), list):
                    raise TlstValidationError(
                        "classification_schemes.json must contain a schemes array"
                    )
                self._document = payload
            for raw in self._document.get("schemes", []):
                if not isinstance(raw, dict):
                    raise TlstValidationError("User schemes must be JSON objects")
                self._registry.register(
                    parse_source_scheme(raw, self._registry.taxonomy)
                )

    def upsert(self, scheme: SourceScheme) -> None:
        self._registry.register(scheme)
        identity = (
            scheme.scheme_key,
            scheme.scheme_version,
            scheme.mapping_revision,
        )
        payload = source_scheme_to_payload(scheme)
        with self._lock:
            schemes = self._document.setdefault("schemes", [])
            index = next(
                (
                    index
                    for index, item in enumerate(schemes)
                    if isinstance(item, dict)
                    and (
                        item.get("scheme_key"),
                        item.get("scheme_version"),
                        item.get("mapping_revision", "1"),
                    ) == identity
                ),
                None,
            )
            if index is None:
                schemes.append(payload)
            elif schemes[index] != payload:
                raise TlstValidationError(
                    f"User mapping revision {identity!r} cannot be overwritten"
                )
            self._save()

    def _save(self) -> None:
        self._document["schemaVersion"] = self.SCHEMA_VERSION
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(self._document, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(self.path)
