"""Invariants B1, transmissió multi-tile i referència independent revalidada."""

from __future__ import annotations

import json
import math
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timezone
from threading import Event

import numpy as np
import pytest
from scipy.integrate import quad

from terralab3d.application.geometric_propagation import GeometricPropagationSession
from terralab3d.application.ports.atmospheric_optics import (
    OpticalFieldRequest,
    OpticalTileSpec,
)
from terralab3d.domain.light_pollution.geometric_transport import (
    SphericalFrame,
    ViewDirection,
)
from terralab3d.domain.light_pollution.optical_field import (
    OpticalCoverageError,
    OpticalField,
    TileBounds,
)
from terralab3d.domain.light_pollution.optical_paths import (
    PathWork,
    optical_depth,
    segment_path,
)
from terralab3d.domain.light_pollution.propagation_kernel import (
    DirectionSet,
    PropagationCancelledError,
    PropagationKernel,
    PropagationRequest,
    StalePropagationError,
)
from terralab3d.domain.light_pollution.reference_single_scattering import (
    ReferenceB1CancelledError,
    solve_reference_b1,
)
from terralab3d.domain.light_pollution.scattering import (
    AerosolReference,
    PhaseFunction,
    ScatteringBand,
    ScatteringConfiguration,
    dry_air_rayleigh,
)
from terralab3d.domain.light_pollution.single_scattering import (
    SingleScatteringTransport,
)
from terralab3d.domain.light_pollution.source_model import (
    AngularEmissionProfile,
    DefinedSpectrum,
    EmissionAmplitude,
    GeodeticPosition,
    PointSourceGeometry,
    RectangularAreaGeometry,
    SourceModel,
)
from terralab3d.infrastructure.adapters.atmosphere.standard_optics import (
    StandardAtmosphericOpticsProvider,
)


def fixture(count=1, *, homogeneous=True, phase=None, rayleigh=True, extinction=1e-5):
    origin = GeodeticPosition(0, 0, 0)
    cuts = [-100000.0] + [2500.0 * i for i in range(1, count)] + [1000000.0]
    field = StandardAtmosphericOpticsProvider().resolve(
        OpticalFieldRequest(
            origin,
            datetime(2026, 10, 19, tzinfo=timezone.utc),
            tuple(
                OpticalTileSpec(f"tile-{i}", "v1", TileBounds(a, b, -1000000, 1000000))
                for i, (a, b) in enumerate(zip(cuts, cuts[1:]))
            ),
            vertical_step_m=1000,
        )
    )
    if homogeneous:
        tiles = []
        for tile in field.tiles:
            p = tile.profile
            provenance = tuple(
                replace(
                    x,
                    model_revision="prescribed-homogeneous-v1",
                    interpretation="Fixture P/T constants definides, no COESA observacional",
                )
                for x in p.provenance
            )
            tiles.append(
                replace(
                    tile,
                    profile=replace(
                        p,
                        heights_m=(0.0, 10000.0),
                        pressure_pa=(101325.0, 101325.0),
                        temperature_k=(288.15, 288.15),
                        revision="prescribed-homogeneous-v1",
                        provenance=provenance,
                    ),
                )
            )
        field = replace(field, tiles=tuple(tiles))
    sigma, rphase = dry_air_rayleigh(550)
    aerosol = phase or PhaseFunction(
        "hg_fallback", "HG prescrit; no aerosol mesurat", asymmetry=0.65
    )
    band = ScatteringBand(
        550,
        sigma if rayleigh else 0,
        rphase,
        tuple(
            AerosolReference(
                t.tile_id, "a1", extinction, 0.9, aerosol, "Fixture aerosol prescrita"
            )
            for t in field.tiles
        ),
        "Model B1 prescrit",
    )
    source = SourceModel(
        "S",
        "v1",
        "Font definida",
        PointSourceGeometry(
            GeodeticPosition(0, math.degrees(5000 / field.radius_m), 0)
        ),
        DefinedSpectrum("flat", "Definició", "CC0-1.0", (400.0, 700.0), (1.0, 1.0)),
        AngularEmissionProfile("up", "Definició", (0.0, 90.0), (1.0, 1.0)),
        EmissionAmplitude(1.0, "W", "defined_absolute", "Definició"),
    )
    return PropagationRequest(
        (source,),
        GeodeticPosition(0, 0, 100),
        DirectionSet((ViewDirection("zenith", 0, 90),)),
        optical_field=field,
        scattering=ScatteringConfiguration(band),
    )


@pytest.mark.parametrize(
    "phase",
    [
        PhaseFunction("isotropic", "Definició"),
        PhaseFunction("rayleigh", "Definició"),
        PhaseFunction("rayleigh", "Definició", depolarization_delta=0.03),
        PhaseFunction("hg_fallback", "HG", asymmetry=0.8),
        PhaseFunction("hg_fallback", "HG", asymmetry=-0.7),
        PhaseFunction(
            "tabulated",
            "Taula definida",
            cosines=(-1.0, -0.2, 1.0),
            relative_values=(1.0, 2.0, 4.0),
        ),
    ],
)
def test_phase_normalization_positive_and_direction(phase):
    points = phase.cosines[1:-1] if phase.kind == "tabulated" else None
    integral = quad(
        lambda mu: 2 * math.pi * phase.density(mu),
        -1,
        1,
        points=points,
        epsabs=1e-12,
        epsrel=1e-12,
    )[0]
    assert integral == pytest.approx(1, abs=1e-10)
    assert all(phase.density(float(mu)) >= 0 for mu in np.linspace(-1, 1, 101))
    if phase.kind == "hg_fallback":
        mean = quad(
            lambda mu: 2 * math.pi * mu * phase.density(mu), -1, 1, epsabs=1e-12
        )[0]
        assert mean == pytest.approx(phase.asymmetry, abs=1e-10)


@pytest.mark.parametrize("wave", [200.0, 400.0, 550.0, 700.0, 1000.0])
def test_rayleigh_published_fit_and_coherent_depolarization(wave):
    sigma, phase = dry_air_rayleigh(wave)
    # Cadena d'unitats independent: ajust eq. 7 en cm² → m².
    s = 1 / (wave / 1000)
    expected = (
        3.9993e-4 * s**4 / (1 - 0.01069 * s**2 - 0.00006681 * s**4) * 1e-24 * 1e-4
    )
    assert sigma == pytest.approx(expected, rel=1e-14)
    assert 0 < phase.depolarization_delta < 0.1
    assert phase.density(1) == phase.density(-1)


def test_two_leg_tau_analytic_reversal_and_turning_height():
    req = fixture(2, rayleigh=False)
    field, config = req.optical_field, req.scattering
    assert field is not None and config is not None
    a = (field.radius_m + 1000, 0.0, 0.0)
    b = (field.radius_m + 1000, 5000.0, 0.0)
    aerosols = (
        replace(config.band.aerosols[0], extinction_per_m=1e-5),
        replace(config.band.aerosols[1], extinction_per_m=3e-5),
    )
    band = replace(config.band, aerosols=aerosols)
    deps = set()
    work = PathWork()
    tau = optical_depth(
        field, band, a, b, config.path_quadrature, 100, lambda: None, deps, work
    )
    reverse = optical_depth(
        field, band, b, a, config.path_quadrature, 100, lambda: None, set(), PathWork()
    )
    assert tau == pytest.approx(0.1, rel=1e-12)
    assert tau == pytest.approx(reverse, rel=1e-12)
    assert {d.tile_id for d in deps} == {"tile-0", "tile-1"}
    frame = SphericalFrame(req.observer)
    start = frame.position_ecef(GeodeticPosition(0, -0.02, 1000))
    end = frame.position_ecef(GeodeticPosition(0, 0.02, 1000))
    _, _, segments = segment_path(field, start, end, 100, lambda: None)
    assert segments and segments[0].start_m == 0
    exponential = replace(
        band, aerosols=tuple(replace(x, scale_height_m=1000) for x in band.aerosols)
    )
    vertical = optical_depth(
        field,
        exponential,
        a,
        (field.radius_m + 5000, 0.0, 0.0),
        config.path_quadrature,
        100,
        lambda: None,
        set(),
        PathWork(),
    )
    assert vertical == pytest.approx(
        1e-5 * 1000 * (math.exp(-1) - math.exp(-5)), rel=1e-9
    )


def test_isotropic_thin_analytic_radiance_no_observer_inverse_square():
    req = fixture(
        rayleigh=False, phase=PhaseFunction("isotropic", "Definició"), extinction=1e-12
    )
    assert req.scattering is not None
    band = replace(
        req.scattering.band,
        aerosols=(
            replace(req.scattering.band.aerosols[0], single_scattering_albedo=1),
        ),
    )
    src = replace(
        req.sources[0], geometry=PointSourceGeometry(GeodeticPosition(0, 0, 0))
    )
    req = replace(
        req,
        sources=(src,),
        observer=GeodeticPosition(0, 0, 1000),
        scattering=replace(req.scattering, band=band),
    )
    result = PropagationKernel().evaluate(req)
    expected = (
        src.spectral_flux(550).value
        / (2 * math.pi)
        * 1e-12
        / (4 * math.pi)
        * (1 / 1000 - 1 / 10000)
    )
    assert result.rays[0].integral == pytest.approx(expected, rel=1e-7)
    assert req.optical_field is not None
    ref = solve_reference_b1(src, req.observer, 0, 90, req.optical_field, band, 10000)
    assert ref.value == pytest.approx(expected, rel=1e-7)


def test_linearity_relative_scale_zero_scattering_and_old_schemas():
    req = fixture()
    kernel = PropagationKernel()
    a = kernel.evaluate(req)
    src = replace(req.sources[0], amplitude=replace(req.sources[0].amplitude, value=3))
    b = kernel.evaluate(replace(req, sources=(src,)))
    assert b.rays[0].integral == pytest.approx(3 * a.rays[0].integral, rel=1e-10)
    relative = replace(
        src,
        source_mode="CONDITIONAL_L3",
        amplitude=EmissionAmplitude(
            3,
            "relative",
            "parametric",
            "Hipòtesi C",
            parameter_name="conditional",
        ),
    )
    c = kernel.evaluate(replace(req, sources=(relative,)))
    assert c.rays[0].integral == b.rays[0].integral
    assert c.integral_unit == "relative m^-2 sr^-1 nm^-1"
    assert a.to_dict()["schemaVersion"] == 3
    json.dumps(a.to_dict(), allow_nan=False)
    assert (
        kernel.evaluate(replace(req, scattering=None)).to_dict()["schemaVersion"] == 2
    )
    assert (
        kernel.evaluate(replace(req, scattering=None, optical_field=None)).to_dict()[
            "schemaVersion"
        ]
        == 1
    )
    assert req.scattering is not None
    band = replace(
        req.scattering.band,
        rayleigh_cross_section_m2=0,
        aerosols=(
            replace(req.scattering.band.aerosols[0], single_scattering_albedo=0),
        ),
    )
    assert (
        kernel.evaluate(replace(req, scattering=replace(req.scattering, band=band)))
        .rays[0]
        .integral
        == 0
    )


def test_source_leg_dependencies_outside_observer_los_and_optics_revision():
    req = fixture(2)
    a = PropagationKernel().evaluate(req)
    assert {d.tile_id for d in a.optical_traces[0].sampled_dependencies} == {
        "tile-0",
        "tile-1",
    }
    assert {s.dependency.tile_id for s in a.optical_traces[0].traversed_segments} == {
        "tile-0"
    }
    assert req.scattering is not None
    changed = replace(
        req.scattering.band,
        aerosols=(
            req.scattering.band.aerosols[0],
            replace(
                req.scattering.band.aerosols[1], version="a2", extinction_per_m=2e-5
            ),
        ),
    )
    b = PropagationKernel().evaluate(
        replace(req, scattering=replace(req.scattering, band=changed))
    )
    assert a.optical_dependency_signature != b.optical_dependency_signature
    assert (
        a.input_signature != b.input_signature
        and a.rays[0].integral != b.rays[0].integral
    )


def test_source_superposition_zenith_and_forward_phase():
    req = fixture()
    kernel = PropagationKernel()
    single = kernel.evaluate(req)
    other = replace(
        req.sources[0],
        source_model_id="S2",
        amplitude=replace(req.sources[0].amplitude, value=2),
    )
    combined = kernel.evaluate(replace(req, sources=(*req.sources, other)))
    assert sum(r.integral for r in combined.rays) == pytest.approx(
        3 * single.rays[0].integral, rel=1e-10
    )
    phase = PhaseFunction("hg_fallback", "HG prescrit", asymmetry=0.8)
    assert phase.density(0.9) > phase.density(-0.9)
    assert combined.counters.los_count == 2


@pytest.mark.parametrize("height", [1000.0, 5000.0])
def test_source_and_observer_on_vertical_knot_at_nonzero_latitude(height):
    req = fixture(homogeneous=False)
    assert isinstance(req.sources[0].geometry, PointSourceGeometry)
    source_pos = GeodeticPosition(41.45313029652874, 2.3830927748174986, height)
    source = replace(req.sources[0], geometry=PointSourceGeometry(source_pos))
    assert req.optical_field is not None
    origin = GeodeticPosition(41.3875, 2.1666667, height)
    field = replace(req.optical_field, origin=origin)
    result = PropagationKernel().evaluate(
        replace(req, sources=(source,), observer=origin, optical_field=field)
    )
    assert result.rays[0].integral > 0


def test_reference_independence_refinement_and_rectangle(monkeypatch):
    req = fixture()
    assert req.optical_field is not None and req.scattering is not None
    assert isinstance(req.sources[0].geometry, PointSourceGeometry)
    src = replace(
        req.sources[0],
        geometry=RectangularAreaGeometry(
            req.sources[0].geometry.position, 200, 300, 20
        ),
    )
    req = replace(req, sources=(src,))
    assert req.scattering is not None and req.optical_field is not None
    values = []
    for order in (2, 4, 8):
        values.append(
            PropagationKernel()
            .evaluate(
                replace(req, scattering=replace(req.scattering, area_order=order))
            )
            .rays[0]
            .integral
        )

    def forbidden(*args, **kwargs):
        raise AssertionError("La referència no pot reutilitzar el runtime")

    monkeypatch.setattr(OpticalField, "sample", forbidden)
    monkeypatch.setattr(OpticalField, "traverse", forbidden)
    monkeypatch.setattr(PhaseFunction, "density", forbidden)
    refs = [
        solve_reference_b1(
            src,
            req.observer,
            0,
            90,
            req.optical_field,
            req.scattering.band,
            10000,
            relative_tolerance=t,
            path_order=o,
            area_order=o,
        )
        for t, o in ((1e-7, 8), (1e-9, 12), (1e-11, 16))
    ]
    assert abs(values[1] - values[2]) < abs(values[0] - values[1])
    assert (
        abs(refs[-1].value - refs[-2].value)
        <= sum(r.los_error_estimate for r in refs[-2:]) + 1e-10 * refs[-1].value
    )
    # Cap llindar de discrepància runtime↔SG-REF: es registra a B1.


def test_invalid_coverage_singularities_and_phase_parameters():
    req = fixture(2)
    assert req.optical_field is not None and req.scattering is not None
    with pytest.raises(ValueError):
        replace(req, optical_field=None)
    with pytest.raises(ValueError):
        PhaseFunction("hg_fallback", "HG", asymmetry=1)
    with pytest.raises(ValueError):
        PhaseFunction(
            "tabulated", "Taula", cosines=(-1, 0, 1), relative_values=(1, -1, 1)
        )
    with pytest.raises(ValueError):
        replace(req.scattering.band, rayleigh_cross_section_m2=math.nan)
    with pytest.raises(ValueError):
        replace(req.scattering.band.aerosols[0], single_scattering_albedo=1.1)
    with pytest.raises(ValueError):
        dry_air_rayleigh(1100)
    missing = replace(req.optical_field, tiles=(req.optical_field.tiles[0],))
    config = replace(
        req.scattering,
        band=replace(req.scattering.band, aerosols=(req.scattering.band.aerosols[0],)),
    )
    with pytest.raises(OpticalCoverageError):
        PropagationKernel().evaluate(
            replace(req, optical_field=missing, scattering=config)
        )
    src = replace(
        req.sources[0], geometry=PointSourceGeometry(GeodeticPosition(0, 0, 200))
    )
    with pytest.raises(ValueError, match="singular"):
        PropagationKernel().evaluate(replace(req, sources=(src,)))


def test_cancel_stale_in_flight_and_reference_cancel(monkeypatch):
    req = fixture()
    session = GeometricPropagationSession()
    old = session.begin(req)
    started, released = Event(), Event()
    original = SingleScatteringTransport.value

    def blocking(self, *args):
        if not started.is_set():
            started.set()
            assert released.wait(5)
        return original(self, *args)

    monkeypatch.setattr(SingleScatteringTransport, "value", blocking)
    with ThreadPoolExecutor(max_workers=1) as pool:
        job = pool.submit(session.compute, old)
        assert started.wait(5)
        new = session.begin(req)
        released.set()
        with pytest.raises(StalePropagationError):
            job.result(timeout=5)
    assert session.result is None and session.stale_results_discarded == 1
    assert session.compute(new).rays[0].integral > 0
    with pytest.raises(PropagationCancelledError):
        PropagationKernel().evaluate(req, cancelled=lambda: True)
    assert req.optical_field is not None and req.scattering is not None
    with pytest.raises(ReferenceB1CancelledError):
        solve_reference_b1(
            req.sources[0],
            req.observer,
            0,
            90,
            req.optical_field,
            req.scattering.band,
            10000,
            cancelled=lambda: True,
        )
