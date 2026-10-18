"""Representació espectral adaptativa per a corbes lineals tabulades del Pas 7.4.

Cada interval conserva tots els nusos d'entrada. Simpson integra exactament
el producte d'una SPD i fins a dues respostes lineals dins de cada interval,
abans de l'error d'arrodoniment de punt flotant.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

import numpy as np

from .spectral_oracle import (
    DIMENSIONLESS_UNIT,
    RADIANCE_UNIT,
    RELATIVE_UNIT,
    SPECTRAL_RADIANCE_UNIT,
    SpectralCurve,
)


STRATEGY_ID = "tl3d-sky-v1-knot-union-simpson-1"


def _signature(curves: tuple[SpectralCurve, ...]) -> str:
    digest = hashlib.sha256()
    for curve in curves:
        for token in (curve.source_id, curve.unit, curve.outside_support):
            digest.update(token.encode("utf-8"))
            digest.update(b"\0")
        for wavelength, value in zip(curve.wavelengths_nm, curve.values):
            digest.update(wavelength.hex().encode("ascii"))
            digest.update(b"=")
            digest.update(value.hex().encode("ascii"))
            digest.update(b";")
    return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class SpectralBandSet:
    band_set_id: str
    strategy_id: str
    knots_nm: tuple[float, ...]
    input_signature: str

    @property
    def band_count(self) -> int:
        return len(self.knots_nm) - 1


@dataclass(frozen=True, slots=True)
class SpectralBandResult:
    value: float
    unit: str
    band_set_id: str
    input_signature: str
    band_count: int


def build_spectral_band_set(
    source: SpectralCurve,
    responses: tuple[SpectralCurve, ...],
    wavelength_start_nm: float,
    wavelength_end_nm: float,
) -> SpectralBandSet:
    """Construeix bandes pels nusos, sense interpolar-hi estructures absents."""
    if source.unit not in {SPECTRAL_RADIANCE_UNIT, RELATIVE_UNIT}:
        raise ValueError("La font no és una SPD o radiància espectral")
    if not 1 <= len(responses) <= 2 or any(curve.unit != DIMENSIONLESS_UNIT for curve in responses):
        raise ValueError("El domini homologat admet una o dues respostes adimensionals")
    if not (
        math.isfinite(wavelength_start_nm)
        and math.isfinite(wavelength_end_nm)
        and wavelength_start_nm < wavelength_end_nm
    ):
        raise ValueError("Domini espectral invàlid")
    curves = (source, *responses)
    for curve in curves:
        if curve.outside_support == "unavailable" and (
            wavelength_start_nm < curve.wavelengths_nm[0]
            or wavelength_end_nm > curve.wavelengths_nm[-1]
        ):
            raise ValueError(f"El domini supera el suport de {curve.source_id}")
    knots = tuple(sorted({wavelength_start_nm, wavelength_end_nm} | {
        wavelength
        for curve in curves
        for wavelength in curve.wavelengths_nm
        if wavelength_start_nm < wavelength < wavelength_end_nm
    }))
    digest = hashlib.sha256()
    digest.update(STRATEGY_ID.encode("ascii"))
    for knot in knots:
        digest.update(b";")
        digest.update(knot.hex().encode("ascii"))
    return SpectralBandSet(
        band_set_id=f"{STRATEGY_ID}:{digest.hexdigest()}",
        strategy_id=STRATEGY_ID,
        knots_nm=knots,
        input_signature=_signature(curves),
    )


def _one_sided_endpoints(
    curve: SpectralCurve,
    left: np.ndarray,
    right: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Valors límit interns: extrapolació zero pot saltar al nus del suport."""
    x = np.asarray(curve.wavelengths_nm)
    y = np.asarray(curve.values)
    mid = left + (right - left) / 2
    index = np.clip(np.searchsorted(x, mid, side="right") - 1, 0, len(x) - 2)
    slope = (y[index + 1] - y[index]) / (x[index + 1] - x[index])
    value_left = y[index] + slope * (left - x[index])
    value_mid = y[index] + slope * (mid - x[index])
    value_right = y[index] + slope * (right - x[index])
    if curve.outside_support == "zero":
        inside = (mid >= x[0]) & (mid <= x[-1])
        value_left = np.where(inside, value_left, 0.0)
        value_mid = np.where(inside, value_mid, 0.0)
        value_right = np.where(inside, value_right, 0.0)
    return value_left, value_mid, value_right


def integrate_band_set(
    band_set: SpectralBandSet,
    source: SpectralCurve,
    responses: tuple[SpectralCurve, ...],
) -> SpectralBandResult:
    """Avalua el bandset exactament per a la identitat d'entrada amb què es va construir."""
    curves = (source, *responses)
    if band_set.strategy_id != STRATEGY_ID or band_set.input_signature != _signature(curves):
        raise ValueError("El bandSetId o les corbes han canviat: cal reconstruir el bandset i la cache")
    expected = build_spectral_band_set(source, responses, band_set.knots_nm[0], band_set.knots_nm[-1])
    if expected.band_set_id != band_set.band_set_id or expected.knots_nm != band_set.knots_nm:
        raise ValueError("El bandSetId ja no cobreix els nusos d'entrada")
    knots = np.asarray(band_set.knots_nm)
    left, right = knots[:-1], knots[1:]
    products = [np.ones_like(left), np.ones_like(left), np.ones_like(left)]
    for curve in curves:
        values = _one_sided_endpoints(curve, left, right)
        for product, value in zip(products, values):
            product *= value
    terms = (right - left) * (products[0] + 4 * products[1] + products[2]) / 6
    return SpectralBandResult(
        value=math.fsum(float(term) for term in terms),
        unit=RADIANCE_UNIT if source.unit == SPECTRAL_RADIANCE_UNIT else "relative nm",
        band_set_id=band_set.band_set_id,
        input_signature=band_set.input_signature,
        band_count=band_set.band_count,
    )
