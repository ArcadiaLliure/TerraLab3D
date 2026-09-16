from __future__ import annotations

import asyncio
import json
import math
from pathlib import Path

import numpy as np
import pytest

from terralab3d.application.observation_coordinator import ObservationCoordinator
from terralab3d.application.star_coordinator import StarCoordinator, _filter_deep_batch, _merge_brightest
from terralab3d.domain.imaging.calculations import PhotographicLimitingMagnitudeModelV1
from terralab3d.domain.imaging.models import PhotographicLimitingMagnitudeInputs
from terralab3d.domain.optics.calculations import (
    OpticalValidationError,
    camera_field,
    camera_metrics,
    circular_solid_angle_sr,
    rectangular_solid_angle_sr,
    telescope_field,
    telescope_metrics,
)
from terralab3d.domain.optics.models import (
    CameraCaptureSettings,
    CameraProfile,
    SensorFormat,
    TelescopeSettings,
)
from terralab3d.domain.stars.models import GaiaAvailability, StarBatch
from terralab3d.infrastructure.adapters.persistence.adapter import AtomicTextPreferencesAdapter
from terralab3d.infrastructure.adapters.star_catalog_adapter import GaiaStarCatalogAdapter


def test_camera_and_telescope_geometry_are_scientific() -> None:
    profile = CameraProfile("camera:full-frame", "Full Frame", SensorFormat("ff", 36.0, 24.0), True)
    field = camera_field(profile, CameraCaptureSettings("camera:full-frame", focal_length_mm=50.0))
    assert field.width_deg == pytest.approx(39.5978, abs=1e-4)
    assert field.height_deg == pytest.approx(26.9915, abs=1e-4)
    assert field.solid_angle_sr == pytest.approx(rectangular_solid_angle_sr(field.width_deg, field.height_deg))

    telescope = TelescopeSettings(400.0, 80.0, 20.0, 50.0)
    scope_field = telescope_field(telescope)
    metrics = telescope_metrics(telescope)
    assert metrics.magnification == pytest.approx(20.0)
    assert metrics.exit_pupil_mm == pytest.approx(4.0)
    assert metrics.true_fov_deg == pytest.approx(2.5)
    assert scope_field.solid_angle_sr == pytest.approx(circular_solid_angle_sr(2.5))


def test_pixel_scale_uses_resolution_and_checks_square_pitch() -> None:
    sensor = SensorFormat(
        "custom", 36.0, 24.0, 6000, 4000, True, pixel_pitch_um=6.0,
    )
    profile = CameraProfile("camera:user:test", "Test", sensor)
    field = camera_field(profile, CameraCaptureSettings(profile.profile_id, focal_length_mm=100.0))
    metrics = camera_metrics(profile, field, 100.0)
    assert metrics.pixel_scale_x_arcsec == pytest.approx(field.width_deg * 3600.0 / 6000.0)
    assert metrics.pixel_scale_y_arcsec == pytest.approx(field.height_deg * 3600.0 / 4000.0)

    bad = CameraProfile(
        "camera:user:bad", "Bad",
        SensorFormat("custom", 36.0, 24.0, 6000, 4000, True, pixel_pitch_um=6.2),
    )
    with pytest.raises(OpticalValidationError) as error:
        camera_metrics(bad, camera_field(bad, CameraCaptureSettings(bad.profile_id)), 250.0)
    assert error.value.field == "pixelPitchUm"


def test_non_square_pixels_require_axis_pitches_when_declared() -> None:
    profile = CameraProfile(
        "camera:user:rect", "Rectangular",
        SensorFormat("custom", 20.0, 10.0, square_pixels=False, pixel_pitch_um=4.0),
    )
    with pytest.raises(OpticalValidationError):
        camera_metrics(profile, camera_field(profile, CameraCaptureSettings(profile.profile_id)), 250.0)

    valid = CameraProfile(
        "camera:user:rect-valid", "Rectangular",
        SensorFormat("custom", 20.0, 10.0, square_pixels=False, pixel_pitch_x_um=4.0, pixel_pitch_y_um=5.0),
    )
    metrics = camera_metrics(valid, camera_field(valid, CameraCaptureSettings(valid.profile_id)), 250.0)
    assert metrics.pixel_scale_x_arcsec == pytest.approx(206.265 * 4.0 / 250.0)
    assert metrics.pixel_scale_y_arcsec == pytest.approx(206.265 * 5.0 / 250.0)


def test_square_pitch_accepts_exact_two_percent_and_rejects_above() -> None:
    at_limit = CameraProfile(
        "camera:user:edge", "Edge",
        SensorFormat("custom", 36.72, 24.48, 6000, 4000, True, pixel_pitch_um=6.0),
    )
    camera_metrics(at_limit, camera_field(at_limit, CameraCaptureSettings(at_limit.profile_id)), 250.0)
    over_limit = CameraProfile(
        "camera:user:over", "Over",
        SensorFormat("custom", 36.721, 24.481, 6000, 4000, True, pixel_pitch_um=6.0),
    )
    with pytest.raises(OpticalValidationError):
        camera_metrics(over_limit, camera_field(over_limit, CameraCaptureSettings(over_limit.profile_id)), 250.0)


def test_photographic_model_v1_has_golden_terms_and_iso_independent_photons() -> None:
    model = PhotographicLimitingMagnitudeModelV1()
    values = PhotographicLimitingMagnitudeInputs(250.0, 4.0, 800.0, 2.0, 0.2, 6.1, 0.9)
    result = model.compute(values)
    aperture = 62.5
    atmosphere = 10 ** (-0.4 * 0.2)
    iso_gain = 2.5 + 1.25 * math.log10(2.0) * 3.0
    short = 1.6 * math.log10(2.5)
    expected = 3.4 + 2.5 * math.log10(aperture**2) + 1.25 * math.log10(2.0) + iso_gain + 2.5 * math.log10(0.9 * atmosphere) - short - 1.5
    assert result.estimated_limit_magnitude == pytest.approx(expected)
    assert result.captured_photon_index == pytest.approx(aperture**2 * 2.0 * 0.9 * atmosphere)
    high_iso = model.compute(PhotographicLimitingMagnitudeInputs(250.0, 4.0, 6400.0, 2.0, 0.2, 6.1, 0.9))
    assert high_iso.captured_photon_index == pytest.approx(result.captured_photon_index)
    assert high_iso.estimated_limit_magnitude > result.estimated_limit_magnitude


def test_photographic_model_v1_golden_branches_and_clamp() -> None:
    model = PhotographicLimitingMagnitudeModelV1()
    low_iso = model.compute(PhotographicLimitingMagnitudeInputs(50, 2, 100, 5, 0, 7.6))
    assert low_iso.iso_detection_gain_magnitude == pytest.approx(2.5)
    assert low_iso.short_exposure_penalty_magnitude == 0.0
    assert low_iso.sky_penalty_magnitude == 0.0
    assert low_iso.atmospheric_transmission == 1.0
    beyond_knee = model.compute(PhotographicLimitingMagnitudeInputs(50, 2, 1600, 1, 1, 5.6, 0.5))
    expected_iso = 2.5 + 1.25 * math.log10(2) * (3 + 0.25)
    assert beyond_knee.iso_detection_gain_magnitude == pytest.approx(expected_iso)
    assert beyond_knee.short_exposure_penalty_magnitude == pytest.approx(1.6 * math.log10(5))
    assert beyond_knee.sky_penalty_magnitude == pytest.approx(2.0)
    assert beyond_knee.total_transmission == pytest.approx(0.5 * 10 ** -0.4)
    clamped = model.compute(PhotographicLimitingMagnitudeInputs(10_000, 1, 1_000_000, 100_000, 0, 8))
    assert clamped.estimated_limit_magnitude == 22.0


def test_profiles_and_selected_profile_survive_restart(tmp_path: Path) -> None:
    published: list[dict] = []

    async def publish(payload: dict) -> None:
        published.append(payload)

    async def scenario() -> None:
        preferences = AtomicTextPreferencesAdapter(tmp_path)
        coordinator = ObservationCoordinator(preferences, publish)
        await coordinator.create_profile({
            "name": "Personal", "widthMm": 20.0, "heightMm": 15.0,
            "resolutionWidthPx": None, "resolutionHeightPx": None,
        })
        selected = coordinator.snapshot.camera.selected_profile_id
        restored = ObservationCoordinator(preferences, publish)
        assert restored.snapshot.mode.value == "eye"
        assert restored.snapshot.camera.selected_profile_id == selected
        assert any(profile.name == "Personal" for profile in restored.snapshot.camera_profiles)

    asyncio.run(scenario())


def test_corrupt_profiles_do_not_block_eye_startup(tmp_path: Path) -> None:
    corrupt = tmp_path / "camera_profiles.json"
    corrupt.write_text("{broken", encoding="utf-8")

    async def publish(_: dict) -> None:
        return None

    coordinator = ObservationCoordinator(AtomicTextPreferencesAdapter(tmp_path), publish)
    assert coordinator.snapshot.mode.value == "eye"
    assert coordinator.snapshot.warning is not None
    assert corrupt.read_text(encoding="utf-8") == "{broken"


def test_camera_frame_rotation_is_versioned_and_validated(tmp_path: Path) -> None:
    published: list[dict] = []

    async def publish(payload: dict) -> None:
        published.append(payload)

    coordinator = ObservationCoordinator(AtomicTextPreferencesAdapter(tmp_path), publish)
    asyncio.run(coordinator.configure_camera({"frameRotationDeg": -37.5}))
    assert coordinator.snapshot.camera.frame_rotation_deg == pytest.approx(-37.5)
    assert published[-1]["camera"]["frameRotationDeg"] == pytest.approx(-37.5)

    with pytest.raises(OpticalValidationError):
        asyncio.run(coordinator.configure_camera({"frameRotationDeg": 181}))


def test_deep_filter_deduplicates_and_top_n_is_global() -> None:
    first = _batch([1, 2, 0], [9.0, 10.0, 11.0], [0.0, 1.0, 2.0])
    second = _batch([2, 3, 0], [9.5, 8.5, 10.5], [3.0, 4.0, 2.0])
    seen: set[object] = set()
    a, keys = _filter_deep_batch(first, 8.0, 12.0, seen)
    seen.update(keys)
    b, _ = _filter_deep_batch(second, 8.0, 12.0, seen)
    selected = _merge_brightest(_merge_brightest(None, a, 3), b, 3)
    assert len(selected) == 3
    assert sorted(selected.mag.tolist()) == pytest.approx([8.5, 9.0, 10.0])
    assert selected.mag.max() <= 10.0


def test_deep_query_publishes_one_bounded_global_resource() -> None:
    coordinator = StarCoordinator()
    adapter = object.__new__(GaiaStarCatalogAdapter)
    adapter._availability = GaiaAvailability.READY
    batches = [_batch(list(range(1 + offset, 11 + offset)), list(np.linspace(8.1 + offset / 100, 12, 10)), list(np.linspace(0, 1, 10))) for offset in (0, 10, 20)]
    adapter.query_cone = lambda *_args, **_kwargs: iter(batches)  # type: ignore[method-assign]
    coordinator._adapter = adapter
    published: list[tuple[str, dict, int]] = []

    async def publish(resource_id: str, _version: str, metadata: dict, payload: bytes) -> None:
        published.append((resource_id, metadata, len(payload)))

    async def status(_: dict) -> None:
        return None

    async def transform(_: dict) -> None:
        return None

    coordinator.set_publishers(publish, status, transform)
    result = asyncio.run(coordinator.request_deep_catalog(
        deep_query_revision=4, ra_deg=0, dec_deg=0, radius_deg=5,
        photometric_limit=12, maximum_stars=7,
    ))
    assert result["selectedStarCount"] == 7
    assert result["truncated"] is True
    assert len(published) == 1
    assert published[0][0] == "stars:deep:camera"
    assert published[0][1]["deepQueryRevision"] == 4
    assert len(coordinator._batches["stars:deep:camera"]) == 7


def test_deep_query_cancellation_prevents_stale_publication() -> None:
    coordinator = StarCoordinator()
    adapter = object.__new__(GaiaStarCatalogAdapter)
    adapter._availability = GaiaAvailability.READY

    def query(*_args, **_kwargs):
        yield _batch([1], [9.0], [0.0])
        coordinator.cancel_deep_catalog(2)
        yield _batch([2], [9.5], [0.1])

    adapter.query_cone = query  # type: ignore[method-assign]
    coordinator._adapter = adapter
    published: list[str] = []

    async def publish(resource_id: str, _version: str, _metadata: dict, _payload: bytes) -> None:
        published.append(resource_id)

    async def noop(_: dict) -> None:
        return None

    coordinator.set_publishers(publish, noop, noop)
    result = asyncio.run(coordinator.request_deep_catalog(
        deep_query_revision=1, ra_deg=0, dec_deg=0, radius_deg=5,
        photometric_limit=12, maximum_stars=7,
    ))
    assert result["state"] == "cancelled"
    assert published == []


def test_required_values_are_strictly_positive() -> None:
    with pytest.raises(OpticalValidationError):
        camera_field(
            CameraProfile("bad", "Bad", SensorFormat("bad", 36.0, 24.0)),
            CameraCaptureSettings("bad", focal_length_mm=0.0),
        )
    optional_null = CameraProfile("ok", "Ok", SensorFormat("ok", 36.0, 24.0, pixel_pitch_um=None))
    camera_metrics(optional_null, camera_field(optional_null, CameraCaptureSettings("ok")), 250.0)
    invalid_optional = CameraProfile("bad", "Bad", SensorFormat("bad", 36.0, 24.0, pixel_pitch_um=math.nan))
    with pytest.raises(OpticalValidationError):
        camera_metrics(invalid_optional, camera_field(invalid_optional, CameraCaptureSettings("bad")), 250.0)


def _batch(source_ids: list[int], magnitudes: list[float], ras: list[float]) -> StarBatch:
    size = len(source_ids)
    return StarBatch(
        ra=np.asarray(ras, dtype=np.float64),
        dec=np.zeros(size, dtype=np.float64),
        mag=np.asarray(magnitudes, dtype=np.float32),
        bp_rp=np.ones(size, dtype=np.float32),
        source_id=np.asarray(source_ids, dtype=np.int64),
    )
