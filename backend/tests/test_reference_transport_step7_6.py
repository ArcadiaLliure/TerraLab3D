"""Contrasts independents del transport de referència; cap golden inventat."""

from __future__ import annotations

import json
import math
from dataclasses import replace
from typing import Any

import numpy as np
import pytest
from scipy.special import exp1

from terralab3d.domain.light_pollution.reference_transport import (
    ReferenceCancelledError,
    ReferenceConvergenceError,
    ReferenceOptics,
    ReferencePhase,
    ReferenceSettings,
    solve_reference,
)
from terralab3d.domain.light_pollution.reference_multiple_scattering import (
    estimate_multiple_scattering,
)
from terralab3d.domain.light_pollution.source_model import (
    AngularEmissionProfile,
    AzimuthalAngularEmissionProfile,
    DefinedSpectrum,
    EmissionAmplitude,
    GeodeticPosition,
    PointSourceGeometry,
    RectangularAreaGeometry,
    SourceModel,
)

R = 6371008.8
OBSERVER = GeodeticPosition(0, 0, 100)


def source(east=0.0, north=0.0, area=False, orientation=0.0):
    p = GeodeticPosition(math.degrees(north / R), math.degrees(east / R), 0)
    return SourceModel(
        "test-sgref",
        "test-v1",
        "Definició de prova",
        RectangularAreaGeometry(p, 1000, 600, orientation)
        if area
        else PointSourceGeometry(p),
        DefinedSpectrum(
            "flat", "Definició constant", "CC0-1.0", (400.0, 700.0), (1.0, 1.0)
        ),
        AngularEmissionProfile(
            "uniform", "Definició uniforme", (0.0, 90.0), (1.0, 1.0)
        ),
        EmissionAmplitude(1000, "W", "defined_absolute", "Entrada definida"),
    )


def optics(
    ext=3e-5, sca=2e-5, phase=ReferencePhase("isotropic"), waves=(450.0, 550.0, 650.0)
):
    return ReferenceOptics(
        waves,
        (ext,) * len(waves),
        (sca,) * len(waves),
        10000,
        phase,
        "Slab definit de prova",
    )


@pytest.mark.parametrize("k", [1e-8, 3e-5, 1e-3])
@pytest.mark.parametrize(
    "phase",
    [
        ReferencePhase("isotropic"),
        ReferencePhase("rayleigh"),
        ReferencePhase("hg", 0.6),
    ],
)
def test_exact_vertical_point_finite_extinction(k, phase):
    # Antiderivada independent: ∫ exp[-k(h+2s)]/(h+s)^2 ds.
    s = source()
    medium = optics(k, 0.8 * k, phase)
    result = solve_reference((s,), OBSERVER, 0, 90, medium)
    h, b = 100.0, 10000.0
    a = 2 * k
    closed = math.exp(k * h) * (
        math.exp(-a * h) / h - math.exp(-a * b) / b + a * (exp1(a * b) - exp1(a * h))
    )
    expected = (
        s.spectral_flux(550).value
        / (2 * math.pi)
        * 0.8
        * k
        * phase.density(np.array([-1.0]))[0]
        * closed
    )
    assert result.values == pytest.approx((expected,) * 3, rel=1e-8, abs=1e-20)
    assert (
        abs(result.values[0] - expected) <= result.numerical_error_estimate[0] + 1e-20
    )


@pytest.mark.parametrize("multiplier", [0.01, 2.0, 100.0])
def test_linearity_relative_scale_and_source_sum(multiplier):
    s = source(2000)
    a = solve_reference((s,), OBSERVER, 30, 60, optics())
    other = replace(
        s,
        source_model_id="scaled",
        amplitude=replace(s.amplitude, value=s.amplitude.value * multiplier),
    )
    b = solve_reference((other,), OBSERVER, 30, 60, optics())
    total = solve_reference((s, other), OBSERVER, 30, 60, optics())
    assert np.array(b.values) == pytest.approx(
        np.array(a.values) * multiplier, rel=1e-8
    )
    assert np.array(total.values) == pytest.approx(
        np.array(a.values) * (1 + multiplier), rel=1e-8
    )
    relative = replace(
        s,
        source_mode="CONDITIONAL_L3",
        amplitude=EmissionAmplitude(
            1000, "relative", "parametric", "Escala de prova", "test-scale"
        ),
    )
    c = solve_reference((relative,), OBSERVER, 30, 60, optics())
    assert c.values == a.values and c.unit.startswith("relative ")
    assert c.input_signature != a.input_signature
    assert c.source_modes == ("CONDITIONAL_L3",)


@pytest.mark.parametrize("orientation", [0.0, 37.0, 90.0])
def test_rectangle_equals_four_raster_cells_with_rotation(orientation):
    s = source(2500, 1000, True, orientation)
    angle = math.radians(orientation)
    cells = []
    for i, (u, v) in enumerate(((-250, -150), (-250, 150), (250, -150), (250, 150))):
        east = 2500 + u * math.cos(angle) + v * math.sin(angle)
        north = 1000 - u * math.sin(angle) + v * math.cos(angle)
        p = GeodeticPosition(math.degrees(north / R), math.degrees(east / R), 0)
        cells.append(
            replace(
                s,
                source_model_id=f"raster-{i}",
                geometry=RectangularAreaGeometry(p, 500, 300, orientation),
                amplitude=replace(s.amplitude, value=250),
            )
        )
    whole = solve_reference((s,), OBSERVER, 70, 30, optics())
    raster = solve_reference(tuple(cells), OBSERVER, 70, 30, optics())
    assert whole.values == pytest.approx(raster.values, rel=1e-6)
    assert len(whole.refinement_history) >= 3
    final_order = whole.refinement_history[-1]["areaOrder"]
    assert isinstance(final_order, int) and final_order >= 32
    json.dumps(whole.to_dict(), allow_nan=False)


def test_zero_scattering_outside_support_and_reproducibility():
    s = source(2000)
    a = solve_reference((s,), OBSERVER, 10, 45, optics(sca=0))
    assert a.values == (0.0, 0.0, 0.0)
    b = solve_reference((s,), OBSERVER, 10, 45, optics(waves=(350.0, 800.0)))
    assert b.values == (0.0, 0.0)
    c = solve_reference((s,), OBSERVER, 10, 45, optics())
    assert c == solve_reference((s,), OBSERVER, 10, 45, optics())
    assert min(c.values) > 0 and max(c.numerical_error_estimate) > 0
    dto = c.to_dict()
    assert dto["runtimeGate"] == "not_evaluated_step_7.12"
    assert dto["structuralUncertainty"] == "not_quantified"
    low = solve_reference((s,), OBSERVER, 10, 0.5, optics())
    assert all(math.isfinite(v) and v >= 0 for v in low.values)


def test_azimuthal_direction_emission_is_used():
    s = source(0, 2000)
    axial = s.angular
    assert isinstance(axial, AngularEmissionProfile)
    modulated = replace(
        s,
        angular=AzimuthalAngularEmissionProfile(
            "az-test",
            "Definició de prova",
            axial,
            (0.0, 90.0, 180.0, 270.0, 360.0),
            (1.0, 2.0, 3.0, 2.0, 1.0),
        ),
    )
    a = solve_reference((s,), OBSERVER, 0, 90, optics())
    b = solve_reference((modulated,), OBSERVER, 0, 90, optics())
    # Font al nord i LOS zenital: azimut emissor sud=180°, factor 3/2.
    assert b.values == pytest.approx(np.array(a.values) * 1.5, rel=1e-8)


def test_elevated_source_thin_support_near_slab_top_is_not_missed():
    s = source(1000)
    z = 9999.999
    s = replace(
        s, geometry=PointSourceGeometry(GeodeticPosition(0, math.degrees(1000 / R), z))
    )
    observer = GeodeticPosition(0, 0, 0)
    medium = optics(waves=(550.0,))
    result = solve_reference((s,), observer, 0, 90, medium)
    x, w = np.polynomial.legendre.leggauss(32)
    heights = z + (10000 - z) * (x + 1) / 2
    distance = np.sqrt(1000**2 + (heights - z) ** 2)
    expected = float(
        np.sum(w * np.exp(-3e-5 * (distance + heights)) / distance**2) * (10000 - z) / 2
    )
    expected *= s.spectral_flux(550).value / (2 * math.pi) * 2e-5 / (4 * math.pi)
    assert result.values[0] > 0
    assert result.values[0] == pytest.approx(expected, rel=1e-8, abs=1e-20)


def test_azimuth_periodic_signature_matches_calculation():
    s = source(3000)
    first = solve_reference((s,), OBSERVER, 90, 45, optics())
    wrapped = solve_reference((s,), OBSERVER, 450, 45, optics())
    assert first == wrapped


@pytest.mark.parametrize(
    "phase",
    [
        ReferencePhase("isotropic"),
        ReferencePhase("rayleigh"),
        ReferencePhase("hg", 0.6),
    ],
)
def test_phase_normalized_on_sphere(phase):
    x, w = np.polynomial.legendre.leggauss(128)
    assert float(2 * math.pi * np.dot(phase.density(x), w)) == pytest.approx(
        1, abs=1e-12
    )


def test_high_resolution_phase_and_fine_spectral_route():
    analytic = ReferencePhase("hg", 0.6)
    x = np.linspace(-1, 1, 16385)
    table = ReferencePhase(
        "tabulated", cosines=tuple(x), relative_values=tuple(analytic.density(x))
    )
    waves = tuple(float(w) for w in range(400, 701))
    a = solve_reference(
        (source(3000),), OBSERVER, 90, 60, optics(phase=analytic, waves=waves)
    )
    b = solve_reference(
        (source(3000),), OBSERVER, 90, 60, optics(phase=table, waves=waves)
    )
    assert len(b.values) == 301
    assert b.values == pytest.approx(a.values, rel=1e-6)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"elevation_deg": 0},
        {"elevation_deg": float("nan")},
        {"azimuth_deg": float("inf")},
        {"sources": ()},
    ],
)
def test_bad_solver_inputs_fail_closed(kwargs):
    arguments: dict[str, Any] = dict(
        sources=(source(2000),),
        observer=OBSERVER,
        azimuth_deg=0,
        elevation_deg=45,
        optics=optics(),
    )
    arguments.update(kwargs)
    with pytest.raises(ValueError):
        solve_reference(**arguments)


def test_units_identity_singular_geometry_and_cancellation():
    s = source()
    rel = replace(
        s,
        source_model_id="rel",
        amplitude=EmissionAmplitude(1, "relative", "parametric", "Prova", "r"),
    )
    for inputs in ((s, s), (s, rel)):
        with pytest.raises(ValueError):
            solve_reference(inputs, OBSERVER, 0, 90, optics())
    for singular in (s, source(area=True)):
        with pytest.raises(ValueError, match="singular"):
            solve_reference((singular,), GeodeticPosition(0, 0, 0), 0, 90, optics())
    with pytest.raises(ReferenceCancelledError):
        solve_reference(
            (source(2000),), OBSERVER, 0, 90, optics(), cancelled=lambda: True
        )
    with pytest.raises(ReferenceConvergenceError):
        solve_reference(
            (source(600, area=True),),
            OBSERVER,
            90,
            10,
            optics(),
            ReferenceSettings(area_orders=(2, 3, 4), area_relative_tolerance=1e-12),
        )


@pytest.mark.parametrize(
    "factory",
    [
        lambda: ReferenceOptics(
            (550.0,), (1e-5,), (2e-5,), 10000, ReferencePhase("isotropic"), "Prova"
        ),
        lambda: ReferenceOptics(
            (550.0,),
            (float("nan"),),
            (0.0,),
            10000,
            ReferencePhase("isotropic"),
            "Prova",
        ),
        lambda: ReferenceSettings(area_orders=(8, 8, 16)),
        lambda: ReferencePhase("hg", 1),
        lambda: ReferencePhase(
            "tabulated", cosines=(-1.0, 0.0, 1.0), relative_values=(0.0, -1.0, 0.0)
        ),
    ],
)
def test_invalid_optical_contracts(factory):
    with pytest.raises(ValueError):
        factory()


def mc_source():
    s = source(15000, area=True)
    return replace(
        s,
        geometry=replace(s.geometry, east_width_m=20000, north_height_m=20000),
        angular=AngularEmissionProfile(
            "bounded", "Perfil lineal de prova", (0.0, 90.0), (1.0, 0.0)
        ),
    )


def test_multiple_scattering_reproducible_monotonic_and_bounded():
    s = mc_source()
    params = (s, GeodeticPosition(0, 0, 0), 0, 90, 550, 3e-5, 0.8, 10000)
    a = estimate_multiple_scattering(*params, photons=32768, seed=7601)
    assert a == estimate_multiple_scattering(*params, photons=32768, seed=7601)
    lower = estimate_multiple_scattering(
        *params[:6], 0.4, 10000, photons=32768, seed=7601
    )
    assert a.single_scattering == pytest.approx(lower.single_scattering * 2, rel=1e-14)
    assert a.higher_orders > lower.higher_orders * 4
    assert a.all_orders == pytest.approx(a.single_scattering + a.higher_orders)
    assert a.higher_orders > 6 * a.higher_orders_standard_error
    assert a.truncation_upper_bound < a.all_orders * 1e-8
    dto = a.to_dict()
    bias_error = dto["biasFractionStandardError"]
    assert isinstance(bias_error, float) and 0 < bias_error < 0.05
    json.dumps(dto, allow_nan=False)
    deterministic = solve_reference(
        (s,),
        GeodeticPosition(0, 0, 0),
        0,
        90,
        optics(ext=3e-5, sca=2.4e-5, waves=(550.0,)),
    )
    assert (
        abs(a.single_scattering - deterministic.values[0])
        <= 6 * a.single_standard_error + deterministic.numerical_error_estimate[0]
    )


def test_multiple_scattering_rejects_unbounded_radiance_and_cancels():
    with pytest.raises(ValueError, match="limitada"):
        estimate_multiple_scattering(
            source(15000, area=True), OBSERVER, 0, 90, 550, 3e-5, 0.8, 10000, photons=16
        )
    with pytest.raises(InterruptedError):
        estimate_multiple_scattering(
            mc_source(),
            OBSERVER,
            0,
            90,
            550,
            3e-5,
            0.8,
            10000,
            photons=16,
            cancelled=lambda: True,
        )
