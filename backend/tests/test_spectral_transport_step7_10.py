"""Invariants de composició, compartició geomètrica i transport espectral."""

from dataclasses import replace
from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from benchmark_skyglow_spectral import fixture
from terralab3d.domain.light_pollution.gas_absorption import effective_band_transmission
from terralab3d.domain.light_pollution.geometric_transport import ViewDirection
from terralab3d.domain.light_pollution.propagation_kernel import (
    DirectionSet,
    PropagationCancelledError,
    PropagationKernel,
    StalePropagationError,
)
from terralab3d.domain.light_pollution.spectral_transport import SpectralOperator
from terralab3d.domain.light_pollution.transport_profiling import TransportProfiler
from terralab3d.domain.light_pollution.vector_quadrature import integrate_vector_gk15
from terralab3d.domain.light_pollution.gauss_kronrod import (
    QuadratureSettings,
    QuadratureConvergenceError,
)
from terralab3d.infrastructure.adapters.atmosphere.gas_catalog import load_ozone_lut


@pytest.fixture
def request_b4():
    return replace(
        fixture(1), directions=DirectionSet((ViewDirection("zenith", 0, 90),))
    )


def test_jensen_and_unlit_bands():
    w = np.array([[1.0, 1.0], [0.0, 0.0]])
    tau = np.array([[0.0, 4.0], [0.0, 4.0]])
    t = effective_band_transmission(w, tau)
    assert t[0] == pytest.approx((1 + np.exp(-4)) / 2)
    assert t[0] > np.exp(-2)
    assert np.isnan(t[1])


@pytest.mark.parametrize("bad", [-1.0, np.nan, np.inf])
def test_rejects_invalid_tau(bad):
    with pytest.raises(ValueError):
        effective_band_transmission(np.ones((1, 2)), np.array([[0.0, bad]]))


def test_temperature_and_wavelength_support():
    lut = load_ozone_lut()
    for t in (193.0, 300.0, np.nan):
        with pytest.raises(ValueError):
            lut.temperature_weights(t)
    for w in (379.0, 781.0, np.nan):
        with pytest.raises(ValueError):
            lut.matrix(np.array([w]))
    assert lut.temperature_weights(288.0).sum() == pytest.approx(1.0)
    assert len(lut.wavelengths_nm) == 801
    with pytest.raises(ValueError):
        replace(lut, cross_sections_m2=((-1.0,),))


def test_unknown_gas_and_incomplete_tile_rejected(request_b4):
    cfg = request_b4.spectral
    assert cfg and cfg.gas
    with pytest.raises(ValueError):
        replace(cfg.gas, profiles=(replace(cfg.gas.profiles[0], species="H2O"),))
    with pytest.raises(ValueError):
        cfg.gas.profile("unknown", "O3")
    with pytest.raises(ValueError):
        replace(
            request_b4,
            spectral=replace(
                cfg,
                gas=replace(
                    cfg.gas, profiles=(replace(cfg.gas.profiles[0], tile_id="other"),)
                ),
            ),
        )
    with pytest.raises(ValueError):
        replace(cfg, gas=None)


def test_vector_gk_preserves_zero_and_shares_samples():
    points = []

    def f(x):
        points.append(x)
        return np.array([0.0, x**2, 1e24 * x**2])

    q = integrate_vector_gk15(f, 0, 1, QuadratureSettings(1e-10, 1e-20), lambda: None)
    assert q.value == pytest.approx([0.0, 1 / 3, 1e24 / 3])
    assert q.evaluations == len(points) == 15
    with pytest.raises(QuadratureConvergenceError):
        integrate_vector_gk15(
            lambda x: np.array([np.nan]), 0, 1, QuadratureSettings(), lambda: None
        )


def test_b4_reduces_radiance_and_zero_composition_matches_b2(request_b4):
    cfg = request_b4.spectral
    assert cfg and cfg.gas
    kernel = PropagationKernel()
    b4 = kernel.evaluate(request_b4)
    no_gas = replace(
        request_b4,
        spectral=replace(cfg, gas=None, gas_status="disabled_explicit_B2_diagnostic"),
    )
    b2 = kernel.evaluate(no_gas)
    zero = replace(
        cfg.gas,
        profiles=tuple(
            replace(p, mole_fractions=tuple(0.0 for _ in p.mole_fractions))
            for p in cfg.gas.profiles
        ),
    )
    z = kernel.evaluate(replace(request_b4, spectral=replace(cfg, gas=zero)))
    assert 0 < b4.rays[0].integral < b2.rays[0].integral
    # Bandes 0,5 nm vs 1 nm: Simpson convergeix, però no s'exigeix identitat.
    assert z.rays[0].integral == pytest.approx(b2.rays[0].integral, rel=2e-7)
    assert b4.integral_unit == "W m^-2 sr^-1"
    assert b4.to_dict()["schemaVersion"] == 4
    assert b4.to_dict()["stage"] == "single_scattering_spectral_direct_B4"
    assert b2.to_dict()["stage"] == "single_scattering_spectral_direct_B2"
    assert b4.input_signature != z.input_signature != b2.input_signature


def test_shared_geometry_does_not_scale_with_wavelength_count(request_b4, monkeypatch):
    import terralab3d.domain.light_pollution.spectral_transport as module

    calls = 0
    real = module.segment_path

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return real(*args, **kwargs)

    monkeypatch.setattr(module, "segment_path", counted)
    r = PropagationKernel().evaluate(request_b4)
    assert calls == 2 * r.counters.quadrature_node_count
    assert r.transport_diagnostics[0].phase_evaluations > 1000 * calls


def test_band_identity_and_lut_invalidation(request_b4):
    cfg = request_b4.spectral
    assert cfg and cfg.gas
    op = SpectralOperator(request_b4.sources[0], cfg)
    revised = replace(cfg, gas=replace(cfg.gas, revision="new-revision"))
    other = SpectralOperator(request_b4.sources[0], revised)
    assert op.band_set.band_set_id == other.band_set.band_set_id
    assert op.band_set.input_signature != other.band_set.input_signature
    assert cfg.signature != revised.signature
    assert np.isfinite(op.weights).all() and (op.weights >= 0).all()


def test_cancellation_and_stale(request_b4):
    with pytest.raises(PropagationCancelledError):
        PropagationKernel().evaluate(request_b4, cancelled=lambda: True)
    with pytest.raises(StalePropagationError):
        PropagationKernel().evaluate(request_b4, is_current=lambda: False)


def test_profiler_excludes_children():
    p = TransportProfiler()
    with p.measure("quadrature"):
        with p.measure("geometry"):
            sum(range(1000))
    assert p.nanoseconds["geometry"] > 0
    assert p.nanoseconds["quadrature"] > 0
    assert p.calls["geometry"] == 1
    assert not p._stack


def test_variable_columns_and_reference_gas(request_b4):
    from terralab3d.domain.light_pollution.reference_single_scattering import (
        solve_reference_b1,
    )

    cfg = request_b4.spectral
    field = request_b4.optical_field
    assert cfg and cfg.gas and field
    # Una banda molt estreta verifica els dos trajectes amb SG-REF independent.
    narrow = replace(cfg, wavelength_start_nm=549.999, wavelength_end_nm=550.001)
    r = PropagationKernel().evaluate(replace(request_b4, spectral=narrow))
    band = cfg.monochromatic().band
    ref = solve_reference_b1(
        request_b4.sources[0],
        request_b4.observer,
        0,
        90,
        field,
        band,
        10000.0,
        gas=cfg.gas,
    )
    response = np.interp(
        550.0, cfg.responses[0].wavelengths_nm, cfg.responses[0].values
    )
    assert r.rays[0].integral / 0.002 == pytest.approx(ref.value * response, rel=2e-5)


def test_variable_pressure_temperature_columns(request_b4):
    from terralab3d.domain.light_pollution.reference_single_scattering import (
        solve_reference_b1,
    )

    cfg, field = request_b4.spectral, request_b4.optical_field
    assert cfg and cfg.gas and field
    field = replace(
        field,
        tiles=tuple(
            replace(
                t,
                profile=replace(
                    t.profile,
                    pressure_pa=(101325.0, 50000.0),
                    temperature_k=(288.15, 283.15),
                ),
            )
            for t in field.tiles
        ),
    )
    narrow = replace(cfg, wavelength_start_nm=549.999, wavelength_end_nm=550.001)
    actual = PropagationKernel().evaluate(
        replace(request_b4, optical_field=field, spectral=narrow)
    )
    reference = solve_reference_b1(
        request_b4.sources[0],
        request_b4.observer,
        0,
        90,
        field,
        cfg.monochromatic().band,
        10000.0,
        gas=cfg.gas,
        path_order=16,
    )
    response = np.interp(
        550.0, cfg.responses[0].wavelengths_nm, cfg.responses[0].values
    )
    assert actual.rays[0].integral / 0.002 == pytest.approx(
        reference.value * response, rel=2e-5
    )
    assert actual.transport_diagnostics[0].transmission_nodes > 0


def test_independent_spectral_reference_avoids_runtime(request_b4, monkeypatch):
    import terralab3d.domain.light_pollution.spectral_transport as runtime
    from terralab3d.domain.light_pollution.optical_field import OpticalField
    from terralab3d.domain.light_pollution.scattering import PhaseFunction
    from terralab3d.domain.light_pollution.reference_spectral_transport import (
        solve_reference_spectral,
    )

    cfg, field = request_b4.spectral, request_b4.optical_field
    assert cfg and field
    cfg = replace(cfg, wavelength_start_nm=549.0, wavelength_end_nm=551.0)

    def forbidden(*args, **kwargs):
        raise AssertionError("La referència ha cridat el runtime")

    monkeypatch.setattr(OpticalField, "sample", forbidden)
    monkeypatch.setattr(OpticalField, "traverse", forbidden)
    monkeypatch.setattr(PhaseFunction, "density", forbidden)
    monkeypatch.setattr(runtime.SpectralOperator, "__init__", forbidden)
    monkeypatch.setattr(runtime.SpectralScatteringTransport, "value", forbidden)
    reference = solve_reference_spectral(
        request_b4.sources[0], request_b4.observer, field, cfg, 0.0, 90.0, 10000.0
    )
    assert reference.value > 0


def test_multiple_declared_absorbers(request_b4):
    cfg = request_b4.spectral
    assert cfg and cfg.gas
    # Segona espècie analítica definida només per a aquesta prova, no NO2.
    second = replace(
        cfg.gas.luts[0],
        species="defined_test_absorber",
        evidence_reference="Fixture sintètica explícita; secció idèntica a la primera",
    )
    gas = replace(
        cfg.gas,
        luts=(*cfg.gas.luts, second),
        profiles=(
            *cfg.gas.profiles,
            replace(cfg.gas.profiles[0], species=second.species),
        ),
    )
    first = PropagationKernel().evaluate(request_b4)
    both = PropagationKernel().evaluate(
        replace(request_b4, spectral=replace(cfg, gas=gas))
    )
    assert 0 < both.rays[0].integral < first.rays[0].integral


def test_relative_scale_remains_relative(request_b4):
    from terralab3d.domain.light_pollution.source_model import EmissionAmplitude

    s = request_b4.sources[0]
    relative = replace(
        s,
        amplitude=EmissionAmplitude(
            3 * s.amplitude.value,
            "relative",
            "parametric",
            "Fixture paramètrica",
            "test_scale",
        ),
    )
    r = PropagationKernel().evaluate(replace(request_b4, sources=(relative,)))
    absolute = PropagationKernel().evaluate(request_b4)
    assert r.integral_unit == "relative m^-2 sr^-1"
    assert r.rays[0].integral == pytest.approx(3 * absolute.rays[0].integral, rel=2e-14)


def test_strict_atmospheric_temperature_domain(request_b4):
    field = request_b4.optical_field
    assert field
    cold = replace(
        field,
        tiles=tuple(
            replace(t, profile=replace(t.profile, temperature_k=(200.0, 200.0)))
            for t in field.tiles
        ),
    )
    with pytest.raises(ValueError, match="tèrmic"):
        replace(request_b4, optical_field=cold)


def test_ceiling_fixtures_cover_50km_and_share_aerosol():
    from diagnose_spectral_transport_step7_10 import ceiling_fixture
    mono = ceiling_fixture("B1_standard")
    spectral = ceiling_fixture("B4_standard")
    assert mono.optical_field and spectral.optical_field and mono.scattering and spectral.spectral
    assert mono.optical_field.signature == spectral.optical_field.signature
    assert min(t.profile.heights_m[-1] for t in mono.optical_field.tiles) == 50000.
    assert all(a.scale_height_m == 1200. for a in mono.scattering.band.aerosols)
    assert all(a.reference.scale_height_m == 1200. for a in spectral.spectral.aerosols)


def test_temperature_knots_partition_columns_without_crossing(request_b4):
    from terralab3d.domain.light_pollution.geometric_transport import SphericalFrame, make_ray
    from terralab3d.domain.light_pollution.optical_paths import segment_path
    from terralab3d.domain.light_pollution.spectral_transport import SpectralScatteringTransport
    cfg, field = request_b4.spectral, request_b4.optical_field
    assert cfg and cfg.gas and field
    field = replace(field, tiles=tuple(replace(t, profile=replace(t.profile, pressure_pa=(101325., 25000.), temperature_k=(288.15, 223.15))) for t in field.tiles))
    ray = make_ray(SphericalFrame(request_b4.observer, field.radius_m), ViewDirection("vertical", 0., 90.), 10000.)
    op = SpectralOperator(request_b4.sources[0], cfg)
    transport = SpectralScatteringTransport(request_b4.sources[0], field, cfg, ray, 4096, lambda: None, set(), TransportProfiler(), op)
    assert transport.thermal_heights
    _, _, segments = segment_path(field, ray.origin_ecef_m, ray.point(ray.length_m), 4096, lambda: None, transport.thermal_heights)
    for segment in segments:
        first = field.sample(ray.point(segment.start_m)).temperature_k
        last = field.sample(ray.point(segment.end_m)).temperature_k
        assert not any(min(first, last) + 1e-7 < t < max(first, last) - 1e-7 for t in cfg.gas.luts[0].temperatures_k)
    depth = transport._depth(ray.origin_ecef_m, ray.point(ray.length_m))
    assert np.isfinite(depth).all() and (depth > 0).all()
    assert transport.work.nodes <= 30 * len(segments)


def test_variable_gas_reference_thermal_partition_is_independent(request_b4, monkeypatch):
    from terralab3d.domain.light_pollution.optical_field import OpticalField
    from terralab3d.domain.light_pollution.reference_single_scattering import solve_reference_b1
    cfg, field = request_b4.spectral, request_b4.optical_field
    assert cfg and cfg.gas and field
    field = replace(field, tiles=tuple(replace(t, profile=replace(t.profile, pressure_pa=(101325., 25000.), temperature_k=(288.15, 223.15))) for t in field.tiles))
    def forbidden(*args, **kwargs):
        raise AssertionError("SG-REF ha usat una travessa/mostra del runtime")
    monkeypatch.setattr(OpticalField, "sample", forbidden)
    monkeypatch.setattr(OpticalField, "traverse", forbidden)
    values = [solve_reference_b1(request_b4.sources[0], request_b4.observer, 0., 90., field, cfg.monochromatic().band, 10000., gas=cfg.gas, path_order=n).value for n in (8, 12, 16)]
    assert abs(values[-1] / values[-2] - 1) < 1e-10


