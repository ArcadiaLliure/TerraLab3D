from __future__ import annotations

import asyncio
import json
import math
from datetime import datetime, timezone
from importlib.resources import files

import pytest

from terralab3d.application.constellation_coordinator import ConstellationCoordinator
from terralab3d.application.apparent_trajectory import observable_from_message
from terralab3d.application.observable_positions import ObservablePositionService
from terralab3d.domain.constellations.calculations import ConstellationValidationError
from terralab3d.domain.constellations.models import EditableConstellation
from terralab3d.domain.constellations.services import ConstellationDocumentHistory
from terralab3d.domain.identifiers import ConstellationId
from terralab3d.domain.search.calculations import DefaultSearchNormalizationCalculator
from terralab3d.domain.search.indexer import AstronomicalSearchIndex
from terralab3d.domain.search.models import SearchQuery, SearchTargetKind
from terralab3d.domain.solar_system.models import ScientificObserver
from terralab3d.domain.stars.star_pick_models import ResolvedStarPick, StarPickResponse
from terralab3d.domain.visibility.models import ObservableFamily, ObservableObject
from terralab3d.infrastructure.catalogs.constellations import PackagedConstellationCatalog
from terralab3d.infrastructure.adapters.persistence.adapter import AtomicTextPreferencesAdapter


class MemoryPreferences:
    def __init__(self, values: dict[str, str] | None = None) -> None:
        self.values = values or {}
        self.backups: list[str] = []

    def load_text(self, key: str) -> str | None:
        return self.values.get(key)

    def save_text(self, key: str, value: str) -> None:
        self.values[key] = value

    def backup_invalid(self, key: str) -> str:
        self.backups.append(key)
        return f"{key}.invalid-test.json"


class FixedStarResolver:
    def __init__(self, status: str = "ok") -> None:
        self.status = status

    def resolve(self, request):
        if self.status != "ok":
            return StarPickResponse(request.request_id, request.generation, self.status)
        return StarPickResponse(
            request.request_id,
            request.generation,
            "ok",
            ResolvedStarPick(
                request.resource_id,
                request.resource_version,
                request.catalog_index,
                123456789012345678,
                83.82208,
                -5.39111,
                1.7,
                0.2,
                "general",
            ),
        )


def test_packaged_catalog_has_88_entities_and_discontinuous_serpens() -> None:
    catalog = PackagedConstellationCatalog().catalog
    assert len(catalog.entries) == 88
    serpens = [entry for entry in catalog.entries if str(entry.constellation_id) == "Ser"]
    assert len(serpens) == 1
    assert {component.component_id for component in serpens[0].visual_components} == {"caput", "cauda"}
    assert all(component.rank == 3 for component in serpens[0].visual_components)
    assert all(component.strokes for component in serpens[0].visual_components)
    assert len(serpens[0].visual_components) == 2

    # Cada traç és independent: el model no té cap aresta entre components.
    caput, cauda = sorted(serpens[0].visual_components, key=lambda item: item.component_id)
    assert caput.strokes is not cauda.strokes


def test_d3_celestial_notice_is_included_in_the_python_distribution() -> None:
    notice = files("terralab3d").joinpath("THIRD-PARTY.md").read_text(encoding="utf-8")
    assert "Copyright (c) 2015, Olaf Frohn" in notice
    assert "Redistribution and use in source and binary forms" in notice
    assert "7e720a3de062059d4c5400a379146a601d9010e0" in notice


def test_constellations_are_searchable_by_latin_name_and_abbreviation() -> None:
    packaged = PackagedConstellationCatalog()
    index = AstronomicalSearchIndex(DefaultSearchNormalizationCalculator())
    index.build_index([], [], [], packaged.search_records())
    for query in ("Orion", "Ori"):
        results = index.search(SearchQuery(query, frozenset({SearchTargetKind.CONSTELLATION}), 5))
        assert results[0].target_ref == "Ori"
        assert results[0].kind is SearchTargetKind.CONSTELLATION
        assert results[0].coordinate_snapshot is not None
        assert results[0].angular_radius_deg is not None


def test_packaged_catalog_has_finite_values_and_one_degree_maximum_arc_step() -> None:
    catalog = PackagedConstellationCatalog().catalog
    ranks = set()
    for entry in catalog.entries:
        assert math.isfinite(entry.center.right_ascension_deg)
        assert math.isfinite(entry.center.declination_deg)
        assert math.isfinite(entry.angular_radius_deg)
        for component in entry.visual_components:
            ranks.add(component.rank)
            for stroke in component.strokes:
                for start, end in zip(stroke, stroke[1:]):
                    ra1 = math.radians(start.right_ascension_deg)
                    dec1 = math.radians(start.declination_deg)
                    ra2 = math.radians(end.right_ascension_deg)
                    dec2 = math.radians(end.declination_deg)
                    cosine = (
                        math.sin(dec1) * math.sin(dec2)
                        + math.cos(dec1) * math.cos(dec2) * math.cos(ra1 - ra2)
                    )
                    separation = math.degrees(math.acos(max(-1.0, min(1.0, cosine))))
                    assert separation <= 1.000001
    assert ranks == {1, 2, 3}


def test_history_is_limited_per_document_and_not_serialized() -> None:
    history = ConstellationDocumentHistory(history_limit=256)
    group = EditableConstellation(ConstellationId("constellation:user:test"), "Inicial")
    history.create(group)
    for index in range(300):
        history.rename(group.constellation_id, f"Nom {index}")
    assert history.undo_depth == 256
    assert history.can_undo
    history.undo()
    assert history.can_redo
    history.rename(group.constellation_id, "Branca nova")
    assert not history.can_redo


def test_backend_resolves_snap_and_rejects_stale_without_mutation() -> None:
    async def scenario() -> None:
        published = []

        async def publish(payload):
            published.append(payload)

        preferences = MemoryPreferences()
        resolver = FixedStarResolver()
        coordinator = ConstellationCoordinator(preferences, publish, resolver)  # type: ignore[arg-type]
        await coordinator.apply({"action": "create_group", "documentRevision": 1, "constellationId": "user:orion", "name": "Orión propi"})
        await coordinator.apply({
            "action": "append_node",
            "documentRevision": 2,
            "requestId": "snap-1",
            "constellationId": "user:orion",
            "resourceId": "sky.stars.general",
            "resourceVersion": "v7",
            "catalogIndex": 42,
            "raDeg": 0,
            "decDeg": 0,
        })
        node = coordinator.snapshot_payload()["constellations"][0]["nodes"][0]
        assert node["raDeg"] == pytest.approx(83.82208)
        assert node["decDeg"] == pytest.approx(-5.39111)
        assert node["sourceId"] == "123456789012345678"
        persisted = json.loads(preferences.values["constellations.v1"])
        assert "canUndo" not in persisted

        resolver.status = "stale"
        before = coordinator.snapshot_payload()
        with pytest.raises(ConstellationValidationError):
            await coordinator.apply({
                "action": "append_node",
                "documentRevision": 3,
                "requestId": "snap-stale",
                "constellationId": "user:orion",
                "resourceId": "sky.stars.general",
                "resourceVersion": "old",
                "catalogIndex": 42,
            })
        after = coordinator.snapshot_payload()
        assert after == before

        restored = ConstellationCoordinator(preferences, publish, FixedStarResolver())  # type: ignore[arg-type]
        assert restored.snapshot_payload()["constellations"][0]["nodes"][0]["sourceId"] == "123456789012345678"
        assert restored.snapshot_payload()["canUndo"] is False

    asyncio.run(scenario())


def test_undo_of_group_creation_clears_dangling_selection() -> None:
    async def scenario() -> None:
        async def publish(_payload):
            return None

        coordinator = ConstellationCoordinator(MemoryPreferences(), publish, FixedStarResolver())  # type: ignore[arg-type]
        await coordinator.apply({"action": "create_group", "documentRevision": 1, "constellationId": "user:new"})
        await coordinator.apply({"action": "undo", "documentRevision": 2})
        snapshot = coordinator.snapshot_payload()
        assert snapshot["selectedConstellationId"] is None
        assert snapshot["editing"] is False

    asyncio.run(scenario())


def test_invalid_document_is_backed_up_before_empty_fallback() -> None:
    preferences = MemoryPreferences({"constellations.v1": "{invalid"})

    async def publish(_payload):
        return None

    coordinator = ConstellationCoordinator(preferences, publish, FixedStarResolver())  # type: ignore[arg-type]
    assert preferences.backups == ["constellations.v1"]
    assert json.loads(preferences.values["constellations.v1"])["constellations"] == []
    assert coordinator.snapshot_payload()["constellations"] == []
    assert "còpia datada" in coordinator.snapshot_payload()["warning"]


def test_invalid_file_is_preserved_before_atomic_empty_replacement(tmp_path) -> None:
    adapter = AtomicTextPreferencesAdapter(tmp_path)
    adapter.save_text("constellations.v1", "{invalid")

    async def publish(_payload):
        return None

    ConstellationCoordinator(adapter, publish, FixedStarResolver())  # type: ignore[arg-type]
    assert json.loads((tmp_path / "constellations.v1.json").read_text(encoding="utf-8"))["constellations"] == []
    backups = list(tmp_path.glob("constellations.v1.invalid-*.json"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "{invalid"


def test_legacy_migration_is_idempotent_and_keeps_the_original(tmp_path) -> None:
    adapter = AtomicTextPreferencesAdapter(tmp_path)
    legacy = json.dumps([{
        "id": "legacy:1",
        "name": "Figura antiga",
        "points": [{"ra": 10.0, "dec": 20.0}],
    }])
    adapter.save_text("terralab_constellations", legacy)

    async def publish(_payload):
        return None

    first = ConstellationCoordinator(adapter, publish, FixedStarResolver())  # type: ignore[arg-type]
    second = ConstellationCoordinator(adapter, publish, FixedStarResolver())  # type: ignore[arg-type]
    assert first.snapshot_payload()["constellations"] == second.snapshot_payload()["constellations"]
    assert adapter.load_text("terralab_constellations") == legacy
    assert adapter.load_text("constellations.v1") is not None


def test_constellation_center_is_a_fixed_equatorial_observable() -> None:
    entry = PackagedConstellationCatalog().find("Ori")
    assert entry is not None
    observable = ObservableObject(
        object_id="Ori",
        family=ObservableFamily.CONSTELLATION,
        display_name=entry.name,
        right_ascension_deg=entry.center.right_ascension_deg,
        declination_deg=entry.center.declination_deg,
        frame="ICRS",
    )
    assert observable.has_apparent_position
    position = ObservablePositionService(None).position_at(
        observable,
        datetime(2026, 9, 17, tzinfo=timezone.utc),
        ScientificObserver(41.0, 2.0, 100.0),
    )
    assert position.valid


def test_constellation_trajectory_contract_rejects_non_finite_coordinates() -> None:
    with pytest.raises(ValueError, match="finite"):
        observable_from_message({
            "observable": {
                "objectId": "constellation:Ori",
                "family": "constellation",
                "displayName": "Orion",
                "rightAscensionDeg": float("nan"),
                "declinationDeg": -5.0,
                "frame": "ICRS",
            }
        })
