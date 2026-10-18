"""Conservació i dimensions de fonts S definides, sense VIIRS ni Black Marble."""

from __future__ import annotations

import json
import math
from dataclasses import FrozenInstanceError, replace

import numpy as np
import pytest

from terralab3d.domain.light_pollution.source_model import (
    AngularEmissionProfile,
    AzimuthalAngularEmissionProfile,
    DefinedSpectrum,
    EmissionAmplitude,
    GeodeticPosition,
    PointSourceGeometry,
    RectangularAreaGeometry,
    SourceModel,
    SourceModelEnsemble,
    mix_defined_spectra,
)


def _triangle() -> DefinedSpectrum:
    return DefinedSpectrum(
        "triangle_analitic", "fixture analítica de 7.5", "fixture",
        (400.0, 500.0, 600.0), (0.0, 1.0, 0.0),
    )


def _axial() -> AngularEmissionProfile:
    return AngularEmissionProfile("uniform_intensity", "fixture analítica de 7.5", (0.0, 90.0), (1.0, 1.0))


def _source(*, area: bool = False, parametric: bool = False) -> SourceModel:
    position = GeodeticPosition(41.38, 2.17, 25.0)
    geometry = RectangularAreaGeometry(position, 10.0, 20.0) if area else PointSourceGeometry(position)
    amplitude = (
        EmissionAmplitude(1.0, "relative", "parametric", "fixture de paràmetre lliure", "P_source")
        if parametric else EmissionAmplitude(100.0, "W", "defined_absolute", "fixture física definida")
    )
    return SourceModel("fixture_source", "v1", "fixture analítica explícita", geometry, _triangle(), _axial(), amplitude)


def _integrate_angular(angular: AngularEmissionProfile | AzimuthalAngularEmissionProfile) -> float:
    """Quadratura independent en cosθ i azimut, sense usar l'integral de producció."""
    nodes, weights = np.polynomial.legendre.leggauss(80)
    cosines = (nodes + 1) / 2
    azimuths = (nodes + 1) * 180
    total = 0.0
    for cosine, weight_cos in zip(cosines, weights):
        theta = math.degrees(math.acos(float(cosine)))
        for azimuth, weight_az in zip(azimuths, weights):
            total += float(weight_cos * weight_az) * angular.density_per_sr(theta, float(azimuth))
    return total * math.pi / 2


def test_point_source_conserves_spectral_power_and_hemispheric_flux() -> None:
    source = _source()
    assert source.source_mode == "DEFINED_SOURCE"
    assert source.spectrum.raw_integral_nm == pytest.approx(100.0)
    spectral = [source.spectral_flux(wavelength).value for wavelength in source.spectrum.wavelengths_nm]
    assert np.trapezoid(spectral, source.spectrum.wavelengths_nm) == pytest.approx(100.0)
    assert source.spectral_flux(500.0).unit == "W nm^-1"
    assert source.spectral_radiant_intensity(500.0, 30.0).unit == "W sr^-1 nm^-1"
    assert source.spectral_radiant_intensity(500.0, 30.0).value == pytest.approx(1 / (2 * math.pi))
    assert _integrate_angular(source.angular) == pytest.approx(1.0, rel=1e-12)
    with pytest.raises(ValueError, match="puntual"):
        source.surface_spectral_radiance(500.0, 0.0)


def test_area_source_keeps_exitance_intensity_density_and_radiance_distinct() -> None:
    source = _source(area=True)
    assert isinstance(source.geometry, RectangularAreaGeometry)
    assert source.geometry.area_m2 == 200.0
    assert source.surface_spectral_exitance(500.0).value == pytest.approx(0.005)
    direction = source.area_spectral_radiant_intensity_density(500.0, 60.0)
    radiance = source.surface_spectral_radiance(500.0, 60.0)
    assert direction.unit == "W m^-2 sr^-1 nm^-1"
    assert radiance.unit == "W m^-2 sr^-1 nm^-1"
    assert direction.value == pytest.approx(radiance.value * math.cos(math.radians(60)))
    assert source.spectral_radiant_intensity(500.0, 60.0).value == pytest.approx(direction.value * 200)
    with pytest.raises(ValueError, match="cosθ positiu"):
        source.surface_spectral_radiance(500.0, 90.0)


def test_azimuthal_source_is_periodic_anisotropic_and_normalized() -> None:
    angular = AzimuthalAngularEmissionProfile(
        "anisotropic_fixture", "fixture analítica de 7.5", _axial(),
        (0.0, 90.0, 180.0, 270.0, 360.0), (1.0, 2.0, 1.0, 0.0, 1.0),
    )
    assert angular.density_per_sr(20.0, 90.0) > angular.density_per_sr(20.0, 270.0)
    assert angular.density_per_sr(20.0, 450.0) == angular.density_per_sr(20.0, 90.0)
    assert _integrate_angular(angular) == pytest.approx(1.0, rel=2e-5)
    source = replace(_source(), angular=angular)
    assert source.spectral_radiant_intensity(500.0, 20.0, 90.0).value > 0


def test_narrow_spectrum_and_mixture_preserve_input_knots() -> None:
    narrow = DefinedSpectrum(
        "narrow_fixture", "fixture triangular de 0,02 nm", "fixture",
        (400.0, 499.99, 500.0, 500.01, 600.0), (0.0, 0.0, 1.0, 0.0, 0.0),
    )
    mixture = mix_defined_spectra("mixed_fixture", ((_triangle(), 3.0), (narrow, 1.0)), "mescla declarada")
    assert 499.99 in mixture.wavelengths_nm and 500.01 in mixture.wavelengths_nm
    integrated = np.trapezoid(
        [mixture.density_per_nm(wavelength) for wavelength in mixture.wavelengths_nm],
        mixture.wavelengths_nm,
    )
    assert integrated == pytest.approx(1.0)
    assert mixture.density_per_nm(500.0) > _triangle().density_per_nm(500.0)
    assert mixture.components == (("triangle_analitic", None, 0.75), ("narrow_fixture", None, 0.25))
    assert mixture.origin_kind == "derived_mixture"
    with pytest.raises(ValueError, match="mateix suport"):
        mix_defined_spectra("bad", ((_triangle(), 1.0), (
            DefinedSpectrum("shifted", "fixture", "fixture", (420.0, 500.0, 620.0), (0.0, 1.0, 0.0)), 1.0,
        )), "fixture")


def test_parametric_power_cannot_be_presented_as_watts() -> None:
    source = _source(parametric=True)
    assert source.amplitude.absolute_calibration_status == "parametric"
    assert source.spectral_flux(500.0).unit == "relative nm^-1"
    assert source.to_dict()["amplitude"]["parameterName"] == "P_source"  # type: ignore[index]
    with pytest.raises(ValueError, match="watts"):
        EmissionAmplitude(1.0, "W", "parametric", "fixture", "P_source")
    with pytest.raises(ValueError, match="paràmetre"):
        EmissionAmplitude(1.0, "relative", "parametric", "fixture")


def test_invalid_spectrum_geometry_and_angular_inputs_are_rejected() -> None:
    with pytest.raises(ValueError, match="SHA-256"):
        DefinedSpectrum(
            "published", "taula de prova", "fixture", (400.0, 500.0), (1.0, 1.0),
            origin_kind="published_table",
        )
    with pytest.raises(ValueError, match="no negatiu"):
        DefinedSpectrum("negative", "fixture", "fixture", (400.0, 500.0), (1.0, -1.0))
    with pytest.raises(ValueError, match="no nul"):
        DefinedSpectrum("zero", "fixture", "fixture", (400.0, 500.0), (0.0, 0.0))
    with pytest.raises(ValueError, match="no finits"):
        DefinedSpectrum("nan", "fixture", "fixture", (400.0, 500.0), (1.0, math.nan))
    with pytest.raises(ValueError, match="costats positius"):
        RectangularAreaGeometry(GeodeticPosition(0, 0, 0), 0, 10)
    with pytest.raises(ValueError, match="periòdic"):
        AzimuthalAngularEmissionProfile("bad", "fixture", _axial(), (0, 360), (1, 2))
    with pytest.raises(ValueError, match="negativa|positiva"):
        EmissionAmplitude(-1.0, "W", "defined_absolute", "fixture")
    too_large = replace(
        _source(),
        spectrum=DefinedSpectrum("narrow", "fixture", "fixture", (499.99, 500.0, 500.01), (0.0, 1.0, 0.0)),
        amplitude=EmissionAmplitude(1e308, "W", "defined_absolute", "fixture límit"),
    )
    with pytest.raises(ValueError, match="finita"):
        too_large.spectral_flux(500.0)


def test_serialization_and_ensemble_preserve_provenance_without_observations() -> None:
    source = _source()
    payload = source.to_dict()
    assert payload["sourceMode"] == "DEFINED_SOURCE"
    assert payload["uncertaintyStatus"] == "not_quantified"
    assert payload["spectrum"]["evidenceReference"] == "fixture analítica de 7.5"  # type: ignore[index]
    assert payload["spectrum"]["originKind"] == "defined_input"  # type: ignore[index]
    assert "granuleId" not in json.dumps(payload)
    assert payload["geometry"]["kind"] == "point"  # type: ignore[index]
    json.dumps(payload, allow_nan=False)
    with pytest.raises(FrozenInstanceError):
        source.revision = "changed"  # type: ignore[misc]
    ensemble = SourceModelEnsemble("two_scenarios", (source, replace(source, source_model_id="alternative")))
    assert len(ensemble.alternatives) == 2
    with pytest.raises(ValueError, match="únics"):
        SourceModelEnsemble("duplicate", (source, source))
