"""Invariants B0, quadratura analítica i descart de revisions amb fils reals."""

from __future__ import annotations

import json
import math
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Event

import numpy as np
import pytest
from pyproj import Transformer

from terralab3d.application.geometric_propagation import GeometricPropagationSession
from terralab3d.domain.light_pollution.gauss_kronrod import (
    QuadratureConvergenceError,
    QuadratureSettings,
    integrate_gk15,
)
from terralab3d.domain.light_pollution.geometric_transport import (
    EARTH_RADIUS_M,
    GeometricPartition,
    SphericalFrame,
    ViewDirection,
    make_ray,
)
from terralab3d.domain.light_pollution.propagation_kernel import (
    DirectionSet,
    PropagationCancelledError,
    PropagationKernel,
    PropagationOptions,
    PropagationRequest,
    StalePropagationError,
)
from terralab3d.domain.light_pollution.source_model import (
    AngularEmissionProfile,
    DefinedSpectrum,
    EmissionAmplitude,
    GeodeticPosition,
    PointSourceGeometry,
    SourceModel,
)


def request() -> PropagationRequest:
    s = SourceModel(
        "b0-test",
        "v1",
        "Fixture definida",
        PointSourceGeometry(GeodeticPosition(41.4, 2.2, 0)),
        DefinedSpectrum(
            "flat", "Definició de prova", "CC0-1.0", (400.0, 700.0), (1.0, 1.0)
        ),
        AngularEmissionProfile(
            "uniform", "Definició de prova", (0.0, 90.0), (1.0, 1.0)
        ),
        EmissionAmplitude(1, "W", "defined_absolute", "Definició de prova"),
    )
    directions = DirectionSet(
        tuple(ViewDirection(str(e), 30, e) for e in (0.5, 2, 5, 10, 20, 30, 45, 60, 90))
    )
    return PropagationRequest(
        (s,), GeodeticPosition(41.3875, 2.1666667, 100), directions
    )


@pytest.mark.parametrize(
    "lat,lon",
    [(0, 0), (90, 0), (-90, 180), (41.3875, 2.1666667), (0, 180), (70, -179.999)],
)
def test_spherical_ecef_against_independent_proj_and_rotation(lat, lon):
    p = GeodeticPosition(lat, lon, 100)
    frame = SphericalFrame(p)
    transform = Transformer.from_crs(
        f"+proj=longlat +R={EARTH_RADIUS_M}",
        f"+proj=geocent +R={EARTH_RADIUS_M}",
        always_xy=True,
    )
    expected = transform.transform(lon, lat, 100)
    assert frame.position_ecef(p) == pytest.approx(
        expected, abs=64 * np.finfo(float).eps * EARTH_RADIUS_M
    )
    rotation = np.array(frame.basis)
    assert rotation @ rotation.T == pytest.approx(np.eye(3), abs=1e-15)
    assert np.linalg.det(rotation) == pytest.approx(1, abs=1e-15)
    vector = (12.0, -45.0, 78.0)
    assert frame.ecef_to_enu(frame.enu_to_ecef(vector)) == pytest.approx(
        vector, abs=1e-13
    )


@pytest.mark.parametrize("elevation", [0.5, 2, 10, 45, 89.999999, 90])
def test_ray_endpoint_on_sphere_and_contiguous_partition(elevation):
    frame = SphericalFrame(GeodeticPosition(41.3, 2.1, 100))
    ray = make_ray(frame, ViewDirection("view", 137, elevation), 10000)
    assert math.hypot(*ray.point(ray.length_m)) == pytest.approx(
        EARTH_RADIUS_M + 10000, abs=1e-7
    )
    q = (EARTH_RADIUS_M + 100) * math.sin(math.radians(elevation))
    independent = -q + math.sqrt(
        q * q + (EARTH_RADIUS_M + 10000) ** 2 - (EARTH_RADIUS_M + 100) ** 2
    )
    assert ray.length_m == pytest.approx(independent, abs=1e-7)
    segments = GeometricPartition().segments(ray, 10000, 4096)
    assert segments[0].start_m == 0 and segments[-1].end_m == ray.length_m
    assert all(a.end_m == b.start_m for a, b in zip(segments, segments[1:]))
    assert all(s.end_m > s.start_m for s in segments)


@pytest.mark.parametrize("power", range(24))
def test_gk15_polynomials_against_exact_antiderivative(power):
    result = integrate_gk15(
        lambda x: x**power, ((0.0, 1.0),), QuadratureSettings(1e-11, 1e-13)
    )
    assert result.value == pytest.approx(1 / (power + 1), abs=1e-13)
    assert result.evaluations == 15 + 30 * result.subdivisions
    assert result.leaf_intervals == 1 + result.subdivisions


def test_gk15_adaptive_segments_and_failure():
    def f(x: float) -> float:
        return math.exp(-100 * x)

    loose = integrate_gk15(f, ((0.0, 1.0),), QuadratureSettings(1e-4, 1e-8))
    tight = integrate_gk15(f, ((0.0, 1.0),), QuadratureSettings(1e-11, 1e-13))
    assert tight.subdivisions > 0 and tight.evaluations >= loose.evaluations
    assert tight.value == pytest.approx((1 - math.exp(-100)) / 100, abs=1e-13)
    piecewise = integrate_gk15(
        lambda x: 2 if x < 0.123 else 5, ((0.0, 0.123), (0.123, 1.0))
    )
    assert piecewise.value == pytest.approx(2 * 0.123 + 5 * 0.877)
    assert piecewise.evaluations == 30 and piecewise.subdivisions == 0
    with pytest.raises(QuadratureConvergenceError):
        integrate_gk15(f, ((0.0, 1.0),), QuadratureSettings(1e-12, 1e-14, 1))
    with pytest.raises(QuadratureConvergenceError):
        integrate_gk15(lambda x: float("nan"), ((0.0, 1.0),))


def test_kernel_zenith_same_operator_reproducible_counters_and_units():
    req = request()
    kernel = PropagationKernel()
    result = kernel.evaluate(req)
    assert result == kernel.evaluate(req)
    assert len(result.rays) == 9 and result.counters.los_count == 9
    for ray in result.rays:
        assert abs(ray.integral - ray.path_length_m) <= 64 * np.finfo(float).eps * max(
            1, ray.path_length_m
        )
        assert (
            ray.counters.quadrature_node_count
            == 15 * ray.counters.segment_count + 30 * ray.counters.gk_subdivision_count
        )
        assert (
            ray.counters.leaf_interval_count
            == ray.counters.segment_count + ray.counters.gk_subdivision_count
        )
    single = kernel.evaluate(
        replace(req, directions=DirectionSet((req.directions.directions[-1],)))
    )
    assert single.rays[0] == result.rays[-1]
    assert single.rays[0].counters.quadrature_node_count > 0
    assert result.integral_unit == "m"
    assert result.to_dict()["stage"] == "geometry_B0_not_radiance"
    json.dumps(result.to_dict(), allow_nan=False)
    assert (
        kernel.evaluate(replace(req, revision=1)).input_signature
        != result.input_signature
    )


def test_kernel_source_bearing_relative_sources_and_segment_invariance():
    req = request()
    one = replace(
        req, directions=DirectionSet((ViewDirection("view", 0, 30),), "source_bearing")
    )
    result = PropagationKernel().evaluate(one)
    assert 0 < result.rays[0].azimuth_deg < 90
    different = replace(
        one,
        options=replace(
            one.options, partition=GeometricPartition(1000, (2000.0, 4000.0, 6000.0))
        ),
    )
    finer = PropagationKernel().evaluate(different)
    assert finer.rays[0].integral == pytest.approx(result.rays[0].integral, rel=1e-14)
    assert finer.counters.segment_count > result.counters.segment_count
    relative = replace(
        req.sources[0],
        source_mode="CONDITIONAL_L3",
        amplitude=EmissionAmplitude(
            1, "relative", "parametric", "Definició de prova", "r"
        ),
    )
    conditional = PropagationKernel().evaluate(replace(req, sources=(relative,)))
    assert conditional.rays == PropagationKernel().evaluate(req).rays


@pytest.mark.parametrize(
    "factory",
    [
        lambda: ViewDirection("view", float("nan"), 30),
        lambda: ViewDirection("view", 0, 0),
        lambda: GeometricPartition(0),
        lambda: QuadratureSettings(0, 1),
        lambda: PropagationOptions(model_version="incompatible"),
        lambda: replace(request(), revision=-1),
        lambda: replace(request(), sources=()),
    ],
)
def test_invalid_requests_fail_closed(factory):
    with pytest.raises(ValueError):
        factory()


def test_budget_cancel_and_stale_do_not_publish_partial():
    req = request()
    with pytest.raises(ValueError):
        PropagationKernel().evaluate(
            replace(req, options=replace(req.options, max_segments_per_ray=1))
        )
    with pytest.raises(PropagationCancelledError):
        PropagationKernel().evaluate(req, cancelled=lambda: True)
    with pytest.raises(StalePropagationError):
        PropagationKernel().evaluate(req, is_current=lambda: False)
    session = GeometricPropagationSession()
    current = session.begin(req)
    session.cancel()
    with pytest.raises(PropagationCancelledError):
        session.compute(current)
    assert session.result is None and session.cancelled_jobs == 1
    session.close()
    with pytest.raises(RuntimeError):
        session.begin(req)


def test_real_inflight_revision_is_discarded_without_timing_race():
    session = GeometricPropagationSession()
    entered, release = Event(), Event()
    old = session.begin(request())

    def blocked(sample, source):
        entered.set()
        assert release.wait(5)
        return 1.0

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(session.compute, old, blocked)
        assert entered.wait(5)
        current = session.begin(request())
        release.set()
        with pytest.raises(StalePropagationError):
            future.result(timeout=5)
    assert session.result is None and session.stale_results_discarded == 1
    latest = session.compute(current)
    assert session.result == latest and latest.revision > old.revision
    session.close()
