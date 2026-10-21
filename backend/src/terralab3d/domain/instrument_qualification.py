"""Distingeix banda nominal AB, resposta del dispositiu i observacions natives."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class InstrumentEvidence:
    profile_id: str
    provenance: str
    spectral_response_known: bool
    wavelength_basis_known: bool
    spectral_coverage_bounded: bool
    angular_model_known: bool
    angular_coverage_bounded: bool
    device_id: str | None = None
    dark_calibration_known: bool = False
    native_gain_known: bool = False
    native_zero_point_known: bool = False

    def __post_init__(self) -> None:
        if not self.profile_id or not self.provenance:
            raise ValueError("Cal identitat i procedència del perfil")


def qualify_instrument(
    evidence: InstrumentEvidence,
    *,
    target: Literal["nominal_ab", "native_frequency", "native_magnitude"],
    absolute_source_scale: bool,
) -> dict[str, object]:
    if target not in {"nominal_ab", "native_frequency", "native_magnitude"}:
        raise ValueError("Modalitat instrumental desconeguda")
    missing = []
    if not absolute_source_scale:
        missing.append("Escala C relativa: cap lectura absoluta")
    for flag, reason in (
        (evidence.spectral_response_known, "Forma espectral no acreditada"),
        (evidence.wavelength_basis_known, "Convenció espectral no identificada"),
        (evidence.spectral_coverage_bounded, "Suport/cues espectrals sense cota"),
        (evidence.angular_model_known, "Model angular no identificat"),
        (evidence.angular_coverage_bounded, "Cobertura angular sense cota"),
    ):
        if not flag:
            missing.append(reason)
    if target != "nominal_ab":
        for flag, reason in (
            (bool(evidence.device_id), "Dispositiu/calibratge natiu no identificat"),
            (evidence.dark_calibration_known, "Fosc i domini tèrmic no acreditats"),
            (evidence.native_gain_known, "Guany natiu no acreditat"),
        ):
            if not flag:
                missing.append(reason)
        if target == "native_magnitude" and not evidence.native_zero_point_known:
            missing.append("Zero point natiu no acreditat")
    return dict(
        profileId=evidence.profile_id,
        target=target,
        status="unavailable"
        if missing
        else "nominal_model"
        if target == "nominal_ab"
        else "device_model",
        missing=missing,
        individualCalibrationRequired=target != "nominal_ab",
        observationalValidation=False,
        provenance=evidence.provenance,
    )


def missing_coverage_error(
    *,
    known_signal: float,
    missing_weight_fraction: float,
    missing_radiance_upper: float | None,
    magnitude_maximum: float = 0.001,
) -> dict[str, object]:
    """known_signal usa la normalització TOTAL; no la part coneguda renormalitzada.

    Només acota l’efecte d’una regió absent si existeix una cota física
    de la radiància ponderable en aquella regió. Pes petit no implica error petit.
    """
    if (
        not math.isfinite(known_signal)
        or known_signal < 0
        or not math.isfinite(missing_weight_fraction)
        or not 0 <= missing_weight_fraction <= 1
        or not math.isfinite(magnitude_maximum)
        or magnitude_maximum <= 0
        or (
            missing_radiance_upper is not None
            and (
                not math.isfinite(missing_radiance_upper) or missing_radiance_upper < 0
            )
        )
    ):
        raise ValueError("Cota de cobertura invàlida")
    if missing_weight_fraction == 0:
        return dict(status="PASS", upperMissingSignal=0.0, upperErrorMag=0.0)
    if missing_radiance_upper is None:
        return dict(
            status="UNAVAILABLE",
            upperMissingSignal=None,
            upperErrorMag=None,
            reason="Manca cota de radiància; no es pressuposa nul·la",
        )
    upper = missing_weight_fraction * missing_radiance_upper
    error = (
        2.5 * math.log1p(upper / known_signal) / math.log(10)
        if known_signal
        else 0.0
        if upper == 0
        else None
    )
    return dict(
        status="PASS" if error is not None and error <= magnitude_maximum else "FAIL",
        upperMissingSignal=upper,
        upperErrorMag=error,
    )
