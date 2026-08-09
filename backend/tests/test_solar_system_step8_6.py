from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

import pytest

from terralab3d.application.orbit_sampler import OrbitSampler
from terralab3d.domain.solar_system.catalog import SatelliteCatalogSnapshot
from terralab3d.domain.solar_system.models import (
    CoverageStatus,
    PhysicalModelQuality,
    ScientificObserver,
)
from terralab3d.infrastructure.adapters.ephemeris.spice_adapter import (
    SpiceEphemerisAdapter,
)
from terralab3d.infrastructure.adapters.file_assets.solar_system import (
    ManagedSolarSystemAssets,
)


FIXTURE_ROOT = Path(__file__).parent / "fixtures"
SNAPSHOT_INSTANT = datetime(2026, 7, 9, tzinfo=timezone.utc)


@pytest.fixture(scope="module")
def assets() -> ManagedSolarSystemAssets:
    value = ManagedSolarSystemAssets()
    if value.kernel_manifest_path is None or value.satellite_catalog is None:
        pytest.skip("Managed Step 8.6 resources are not installed")
    return value


@pytest.fixture(scope="module")
def spice_adapter(assets: ManagedSolarSystemAssets) -> SpiceEphemerisAdapter:
    assert assets.kernel_manifest_path is not None
    assert assets.satellite_catalog is not None
    adapter = SpiceEphemerisAdapter(
        assets.kernel_manifest_path,
        assets.satellite_catalog,
    )
    yield adapter
    adapter.close()


def test_catalog_snapshot_has_all_461_satellites_and_explicit_gaps() -> None:
    path = (
        Path(__file__).parents[1]
        / "src"
        / "terralab3d"
        / "data"
        / "solar_system"
        / "satellite_catalog_2026-07-09.json"
    )
    catalog = SatelliteCatalogSnapshot.from_dict(json.loads(path.read_text(encoding="utf-8")))
    assert catalog.total_count == 461
    assert catalog.by_parent == {
        "earth": 1,
        "mars": 2,
        "jupiter": 115,
        "saturn": 293,
        "uranus": 29,
        "neptune": 16,
        "pluto": 5,
    }
    naif_ids = [item.naif_id for item in catalog.satellites if item.naif_id is not None]
    assert len(naif_ids) == len(set(naif_ids))
    without_spk = {item.name for item in catalog.satellites if not item.has_spk}
    assert without_spk == {"S/2009 S1", "S/2025 U1"}
    assert catalog.with_spk_count == 459


def test_every_installed_resource_passes_manifest_validation(
    assets: ManagedSolarSystemAssets,
) -> None:
    # Construction verifies path confinement, byte size and SHA-256 for every
    # texture and every installed kernel before exposing the descriptor.
    assert assets.descriptor.status.value == "ready"
    assert len(assets.descriptor.textures) == 9
    assert assets.satellite_catalog is not None
    assert assets.satellite_catalog.total_count == 461


def test_horizons_j2000_vectors_match_installed_spks(
    spice_adapter: SpiceEphemerisAdapter,
) -> None:
    import spiceypy as spice

    payload = json.loads(
        (FIXTURE_ROOT / "horizons_satellites_2026_07_09.json").read_text(encoding="utf-8")
    )
    assert payload["apiSignature"]["source"] == "NASA/JPL Horizons API"
    for fixture in payload["fixtures"]:
        et = (float(fixture["julianDateTdb"]) - 2_451_545.0) * 86_400.0
        state, _ = spice.spkezr(
            str(fixture["naifId"]),
            et,
            "J2000",
            "NONE",
            str(fixture["parentNaifId"]),
        )
        assert math.dist(state[:3], fixture["positionJ2000Km"]) < 0.1, fixture["name"]
        assert math.dist(state[3:], fixture["velocityJ2000KmS"]) < 1.0e-5, fixture["name"]


def test_saturn_center_pck_radii_ring_plane_and_observer_transform(
    spice_adapter: SpiceEphemerisAdapter,
) -> None:
    first = spice_adapter.snapshot(
        SNAPSHOT_INSTANT, ScientificObserver(41.3874, 2.1686, 25.0)
    )
    second = spice_adapter.snapshot(
        SNAPSHOT_INSTANT, ScientificObserver(-35.0, 149.0, 600.0)
    )
    saturn_a = next(item for item in first.planets if item.naif_id == 699)
    saturn_b = next(item for item in second.planets if item.naif_id == 699)
    assert saturn_a.parent_naif_id is None
    assert saturn_a.radii_km == (60_268.0, 60_268.0, 54_364.0)
    assert saturn_a.ephemeris_kernel_id is not None
    assert saturn_a.orientation is not None
    assert saturn_a.orientation.body_to_enu_quaternion is not None
    assert saturn_a.orientation.equatorial_to_enu_quaternion is not None
    assert saturn_a.ring_diagnostics is not None
    assert saturn_b.ring_diagnostics is not None
    assert saturn_a.ring_diagnostics.opening_geocentric_deg == pytest.approx(
        saturn_b.ring_diagnostics.opening_geocentric_deg, abs=1.0e-12
    )
    assert abs(
        saturn_a.ring_diagnostics.opening_topocentric_deg
        - saturn_b.ring_diagnostics.opening_topocentric_deg
    ) > 1.0e-5
    assert saturn_a.orientation.body_to_enu_quaternion != saturn_b.orientation.body_to_enu_quaternion
    assert _norm(saturn_a.direction_enu) == pytest.approx(1.0, abs=1.0e-12)

    pole_from_equatorial_quaternion = _quaternion_apply(
        saturn_a.orientation.equatorial_to_enu_quaternion,
        (0.0, 0.0, 1.0),
    )
    pole_from_icrf = _quaternion_apply(
        first.icrf_to_enu_quaternion,
        saturn_a.orientation.north_pole_icrf,
    )
    assert math.dist(pole_from_equatorial_quaternion, pole_from_icrf) < 1.0e-12


def test_saturn_ring_opening_is_continuous_near_edge_and_changes_sign(
    spice_adapter: SpiceEphemerisAdapter,
) -> None:
    observer = ScientificObserver(0.0, 0.0, 0.0)
    values = []
    for date in (
        datetime(2024, 1, 1, tzinfo=timezone.utc),
        datetime(2025, 3, 23, tzinfo=timezone.utc),
        datetime(2025, 5, 6, tzinfo=timezone.utc),
        datetime(2032, 1, 1, tzinfo=timezone.utc),
    ):
        saturn = next(
            item for item in spice_adapter.snapshot(date, observer).planets if item.naif_id == 699
        )
        assert saturn.ring_diagnostics is not None
        values.append(saturn.ring_diagnostics.opening_geocentric_deg)
    assert values[0] > 0.0
    assert abs(values[1]) < 0.1
    assert values[2] < 0.0
    assert abs(values[3]) > 20.0
    assert all(math.isfinite(value) for value in values)


def test_orientation_availability_is_data_driven_and_hyperion_is_honest(
    spice_adapter: SpiceEphemerisAdapter,
) -> None:
    spice_adapter.set_satellite_systems(("jupiter", "saturn", "uranus"))
    snapshot = spice_adapter.snapshot(
        SNAPSHOT_INSTANT, ScientificObserver(41.3874, 2.1686, 25.0)
    )
    states = {item.naif_id: item for item in snapshot.satellites}
    for naif_id in (501, 502, 606, 609):
        assert states[naif_id].orientation is not None
        assert states[naif_id].orientation_quality is PhysicalModelQuality.IAU_MODEL
    hyperion = states[607]
    assert hyperion.orientation is None
    assert hyperion.orientation_quality is PhysicalModelQuality.UNAVAILABLE

    uranus = next(item for item in snapshot.planets if item.naif_id == 799)
    assert uranus.orientation is not None
    assert uranus.orientation.body_to_enu_quaternion is not None


def test_coverage_and_orbit_generation_are_explicit_and_cached(
    spice_adapter: SpiceEphemerisAdapter,
) -> None:
    definition = next(
        item for item in spice_adapter.satellite_catalog.satellites if item.naif_id == 401
    )
    assert definition.coverage_start_et is not None
    assert definition.coverage_end_et is not None
    assert definition.coverage_at(definition.coverage_start_et) is CoverageStatus.IN_RANGE
    assert definition.coverage_at(definition.coverage_start_et - 1.0) is CoverageStatus.OUT_OF_RANGE
    with pytest.raises(ValueError, match="outside coverage"):
        spice_adapter.sample_orbit(
            definition,
            definition.coverage_start_et - 10.0,
            definition.coverage_start_et + 10.0,
            16,
        )

    sampler = OrbitSampler(spice_adapter)
    center = spice_adapter.utc_to_et(SNAPSHOT_INSTANT)
    first = sampler.sample(
        definition, center - 14_400.0, center + 14_400.0, 128,
        spice_adapter.metadata.kernel_generation or "unknown",
    )
    second = sampler.sample(
        definition, center - 14_400.0, center + 14_400.0, 128,
        spice_adapter.metadata.kernel_generation or "unknown",
    )
    changed = sampler.sample(
        definition, center - 28_800.0, center + 28_800.0, 128,
        spice_adapter.metadata.kernel_generation or "unknown",
    )
    assert first is second
    assert changed.orbit_generation > first.orbit_generation
    assert sampler.sample_count == 2
    assert sampler.cache_hit_count == 1
    assert len(OrbitSampler.encode(first).payload) == 128 * 3 * 4


def _norm(vector: tuple[float, float, float]) -> float:
    return math.sqrt(sum(value * value for value in vector))


def _quaternion_apply(
    quaternion: tuple[float, float, float, float] | None,
    vector: tuple[float, float, float] | None,
) -> tuple[float, float, float]:
    assert quaternion is not None and vector is not None
    x, y, z, w = quaternion
    vx, vy, vz = vector
    # q * v * conjugate(q), expanded for the serialized [x,y,z,w] order.
    tx = 2.0 * (y * vz - z * vy)
    ty = 2.0 * (z * vx - x * vz)
    tz = 2.0 * (x * vy - y * vx)
    return (
        vx + w * tx + y * tz - z * ty,
        vy + w * ty + z * tx - x * tz,
        vz + w * tz + x * ty - y * tx,
    )
