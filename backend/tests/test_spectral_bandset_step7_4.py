"""Contracte de bandes adaptatives: conservació de nusos i invalidació."""

from __future__ import annotations

import random

import pytest

from terralab3d.domain.light_pollution.spectral_bandset import (
    build_spectral_band_set,
    integrate_band_set,
)
from terralab3d.domain.light_pollution.spectral_oracle import (
    DIMENSIONLESS_UNIT,
    RELATIVE_UNIT,
    SpectralCurve,
    integrate_spectral_product,
)


def test_cubic_product_and_narrow_line_are_integrated() -> None:
    source = SpectralCurve("narrow", (0.0, 0.49, 0.5, 0.51, 1.0), (0.0, 0.0, 1.0, 0.0, 0.0), RELATIVE_UNIT)
    first = SpectralCurve("rising", (0.0, 1.0), (0.0, 1.0), DIMENSIONLESS_UNIT)
    second = SpectralCurve("falling", (0.0, 1.0), (1.0, 0.0), DIMENSIONLESS_UNIT)
    band_set = build_spectral_band_set(source, (first, second), 0.0, 1.0)

    result = integrate_band_set(band_set, source, (first, second))

    # Integral analítica del triangle simètric multiplicat per x(1-x).
    assert result.value == pytest.approx(0.002499833333333333, rel=1e-12)
    assert band_set.band_count == 4
    assert result.band_set_id == band_set.band_set_id


def test_zero_extrapolation_has_no_spurious_endpoint_wedge() -> None:
    source = SpectralCurve("flat", (0.0, 4.0), (1.0, 1.0), RELATIVE_UNIT)
    response = SpectralCurve("window", (1.0, 3.0), (2.0, 2.0), DIMENSIONLESS_UNIT, "zero")
    band_set = build_spectral_band_set(source, (response,), 0.0, 4.0)
    assert integrate_band_set(band_set, source, (response,)).value == pytest.approx(4.0)


def test_band_and_input_changes_invalidate_cache_identity() -> None:
    source = SpectralCurve("source", (0.0, 1.0), (1.0, 1.0), RELATIVE_UNIT)
    changed_knots = SpectralCurve("source", (0.0, 0.5, 1.0), (1.0, 1.0, 1.0), RELATIVE_UNIT)
    changed_values = SpectralCurve("source", (0.0, 1.0), (1.0, 2.0), RELATIVE_UNIT)
    response = SpectralCurve("response", (0.0, 1.0), (1.0, 1.0), DIMENSIONLESS_UNIT)
    original = build_spectral_band_set(source, (response,), 0.0, 1.0)
    with_new_knot = build_spectral_band_set(changed_knots, (response,), 0.0, 1.0)
    with_new_values = build_spectral_band_set(changed_values, (response,), 0.0, 1.0)

    assert original.band_set_id != with_new_knot.band_set_id
    assert original.band_set_id == (
        "tl3d-sky-v1-knot-union-simpson-1:"
        "5b114d32bf2dcd1fb3c5a7c41a11ba96d891b09d154a5a54450e32bb883e9a13"
    )
    assert original.band_set_id == with_new_values.band_set_id
    assert original.input_signature != with_new_values.input_signature
    with pytest.raises(ValueError, match="reconstruir"):
        integrate_band_set(original, changed_values, (response,))


def test_unavailable_rsr_support_is_not_extrapolated() -> None:
    source = SpectralCurve("source", (0.0, 4.0), (1.0, 1.0), RELATIVE_UNIT)
    response = SpectralCurve("rsr", (1.0, 3.0), (1.0, 1.0), DIMENSIONLESS_UNIT)
    with pytest.raises(ValueError, match="suport"):
        build_spectral_band_set(source, (response,), 0.0, 4.0)


def test_independent_oracle_for_irregular_positive_curves() -> None:
    randomizer = random.Random(0x544C3344)
    for index in range(20):
        curves = []
        for curve_index in range(3):
            knots = (400.0, *sorted(randomizer.uniform(401.0, 779.0) for _ in range(5)), 780.0)
            values = tuple(randomizer.uniform(0.0, 1.0) for _ in knots)
            curves.append(SpectralCurve(
                f"curve_{index}_{curve_index}", knots, values,
                RELATIVE_UNIT if curve_index == 0 else DIMENSIONLESS_UNIT,
            ))
        source, first, second = curves
        band_set = build_spectral_band_set(source, (first, second), 400.0, 780.0)
        candidate = integrate_band_set(band_set, source, (first, second)).value
        independent = integrate_spectral_product(source, (first, second), 400.0, 780.0).value
        assert candidate == pytest.approx(independent, rel=1e-12)
