"""Configuració autoritativa i escenaris condicionats per al transport únic."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from typing import Any, Literal

from .dnb_measurement import RADIANCE_UNIT, ViirsSpectralResponse
from .source_model import (
    AngularEmissionProfile,
    DefinedSpectrum,
    EmissionAmplitude,
    GeodeticPosition,
    RectangularAreaGeometry,
    SourceModel,
)
from .spectral_library import SpectralLibrary, weighted_integral
from .vnp46 import Vnp46Observation


SIMULATION_REVISION = "black-marble-conditional-v1"
NORMALIZATIONS = {
    "constant_photopic_flux",
    "constant_radiant_power",
    "constant_dnb_reference",
    "conditional_relative",
}
MIXTURES = {
    "led_dominant": (("LED-B2", 0.8), ("HP1", 0.2)),
    "sodium_dominant": (("LED-B2", 0.2), ("HP1", 0.8)),
    "cool_led_dominant": (("LED-B4", 0.95), ("HP1", 0.05)),
}


@dataclass(frozen=True, slots=True)
class SkyglowConfiguration:
    mode: Literal["realistic", "kelvin"] = "realistic"
    kelvin: float = 3000.0
    spectral_family: str = "CIE_LED_B1_B5"
    normalization: str = "constant_photopic_flux"
    mixture_model: str = "deterministic_reference_ensemble_v1"
    revision: str = SIMULATION_REVISION

    def __post_init__(self) -> None:
        if (
            self.mode not in {"realistic", "kelvin"}
            or self.spectral_family != "CIE_LED_B1_B5"
        ):
            raise ValueError("Modalitat o família espectral desconeguda")
        if not math.isfinite(self.kelvin) or not 2800 <= self.kelvin <= 6500:
            raise ValueError("La família CIE cobreix 2.800–6.500 K")
        if (
            self.normalization not in NORMALIZATIONS
            or self.mixture_model != "deterministic_reference_ensemble_v1"
            or self.revision != SIMULATION_REVISION
        ):
            raise ValueError("Normalització, ensemble o revisió incompatible")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> SkyglowConfiguration:
        return cls(**value)

    @property
    def cache_key(self) -> str:
        return hashlib.sha256(
            json.dumps(self.to_dict(), sort_keys=True, allow_nan=False).encode()
        ).hexdigest()


@dataclass(frozen=True, slots=True)
class ConditionalScenario:
    source: SourceModel
    observation: Vnp46Observation
    response: ViirsSpectralResponse
    configuration: SkyglowConfiguration
    baseline_spectrum: DefinedSpectrum
    predicted_dnb_ratio: float
    effective_cct_k: float | None
    cache_key: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source.to_dict(),
            "observation": self.observation.to_dict(),
            "configuration": self.configuration.to_dict(),
            "cacheKey": self.cache_key,
            "baselineSpectrumId": self.baseline_spectrum.spectrum_id,
            "baselineComponents": self.baseline_spectrum.components,
            "predictedDnbRatio": self.predicted_dnb_ratio,
            "effectiveCctK": self.effective_cct_k,
            "rsr": {
                "platform": self.response.platform,
                "releaseId": self.response.release_id,
                "gainStage": self.response.gain_stage,
                "sha256": self.response.local_sha256,
                "sourceUrl": self.response.source_url,
                "sourceMember": self.response.source_member,
                "sourceArchiveSha256": self.response.source_archive_sha256,
                "validFrom": self.response.valid_from.isoformat(),
                "validThrough": self.response.valid_through.isoformat(),
                "role": "public_reference_approximation",
                "l3LinkStatus": self.response.l3_link_status,
            },
            "quality": "conditional_relative",
            "uncertainty": "not_quantified",
            "assumptions": [
                "Mescles de flux radiant hipotètiques; cap pes és una estadística urbana ni una probabilitat",
                "L3 corregit ancorat a radiància relativa de referència 1 nW cm^-2 sr^-1; àrea de referència 1 m²",
                "Direcció de referència zenital hipotètica; no s'inverteixen BRDF ni atmosfera de Black Marble",
                "Patrons angulars analítics alternatius; no equivalència LGS/MGS/HGS",
                "Altura de font definida 0 m; rectangle tangent de 15 arcsec, esfera de radi 6371008.8 m",
                "Suport CIE tabulat; energia fora del suport no coneguda, cap extrapolació",
            ],
            "skyRadiance": None,
            "calculationStatus": "transport_pending",
        }


def build_conditional_scenarios(
    observation: Vnp46Observation,
    response: ViirsSpectralResponse,
    library: SpectralLibrary,
    configuration: SkyglowConfiguration,
) -> tuple[ConditionalScenario, ...]:
    """Escala paramètrica compartida, ancoratge històric i intervenció separats.

    A0=(L3/Lref)*(A/Aref)/(∫s0 R dλ * a0(0)/sr^-1). És un nombre
    relatiu, MAI watts. Les comparacions multipliquen A0 per q(s0)/q(s).
    La resposta DNB predita és una ràtio del mateix operador de referència,
    no una predicció certificada d'una nova observació satel·lital.
    """
    if (
        observation.product_id != "VJ146A2"
        or observation.collection != "002"
        or response.platform != "NOAA-20"
    ):
        raise ValueError(
            "La primera connexió condicionada requereix NOAA-20 VJ146A2.002"
        )
    if (
        observation.radiance_unit != RADIANCE_UNIT
        or observation.is_fill
        or observation.classification != "candidate"
        or observation.quality_flag != 0
    ):
        raise ValueError("L'observació requereix radiància L3 amb QA 0")
    if not math.isfinite(observation.raw_radiance) or observation.raw_radiance <= 0:
        raise ValueError("No hi ha restricció L3 positiva; no es fabrica amplitud")
    if observation.provenance.version_id not in (None, "002"):
        raise ValueError("Release del grànul incompatible")
    if (
        response.gain_stage not in {"LGS", "MGS"}
        or response.application != "diagnostic_at_launch_toa"
    ):
        raise ValueError("Cal una referència NOAA-20 LGS o MGS explícita")
    if any(r < 0 for r in response.relative_response):
        raise ValueError("No es retallen cues negatives de la RSR")
    if not response.source_url.startswith("https://ncc.nesdis.noaa.gov/NOAA-20/"):
        raise ValueError("La referència ha de tenir procedència NOAA-20 oficial")
    target = (
        library.kelvin_spectrum(configuration.kelvin, configuration.spectral_family)
        if configuration.mode == "kelvin"
        else None
    )
    profiles = (
        AngularEmissionProfile(
            "uniform_upward",
            "Hipòtesi analítica, densitat angular uniforme",
            (0.0, 90.0),
            (1.0, 1.0),
        ),
        AngularEmissionProfile(
            "cosine_tabulated",
            "Hipòtesi cosinus tabulat cada 5 graus; no ajust urbà",
            tuple(float(i) for i in range(0, 91, 5)),
            tuple(max(0.0, math.cos(math.radians(i))) for i in range(0, 91, 5)),
        ),
    )
    height = 6371008.8 * math.radians(15 / 3600)
    geometry = RectangularAreaGeometry(
        GeodeticPosition(observation.latitude_deg, observation.longitude_deg, 0),
        height * math.cos(math.radians(observation.latitude_deg)),
        height,
    )
    results = []
    for name, weights in MIXTURES.items():
        baseline = library.mix(name, weights, "radiant_flux")
        spectrum = target if target is not None else baseline
        dnb0 = weighted_integral(
            baseline, response.wavelengths_nm, response.relative_response
        )
        dnb = weighted_integral(
            spectrum, response.wavelengths_nm, response.relative_response
        )
        if min(dnb0, dnb) <= 0:
            raise ValueError("SPD sense resposta DNB positiva")
        scale = 1.0
        if configuration.mode == "kelvin":
            if configuration.normalization == "constant_photopic_flux":
                scale = library.efficacy(baseline) / library.efficacy(spectrum)
            elif configuration.normalization == "constant_dnb_reference":
                scale = dnb0 / dnb
        for angular in profiles:
            key_data = {
                "configuration": configuration.to_dict(),
                "library": library.revision,
                "spectrum": spectrum.components,
                "rsr": response.local_sha256,
                "gain": response.gain_stage,
                "granule": observation.provenance.sha256,
                "observation": observation.to_dict(),
                "baseline": baseline.components,
                "rsrRelease": response.release_id,
                "rsrApplication": response.application,
                "angular": asdict(angular),
                "geometry": asdict(geometry),
            }
            key = hashlib.sha256(
                json.dumps(key_data, sort_keys=True, allow_nan=False).encode()
            ).hexdigest()
            amplitude = (
                observation.raw_radiance
                * geometry.area_m2
                / (dnb0 * angular.density_per_sr(0))
            ) * scale
            source = SourceModel(
                f"C:{name}:{angular.profile_id}:{key[:16]}",
                SIMULATION_REVISION,
                f"conditional-scenario:{key}; observation:{observation.provenance.granule_id}:{observation.row}:{observation.column}",
                geometry,
                spectrum,
                angular,
                EmissionAmplitude(
                    amplitude,
                    "relative",
                    "parametric",
                    "Ancoratge relatiu L3, sense calibratge absolut",
                    "unknown_L3_to_upward_flux_scale",
                ),
                source_mode="CONDITIONAL_L3",
            )
            chroma = library.colorimetry(spectrum)
            results.append(
                ConditionalScenario(
                    source,
                    observation,
                    response,
                    configuration,
                    baseline,
                    scale * dnb / dnb0,
                    chroma.cct_k if chroma.distance_uv <= 0.02 else None,
                    key,
                )
            )
    return tuple(results)
