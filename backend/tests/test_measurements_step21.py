from __future__ import annotations

import asyncio
import math
from pathlib import Path

import pytest

from terralab3d.application.measurement_coordinator import MeasurementCoordinator
from terralab3d.domain.geometry import HorizontalCoordinate
from terralab3d.domain.identifiers import MeasurementId
from terralab3d.domain.measurements.calculations import MeasurementValidationError, SphericalMeasurementCalculator
from terralab3d.domain.measurements.models import Measurement, MeasurementKind
from terralab3d.domain.measurements.services import MeasurementDocumentHistory
from terralab3d.infrastructure.adapters.persistence.adapter import AtomicTextPreferencesAdapter
from terralab3d.infrastructure.adapters.persistence import adapter as persistence_adapter_module


def measurement(kind: MeasurementKind, start=(0.0, 0.0), end=(10.0, 10.0), key="m1") -> Measurement:
    return Measurement(
        MeasurementId(key), kind,
        HorizontalCoordinate(start[0], start[1]),
        HorizontalCoordinate(end[0], end[1]),
    )


def test_angular_distance_wrap_small_and_antipodal() -> None:
    calculator = SphericalMeasurementCalculator()
    assert calculator.angular_distance_deg(HorizontalCoordinate(0, 359.9), HorizontalCoordinate(0, 0.1)) == pytest.approx(0.2)
    assert calculator.angular_distance_deg(HorizontalCoordinate(89.9, 0), HorizontalCoordinate(89.9, 180)) == pytest.approx(0.2)
    assert calculator.angular_distance_deg(HorizontalCoordinate(0, 0), HorizontalCoordinate(0, 180)) == pytest.approx(180)
    tiny = calculator.angular_distance_deg(HorizontalCoordinate(20, 30), HorizontalCoordinate(20.000001, 30.000001))
    assert math.isfinite(tiny) and tiny > 0


@pytest.mark.parametrize("kind", list(MeasurementKind))
def test_all_geometries_are_closed_or_geodesic_and_labelled(kind: MeasurementKind) -> None:
    geometry = SphericalMeasurementCalculator().geometry(measurement(kind))
    assert geometry.label
    assert geometry.paths and len(geometry.paths[0]) >= 49
    if kind is not MeasurementKind.RULER:
        assert geometry.paths[0][0] == geometry.paths[0][-1]
    for path in geometry.paths:
        for point in path:
            assert 0 <= point.azimuth_deg < 360
            assert -90 <= point.altitude_deg <= 90


def test_zero_radius_and_degenerate_rectangle_are_rejected() -> None:
    calculator = SphericalMeasurementCalculator()
    with pytest.raises(MeasurementValidationError):
        calculator.geometry(measurement(MeasurementKind.CIRCLE, end=(0, 0)))
    with pytest.raises(MeasurementValidationError):
        calculator.geometry(measurement(MeasurementKind.RECTANGLE, end=(0, 10)))
    with pytest.raises(MeasurementValidationError, match="quaternion"):
        calculator.geometry(Measurement(
            MeasurementId("fixed-without-frame"),
            MeasurementKind.RULER,
            HorizontalCoordinate(0, 0),
            HorizontalCoordinate(1, 1),
            tracking=False,
        ))


def test_history_is_immutable_bounded_and_supports_undo_redo() -> None:
    history = MeasurementDocumentHistory(history_limit=2)
    original = history.document
    history.upsert(measurement(MeasurementKind.RULER, key="a"))
    first = history.document
    history.upsert(measurement(MeasurementKind.CIRCLE, key="b"))
    history.delete(MeasurementId("a"))
    assert original.measurements == ()
    assert len(first.measurements) == 1
    history.undo()
    assert {str(item.measurement_id) for item in history.document.measurements} == {"a", "b"}
    history.undo()
    assert {str(item.measurement_id) for item in history.document.measurements} == {"a"}
    history.undo()
    assert {str(item.measurement_id) for item in history.document.measurements} == {"a"}
    history.redo()
    assert {str(item.measurement_id) for item in history.document.measurements} == {"a", "b"}


def test_document_round_trip_and_schema_zero_migration(tmp_path: Path) -> None:
    published: list[dict] = []

    async def publish(payload: dict) -> None:
        published.append(payload)

    async def scenario() -> None:
        adapter = AtomicTextPreferencesAdapter(tmp_path)
        coordinator = MeasurementCoordinator(adapter, publish)
        await coordinator.apply({
            "action": "create", "kind": "ruler",
            "start": {"altitudeDeg": 10, "azimuthDeg": 359.9},
            "end": {"altitudeDeg": 10, "azimuthDeg": 0.1},
        })
        restored = MeasurementCoordinator(adapter, publish)
        assert len(restored.snapshot_payload()["measurements"]) == 1
        await restored.apply({"action": "undo"})
        assert len(restored.snapshot_payload()["measurements"]) == 1  # history is intentionally session-local

        (tmp_path / "measurement_document.json").write_text(
            '{"schemaVersion":0,"items":[{"measurementId":"legacy","kind":"circle","start":{"altitudeDeg":10,"azimuthDeg":20},"end":{"altitudeDeg":11,"azimuthDeg":20}}]}',
            encoding="utf-8",
        )
        migrated = MeasurementCoordinator(adapter, publish)
        assert migrated.snapshot_payload()["measurements"][0]["rotationDeg"] == 0

    asyncio.run(scenario())


def test_corrupt_document_is_preserved_and_recovers(tmp_path: Path) -> None:
    path = tmp_path / "measurement_document.json"
    path.write_text("{broken", encoding="utf-8")

    async def publish(_: dict) -> None:
        return None

    coordinator = MeasurementCoordinator(AtomicTextPreferencesAdapter(tmp_path), publish)
    snapshot = coordinator.snapshot_payload()
    assert snapshot["measurements"] == []
    assert snapshot["warning"]
    assert path.read_text(encoding="utf-8") == "{broken"


def test_coordinator_crud_versions_clear_and_restore_with_undo(tmp_path: Path) -> None:
    published: list[dict] = []

    async def publish(payload: dict) -> None:
        published.append(payload)

    async def scenario() -> None:
        coordinator = MeasurementCoordinator(AtomicTextPreferencesAdapter(tmp_path), publish)
        await coordinator.apply({
            "action": "create", "measurementId": "measurement:user:a", "kind": "rectangle",
            "start": {"altitudeDeg": 5, "azimuthDeg": 350},
            "end": {"altitudeDeg": 10, "azimuthDeg": 5},
        })
        created = coordinator.snapshot_payload()["measurements"][0]
        await coordinator.apply({
            "action": "update", "measurementId": "measurement:user:a", "kind": "rectangle",
            "start": {"altitudeDeg": 7, "azimuthDeg": 352},
            "end": {"altitudeDeg": 13, "azimuthDeg": 8},
            "rotationDeg": 12,
        })
        updated = coordinator.snapshot_payload()["measurements"][0]
        assert updated["entityVersion"] == created["entityVersion"] + 1
        await coordinator.apply({"action": "clear"})
        assert coordinator.snapshot_payload()["measurements"] == []
        await coordinator.apply({"action": "undo"})
        assert coordinator.snapshot_payload()["measurements"][0]["rotationDeg"] == 12
        await coordinator.apply({"action": "redo"})
        assert coordinator.snapshot_payload()["measurements"] == []
        assert len(published) == 5

    asyncio.run(scenario())


def test_tracking_toggle_freezes_all_shapes_in_one_persisted_3d_frame(tmp_path: Path) -> None:
    async def publish(_: dict) -> None:
        return None

    async def scenario() -> None:
        adapter = AtomicTextPreferencesAdapter(tmp_path)
        coordinator = MeasurementCoordinator(adapter, publish)
        await coordinator.apply({
            "action": "create", "measurementId": "measurement:user:tracked", "kind": "ruler",
            "start": {"altitudeDeg": 10, "azimuthDeg": 20},
            "end": {"altitudeDeg": 12, "azimuthDeg": 24},
        })
        before = coordinator.snapshot_payload()["measurements"][0]["entityVersion"]
        await coordinator.apply({
            "action": "set_tracking",
            "tracking": False,
            "fixedQuaternion": [0, math.sqrt(0.5), 0, math.sqrt(0.5)],
        })
        frozen = coordinator.snapshot_payload()
        assert frozen["trackingEnabled"] is False
        assert frozen["measurements"][0]["tracking"] is False
        assert frozen["measurements"][0]["fixedQuaternion"] == pytest.approx([0, math.sqrt(0.5), 0, math.sqrt(0.5)])
        assert frozen["measurements"][0]["entityVersion"] == before + 1

        restored = MeasurementCoordinator(adapter, publish).snapshot_payload()
        assert restored["trackingEnabled"] is False
        assert restored["measurements"][0]["fixedQuaternion"] == pytest.approx(frozen["measurements"][0]["fixedQuaternion"])

        await coordinator.apply({"action": "undo"})
        resumed = coordinator.snapshot_payload()
        assert resumed["trackingEnabled"] is True
        assert resumed["measurements"][0]["tracking"] is True
        assert resumed["measurements"][0]["fixedQuaternion"] is None

    asyncio.run(scenario())


def test_atomic_preferences_retry_transient_windows_lock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    real_replace = persistence_adapter_module.os.replace
    attempts = 0

    def flaky_replace(source: Path, target: Path) -> None:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise PermissionError("simulated transient indexer lock")
        real_replace(source, target)

    monkeypatch.setattr(persistence_adapter_module.os, "replace", flaky_replace)
    adapter = AtomicTextPreferencesAdapter(tmp_path)
    adapter.save_text("measurement_document", '{"schemaVersion":1}')
    assert attempts == 3
    assert adapter.load_text("measurement_document") == '{"schemaVersion":1}'
    assert list(tmp_path.glob("*.tmp")) == []
