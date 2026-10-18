"""Camps 1/2/8 tiles, dependències exactes i columnes independents."""

from __future__ import annotations

import json
import math
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from threading import Event

import pytest

from terralab3d.application.geometric_propagation import GeometricPropagationSession
from terralab3d.application.ports.atmospheric_optics import (
    AtmosphericOpticsProvider,
    OpticalFieldRequest,
    OpticalTileSpec,
)
from terralab3d.domain.light_pollution.geometric_transport import (
    SphericalFrame,
    ViewDirection,
    make_ray,
)
from terralab3d.domain.light_pollution.optical_field import (
    BOLTZMANN_J_K,
    OpticalCoverageError,
    OpticalField,
    TileBounds,
)
from terralab3d.domain.light_pollution.propagation_kernel import (
    DirectionSet,
    PropagationCancelledError,
    PropagationKernel,
    PropagationRequest,
    StalePropagationError,
    number_density_integrand,
)
from terralab3d.domain.light_pollution.reference_optical_column import (
    ReferenceColumnCancelledError,
    reference_optical_column,
)
from terralab3d.domain.light_pollution.source_model import (
    AngularEmissionProfile,
    DefinedSpectrum,
    EmissionAmplitude,
    GeodeticPosition,
    PointSourceGeometry,
    SourceModel,
)
from terralab3d.infrastructure.adapters.atmosphere.standard_optics import (
    GEOPOTENTIAL_RADIUS_M,
    StandardAtmosphericOpticsProvider,
    standard_pressure_temperature,
)

TIME = datetime(2026, 10, 19, tzinfo=timezone.utc)
ORIGIN = GeodeticPosition(0, 0, 0)


def field_request(count=1, step=100.0) -> OpticalFieldRequest:
    cuts = [-100.0] + [i * 9600 / count for i in range(1, count)] + [20000.0]
    tiles = tuple(
        OpticalTileSpec(f"tile-{i}", "data-v1", TileBounds(a, b, -20000, 20000))
        for i, (a, b) in enumerate(zip(cuts, cuts[1:]))
    )
    return OpticalFieldRequest(ORIGIN, TIME, tiles, vertical_step_m=step)


def request(field: OpticalField) -> PropagationRequest:
    source = SourceModel(
        "defined",
        "v1",
        "Fixture geomètrica",
        PointSourceGeometry(GeodeticPosition(0, 0.05, 0)),
        DefinedSpectrum("flat", "Definició", "CC0-1.0", (400.0, 700.0), (1.0, 1.0)),
        AngularEmissionProfile("uniform", "Definició", (0.0, 90.0), (1.0, 1.0)),
        EmissionAmplitude(1, "W", "defined_absolute", "Definició"),
    )
    return PropagationRequest(
        (source,),
        GeodeticPosition(0, 0, 100),
        DirectionSet((ViewDirection("east45", 90, 45),)),
        optical_field=field,
    )


@pytest.mark.parametrize(
    "height", [0.0, 1000.0, 10000.0, 15000.0, 25000.0, 40000.0, 50000.0]
)
def test_analytic_provider_against_decimal_hydrostatic_definition(height):
    with localcontext() as ctx:
        ctx.prec = 50
        z = Decimal(height)
        radius = Decimal("6356766")
        h = radius * z / (radius + z)
        bases = [Decimal(x) for x in (0, 11000, 20000, 32000, 47000, 51000)]
        slopes = [Decimal(x) for x in ("-.0065", "0", ".001", ".0028", "0")]
        p, t = Decimal("101325"), Decimal("288.15")
        c = Decimal("9.80665") * Decimal(".0289644") / Decimal("8.31432")
        for i, slope in enumerate(slopes):
            dz = min(h, bases[i + 1]) - bases[i]
            if dz < 0:
                break
            target = t + slope * dz
            log_ratio = -c * dz / t if not slope else -c / slope * (target / t).ln()
            p *= log_ratio.exp()
            t = target
            if h <= bases[i + 1]:
                break
    observed = standard_pressure_temperature(height)
    assert observed == pytest.approx((float(p), float(t)), rel=3e-14)


@pytest.mark.parametrize(
    "h,t",
    [(0, 288.15), (11000, 216.65), (20000, 216.65), (32000, 228.65), (47000, 270.65)],
)
def test_published_geopotential_temperature_knots(h, t):
    z = GEOPOTENTIAL_RADIUS_M * h / (GEOPOTENTIAL_RADIUS_M - h)
    assert standard_pressure_temperature(z)[1] == pytest.approx(t, abs=1e-10)


def test_provider_contract_provenance_time_and_interpolation_convergence():
    provider: AtmosphericOpticsProvider = StandardAtmosphericOpticsProvider()
    errors = []
    for step in (1000.0, 500.0, 250.0, 125.0):
        field = provider.resolve(field_request(step=step))
        errors.append(
            max(
                abs(
                    field.tiles[0].profile.values(h)[0]
                    / standard_pressure_temperature(h)[0]
                    - 1
                )
                for h in (75.0, 175.0, 1375.0, 7675.0, 9875.0)
            )
        )
    assert all(b < a for a, b in zip(errors, errors[1:]))
    field = provider.resolve(field_request())
    assert field == provider.resolve(field_request())
    assert field.signature == provider.resolve(field_request()).signature
    state = field.sample(
        SphericalFrame(ORIGIN).position_ecef(GeodeticPosition(0, 0, 1375))
    )
    assert state.pressure_pa > 0 and state.temperature_k > 0
    assert (
        state.number_density_m3 * BOLTZMANN_J_K * state.temperature_k
        == pytest.approx(state.pressure_pa, rel=1e-15)
    )
    assert state.relative_humidity == 0
    assert (
        state.aerosol_state is None
        and state.gas_absorption_state is None
        and state.cloud_optics is None
    )
    assert {p.field_name for p in state.fields_provenance} == {
        "pressure",
        "temperature",
        "relative_humidity",
        "number_density",
    }
    json.dumps(field.to_dict(), allow_nan=False)
    json.dumps(state.to_dict(), allow_nan=False)


@pytest.mark.parametrize("count", [1, 2, 8])
def test_kernel_exact_tiles_layers_and_independent_column(count):
    field = StandardAtmosphericOpticsProvider().resolve(field_request(count))
    req = request(field)
    result = PropagationKernel().evaluate(
        req,
        number_density_integrand,
        integrand_id="number-column-v1",
        integral_unit="m^-2",
    )
    ray = make_ray(
        SphericalFrame(req.observer), req.directions.directions[0], req.options.top_m
    )
    reference = reference_optical_column(field, ray)
    assert result.rays[0].integral == pytest.approx(
        reference.number_column_m2, rel=1e-8
    )
    trace = result.optical_traces[0]
    assert {d.tile_id for d in trace.sampled_dependencies} == {
        f"tile-{i}" for i in range(count)
    }
    assert set(trace.sampled_dependencies) == {
        s.dependency for s in trace.traversed_segments
    }
    assert (
        trace.traversed_segments[0].start_m == 0
        and trace.traversed_segments[-1].end_m == ray.length_m
    )
    assert all(
        a.end_m == b.start_m
        for a, b in zip(trace.traversed_segments, trace.traversed_segments[1:])
    )
    assert result.to_dict()["schemaVersion"] == 2
    json.dumps(result.to_dict(), allow_nan=False)


def test_partition_invariance_lateral_discontinuity_and_zenith():
    kernel = PropagationKernel()
    one = StandardAtmosphericOpticsProvider().resolve(field_request(1))
    two = StandardAtmosphericOpticsProvider().resolve(field_request(2))

    def column(field):
        return kernel.evaluate(
            request(field),
            number_density_integrand,
            integrand_id="column",
            integral_unit="m^-2",
        )

    assert column(one).rays[0].integral == pytest.approx(
        column(two).rays[0].integral, rel=1e-12
    )
    tile = two.tiles[1]
    profile = replace(
        tile.profile,
        pressure_pa=tuple(p * 0.8 for p in tile.profile.pressure_pa),
        revision="prescribed-contrast-v1",
    )
    changed = replace(
        two, tiles=(two.tiles[0], replace(tile, profile=profile, version="data-v2"))
    )
    assert column(changed).rays[0].integral < column(two).rays[0].integral
    req = request(changed)
    ref = reference_optical_column(
        changed,
        make_ray(SphericalFrame(req.observer), req.directions.directions[0], 10000),
    )
    assert column(changed).rays[0].integral == pytest.approx(
        ref.number_column_m2, rel=1e-8
    )
    zenith = replace(req, directions=DirectionSet((ViewDirection("zenith", 90, 90),)))
    result = kernel.evaluate(zenith, number_density_integrand)
    assert {d.tile_id for d in result.optical_traces[0].sampled_dependencies} == {
        "tile-0"
    }


def test_unused_tiles_and_layers_do_not_invalidate_dependency_signature():
    field = StandardAtmosphericOpticsProvider().resolve(field_request(2))
    extra = replace(
        field.tiles[0], tile_id="unused", bounds=TileBounds(30000, 40000, -20000, 20000)
    )
    first = replace(field, tiles=(*field.tiles, extra))
    second = replace(first, tiles=(*field.tiles, replace(extra, version="data-v999")))
    kernel = PropagationKernel()
    a = kernel.evaluate(request(first), number_density_integrand)
    b = kernel.evaluate(request(second), number_density_integrand)
    assert a.input_signature != b.input_signature
    assert a.optical_dependency_signature == b.optical_dependency_signature
    # L'observador és a 100 m: el nus a 0 m no és usat per cap segment.
    profile = field.tiles[0].profile
    modified = replace(
        profile, pressure_pa=(profile.pressure_pa[0] * 0.99, *profile.pressure_pa[1:])
    )
    c = kernel.evaluate(
        request(
            replace(
                field, tiles=(replace(field.tiles[0], profile=modified), field.tiles[1])
            )
        ),
        number_density_integrand,
    )
    baseline = kernel.evaluate(request(field), number_density_integrand)
    assert c.optical_dependency_signature == baseline.optical_dependency_signature
    modified = replace(
        profile, pressure_pa=tuple(p * 0.99 for p in profile.pressure_pa)
    )
    d = kernel.evaluate(
        request(
            replace(
                field, tiles=(replace(field.tiles[0], profile=modified), field.tiles[1])
            )
        ),
        number_density_integrand,
    )
    assert d.optical_dependency_signature != baseline.optical_dependency_signature


def test_world_origin_time_boundary_ownership_and_no_extrapolation():
    field = StandardAtmosphericOpticsProvider().resolve(field_request(2))
    frame = SphericalFrame(ORIGIN)
    boundary = (6371108.8, 4800.0, 0.0)
    assert field.sample(boundary).dependency.tile_id == "tile-1"
    later = replace(field, time_utc=datetime(2026, 10, 20, tzinfo=timezone.utc))
    assert field.signature != later.signature
    req = request(field)
    shifted = replace(req, observer=GeodeticPosition(0, 0.001, 100))
    assert shifted.optical_field is field
    assert (
        PropagationKernel().evaluate(shifted).optical_field_signature == field.signature
    )
    with pytest.raises(OpticalCoverageError):
        field.sample(frame.position_ecef(GeodeticPosition(0, 0, 10001)))


@pytest.mark.parametrize(
    "failure",
    [
        "missing",
        "gap",
        "overlap",
        "negative",
        "nan",
        "time",
        "radius",
        "provider_top",
        "provider_budget",
    ],
)
def test_bad_fields_fail_closed(failure):
    provider = StandardAtmosphericOpticsProvider()
    spec = field_request(2)
    field = provider.resolve(spec)
    with pytest.raises(ValueError):
        if failure == "missing":
            PropagationKernel().evaluate(
                request(replace(field, tiles=(field.tiles[0],)))
            )
        if failure == "gap":
            PropagationKernel().evaluate(
                request(
                    replace(
                        field,
                        tiles=(
                            field.tiles[0],
                            replace(
                                field.tiles[1],
                                bounds=TileBounds(5000, 20000, -20000, 20000),
                            ),
                        ),
                    )
                )
            )
        if failure == "overlap":
            replace(
                field,
                tiles=(
                    field.tiles[0],
                    replace(field.tiles[1], bounds=field.tiles[0].bounds),
                ),
            )
        if failure == "negative":
            replace(
                field.tiles[0].profile,
                pressure_pa=(-1.0, *field.tiles[0].profile.pressure_pa[1:]),
            )
        if failure == "nan":
            replace(
                field.tiles[0].profile,
                temperature_k=(math.nan, *field.tiles[0].profile.temperature_k[1:]),
            )
        if failure == "time":
            replace(spec, time_utc=datetime(2026, 10, 19))
        if failure == "radius":
            replace(request(field), optical_field=replace(field, radius_m=6370000))
        if failure == "provider_top":
            provider.resolve(replace(spec, top_m=50001))
        if failure == "provider_budget":
            provider.resolve(replace(spec, vertical_step_m=0.001))


def test_optical_cancel_stale_and_backwards_B0_schema():
    req = request(StandardAtmosphericOpticsProvider().resolve(field_request()))
    with pytest.raises(PropagationCancelledError):
        PropagationKernel().evaluate(req, cancelled=lambda: True)
    with pytest.raises(StalePropagationError):
        PropagationKernel().evaluate(req, is_current=lambda: False)
    session = GeometricPropagationSession()
    current = session.begin(req)
    session.cancel()
    with pytest.raises(PropagationCancelledError):
        session.compute(current, number_density_integrand)
    assert session.result is None
    b0 = PropagationKernel().evaluate(replace(req, optical_field=None))
    assert b0.to_dict()["schemaVersion"] == 1 and "optical_traces" not in b0.to_dict()


def test_optical_inflight_revision_with_actual_state_and_snapshot():
    field = StandardAtmosphericOpticsProvider().resolve(field_request(2))
    session = GeometricPropagationSession()
    old = session.begin(request(field))
    entered, release = Event(), Event()

    def blocked(sample, source):
        assert sample.optical_state is not None and sample.optical_state.pressure_pa > 0
        entered.set()
        assert release.wait(5)
        return sample.optical_state.number_density_m3

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(session.compute, old, blocked)
        assert entered.wait(5)
        new = session.begin(
            request(
                replace(field, time_utc=datetime(2026, 10, 20, tzinfo=timezone.utc))
            )
        )
        release.set()
        with pytest.raises(StalePropagationError):
            future.result(timeout=5)
    assert session.result is None
    current = session.compute(new, number_density_integrand, integral_unit="m^-2")
    assert new.optical_field is not None
    assert current.optical_field_signature == new.optical_field.signature
    session.close()


def test_oracle_cancel_and_reject_any_positive_coverage_gap():
    field = StandardAtmosphericOpticsProvider().resolve(field_request(2))
    req = request(field)
    ray = make_ray(SphericalFrame(req.observer), req.directions.directions[0], 10000)
    with pytest.raises(ReferenceColumnCancelledError):
        reference_optical_column(field, ray, cancelled=lambda: True)
    changed = replace(
        field,
        tiles=(
            field.tiles[0],
            replace(
                field.tiles[1], bounds=TileBounds(4800.00000001, 20000, -20000, 20000)
            ),
        ),
    )
    with pytest.raises(OpticalCoverageError):
        PropagationKernel().evaluate(request(changed))


def test_negative_direction_and_budget_and_time_change_dependencies():
    field = StandardAtmosphericOpticsProvider().resolve(field_request(2))
    req = request(field)
    # Tornem cap a l'oest dins del primer tile; no es creen dependències fictícies.
    west = replace(
        req,
        observer=GeodeticPosition(0, 0.04, 100),
        directions=DirectionSet((ViewDirection("west", 270, 60),)),
    )
    # Cobertura explícita a l'oest per incloure tota la LOS descendent en x.
    wide = replace(
        field,
        tiles=(
            replace(field.tiles[0], bounds=TileBounds(-20000, 4800, -20000, 20000)),
            field.tiles[1],
        ),
    )
    result = PropagationKernel().evaluate(
        replace(west, optical_field=wide), number_density_integrand
    )
    assert {d.tile_id for d in result.optical_traces[0].sampled_dependencies} == {
        "tile-0"
    }
    with pytest.raises(ValueError):
        PropagationKernel().evaluate(
            replace(req, options=replace(req.options, max_segments_per_ray=1))
        )
    later = replace(field, time_utc=datetime(2026, 10, 20, tzinfo=timezone.utc))
    a = PropagationKernel().evaluate(req)
    b = PropagationKernel().evaluate(request(later))
    assert a.optical_dependency_signature != b.optical_dependency_signature


def test_zenith_parallel_boundary_ownership_is_azimuth_invariant():
    field = StandardAtmosphericOpticsProvider().resolve(field_request(2))
    field = replace(
        field,
        tiles=(
            replace(field.tiles[0], bounds=TileBounds(-20000, 0, -20000, 20000)),
            replace(field.tiles[1], bounds=TileBounds(0, 20000, -20000, 20000)),
        ),
    )
    views = DirectionSet(
        tuple(ViewDirection(str(az), az, 90) for az in (0.0, 90.0, 180.0, 270.0))
    )
    req = replace(request(field), directions=views)
    result = PropagationKernel().evaluate(req, number_density_integrand)
    for trace in result.optical_traces:
        assert {d.tile_id for d in trace.sampled_dependencies} == {"tile-1"}
    assert max(r.integral for r in result.rays) == pytest.approx(
        min(r.integral for r in result.rays), rel=1e-14
    )
    ref = reference_optical_column(
        field, make_ray(SphericalFrame(req.observer), views.directions[-1], 10000)
    )
    assert result.rays[-1].integral == pytest.approx(ref.number_column_m2, rel=1e-8)
