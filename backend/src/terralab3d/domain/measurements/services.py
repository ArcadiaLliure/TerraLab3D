"""Operacions immutables i historial acotat per al document de mesures."""


from dataclasses import replace
from typing import Protocol
from terralab3d.domain.identifiers import MeasurementId
from .models import Measurement, MeasurementDocument, MeasurementGeometry

class MeasurementGeometryModel(Protocol):
    """Construeix geometria esfèrica i etiquetes per a entitats de mesura."""
    def geometry(self, measurement: Measurement) -> MeasurementGeometry: ...


class MeasurementDocumentHistory:
    def __init__(self, document: MeasurementDocument | None = None, history_limit: int = 50) -> None:
        if history_limit < 1:
            raise ValueError("history_limit ha de ser positiu")
        self._document = document or MeasurementDocument()
        self._limit = history_limit
        self._undo: list[tuple[tuple[Measurement, ...], bool]] = []
        self._redo: list[tuple[tuple[Measurement, ...], bool]] = []

    @property
    def document(self) -> MeasurementDocument:
        return self._document

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    def upsert(self, measurement: Measurement) -> MeasurementDocument:
        current = list(self._document.measurements)
        index = next((i for i, item in enumerate(current) if item.measurement_id == measurement.measurement_id), None)
        if index is None:
            current.append(measurement)
        elif current[index] == measurement:
            return self.select(measurement.measurement_id)
        else:
            current[index] = measurement
        return self._commit(tuple(current), measurement.measurement_id)

    def delete(self, measurement_id: MeasurementId) -> MeasurementDocument:
        remaining = tuple(item for item in self._document.measurements if item.measurement_id != measurement_id)
        if len(remaining) == len(self._document.measurements):
            return self._document
        return self._commit(remaining, None if self._document.selected_measurement_id == measurement_id else self._document.selected_measurement_id)

    def clear(self) -> MeasurementDocument:
        if not self._document.measurements:
            return self._document
        return self._commit((), None)

    def set_tracking(
        self,
        enabled: bool,
        fixed_quaternion_xyzw: tuple[float, float, float, float] | None,
    ) -> MeasurementDocument:
        if self._document.tracking_enabled == enabled and all(item.tracking == enabled for item in self._document.measurements):
            return self._document
        measurements = tuple(replace(
            item,
            tracking=enabled,
            fixed_quaternion_xyzw=None if enabled else fixed_quaternion_xyzw,
        ) for item in self._document.measurements)
        return self._commit(measurements, self._document.selected_measurement_id, enabled)

    def select(self, measurement_id: MeasurementId | None) -> MeasurementDocument:
        if measurement_id is not None and not any(item.measurement_id == measurement_id for item in self._document.measurements):
            measurement_id = None
        self._document = MeasurementDocument(1, self._document.revision + 1, self._document.measurements, measurement_id, self._document.tracking_enabled)
        return self._document

    def undo(self) -> MeasurementDocument:
        if not self._undo:
            return self._document
        self._redo.append((self._document.measurements, self._document.tracking_enabled))
        previous, tracking_enabled = self._undo.pop()
        selected = self._document.selected_measurement_id
        if selected is not None and not any(item.measurement_id == selected for item in previous):
            selected = None
        self._document = MeasurementDocument(1, self._document.revision + 1, previous, selected, tracking_enabled)
        return self._document

    def redo(self) -> MeasurementDocument:
        if not self._redo:
            return self._document
        self._undo.append((self._document.measurements, self._document.tracking_enabled))
        following, tracking_enabled = self._redo.pop()
        selected = self._document.selected_measurement_id
        if selected is not None and not any(item.measurement_id == selected for item in following):
            selected = None
        self._document = MeasurementDocument(1, self._document.revision + 1, following, selected, tracking_enabled)
        return self._document

    def _commit(self, measurements: tuple[Measurement, ...], selected: MeasurementId | None, tracking_enabled: bool | None = None) -> MeasurementDocument:
        self._undo.append((self._document.measurements, self._document.tracking_enabled))
        if len(self._undo) > self._limit:
            del self._undo[0]
        self._redo.clear()
        self._document = MeasurementDocument(
            1,
            self._document.revision + 1,
            measurements,
            selected,
            self._document.tracking_enabled if tracking_enabled is None else tracking_enabled,
        )
        return self._document
