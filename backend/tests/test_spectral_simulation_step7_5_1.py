"""Proves científiques amb integració independent de les taules publicades."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from terralab3d.domain.light_pollution.simulation import (
    SkyglowConfiguration,
    build_conditional_scenarios,
)
from terralab3d.domain.light_pollution.source_model import (
    DefinedSpectrum,
    EmissionAmplitude,
)
from terralab3d.domain.light_pollution.spectral_library import weighted_integral
from terralab3d.infrastructure.adapters.light_pollution.spectral_library import (
    load_spectral_library,
)


@pytest.fixture(scope="module")
def library():
    return load_spectral_library()


@pytest.mark.parametrize("k", [2800, 3000, 3500, 4000, 5000, 6500])
def test_effective_cct_and_nonnegative_measured_structure(library, k):
    spectrum = library.kelvin_spectrum(k)
    color = library.colorimetry(spectrum)
    assert abs(color.cct_k - k) < 0.1
    assert color.distance_uv < 0.002
    assert min(spectrum.relative_power) >= 0
    assert spectrum.origin_kind == "derived_mixture"
    assert all(c[0].startswith("LED-B") for c in spectrum.components)
    # La interpolació convexa no elimina el pic blau real (~450 nm).
    waves, values = np.array(spectrum.wavelengths_nm), np.array(spectrum.relative_power)
    blue = values[(waves >= 430) & (waves <= 470)].max()
    assert blue > values[(waves >= 480) & (waves <= 490)].max()


def test_cct_against_independent_planck_grid(library):
    # Quadratura trapezoïdal densa i cerca de graella, sense el minimitzador.
    spectrum = library.spectra["LED-B1"]
    waves = np.arange(360.0, 830.01, 0.1)
    spd = np.interp(
        waves, spectrum.wavelengths_nm, spectrum.relative_power, left=0, right=0
    )
    cmfs = [np.interp(waves, library.cmf_wavelengths, c) for c in library.cmf_xyz]

    def uv(values):
        x, y, z = [np.trapezoid(c * values, waves) for c in cmfs]
        return np.array([4 * x / (x + 15 * y + 3 * z), 6 * y / (x + 15 * y + 3 * z)])

    target = uv(spd)
    errors = [
        (
            float(
                np.sum(
                    (uv(waves**-5 / np.expm1(1.438776877e7 / (waves * k))) - target)
                    ** 2
                )
            ),
            k,
        )
        for k in range(2700, 2770)
    ]
    assert abs(library.colorimetry(spectrum).cct_k - min(errors)[1]) < 1


def test_mixtures_preserve_radiant_and_photopic_fraction_and_line_knots(library):
    weights = (("LED-B2", 0.3), ("HP1", 0.7))
    for basis in ("radiant_flux", "photopic_flux"):
        mixture = library.mix(basis, weights, basis)
        assert set(library.spectra["HP1"].wavelengths_nm) <= set(mixture.wavelengths_nm)
        assert np.trapezoid(
            mixture.relative_power, mixture.wavelengths_nm
        ) == pytest.approx(1)
        contributions = [
            w if basis == "radiant_flux" else w * library.efficacy(library.spectra[key])
            for key, _, w in mixture.components
        ]
        assert contributions[0] / sum(contributions) == pytest.approx(0.3)
    assert (
        library.spectra["LED-BH1"].relative_power
        != library.spectra["LED-B2"].relative_power
    )
    assert library.technologies["HP1"] == "Standard high pressure sodium lamp"
    assert "FL1" in library.spectra
    metadata = library.describe("LED-B1")
    assert metadata["wavelengthUnit"] == "nm" and 2700 < metadata["cctK"] < 2800
    assert (
        metadata["spectrum"]["asset_sha256"] == library.spectra["LED-B1"].asset_sha256
    )
    assert all(
        s.asset_sha256 and s.license == "CC BY-SA 4.0" for s in library.spectra.values()
    )


def test_narrow_lines_cannot_silently_enter_kelvin_family(library):
    line = DefinedSpectrum(
        "sodium_line_fixture",
        "fixture analítica; no taula mesurada",
        "test",
        (580.0, 588.9, 589.0, 589.1, 600.0),
        (0.0, 0.0, 1.0, 0.0, 0.0),
    )
    assert library.meaningful_cct(line, "low_pressure_sodium") is None
    with pytest.raises(ValueError):
        library.kelvin_spectrum(3000, "low_pressure_sodium")
    with pytest.raises(ValueError):
        library.kelvin_spectrum(1800)


def test_response_integral_matches_analytic_product():
    spectrum = DefinedSpectrum(
        "triangle", "analytic", "test", (400.0, 500.0), (0.0, 2.0)
    )
    # s=x/5000, R=x/100 → ∫sR=2/3.
    assert weighted_integral(spectrum, (400.0, 500.0), (0.0, 1.0)) == pytest.approx(
        2 / 3
    )


@pytest.mark.parametrize(
    "normalization",
    [
        "constant_photopic_flux",
        "constant_radiant_power",
        "constant_dnb_reference",
        "conditional_relative",
    ],
)
def test_conserved_quantity_and_dnb_prediction(
    real_observation_and_response, library, normalization
):
    observation, response = real_observation_and_response
    scenarios = build_conditional_scenarios(
        observation,
        response,
        library,
        SkyglowConfiguration(mode="kelvin", kelvin=5000, normalization=normalization),
    )
    for scenario in scenarios:
        baseline, source = scenario.baseline_spectrum, scenario.source
        # Reconstrucció independent d'A0 amb quadratura trapezoïdal densa.
        waves = np.arange(380.0, 780.001, 0.05)
        s0 = (
            np.interp(waves, baseline.wavelengths_nm, baseline.relative_power)
            / baseline.raw_integral_nm
        )
        s = (
            np.interp(
                waves, source.spectrum.wavelengths_nm, source.spectrum.relative_power
            )
            / source.spectrum.raw_integral_nm
        )
        rsr = np.interp(waves, response.wavelengths_nm, response.relative_response)
        d0 = float(np.trapezoid(s0 * rsr, waves))
        d = float(np.trapezoid(s * rsr, waves))
        base_amplitude = (
            observation.raw_radiance
            * source.geometry.area_m2
            / (d0 * source.angular.density_per_sr(0))
        )
        ratio = source.amplitude.value / base_amplitude
        if normalization == "constant_photopic_flux":
            v = np.interp(waves, library.photopic_wavelengths, library.photopic_values)
            assert ratio * np.trapezoid(s * v, waves) == pytest.approx(
                np.trapezoid(s0 * v, waves), rel=2e-5
            )
            assert scenario.predicted_dnb_ratio != pytest.approx(1, abs=0.001)
        elif normalization == "constant_dnb_reference":
            assert ratio * d == pytest.approx(d0, rel=2e-5)
            assert scenario.predicted_dnb_ratio == pytest.approx(1)
        else:
            assert ratio == pytest.approx(1, rel=2e-5)
        assert source.amplitude.unit == "relative"
        assert source.spectral_flux(500).unit == "relative nm^-1"
        with pytest.raises(ValueError):
            replace(
                source,
                amplitude=EmissionAmplitude(
                    1, "W", "defined_absolute", "injustificat L3"
                ),
            )


def test_response_support_does_not_create_fictitious_ramps():
    flat = DefinedSpectrum("flat", "analytic", "test", (400.0, 600.0), (1.0, 1.0))
    assert weighted_integral(flat, (470.0, 530.0), (1.0, 1.0)) == pytest.approx(0.3)
