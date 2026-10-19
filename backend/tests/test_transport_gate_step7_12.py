"""Contrasts analítics/oracles i política prospectiva del gate 7.12."""

from dataclasses import replace
import math
from pathlib import Path
import sys

import numpy as np
import pytest
from scipy.integrate import quad

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from transport_gate_fixtures_step7_12 import primary
from terralab3d.domain.light_pollution.atmospheric_tail import (
    conditional_tail_bound,
    phase_maximum,
)
from terralab3d.domain.light_pollution.geometric_transport import (
    SphericalFrame,
    make_ray,
)
from terralab3d.domain.light_pollution.optical_field import OpticalField
from terralab3d.domain.light_pollution.radiometric_gate import assess_transport
from terralab3d.domain.light_pollution.reference_spectral_transport import (
    solve_reference_spectral,
)
from terralab3d.domain.light_pollution.reference_variable_spectral import (
    _SpectralMedium,
    solve_reference_variable_spectral,
)
from terralab3d.domain.light_pollution.scattering import PhaseFunction
from terralab3d.domain.light_pollution.spectral_transport import SpectralOperator
from terralab3d.infrastructure.adapters.atmosphere.standard_optics import (
    extended_standard_pressure_temperature,
    standard_pressure_temperature,
    GEOPOTENTIAL_RADIUS_M,
)


def request(*, standard=False):
    return primary(
        dict(
            mode="B4",
            standard=standard,
            stepM=5000,
            area=False,
            distanceM=5000,
            elevationDeg=90,
            terrain="none",
        )
    )


def test_extension_preserves_all_historical_values():
    for h in np.linspace(0, 50000, 501):
        assert extended_standard_pressure_temperature(
            float(h)
        ) == standard_pressure_temperature(float(h))
    for h, t in ((51000.0, 270.65), (71000.0, 214.65)):
        z = GEOPOTENTIAL_RADIUS_M * h / (GEOPOTENTIAL_RADIUS_M - h)
        assert extended_standard_pressure_temperature(z)[1] == pytest.approx(
            t, abs=2e-12
        )
    p, t = extended_standard_pressure_temperature(75000.0)
    assert 0 < p < 3 and 203 < t < 214.65
    with pytest.raises(ValueError):
        extended_standard_pressure_temperature(75000.001)


@pytest.mark.parametrize("height", [55000.0, 65000.0, 75000.0])
def test_extended_pressure_against_independent_hydrostatic_integral(height):
    bases = np.array(
        [0.0, 11000.0, 20000.0, 32000.0, 47000.0, 51000.0, 71000.0, 84852.0]
    )
    temperatures = np.array(
        [288.15, 216.65, 216.65, 228.65, 270.65, 270.65, 214.65, 186.946]
    )

    def gradient(z):
        geopotential = GEOPOTENTIAL_RADIUS_M * z / (GEOPOTENTIAL_RADIUS_M + z)
        temperature = float(np.interp(geopotential, bases, temperatures))
        gravity = 9.80665 * (GEOPOTENTIAL_RADIUS_M / (GEOPOTENTIAL_RADIUS_M + z)) ** 2
        return 0.0289644 * gravity / (8.31432 * temperature)

    cuts = sorted(
        {
            0.0,
            height,
            *(
                GEOPOTENTIAL_RADIUS_M * h / (GEOPOTENTIAL_RADIUS_M - h)
                for h in bases[1:]
                if GEOPOTENTIAL_RADIUS_M * h / (GEOPOTENTIAL_RADIUS_M - h) < height
            ),
        }
    )
    exponent = math.fsum(
        quad(gradient, a, b, epsabs=1e-14, epsrel=1e-12)[0]
        for a, b in zip(cuts, cuts[1:])
    )
    expected = 101325 * math.exp(-exponent)
    assert extended_standard_pressure_temperature(height)[0] == pytest.approx(
        expected, rel=3e-13
    )


@pytest.mark.parametrize(
    "candidate,refs,errors,status",
    [
        (1.0, (1.0, 1.0, 1.0), (0.0, 0.0, 0.0), "PASS"),
        (1.001, (1.0, 1.0, 1.0), (0.0, 0.0, 0.0), "FAIL"),
        (1.0, (0.99, 1.0, 1.0), (0.0, 0.0, 0.0), "REFERENCE_UNRESOLVED"),
        (0.0, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), "PASS"),
        (1e-200, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), "FAIL"),
    ],
)
def test_prospective_decision(candidate, refs, errors, status):
    assert (
        assess_transport(
            candidate, refs, errors, relative_limit=1e-4, reference_resolution=1e-6
        ).status
        == status
    )


def test_variable_oracle_homogeneous_limit_and_independence(monkeypatch):
    req = request()
    args = (
        req.sources[0],
        req.observer,
        req.optical_field,
        req.spectral,
        90.0,
        90.0,
        10000.0,
    )
    old = solve_reference_spectral(*args, spectral_order=2, area_order=2)

    def forbidden(*args, **kwargs):
        raise AssertionError("Helper runtime prohibit a SG-REF")

    monkeypatch.setattr(OpticalField, "sample", forbidden)
    monkeypatch.setattr(OpticalField, "traverse", forbidden)
    monkeypatch.setattr(SpectralOperator, "__init__", forbidden)
    monkeypatch.setattr(PhaseFunction, "density", forbidden)
    new = solve_reference_variable_spectral(
        *args, spectral_order=2, path_order=4, area_order=2
    )
    assert new.value == pytest.approx(old.value, rel=2e-11)
    assert new.los_error_estimate / new.value < 1e-7


def test_tail_positive_and_bounds_hydrostatic_exponential_column():
    req = request(standard=True)
    top = 75000.0
    pressure = req.optical_field.tiles[0].profile.pressure_pa[-1]
    direction = req.directions.directions[0]
    bound = conditional_tail_bound(
        req.sources[0], req.observer, direction, top, pressure, req.spectral
    )
    assert bound.upper_radiance > 0 and bound.aerosol_weighted_length_m > 0
    frame = SphericalFrame(req.observer)
    ray = make_ray(frame, direction, top)
    source = np.asarray(frame.position_ecef(req.sources[0].geometry.position))
    mass = 0.0289644 / 6.02214076e23
    # P(H+x)=P(H) exp(-x/L), amb n definit per la mateixa hidrostàtica.
    for length in (1000.0, 8000.0, 100000.0):

        def f(x):
            h = top + x * length
            n = (
                pressure
                * math.exp(-x)
                / length
                * (frame.radius_m + h) ** 2
                / (mass * 9.80665 * frame.radius_m**2)
            )
            s = ray.distance_to_height(h)
            point = np.asarray(ray.point(s))
            impact2 = (frame.radius_m + req.observer.altitude_m) ** 2 * (
                1 - ray.direction_enu[2] ** 2
            )
            jac = (frame.radius_m + h) / math.sqrt((frame.radius_m + h) ** 2 - impact2)
            return n * jac / float((point - source) @ (point - source)) * length

        numeric = quad(f, 0, 80, epsabs=1e-20, epsrel=1e-11)[0]
        assert 0 < numeric <= bound.molecular_weighted_column
    # La cota no accepta un aerosol de densitat constant exterior.
    cfg = replace(
        req.spectral,
        aerosols=tuple(
            replace(a, reference=replace(a.reference, scale_height_m=None))
            for a in req.spectral.aerosols
        ),
    )
    with pytest.raises(ValueError, match="exponencial"):
        conditional_tail_bound(
            req.sources[0], req.observer, direction, top, pressure, cfg
        )


@pytest.mark.parametrize("g", [-0.99, -0.65, 0.0, 0.65, 0.99])
def test_phase_envelope(g):
    phase = PhaseFunction("hg_fallback", "fixture analítica", asymmetry=g)
    maximum = phase_maximum(phase)
    assert max(
        phase.density(float(mu)) for mu in np.linspace(-1, 1, 1001)
    ) <= maximum * (1 + 2e-13)


def test_variable_gas_columns_against_scalar_high_precision_quad():
    req = request(standard=True)
    field, cfg = req.optical_field, req.spectral
    assert field and cfg and cfg.gas
    medium = _SpectralMedium(req.sources[0], field, cfg, 2, 16, lambda: None)
    frame = SphericalFrame(req.observer)
    start = np.asarray(frame.position_ecef(req.observer))
    end = np.asarray(frame.position_ecef(replace(req.observer, altitude_m=74000.0)))
    computed = medium.depth(start, end)
    profile = field.tiles[0].profile
    gas, lut = cfg.gas.profiles[0], cfg.gas.luts[0]
    # Oracle escalar: integra directament n sigma(T,lambda), sense bases de T.
    for index in (0, len(medium.waves) // 2, len(medium.waves) - 1):
        wavelength = float(medium.waves[index])
        sigma = float(medium.sigma[index])
        aerosol = cfg.aerosols[0]

        def extinction(h):
            temperature = float(np.interp(h, profile.heights_m, profile.temperature_k))
            n = math.exp(
                float(np.interp(h, profile.heights_m, np.log(profile.pressure_pa)))
            ) / (1.380649e-23 * temperature)
            cross = float(
                np.interp(
                    temperature,
                    lut.temperatures_k,
                    [
                        np.interp(wavelength, lut.wavelengths_nm, row)
                        for row in lut.cross_sections_m2
                    ],
                )
            )
            aer = (
                aerosol.reference.extinction_per_m
                * math.exp(-h / aerosol.reference.scale_height_m)
                * (wavelength / aerosol.reference_wavelength_nm)
                ** (-aerosol.angstrom_exponent)
            )
            return n * (sigma + gas.fraction(h) * cross) + aer

        cuts = sorted(
            {
                100.0,
                74000.0,
                *(h for h in profile.heights_m if 100 < h < 74000),
                *(
                    100 + s
                    for s in medium.path.cuts(start, np.array([1.0, 0.0, 0.0]), 73900.0)
                    if 0 < s < 73900
                ),
            }
        )
        expected = math.fsum(
            (b - a) * extinction((a + b) / 2)
            if b - a < 1e-6
            else quad(extinction, a, b, epsabs=1e-14, epsrel=1e-11)[0]
            for a, b in zip(cuts, cuts[1:])
        )
        assert computed[index] == pytest.approx(expected, rel=2e-10, abs=2e-13)
