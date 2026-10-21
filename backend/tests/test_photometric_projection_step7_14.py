"""Oracles analítics independents i contractes d’unitats/domini de7.14."""

import json
import math
import sys
from dataclasses import replace
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch

import numpy as np
import pytest
from scipy.integrate import quad

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from angular_fixtures_step7_13 import fixture
from photometry_fixtures_step7_14 import OUT, profiles
from validate_adaptive_dome_step7_13_v2 import decode
from terralab3d.application.photometric_projections import (
    cie_dome_luminance,
    dome_sensor_availability,
    project_retained,
    retain_spectrum,
)
from terralab3d.domain.light_pollution.geometric_transport import ViewDirection
from terralab3d.domain.light_pollution.propagation_kernel import (
    DirectionSet,
    PropagationCancelledError,
    PropagationKernel,
    StalePropagationError,
)
from terralab3d.domain.light_pollution.spectral_oracle import (
    DIMENSIONLESS_UNIT,
    SpectralCurve,
)
from terralab3d.domain.light_pollution.spectral_transport import SpectralRaySamples
from terralab3d.domain.photometric_projection import (
    AB_REFERENCE_ID,
    GaussianFov,
    PhotometricResponse,
    ProjectionUnavailable,
    ab_reference_radiance,
    average_fov,
    photopic_luminance,
    project_band,
    relative_magnitude_difference,
    sensor_magnitude,
)


def response():
    return PhotometricResponse(
        "analytic-energy-response",
        "CUSTOM_SENSOR",
        SpectralCurve(
            "analytic", (400.0, 500.0, 600.0), (0.1, 1.0, 0.2), DIMENSIONLESS_UNIT
        ),
        "Funció analítica, no instrument físic",
        GaussianFov("analytic-fov", 20.0, "Prescripció"),
        AB_REFERENCE_ID,
        True,
    )


def panels(unit="W m^-2 sr^-1 nm^-1", scale="SI_W", gain=1.0):
    x = (400.0, 500.0, 600.0)
    values = tuple(gain * w * w for a, b in zip(x, x[1:]) for w in (a, (a + b) / 2, b))
    return SpectralRaySamples(
        "analytic",
        "direction",
        x,
        values,
        (0.0,) * 6,
        unit,
        scale,
        "analytic-quadratic-panels",
    )


def test_polynomial_projection_independent_quad():
    c = response()
    expected = sum(
        quad(
            lambda w: w * w * np.interp(w, c.curve.wavelengths_nm, c.curve.values),
            a,
            b,
            epsabs=1e-8,
        )[0]
        for a, b in [(400, 500), (500, 600)]
    )
    assert project_band(panels(), c).value == pytest.approx(expected, rel=1e-14)


def test_ab_reference_independent_decimal50():
    c = response().curve
    with localcontext() as ctx:
        ctx.prec = 50
        total = Decimal(0)
        for aa, bb, va, vb in zip(
            c.wavelengths_nm, c.wavelengths_nm[1:], c.values, c.values[1:]
        ):
            a, b, ta, tb = map(lambda x: Decimal(str(x)), (aa, bb, va, vb))
            slope = (tb - ta) / (b - a)
            total += slope * (b / a).ln() + (ta - slope * a) * (1 / a - 1 / b)
        pi = Decimal("3.1415926535897932384626433832795028841971693993751")
        expected = (
            Decimal("3631e-26")
            * Decimal("299792458e9")
            / ((pi / Decimal(648000)) ** 2)
            * total
        )
    assert ab_reference_radiance(response()) == pytest.approx(
        float(expected), rel=1e-12
    )


def test_units_and_scale_preserved():
    base = project_band(panels(), response())
    converted = project_band(panels("nW cm^-2 sr^-1 nm^-1"), response())
    assert converted.value == pytest.approx(base.value * 1e-5, rel=1e-14)
    assert project_band(panels(gain=3), response()).value == pytest.approx(
        3 * base.value, rel=1e-14
    )
    relative = project_band(
        panels("relative m^-2 sr^-1 nm^-1", "conditional-C"), response()
    )
    assert sensor_magnitude(relative, response(), fov_applied=True)["value"] is None
    assert relative_magnitude_difference(
        replace(relative, value=relative.value * 2), relative
    ) == pytest.approx(-2.5 * math.log10(2))
    with pytest.raises(ValueError, match="escala"):
        relative_magnitude_difference(replace(relative, scale_id="another-C"), relative)


def test_magnitude_zero_point_fov_and_dark():
    c = response()
    s = project_band(panels(), c)
    assert sensor_magnitude(s, c)["status"] == "unavailable"
    m = sensor_magnitude(s, c, fov_applied=True)
    assert m["value"] == pytest.approx(
        -2.5 * math.log10(s.value / ab_reference_radiance(c))
    )
    assert (
        sensor_magnitude(
            s, replace(c, zero_point_id="native-unverified"), fov_applied=True
        )["value"]
        is None
    )
    zero = replace(s, value=0.0)
    assert sensor_magnitude(zero, c, fov_applied=True)["value"] is None
    assert relative_magnitude_difference(zero, s) is None
    assert m["bortleEquivalent"] is None


def test_response_support_and_new_knots_never_filled():
    with pytest.raises(ProjectionUnavailable, match="nusos"):
        project_band(
            panels(),
            replace(
                response(),
                curve=SpectralCurve(
                    "extra", (400.0, 450.0, 600.0), (0.1, 1.0, 0.2), DIMENSIONLESS_UNIT
                ),
            ),
        )
    with pytest.raises(ProjectionUnavailable, match="desconeguda"):
        project_band(
            panels(),
            replace(
                response(),
                curve=SpectralCurve(
                    "missing", (450.0, 600.0), (1.0, 0.2), DIMENSIONLESS_UNIT
                ),
            ),
        )
    with pytest.raises(ValueError, match="V"):
        photopic_luminance(project_band(panels(), response()))


@pytest.mark.parametrize("bad", [float("nan"), -1.0, float("inf")])
def test_invalid_spectral_data(bad):
    with pytest.raises(ValueError):
        project_band(
            replace(panels(), radiance_per_nm=(bad, *panels().radiance_per_nm[1:])),
            response(),
        )


@pytest.mark.parametrize("fwhm", [17.0, 20.0])
@pytest.mark.parametrize("az,el", [(0.0, 90.0), (89.3, 60.0), (275.1, 32.0)])
def test_fov_solid_angle_against_independent_axis_moments(fwhm, az, el):
    f = GaussianFov("prescribed", fwhm, "Prescripció científica de prova")
    pointing = ViewDirection("p", az, el)
    # La mitjana de cosθ i cos²θ es calcula per quadratura escalar θ independent.
    sigma = math.radians(fwhm)

    def density(t):
        return math.exp(-4 * math.log(2) * (t / sigma) ** 2) * math.sin(t)

    norm = quad(density, 0, math.pi / 2, epsabs=1e-14, epsrel=1e-12)[0]
    second = (
        quad(lambda t: density(t) * math.cos(t) ** 2, 0, math.pi / 2, epsabs=1e-14)[0]
        / norm
    )
    u = pointing.enu
    ez2 = u[2] ** 2 * second + (1 - u[2] ** 2) * (1 - second) / 2
    een = u[0] * u[1] * (3 * second - 1) / 2
    expected = 1 + 0.5 * ez2 + 0.2 * een

    def field(a, e):
        ar, er = math.radians(a), math.radians(e)
        return (
            1
            + 0.5 * math.sin(er) ** 2
            + 0.2 * math.cos(er) ** 2 * math.sin(ar) * math.cos(ar)
        )

    actual = average_fov(field, f, pointing, complete_forward_hemisphere=True)
    assert actual == pytest.approx(expected, rel=1e-9)
    assert average_fov(
        lambda a, e: 7.0, f, pointing, complete_forward_hemisphere=True, order=16
    ) == pytest.approx(7.0, rel=2e-15)


def test_missing_fov_never_renormalized_and_cancel():
    f = GaussianFov("prescribed", 20.0, "Prova")
    p = ViewDirection("p", 0.0, 90.0)
    with pytest.raises(ProjectionUnavailable, match="cobertura"):
        average_fov(lambda a, e: 1.0, f, p, complete_forward_hemisphere=False)
    with pytest.raises(ProjectionUnavailable, match="sense dades"):
        average_fov(
            lambda a, e: None if a < 180 else 1.0,
            f,
            p,
            complete_forward_hemisphere=True,
        )
    with pytest.raises(ProjectionUnavailable, match="cancel"):
        average_fov(
            lambda a, e: 1.0,
            f,
            p,
            complete_forward_hemisphere=True,
            cancelled=lambda: True,
        )


def test_capture_same_operator_multiple_projections_without_transport():
    req = fixture("S_B4_chamber_point_5km")
    legacy = PropagationKernel().evaluate(req)
    retained = retain_spectrum(req, profiles())
    cie = project_band(retained.spectral_samples[0], profiles()[0])
    assert cie.value == pytest.approx(legacy.rays[0].integral, rel=1e-7)
    assert retained.to_dict()["schemaVersion"] == 6
    assert "spectral_samples" not in legacy.to_dict()
    with patch.object(
        PropagationKernel, "evaluate", side_effect=AssertionError("Transport repetit")
    ):
        projected = project_retained(
            retained, profiles(), expected_revision=req.revision
        )
    assert projected["physicalTransportEvaluations"] == 0
    with pytest.raises(StalePropagationError):
        project_retained(retained, profiles(), expected_revision=req.revision + 1)
    with pytest.raises(PropagationCancelledError):
        project_retained(
            retained, profiles(), expected_revision=req.revision, cancelled=lambda: True
        )
    with pytest.raises(ProjectionUnavailable):
        project_retained(legacy, profiles(), expected_revision=req.revision)


def test_multiple_sources_summed_before_projection():
    req = fixture("S_B4_chamber_point_5km")
    source = req.sources[0]
    double = replace(
        source,
        source_model_id="second",
        amplitude=replace(source.amplitude, value=2 * source.amplitude.value),
    )
    first = retain_spectrum(req, profiles()[:1])
    both = retain_spectrum(replace(req, sources=(source, double)), profiles()[:1])
    a = project_retained(first, profiles()[:1], expected_revision=req.revision)
    b = project_retained(both, profiles()[:1], expected_revision=req.revision)
    b_rows = cast(list[dict[str, Any]], b["projections"])
    a_rows = cast(list[dict[str, Any]], a["projections"])
    assert b_rows[0]["projection"]["value"] == pytest.approx(
        3 * a_rows[0]["projection"]["value"], rel=1e-12
    )


def test_terrain_zero_and_capture_guards():
    req = fixture("S_B4_chamber_mountain_point_5km")
    req = replace(
        req, directions=DirectionSet((ViewDirection("blocked", 90.2, 23.61),))
    )
    result = retain_spectrum(req, profiles()[:1])
    assert (
        result.spectral_samples and max(result.spectral_samples[0].radiance_per_nm) == 0
    )
    projected = project_retained(result, profiles()[:1], expected_revision=req.revision)
    rows = cast(list[dict[str, Any]], projected["projections"])
    assert rows[0]["projection"]["value"] == 0
    with pytest.raises(PropagationCancelledError):
        retain_spectrum(req, profiles(), cancelled=lambda: True)


def test_registered_dome_and_incomplete_sensor_profiles():
    path = OUT.parent / "pas7.13/adaptatiu-v2/s-b4-chamber-point-5km-camp.json"
    field = decode(json.loads(path.read_text("utf8"))["field"])
    p = profiles()
    lum = cie_dome_luminance(field, 90.0, 45.0, field_response_id=p[0].response_id)
    direct = field.evaluate(90.0, 45.0)
    assert direct is not None
    assert lum["value"] == 683 * direct
    for sensor in p[1:]:
        availability = dome_sensor_availability(
            field, sensor, field_response_id=p[0].response_id
        )
        assert (
            availability["status"] == "unavailable"
            and availability["physicalTransportEvaluations"] == 0
        )
        assert not sensor.sensor_profile_complete and sensor.limitations
