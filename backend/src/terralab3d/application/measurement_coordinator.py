"""Cas d'ús autoritatiu del document persistent de mesures angulars."""

from __future__ import annotations

import json
import logging
import math
import uuid
from typing import Any, Awaitable, Callable

from terralab3d.application.ports.persistence import PreferencesPort
from terralab3d.domain.geometry import HorizontalCoordinate
from terralab3d.domain.identifiers import MeasurementId
from terralab3d.domain.measurements.calculations import (
    MeasurementValidationError,
    SphericalMeasurementCalculator,
)
from terralab3d.domain.measurements.models import (
    Measurement,
    MeasurementDocument,
    MeasurementKind,
)
from terralab3d.domain.measurements.services import MeasurementDocumentHistory

log = logging.getLogger("terralab3d.measurements")
Publisher = Callable[[dict[str, Any]], Awaitable[None]]
PREFERENCES_KEY = "measurement_document"


class MeasurementCoordinator:
    """Valida comandos, conserva historial y publica snapshots completos."""

    def __init__(self, preferences: PreferencesPort, publish: Publisher, history_limit: int = 50) -> None:
        self._preferences = preferences
        self._publish = publish
        self._calculator = SphericalMeasurementCalculator()
        document, warning = self._load_document()
        self._history = MeasurementDocumentHistory(document, history_limit)
        self._warning = warning
        self._entity_versions = {str(item.measurement_id): 1 for item in document.measurements}

    @property
    def revision(self) -> int:
        return self._history.document.revision

    async def publish_current(self) -> None:
        await self._publish(self.snapshot_payload())

    async def apply(self, data: dict[str, Any]) -> None:
        action = str(data.get("action", ""))
        before = self._history.document
        if action in {"create", "update"}:
            measurement = self._measurement_from_payload(data)
            self._calculator.geometry(measurement)
            existed = any(item.measurement_id == measurement.measurement_id for item in before.measurements)
            if action == "create" and existed:
                raise MeasurementValidationError("measurementId", "la mesura ja existeix")
            if action == "update" and not existed:
                raise MeasurementValidationError("measurementId", "la mesura no existeix")
            self._history.upsert(measurement)
            key = str(measurement.measurement_id)
            self._entity_versions[key] = self._entity_versions.get(key, 0) + 1
        elif action == "delete":
            measurement_id = MeasurementId(str(data.get("measurementId", "")))
            self._history.delete(measurement_id)
            self._entity_versions.pop(str(measurement_id), None)
        elif action == "select":
            value = data.get("measurementId")
            self._history.select(None if value in (None, "") else MeasurementId(str(value)))
        elif action == "set_tracking":
            enabled = data.get("tracking")
            if not isinstance(enabled, bool):
                raise MeasurementValidationError("tracking", "el seguiment ha de ser booleà")
            fixed_quaternion = None if enabled else _quaternion_from_payload(data.get("fixedQuaternion"))
            self._history.set_tracking(enabled, fixed_quaternion)
            self._refresh_entity_versions(before)
        elif action == "undo":
            self._history.undo()
            self._refresh_entity_versions(before)
        elif action == "redo":
            self._history.redo()
            self._refresh_entity_versions(before)
        elif action == "clear":
            self._history.clear()
            self._entity_versions.clear()
        else:
            raise MeasurementValidationError("action", "operació de mesura desconeguda")
        if self._history.document != before:
            self._save_document()
        await self.publish_current()

    def snapshot_payload(self) -> dict[str, Any]:
        document = self._history.document
        measurements = []
        for item in document.measurements:
            geometry = self._calculator.geometry(item)
            measurements.append({
                "measurementId": str(item.measurement_id),
                "kind": item.kind.value,
                "start": _coordinate_payload(item.start),
                "end": _coordinate_payload(item.end),
                "rotationDeg": item.rotation_deg,
                "tracking": item.tracking,
                "fixedQuaternion": None if item.fixed_quaternion_xyzw is None else list(item.fixed_quaternion_xyzw),
                "entityVersion": self._entity_versions.get(str(item.measurement_id), 1),
                "geometry": {
                    "paths": [[_coordinate_payload(point) for point in path] for path in geometry.paths],
                    "label": geometry.label,
                    "anchor": _coordinate_payload(geometry.anchor),
                },
            })
        return {
            "type": "measurement_snapshot",
            "schemaVersion": 1,
            "measurementRevision": document.revision,
            "trackingEnabled": document.tracking_enabled,
            "measurements": measurements,
            "selectedMeasurementId": None if document.selected_measurement_id is None else str(document.selected_measurement_id),
            "canUndo": self._history.can_undo,
            "canRedo": self._history.can_redo,
            "warning": self._warning,
        }

    def _measurement_from_payload(self, data: dict[str, Any]) -> Measurement:
        raw_id = str(data.get("measurementId", "")).strip()
        measurement_id = MeasurementId(raw_id or f"measurement:user:{uuid.uuid4()}")
        try:
            kind = MeasurementKind(str(data["kind"]))
            start = _coordinate_from_payload(data["start"])
            end = _coordinate_from_payload(data["end"])
            rotation = float(data.get("rotationDeg", 0.0))
            raw_tracking = data.get("tracking", True)
            if not isinstance(raw_tracking, bool):
                raise ValueError("tracking invàlid")
            tracking = raw_tracking
            fixed_quaternion = None if tracking else _quaternion_from_payload(data.get("fixedQuaternion", [0.0, 0.0, 0.0, 1.0]))
        except (KeyError, TypeError, ValueError) as exc:
            raise MeasurementValidationError("measurement", "payload de mesura invàlid") from exc
        return Measurement(measurement_id, kind, start, end, rotation, tracking, fixed_quaternion)

    def _load_document(self) -> tuple[MeasurementDocument, str | None]:
        try:
            raw = self._preferences.load_text(PREFERENCES_KEY)
            if raw is None:
                return MeasurementDocument(), None
            payload = json.loads(raw)
            version = int(payload.get("schemaVersion", 0))
            if version not in {0, 1}:
                raise ValueError("versió no compatible")
            items = payload.get("measurements", payload.get("items", []))
            measurements = tuple(self._measurement_from_payload(item) for item in items)
            for measurement in measurements:
                self._calculator.geometry(measurement)
            selected = payload.get("selectedMeasurementId")
            selected_id = MeasurementId(str(selected)) if selected and any(str(item.measurement_id) == str(selected) for item in measurements) else None
            tracking_enabled = payload.get("trackingEnabled", all(item.tracking for item in measurements))
            if not isinstance(tracking_enabled, bool):
                raise ValueError("trackingEnabled invàlid")
            return MeasurementDocument(1, 0, measurements, selected_id, tracking_enabled), None
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError, MeasurementValidationError) as exc:
            log.warning("MGP: [MeasurementCoordinator] [load] [%s]", exc)
            return MeasurementDocument(), "No s'ha pogut restaurar el document de mesures; el fitxer es conserva per a diagnòstic."

    def _save_document(self) -> None:
        document = self._history.document
        payload = {
            "schemaVersion": 1,
            "selectedMeasurementId": None if document.selected_measurement_id is None else str(document.selected_measurement_id),
            "trackingEnabled": document.tracking_enabled,
            "measurements": [
                {
                    "measurementId": str(item.measurement_id),
                    "kind": item.kind.value,
                    "start": _coordinate_payload(item.start),
                    "end": _coordinate_payload(item.end),
                    "rotationDeg": item.rotation_deg,
                    "tracking": item.tracking,
                    "fixedQuaternion": None if item.fixed_quaternion_xyzw is None else list(item.fixed_quaternion_xyzw),
                }
                for item in document.measurements
            ],
        }
        self._preferences.save_text(PREFERENCES_KEY, json.dumps(payload, ensure_ascii=False, indent=2))

    def _refresh_entity_versions(self, before: MeasurementDocument) -> None:
        previous = {str(item.measurement_id): item for item in before.measurements}
        current = {str(item.measurement_id): item for item in self._history.document.measurements}
        for key, item in current.items():
            if previous.get(key) != item:
                self._entity_versions[key] = self._entity_versions.get(key, 0) + 1
        for key in set(previous) - set(current):
            self._entity_versions.pop(key, None)


def _coordinate_from_payload(value: Any) -> HorizontalCoordinate:
    if not isinstance(value, dict):
        raise MeasurementValidationError("coordinate", "la coordenada ha de ser un objecte")
    altitude = float(value["altitudeDeg"])
    azimuth = float(value["azimuthDeg"])
    if not math.isfinite(altitude) or not math.isfinite(azimuth):
        raise MeasurementValidationError("coordinate", "la coordenada ha de ser finita")
    return HorizontalCoordinate(altitude, azimuth % 360.0)


def _coordinate_payload(value: HorizontalCoordinate) -> dict[str, float]:
    return {"altitudeDeg": value.altitude_deg, "azimuthDeg": value.azimuth_deg % 360.0}


def _quaternion_from_payload(value: Any) -> tuple[float, float, float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise MeasurementValidationError("fixedQuaternion", "el quaternion congelat necessita quatre components")
    quaternion = tuple(float(component) for component in value)
    if not all(math.isfinite(component) for component in quaternion):
        raise MeasurementValidationError("fixedQuaternion", "el quaternion congelat ha de ser finit")
    norm = math.sqrt(sum(component * component for component in quaternion))
    if norm <= 1e-12:
        raise MeasurementValidationError("fixedQuaternion", "el quaternion congelat no pot ser nul")
    normalized = tuple(component / norm for component in quaternion)
    return normalized  # type: ignore[return-value]
