"""Projeccions de dades espectrals retingudes; mai executa transport físic."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

import numpy as np

from .light_pollution.geometric_transport import ViewDirection
from .light_pollution.spectral_bandset import _one_sided_endpoints
from .light_pollution.spectral_oracle import DIMENSIONLESS_UNIT, SpectralCurve
from .light_pollution.spectral_transport import SpectralRaySamples

PHOTOPIC_KM = 683.0
ARCSEC2_SR = (math.pi / 648000.0) ** 2
AB_FNU_W_M2_HZ = 3631e-26
SPEED_OF_LIGHT_NM_S = 299792458e9
PROJECTION_REVISION = "photometric-panels-and-FOV-v1"
AB_REFERENCE_ID = "AB-3631Jy-arcsec2-tabulated-reference-band-v1"


class ProjectionUnavailable(ValueError):
    """Dades absents o domini no acreditat; no equival a zero."""


@dataclass(frozen=True, slots=True)
class GaussianFov:
    model_id: str
    fwhm_deg: float
    provenance: str
    measured_device: bool = False

    def __post_init__(self) -> None:
        if (
            not self.model_id
            or not self.provenance
            or not math.isfinite(self.fwhm_deg)
            or not 0 < self.fwhm_deg <= 180
        ):
            raise ValueError("FOV gaussià invàlid")

    def peak_response(self, theta_rad: float) -> float:
        return math.exp(
            -4 * math.log(2) * (theta_rad / math.radians(self.fwhm_deg)) ** 2
        )


@dataclass(frozen=True, slots=True)
class PhotometricResponse:
    response_id: str
    kind: str
    curve: SpectralCurve
    provenance: str
    fov: GaussianFov | None = None
    zero_point_id: str | None = None
    sensor_profile_complete: bool = False
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if (
            not self.response_id
            or not self.provenance
            or self.kind not in {"CIE", "SQM", "TESS_W", "CUSTOM_SENSOR"}
            or self.curve.unit != DIMENSIONLESS_UNIT
            or any(v < 0 for v in self.curve.values)
            or max(self.curve.values) <= 0
        ):
            raise ValueError("Resposta fotomètrica invàlida")
        if (
            self.sensor_profile_complete
            and self.kind != "CIE"
            and (self.fov is None or not self.zero_point_id)
        ):
            raise ValueError(
                "Un perfil complet necessita FOV i zero point identificats"
            )


@dataclass(frozen=True, slots=True)
class BandSignal:
    value: float
    los_error_estimate: float
    unit: str
    scale_id: str
    response_id: str
    domain_nm: tuple[float, float]
    band_set_id: str
    source_id: str
    direction_id: str

    @property
    def absolute(self) -> bool:
        return self.unit == "W m^-2 sr^-1"


def _validated_arrays(samples: SpectralRaySamples):
    x = np.asarray(samples.knots_nm, dtype=float)
    y = np.asarray(samples.radiance_per_nm, dtype=float)
    e = np.asarray(samples.los_error_per_nm, dtype=float)
    if (
        len(x) < 2
        or len(y) != 3 * (len(x) - 1)
        or y.shape != e.shape
        or not np.all(np.isfinite(x))
        or not np.all(np.diff(x) > 0)
        or x[0] <= 0
        or not np.all(np.isfinite(y))
        or not np.all(np.isfinite(e))
        or np.any(y < 0)
        or np.any(e < 0)
        or not samples.scale_id
        or not samples.band_set_id
        or not samples.source_id
        or not samples.direction_id
    ):
        raise ValueError("Panells de radiància invàlids")
    if samples.unit == "W m^-2 sr^-1 nm^-1":
        factor, unit = 1.0, "W m^-2 sr^-1"
    elif samples.unit == "nW cm^-2 sr^-1 nm^-1":
        factor, unit = 1e-5, "W m^-2 sr^-1"
    elif samples.unit == "relative m^-2 sr^-1 nm^-1":
        factor, unit = 1.0, "relative m^-2 sr^-1"
    else:
        raise ValueError("Unitat de radiància espectral desconeguda")
    return x, y.reshape(-1, 3) * factor, e.reshape(-1, 3) * factor, unit


def project_band(
    samples: SpectralRaySamples,
    response: PhotometricResponse,
    *,
    domain_nm: tuple[float, float] | None = None,
) -> BandSignal:
    """Simpson sobre densitats ja transportades, sense normalitzar la font."""
    x, y, errors, unit = _validated_arrays(samples)
    lo, hi = domain_nm or (float(x[0]), float(x[-1]))
    if not x[0] <= lo < hi <= x[-1] or lo not in x or hi not in x:
        raise ProjectionUnavailable(
            "El domini de projecció ha de seguir els panells retinguts"
        )
    c = response.curve
    if c.outside_support == "unavailable" and (
        lo < c.wavelengths_nm[0] or hi > c.wavelengths_nm[-1]
    ):
        raise ProjectionUnavailable(
            "Resposta desconeguda en una part de l’espectre; no s’omple amb zero"
        )
    if any(w not in x for w in c.wavelengths_nm if lo < w < hi):
        raise ProjectionUnavailable(
            "Falten nusos de resposta: cal incloure’ls abans del transport"
        )
    selected = (x[:-1] >= lo) & (x[1:] <= hi)
    left, right = x[:-1][selected], x[1:][selected]
    response_values = np.column_stack(_one_sided_endpoints(c, left, right))
    weights = response_values * (right - left)[:, None] * np.array([1, 4, 1]) / 6
    value = math.fsum(float(v) for v in (weights * y[selected]).ravel())
    error = math.fsum(float(v) for v in (weights * errors[selected]).ravel())
    return BandSignal(
        value,
        error,
        unit,
        samples.scale_id,
        response.response_id,
        (lo, hi),
        samples.band_set_id,
        samples.source_id,
        samples.direction_id,
    )


def ab_reference_radiance(response: PhotometricResponse) -> float:
    """Referència AB de banda tabulada: 3631 Jy per arcsec²; resposta d’energia.

    Integra analíticament cada tram lineal de T(λ)/λ², amb λ en nm.
    No és el zero point d’una lectura nativa en Hz.
    """
    c = response.curve
    if c.wavelengths_nm[0] <= 0:
        raise ValueError("La referència AB requereix longituds d’ona positives")
    terms = []
    for a, b, ta, tb in zip(
        c.wavelengths_nm, c.wavelengths_nm[1:], c.values, c.values[1:]
    ):
        slope = (tb - ta) / (b - a)
        terms.append(
            slope * math.log1p((b - a) / a) + (ta - slope * a) * (b - a) / (a * b)
        )
    result = AB_FNU_W_M2_HZ * SPEED_OF_LIGHT_NM_S / ARCSEC2_SR * math.fsum(terms)
    if not math.isfinite(result) or result <= 0:
        raise ValueError("Referència AB nul·la o no finita")
    return result


def photopic_luminance(signal: BandSignal) -> dict[str, object]:
    if signal.response_id != "CIE-V-2019-tabulated":
        raise ValueError("La luminància fotòpica requereix V(λ), no SQM/TESS")
    return dict(
        kind="PHOTOPIC_LUMINANCE" if signal.absolute else "RELATIVE_PHOTOPIC_SIGNAL",
        status="available" if signal.absolute else "relative",
        value=PHOTOPIC_KM * signal.value,
        unit="cd m^-2" if signal.absolute else "relative (683 V-weighted)",
        losErrorEstimate=PHOTOPIC_KM * signal.los_error_estimate,
        spectralResponseId=signal.response_id,
        sourceScale=signal.scale_id,
        zeroPointId=None,
        provenance="CIE V(λ), Km=683 lm/W; component artificial modelat",
    )


def sensor_magnitude(
    signal: BandSignal,
    response: PhotometricResponse,
    *,
    fov_applied: bool = False,
    allow_reference: bool = False,
) -> dict[str, object]:
    if signal.response_id != response.response_id:
        raise ValueError("La resposta de la radiància ponderada no coincideix")
    reason = None
    if not signal.absolute:
        reason = "Escala C relativa: cap magnitud AB absoluta sense calibratge"
    elif response.zero_point_id != AB_REFERENCE_ID:
        reason = (
            "Zero point desconegut o natiu: no es substitueix silenciosament per AB"
        )
    elif not response.sensor_profile_complete and not allow_reference:
        reason = "Perfil instrumental incomplet: " + "; ".join(response.limitations)
    elif not fov_applied and not allow_reference:
        reason = "Radiància direccional: encara no és la lectura integrada pel FOV"
    elif signal.value <= 0:
        reason = (
            "Senyal zero exacte: magnitud logarítmica no finita, sense sòl artificial"
        )
    value = (
        None
        if reason
        else -2.5 * math.log10(signal.value / ab_reference_radiance(response))
    )
    return dict(
        kind=response.kind if not allow_reference else "DIRECTIONAL_REFERENCE_BAND_AB",
        status="unavailable"
        if reason
        else "conditional_reference"
        if allow_reference
        else "available",
        value=value,
        unit="mag_AB arcsec^-2" if value is not None else None,
        reason=reason,
        spectralResponseId=response.response_id,
        zeroPointId=response.zero_point_id,
        fovModelId=response.fov.model_id if response.fov and fov_applied else None,
        domainNm=signal.domain_nm,
        weightedRadiance=signal.value,
        weightedRadianceUnit=signal.unit,
        sourceScale=signal.scale_id,
        predictionUncertainty=dict(
            numericalLosEstimate=signal.los_error_estimate,
            spectralDiscretization="pressupost separat 0,01 mag; consumir gate registrat",
            spectralPriorEnsemble=None,
            responseSystematic=None,
            fovSystematic=None,
            nativeCalibration=None,
        ),
        provenance=response.provenance,
        bortleEquivalent=None,
        bortlePolicyId=None,
    )


def relative_magnitude_difference(
    candidate: BandSignal, reference: BandSignal
) -> float | None:
    if (
        candidate.unit != reference.unit
        or candidate.scale_id != reference.scale_id
        or candidate.response_id != reference.response_id
        or candidate.domain_nm != reference.domain_nm
    ):
        raise ValueError("Els contrastos requereixen la mateixa escala, banda i suport")
    if min(candidate.value, reference.value) <= 0:
        return None
    return -2.5 * math.log10(candidate.value / reference.value)


def average_fov(
    field: Callable[[float, float], float | None],
    fov: GaussianFov,
    pointing: ViewDirection,
    *,
    complete_forward_hemisphere: bool,
    order: int = 64,
    cancelled: Callable[[], bool] | None = None,
) -> float:
    """Mitjana en angle sòlid; mai elimina i renormalitza punts sense cobertura."""
    if not complete_forward_hemisphere:
        raise ProjectionUnavailable(
            "El FOV té pes fora de la cobertura angular acreditada"
        )
    if type(order) is not int or not 4 <= order <= 512:
        raise ValueError("Ordre de quadratura angular invàlid")
    mu, w = np.polynomial.legendre.leggauss(order)
    mu, w = (mu + 1) / 2, w / 2
    az = math.radians(pointing.azimuth_deg)
    center = np.array(pointing.enu)
    t1 = np.array([math.cos(az), -math.sin(az), 0.0])
    t2 = np.cross(center, t1)
    phi = 2 * math.pi * (np.arange(2 * order) + 0.5) / (2 * order)
    terms, total = [], []
    for m, weight in zip(mu, w):
        if cancelled is not None and cancelled():
            raise ProjectionUnavailable(
                "Projecció angular cancel·lada; cap resultat parcial"
            )
        angular_weight = float(weight) * fov.peak_response(math.acos(float(m)))
        for p in phi:
            direction = m * center + math.sqrt(1 - float(m) ** 2) * (
                math.cos(float(p)) * t1 + math.sin(float(p)) * t2
            )
            a = math.degrees(math.atan2(float(direction[0]), float(direction[1]))) % 360
            e = math.degrees(math.asin(max(-1.0, min(1.0, float(direction[2])))))
            value = field(a, e)
            if value is None:
                raise ProjectionUnavailable(
                    "FOV sense dades: no es confon amb zero físic"
                )
            if not math.isfinite(value) or value < 0:
                raise ValueError("Camp de radiància invàlid")
            terms.append(angular_weight * value)
            total.append(angular_weight)
    return math.fsum(terms) / math.fsum(total)
