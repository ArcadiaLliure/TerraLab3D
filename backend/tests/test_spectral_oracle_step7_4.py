"""Invariants de l'oracle espectral fi del Pas 7.4."""

from __future__ import annotations

import math

import pytest

from terralab3d.domain.light_pollution.spectral_oracle import (
    DIMENSIONLESS_UNIT,
    RADIANCE_UNIT,
    SPECTRAL_RADIANCE_UNIT,
    SpectralCurve,
    integrate_spectral_product,
)


def test_integral_analytic_of_two_linear_curves_and_units() -> None:
    source = SpectralCurve("analytic_source", (0.0, 1.0), (1.0, 2.0), SPECTRAL_RADIANCE_UNIT)
    response = SpectralCurve("analytic_response", (0.0, 1.0), (2.0, 1.0), DIMENSIONLESS_UNIT)

    result = integrate_spectral_product(source, (response,), 0.0, 1.0)

    # Integral exacta de (1 + x)(2 - x) = 2 + x - x².
    assert result.value == pytest.approx(13.0 / 6.0, rel=1e-14)
    assert result.unit == RADIANCE_UNIT
    assert result.source_ids == ("analytic_source", "analytic_response")


def test_narrow_line_is_not_lost_between_wide_sampling_nodes() -> None:
    source = SpectralCurve(
        "synthetic_narrow_line",
        (400.0, 499.5, 500.0, 500.5, 600.0),
        (0.0, 0.0, 1.0, 0.0, 0.0),
        SPECTRAL_RADIANCE_UNIT,
    )
    response = SpectralCurve("flat_response", (400.0, 600.0), (1.0, 1.0), DIMENSIONLESS_UNIT)

    result = integrate_spectral_product(source, (response,), 400.0, 600.0)

    # Àrea del triangle: base 1 nm, altura 1 unitat espectral.
    assert result.value == pytest.approx(0.5, rel=1e-14)
    assert result.interval_count == 4


def test_declared_zero_extrapolation_and_unavailable_support_differ() -> None:
    source = SpectralCurve("broad_source", (0.0, 4.0), (1.0, 1.0), SPECTRAL_RADIANCE_UNIT)
    response = SpectralCurve("restricted_response", (1.0, 3.0), (2.0, 2.0), DIMENSIONLESS_UNIT)
    with pytest.raises(ValueError, match="suport"):
        integrate_spectral_product(source, (response,), 0.0, 4.0)

    zero_response = SpectralCurve(
        "restricted_response", (1.0, 3.0), (2.0, 2.0), DIMENSIONLESS_UNIT, "zero"
    )
    result = integrate_spectral_product(source, (zero_response,), 0.0, 4.0)
    assert result.value == pytest.approx(4.0, rel=1e-14)


def test_invalid_curves_and_domain_are_rejected() -> None:
    with pytest.raises(ValueError, match="creixents"):
        SpectralCurve("reverse", (2.0, 1.0), (1.0, 1.0), DIMENSIONLESS_UNIT)
    with pytest.raises(ValueError, match="finits"):
        SpectralCurve("nan", (1.0, 2.0), (1.0, math.nan), DIMENSIONLESS_UNIT)
    with pytest.raises(ValueError, match="negatius"):
        SpectralCurve("negative_spd", (1.0, 2.0), (1.0, -1.0), SPECTRAL_RADIANCE_UNIT)
    with pytest.raises(ValueError, match="suport espectral"):
        SpectralCurve("unknown_support", (1.0, 2.0), (1.0, 1.0), DIMENSIONLESS_UNIT, "clamp")  # type: ignore[arg-type]
    source = SpectralCurve("source", (0.0, 1.0), (1.0, 1.0), SPECTRAL_RADIANCE_UNIT)
    response = SpectralCurve("response", (0.0, 1.0), (1.0, 1.0), DIMENSIONLESS_UNIT)
    with pytest.raises(ValueError, match="Domini"):
        integrate_spectral_product(source, (response,), 1.0, 0.0)
