"""Atomic, compatibility-preserving persistence for ordered data sources."""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from threading import RLock
from typing import Any

from terralab3d.infrastructure.app_paths import resolve_data_root


class DataSourceRepository:
    SCHEMA_VERSION = 5

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (resolve_data_root() / "config" / "data_sources.json")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._document: dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        with self._lock:
            if not self.path.exists():
                self._document = {
                    "schemaVersion": self.SCHEMA_VERSION,
                    "sources": [],
                    "selections": {},
                }
                self.save()
                return
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("data_sources.json must contain an object")
            if not isinstance(payload.get("sources", []), list):
                raise ValueError("data_sources.json sources must be an array")
            if not isinstance(payload.get("selections", {}), dict):
                raise ValueError("data_sources.json selections must be an object")
            self._document = payload
            if self._migrate_in_place():
                self.save()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self._document)

    def elevation_records(self) -> tuple[dict[str, Any], ...]:
        with self._lock:
            records = {
                str(item.get("id")): copy.deepcopy(item)
                for item in self._document.get("sources", [])
                if isinstance(item, dict) and item.get("layer_type") == "elevation"
            }
            selection = self._elevation_selection()
            ordered = [str(value) for value in selection.get("source_ids", [])]
            result = [records.pop(source_id) for source_id in ordered if source_id in records]
            result.extend(records[key] for key in sorted(records))
            return tuple(result)

    def active_elevation_source_id(self) -> str | None:
        selection = self._elevation_selection()
        values = selection.get("source_ids", [])
        return str(values[0]) if values else None

    def land_cover_records(self) -> tuple[dict[str, Any], ...]:
        with self._lock:
            return tuple(
                copy.deepcopy(item)
                for item in self._document.get("sources", [])
                if isinstance(item, dict)
                and item.get("layer_type") in {
                    "land_cover_categorical", "land_cover_rgb", "surface_categorical",
                }
            )

    def active_land_cover_source_id(self) -> str | None:
        selection = self._land_cover_selection()
        value = selection.get("source_id")
        return str(value) if value else None

    def activate_elevation(self, source: dict[str, Any]) -> tuple[str, ...]:
        source_id = str(source.get("id", "")).strip()
        if not source_id:
            raise ValueError("Elevation source id is required")
        record = copy.deepcopy(source)
        record["id"] = source_id
        record["layer_type"] = "elevation"
        record.setdefault("enabled", True)
        with self._lock:
            items = self._document.setdefault("sources", [])
            index = next(
                (index for index, item in enumerate(items) if isinstance(item, dict) and str(item.get("id")) == source_id),
                None,
            )
            if index is None:
                items.append(record)
            else:
                # Preserve fields unknown to this version while updating owned fields.
                items[index] = {**items[index], **record}
            selection = self._elevation_selection()
            old_order = [str(value) for value in selection.get("source_ids", [])]
            selection["mode"] = "manual"
            selection["source_ids"] = [source_id, *(value for value in old_order if value != source_id)]
            selection.pop("source_id", None)
            self.save()
            return tuple(selection["source_ids"])

    def restore_elevation_order(self, source_ids: tuple[str, ...]) -> None:
        with self._lock:
            selection = self._elevation_selection()
            selection["mode"] = "manual"
            selection["source_ids"] = list(dict.fromkeys(source_ids))
            selection.pop("source_id", None)
            self.save()

    def activate_land_cover(self, source: dict[str, Any]) -> str:
        source_id = str(source.get("id", "")).strip()
        if not source_id:
            raise ValueError("Land-cover source id is required")
        record = copy.deepcopy(source)
        record["id"] = source_id
        record["layer_type"] = "land_cover_categorical"
        record.setdefault("enabled", True)
        with self._lock:
            items = self._document.setdefault("sources", [])
            index = next(
                (
                    index for index, item in enumerate(items)
                    if isinstance(item, dict) and str(item.get("id")) == source_id
                ),
                None,
            )
            if index is None:
                items.append(record)
            else:
                items[index] = {**items[index], **record}
            selection = self._land_cover_selection()
            selection["mode"] = "manual"
            selection["source_id"] = source_id
            self.save()
        return source_id

    def restore_land_cover_source(self, source_id: str | None) -> None:
        with self._lock:
            selection = self._land_cover_selection()
            if source_id:
                selection["mode"] = "manual"
                selection["source_id"] = source_id
            else:
                selection["mode"] = "automatic"
                selection.pop("source_id", None)
            self.save()

    def remove(self, source_id: str) -> dict[str, Any] | None:
        with self._lock:
            items = self._document.setdefault("sources", [])
            removed = next(
                (item for item in items if isinstance(item, dict) and str(item.get("id")) == source_id),
                None,
            )
            self._document["sources"] = [
                item for item in items
                if not isinstance(item, dict) or str(item.get("id")) != source_id
            ]
            elevation = self._elevation_selection()
            elevation["source_ids"] = [
                value for value in elevation.get("source_ids", []) if str(value) != source_id
            ]
            land_cover = self._land_cover_selection()
            if str(land_cover.get("source_id") or "") == source_id:
                land_cover["mode"] = "automatic"
                land_cover.pop("source_id", None)
            self.save()
            return copy.deepcopy(removed)

    def refresh_external_validity(self) -> tuple[str, ...]:
        """Mark missing external sources invalid while leaving fallbacks ordered."""

        invalid: list[str] = []
        changed = False
        with self._lock:
            for item in self._document.setdefault("sources", []):
                if not isinstance(item, dict) or item.get("ownership") != "external":
                    continue
                accessible = Path(str(item.get("original_path") or item.get("path", ""))).exists()
                if bool(item.get("valid", True)) != accessible:
                    item["valid"] = accessible
                    changed = True
                if accessible:
                    item.pop("validation_error", None)
                else:
                    item["validation_error"] = "external_source_missing"
                    invalid.append(str(item.get("id", "")))
            if changed:
                self.save()
        return tuple(value for value in invalid if value)

    def save(self) -> None:
        with self._lock:
            self._document["schemaVersion"] = self.SCHEMA_VERSION
            temp = self.path.with_suffix(self.path.suffix + ".tmp")
            with temp.open("w", encoding="utf-8") as handle:
                json.dump(self._document, handle, ensure_ascii=False, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            temp.replace(self.path)

    def _elevation_selection(self) -> dict[str, Any]:
        selections = self._document.setdefault("selections", {})
        value = selections.setdefault("elevation", {})
        if not isinstance(value, dict):
            value = {}
            selections["elevation"] = value
        return value

    def _land_cover_selection(self) -> dict[str, Any]:
        selections = self._document.setdefault("selections", {})
        value = selections.setdefault("land_cover", {})
        if not isinstance(value, dict):
            value = {}
            selections["land_cover"] = value
        return value

    def _migrate_in_place(self) -> bool:
        changed = self._document.get("schemaVersion") != self.SCHEMA_VERSION
        selection = self._elevation_selection()
        if "source_ids" not in selection:
            legacy = selection.get("source_id")
            selection["source_ids"] = [legacy] if legacy else []
            changed = True
        if "source_id" in selection:
            selection.pop("source_id", None)
            changed = True
        self._document.setdefault("sources", [])
        self._document.setdefault("selections", {})
        self._land_cover_selection()
        self._document["schemaVersion"] = self.SCHEMA_VERSION
        return changed
