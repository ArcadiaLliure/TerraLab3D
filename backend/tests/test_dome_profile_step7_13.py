"""Oracle SciPy, propietats de forma i ruta real del kernel; cap fotometria nova."""

import json
import math
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from scipy.interpolate import PchipInterpolator

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from angular_fixtures_step7_13 import fixture
from terralab3d.application.dome_sampling import sample_dome
from terralab3d.domain.light_pollution.dome_profile import (
    DomeField,
    DomeProfile,
    pchip_value,
)
from terralab3d.domain.light_pollution.geometric_transport import ViewDirection
from terralab3d.domain.light_pollution.terrain_visibility import TerrainCoverageError
from terralab3d.domain.light_pollution.propagation_kernel import (
    DirectionSet,
    PropagationCancelledError,
    PropagationKernel,
    StalePropagationError,
)

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("seed", range(8))
def test_pchip_independent_scipy(seed):
    rng = np.random.default_rng(seed)
    x = np.cumsum(rng.uniform(0.1, 10, 15))
    y = rng.normal(0, 30, 15)
    oracle = PchipInterpolator(x, y)
    for q in np.linspace(x[0], x[-1], 103):
        assert pchip_value(tuple(x), tuple(y), float(q)) == pytest.approx(
            oracle(q), abs=2e-13
        )


def test_shared_golden():
    data = json.loads(
        (
            ROOT / "docs/evidencies/pas7.13/golden-pchip-python-typescript.json"
        ).read_text(encoding="utf8")
    )
    for case in data["cases"]:
        p = case["profile"]
        profile = DomeProfile(
            p["azimuthDeg"],
            tuple(p["elevationSamplesDeg"]),
            tuple(p["radianceSamples"]),
            p["epsilonRadiance"],
        )
        for query in case["queries"]:
            assert profile.evaluate(query["elevationDeg"]) == pytest.approx(
                query["expected"], rel=data["toleranceRelative"], abs=0
            )


@pytest.mark.parametrize("values", [(1.0, 2.0, 4.0), (4.0, 2.0, 1.0), (1.0, 4.0, 1.0)])
def test_no_overshoot_and_exact_knots(values):
    p = DomeProfile(0, (0.5, 20.0, 90.0), values, 1e-15)
    for i in range(2):
        for q in np.linspace(p.elevations_deg[i], p.elevations_deg[i + 1], 101):
            value = p.evaluate(float(q))
            assert (
                value is not None
                and min(values[i : i + 2]) - 1e-14
                <= value
                <= max(values[i : i + 2]) + 1e-14
            )
    assert tuple(p.evaluate(q) for q in p.elevations_deg) == values


def test_zero_does_not_create_transparent_occlusion():
    p = DomeProfile(90, (0.5, 2.0, 5.0, 90.0), (0.0, 0.0, 1e-12, 2e-12), 1e-27)
    assert p.evaluate(0.5) == 0
    assert p.evaluate(1) is None  # Dos zeros no demostren foscor entre ells.
    assert p.evaluate(3) is None
    value = p.evaluate(40)
    assert value is not None and value > 0
    blocked = replace(p, blocked_intervals=(False, False, True))
    assert blocked.evaluate(40) is None
    assert blocked.evaluate(90) == 2e-12


@pytest.mark.parametrize("az", [-720.0, -360.0, 0.0, 360.0, 720.0])
def test_azimuth_wrap_and_zenith(az):
    p = DomeProfile(0.0, (0.5, 20.0, 90.0), (4e-12, 2e-12, 1e-12), 1e-27)
    field = DomeField(
        (p, replace(p, azimuth_deg=180.0)), "W m^-2 sr^-1", "fixture", 0, 75000.0
    )
    assert field.evaluate(az, 20) == 2e-12
    assert field.evaluate(az + 37.5, 90) == 1e-12
    assert field.evaluate(-0.00001, 20) == pytest.approx(
        field.evaluate(359.99999, 20), rel=1e-14
    )


@pytest.mark.parametrize("e", [0.0, 90.1, float("nan")])
def test_no_extrapolation(e):
    p = DomeProfile(0, (0.5, 90.0), (1.0, 2.0), 1e-15)
    with pytest.raises(ValueError):
        p.evaluate(e)


def test_invalid_epsilon_and_nodes():
    with pytest.raises(ValueError):
        DomeProfile(0, (0.5, 90.0), (1e-12, 1e-12), 1e-20)
    with pytest.raises(ValueError):
        DomeProfile(0, (0.5, 0.5), (1.0, 2.0), 1e-15)


def test_direct_service_same_kernel_and_linear_sum():
    req = fixture("S_B4_chamber_point_5km")
    req = replace(
        req,
        sources=(
            req.sources[0],
            replace(req.sources[0], source_model_id="second-source"),
        ),
    )
    result = sample_dome(
        req, (0.0, 90.0, 180.0, 270.0), elevations_deg=(0.5, 30.0, 90.0)
    )
    direct = PropagationKernel().evaluate(
        replace(req, directions=DirectionSet((ViewDirection("zenith", 90, 90),)))
    )
    expected = math.fsum(r.integral for r in direct.rays)
    assert result.evaluate(90, 90) == expected
    for az in (0.0, 45.0, 90.0, 180.0, 270.0, 359.9):
        assert result.evaluate(az, 90) == pytest.approx(expected, rel=1e-12, abs=0)
    assert result.top_m == 75000
    assert "inputSignature=" in result.provenance


@pytest.mark.parametrize("kind", ["cancel", "stale"])
def test_cooperative_guard(kind):
    req = fixture("S_B4_chamber_point_5km")
    with pytest.raises(
        PropagationCancelledError if kind == "cancel" else StalePropagationError
    ):
        sample_dome(
            req,
            (0.0, 180.0),
            cancelled=lambda: kind == "cancel",
            is_current=lambda: kind != "stale",
        )


def test_terrain_no_unproved_interpolation():
    req = fixture("S_B4_chamber_mountain_point_5km")
    result = sample_dome(req, (89.0, 90.0), elevations_deg=(0.5, 90.0))
    assert result.direct_only
    assert result.evaluate(90, 0.5) == 0
    assert result.evaluate(90, 25) is None
    assert result.evaluate(91, 90) is None


def test_terrain_missing_coverage_is_not_transparent():
    req = fixture("S_B4_chamber_mountain_point_5km")
    with pytest.raises(TerrainCoverageError):
        sample_dome(req, (0.0, 270.0), elevations_deg=(0.5, 90.0))


@pytest.mark.parametrize(
    "mode", ["C_realista_chamber_point_5km", "C_kelvins3000_chamber_point_5km"]
)
def test_c_keeps_relative_scale(mode):
    result = sample_dome(fixture(mode), (0.0, 180.0), elevations_deg=(0.5, 90.0))
    assert result.radiance_unit.startswith("relative ")
    assert all(v > 0 for p in result.profiles for v in p.radiances)


def test_no_implicit_standard_10km():
    req = fixture("S_B4_standard_point_5km")
    assert req.options.top_m == 75000
    assert req.optical_field is not None
    assert all(t.profile.heights_m[-1] == 75000 for t in req.optical_field.tiles)
