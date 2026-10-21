"""Oracles independents de coordenades, conservació i qualificació nominal."""

import math
from dataclasses import replace
from decimal import Decimal, localcontext
from unittest.mock import patch
from typing import cast

import numpy as np
import pytest
from scipy.integrate import quad
from scipy.optimize import brentq

from terralab3d.application.coordinate_photometry import (
    coordinate_ab_reference,
    project_coordinate_band,
)
from terralab3d.domain.instrument_qualification import (
    InstrumentEvidence,
    missing_coverage_error,
    qualify_instrument,
)
from terralab3d.domain.light_pollution.propagation_kernel import PropagationKernel
from terralab3d.domain.light_pollution.spectral_oracle import (
    DIMENSIONLESS_UNIT,
    RELATIVE_UNIT,
    SpectralCurve,
)
from terralab3d.domain.light_pollution.spectral_transport import SpectralRaySamples
from terralab3d.domain.photometric_projection import (
    AB_FNU_W_M2_HZ,
    ARCSEC2_SR,
    SPEED_OF_LIGHT_NM_S,
    ProjectionUnavailable,
)
from terralab3d.domain.wavelength_coordinates import (
    CoordinateCurve,
    air_from_vacuum,
    air_jacobian,
    standard_air_index,
    vacuum_from_air,
)


def decimal_air(v: float, ppm: int = 450) -> Decimal:
    # Implementació escalar Decimal independent de les funcions del candidat.
    with localcontext() as ctx:
        ctx.prec = 60
        w = Decimal(str(v))
        s = Decimal(10) ** 6 / (w * w)
        n = 1 + (
            Decimal(5792105) / (Decimal("238.0185") - s)
            + Decimal(167917) / (Decimal("57.362") - s)
        ) * Decimal("1e-8") * (1 + Decimal("0.534e-6") * (ppm - 450))
        return w / n


@pytest.mark.parametrize("ppm", [300, 450])
@pytest.mark.parametrize(
    "vacuum", [300.0, 380.0, 435.25, 500.005, 550.0, 780.0, 1045.0, 1700.0]
)
def test_coordinate_roundtrip_and_decimal(vacuum, ppm):
    expected = float(decimal_air(vacuum, ppm))
    assert air_from_vacuum(vacuum, co2_ppm=ppm) == pytest.approx(expected, abs=2e-12)
    assert vacuum_from_air(expected, co2_ppm=ppm) == pytest.approx(vacuum, abs=2e-10)


@pytest.mark.parametrize("w", [301.0, 550.0, 1699.0])
def test_jacobian_decimal_finite_difference(w):
    with localcontext() as ctx:
        ctx.prec = 60
        h = Decimal("0.001")
        derivative = (decimal_air(w + 0.001) - decimal_air(w - 0.001)) / (2 * h)
        assert air_jacobian(w) == pytest.approx(float(derivative), rel=1e-8)
    assert standard_air_index(w) > 1


def response():
    return CoordinateCurve(
        SpectralCurve(
            "analytic-air-response",
            (400.0, 500.0, 700.0),
            (0.2, 1.0, 0.1),
            DIMENSIONLESS_UNIT,
            "unavailable",
        ),
        "standard_air_450ppm_nm",
        "response",
    )


def panels(values=None, unit="W m^-2 sr^-1 nm^-1"):
    knots = (390.0, 500.0, 710.0)
    ys = values or tuple(
        w * w for a, b in zip(knots, knots[1:]) for w in (a, (a + b) / 2, b)
    )
    return SpectralRaySamples(
        "analytic-source",
        "analytic-direction",
        knots,
        ys,
        (0.0,) * 6,
        unit,
        "SI_W",
        "analytic-panels",
    )


def test_density_jacobian_and_flux_conservation():
    native = SpectralCurve(
        "analytic-density",
        (400.0, 500.0, 700.0),
        (0.2, 1.0, 0.1),
        RELATIVE_UNIT,
        "zero",
    )
    converted = CoordinateCurve(native, "standard_air_450ppm_nm", "density")
    resp = response()
    w = 550.0
    assert converted.at_vacuum(w) / resp.at_vacuum(w) == pytest.approx(
        air_jacobian(w), rel=1e-14
    )
    x = converted.vacuum_knots
    integral = sum(
        quad(converted.at_vacuum, a, b, epsabs=1e-10, epsrel=1e-12)[0]
        for a, b in zip(x, x[1:])
    )
    expected = 100 * 0.6 + 200 * 0.55
    assert integral == pytest.approx(expected, rel=1e-10)
    table = converted.linearized_vacuum()
    linear_integral = sum(
        (b - a) * (ya + yb) / 2
        for a, b, ya, yb in zip(
            table.wavelengths_nm,
            table.wavelengths_nm[1:],
            table.values,
            table.values[1:],
        )
    )
    assert linear_integral == pytest.approx(expected, rel=1e-10)
    assert native.wavelengths_nm == (400.0, 500.0, 700.0)


def test_coordinate_projection_quad_and_zero_new_transport():
    r = response()
    x = r.vacuum_knots
    expected = sum(
        quad(
            lambda w: w
            * w
            * float(
                np.interp(float(decimal_air(w)), r.curve.wavelengths_nm, r.curve.values)
            ),
            a,
            b,
            epsabs=1e-7,
            epsrel=1e-12,
        )[0]
        for a, b in zip(x, x[1:])
    )
    with patch.object(
        PropagationKernel,
        "evaluate",
        side_effect=AssertionError("No repetir transport"),
    ):
        result = project_coordinate_band(
            panels(), r, input_radiance_basis="vacuum_nm", domain_nm=(x[0], x[-1])
        )
    assert result.signal.value == pytest.approx(expected, rel=1e-10)
    assert result.refinement_error / result.signal.value < 1e-10
    assert result.physical_transport_evaluations == 0
    with pytest.raises(ProjectionUnavailable):
        project_coordinate_band(
            panels(), r, input_radiance_basis="unspecified", domain_nm=(x[0], x[-1])
        )
    with pytest.raises(ProjectionUnavailable):
        project_coordinate_band(
            panels(), r, input_radiance_basis="vacuum_nm", domain_nm=(390.0, 710.0)
        )


def test_ab_reference_in_native_air_independent_oracle():
    r = response()

    def integrand(a):
        v = cast(
            float, brentq(lambda w: float(decimal_air(w)) - a, a, a + 1, xtol=1e-12)
        )
        jac = float(
            (decimal_air(v + 0.001) - decimal_air(v - 0.001)) / Decimal("0.002")
        )
        t = float(np.interp(a, r.curve.wavelengths_nm, r.curve.values))
        return t * AB_FNU_W_M2_HZ * SPEED_OF_LIGHT_NM_S / (ARCSEC2_SR * v * v * jac)

    expected = sum(
        quad(integrand, a, b, epsabs=1e-10, epsrel=1e-11)[0]
        for a, b in zip(r.curve.wavelengths_nm, r.curve.wavelengths_nm[1:])
    )
    assert coordinate_ab_reference(r) == pytest.approx(expected, rel=1e-10)


def test_physical_zeros_and_negative_polynomial():
    r = response()
    a, b = r.vacuum_knots[0], r.vacuum_knots[-1]
    zero = project_coordinate_band(
        panels((0.0,) * 6), r, input_radiance_basis="vacuum_nm", domain_nm=(a, b)
    )
    assert zero.signal.value == zero.refinement_error == 0
    with pytest.raises(ProjectionUnavailable, match="negatiu"):
        project_coordinate_band(
            panels((1.0, 0.0, 0.0, 0.0, 0.0, 0.0)),
            r,
            input_radiance_basis="vacuum_nm",
            domain_nm=(a, b),
        )


def test_conversion_domain_and_role_guards():
    with pytest.raises(ValueError):
        standard_air_index(299.0)
    with pytest.raises(ValueError):
        standard_air_index(550.0, co2_ppm=400)
    with pytest.raises(ValueError):
        vacuum_from_air(float("nan"))
    with pytest.raises(ValueError):
        CoordinateCurve(response().curve, "vacuum_nm", "density")
    with pytest.raises(ValueError):
        CoordinateCurve(response().curve, "unspecified", "response")  # type: ignore[arg-type]


def evidence():
    return InstrumentEvidence(
        "defined-nominal-optics",
        "Model nominal prescrit complet",
        True,
        True,
        True,
        True,
        True,
    )


def test_nominal_ab_does_not_require_individual_calibration():
    r = qualify_instrument(evidence(), target="nominal_ab", absolute_source_scale=True)
    assert (
        r["status"] == "nominal_model" and r["individualCalibrationRequired"] is False
    )
    assert r["observationalValidation"] is False
    for target in ("native_frequency", "native_magnitude"):
        assert (
            qualify_instrument(evidence(), target=target, absolute_source_scale=True)[
                "status"
            ]
            == "unavailable"
        )
    native = replace(
        evidence(),
        device_id="defined-device",
        dark_calibration_known=True,
        native_gain_known=True,
        native_zero_point_known=True,
    )
    assert (
        qualify_instrument(
            native, target="native_magnitude", absolute_source_scale=True
        )["status"]
        == "device_model"
    )
    assert (
        qualify_instrument(native, target="nominal_ab", absolute_source_scale=False)[
            "status"
        ]
        == "unavailable"
    )


def test_unknown_wings_remain_blocking_even_for_nominal_model():
    r = qualify_instrument(
        replace(evidence(), spectral_coverage_bounded=False),
        target="nominal_ab",
        absolute_source_scale=True,
    )
    assert r["status"] == "unavailable"
    tiny = missing_coverage_error(
        known_signal=1.0, missing_weight_fraction=1e-30, missing_radiance_upper=None
    )
    assert tiny["status"] == "UNAVAILABLE"
    bounded = missing_coverage_error(
        known_signal=1.0, missing_weight_fraction=1e-30, missing_radiance_upper=1e20
    )
    assert bounded["status"] == "PASS"
    assert isinstance(bounded["upperErrorMag"], float) and bounded["upperErrorMag"] > 0
    bright = missing_coverage_error(
        known_signal=1.0, missing_weight_fraction=0.01, missing_radiance_upper=1.0
    )
    assert bright["status"] == "FAIL"
    assert (
        missing_coverage_error(
            known_signal=0.0, missing_weight_fraction=0.01, missing_radiance_upper=1.0
        )["upperErrorMag"]
        is None
    )
    with pytest.raises(ValueError):
        missing_coverage_error(
            known_signal=math.inf, missing_weight_fraction=0.1, missing_radiance_upper=1
        )
