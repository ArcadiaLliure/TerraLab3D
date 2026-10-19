"""Oracles independents, refinament, zeros i límits de la reconstrucció v2."""

import math
import json
import random
import sys
from dataclasses import replace
from pathlib import Path

import pytest
from scipy.interpolate import PchipInterpolator

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from angular_fixtures_step7_13 import fixture
from terralab3d.application.adaptive_dome_sampling import sample_adaptive_dome
from terralab3d.domain.light_pollution.adaptive_dome import (
    AdaptiveDomeField,
    AdaptiveSettings,
    AngularBudgetExceededError,
    build_adaptive_dome,
    magnitude_error,
)
from terralab3d.domain.light_pollution.dome_profile import DomeProfile
from terralab3d.domain.light_pollution.propagation_kernel import (
    PropagationCancelledError,
    StalePropagationError,
)


def test_shared_ragged_golden_independent_scipy():
    from validate_adaptive_dome_step7_13_v2 import decode

    path = (
        Path(__file__).resolve().parents[2]
        / "docs/evidencies/pas7.13/adaptatiu-v2/golden-python-typescript-v2.json"
    )
    data = json.loads(path.read_text(encoding="utf8"))
    for case in data["cases"]:
        field = decode(case["field"])
        for query in case["queries"]:
            assert field.evaluate(
                query["azimuthDeg"], query["elevationDeg"]
            ) == pytest.approx(query["expected"], rel=data["relativeMaximum"], abs=0)


def manufactured(a, e):
    d = (a - 90 + 180) % 360 - 180
    return math.exp(4 * math.exp(-((d / 4) ** 2)) * ((90 - e) / 89.5) ** 2 - e / 40)


def test_adaptive_refinement_on_independent_points():
    result = build_adaptive_dome(
        manufactured,
        radiance_unit="relative",
        provenance="Analítica",
        revision=0,
        top_m=75000.0,
    )
    assert 8 < len(result.field.profiles) < 128
    assert any(len(p.elevations_deg) > 9 for p in result.field.profiles)
    assert result.maximum_vertical_probe_error_mag <= 0.002
    assert result.maximum_azimuth_probe_error_mag <= 0.002
    rng = random.Random(91827)
    for _ in range(350):
        a, e = rng.uniform(0, 360), rng.uniform(0.5, 90)
        assert magnitude_error(result.field.evaluate(a, e), manufactured(a, e)) < 0.01


@pytest.mark.parametrize(
    "az", [-720.3, -0.3, 0.3, 45.0, 95.0, 180.0, 270.0, 359.7, 719.7]
)
def test_periodic_pchip_independent_scipy(az):
    angles = (0.0, 90.0, 180.0, 270.0)
    b = (1.0, 4.0, 2.0, 3.0)
    profiles = tuple(
        DomeProfile(a, (0.5, 90.0), (v, 1.0), 1e-15) for a, v in zip(angles, b)
    )
    field = AdaptiveDomeField(profiles, "relative", "fixture", 0, 75000.0)
    x = tuple(a + shift for shift in (-360, 0, 360) for a in angles)
    y = tuple(math.log(v + 1e-15) for _ in range(3) for v in b)
    expected = math.exp(PchipInterpolator(x, y)(az % 360)) - 1e-15
    assert field.evaluate(az, 0.5) == pytest.approx(expected, rel=2e-14)
    assert field.evaluate(az, 90) == pytest.approx(1.0, rel=2e-14)


def test_zero_and_topology_barriers():
    profiles = tuple(
        DomeProfile(float(a), (0.5, 2.0, 90.0), (0.0, 1.0, 1.0), 1e-15)
        for a in (0, 90, 180, 270)
    )
    field = AdaptiveDomeField(profiles, "relative", "fixture", 0, 75000.0)
    assert field.evaluate(0, 0.5) == 0
    assert field.evaluate(45, 0.5) is None
    assert field.evaluate(0, 1.0) is None
    blocked = replace(field, blocked_azimuth_intervals=(True, False, False, False))
    assert blocked.evaluate(45, 45) is None
    assert blocked.evaluate(90, 90) == 1


def test_budget_exhaustion_does_not_publish_field():
    with pytest.raises(AngularBudgetExceededError):
        build_adaptive_dome(
            manufactured,
            radiance_unit="relative",
            provenance="fixture",
            revision=0,
            top_m=75000.0,
            settings=AdaptiveSettings(maximum_samples=8),
        )


def test_hidden_zero_requires_direct():
    with pytest.raises(ValueError, match="zero"):
        build_adaptive_dome(
            lambda a, e: 0.0,
            radiance_unit="relative",
            provenance="fixture",
            revision=0,
            top_m=75000.0,
        )


@pytest.mark.parametrize("flag", ["cancel", "stale"])
def test_kernel_guard(flag):
    req = fixture("S_B4_chamber_point_5km")
    with pytest.raises(
        PropagationCancelledError if flag == "cancel" else StalePropagationError
    ):
        sample_adaptive_dome(
            req, cancelled=lambda: flag == "cancel", is_current=lambda: flag != "stale"
        )


def test_dem_never_assumed_continuous():
    with pytest.raises(ValueError, match="DEM"):
        sample_adaptive_dome(fixture("S_B4_chamber_mountain_point_5km"))


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(internal_magnitude_maximum=0),
        dict(maximum_samples=0),
        dict(maximum_azimuth_profiles=3),
    ],
)
def test_invalid_settings(kwargs):
    with pytest.raises(ValueError):
        AdaptiveSettings(**kwargs)


def test_inconsistent_zenith_rejected():
    profiles = tuple(
        DomeProfile(float(a), (0.5, 90.0), (1.0, float(a + 1)), 1e-15)
        for a in (0, 90, 180, 270)
    )
    with pytest.raises(ValueError, match="zenit"):
        AdaptiveDomeField(profiles, "relative", "fixture", 0, 75000.0)
