"""Absorció d'una composició prescrita, sense espècies ni zeros implícits.

Seccions eficaces en m²/molècula, λ de buit en nm, interpolació lineal
en λ i T. No es modela eixamplament per pressió amb aquestes taules.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import numpy as np

from .optical_field import fingerprint


@dataclass(frozen=True, slots=True)
class GasCrossSectionLut:
    species: str
    revision: str
    wavelengths_nm: tuple[float, ...]
    temperatures_k: tuple[float, ...]
    cross_sections_m2: tuple[tuple[float, ...], ...]
    evidence_reference: str
    license: str
    asset_sha256: str

    def __post_init__(self) -> None:
        if not all(
            (
                self.species,
                self.revision,
                self.evidence_reference,
                self.license,
                self.asset_sha256,
            )
        ):
            raise ValueError("Cal procedència completa de la LUT gasosa")
        for axis in (self.wavelengths_nm, self.temperatures_k):
            if (
                len(axis) < 2
                or any(not math.isfinite(x) or x <= 0 for x in axis)
                or any(b <= a for a, b in zip(axis, axis[1:]))
            ):
                raise ValueError("Eixos de LUT invàlids")
        if len(self.cross_sections_m2) != len(self.temperatures_k) or any(
            len(row) != len(self.wavelengths_nm)
            or any(not math.isfinite(x) or x < 0 for x in row)
            for row in self.cross_sections_m2
        ):
            raise ValueError("Seccions eficaces negatives, no finites o incompletes")

    def matrix(self, wavelengths_nm: np.ndarray) -> np.ndarray:
        if (
            np.any(~np.isfinite(wavelengths_nm))
            or np.any(wavelengths_nm < self.wavelengths_nm[0])
            or np.any(wavelengths_nm > self.wavelengths_nm[-1])
        ):
            raise ValueError("La LUT no permet extrapolació espectral")
        return np.array(
            [
                np.interp(wavelengths_nm, self.wavelengths_nm, row)
                for row in self.cross_sections_m2
            ]
        )

    def temperature_weights(self, temperature_k: float) -> np.ndarray:
        if (
            not math.isfinite(temperature_k)
            or not self.temperatures_k[0] <= temperature_k <= self.temperatures_k[-1]
        ):
            raise ValueError("Temperatura fora de la LUT; no s'extrapola")
        i = min(
            int(np.searchsorted(self.temperatures_k, temperature_k, side="right")) - 1,
            len(self.temperatures_k) - 2,
        )
        f = (temperature_k - self.temperatures_k[i]) / (
            self.temperatures_k[i + 1] - self.temperatures_k[i]
        )
        weights = np.zeros(len(self.temperatures_k))
        weights[i : i + 2] = (1 - f, f)
        return weights


@dataclass(frozen=True, slots=True)
class GasMixingProfile:
    tile_id: str
    species: str
    heights_m: tuple[float, ...]
    mole_fractions: tuple[float, ...]
    evidence_reference: str

    def __post_init__(self) -> None:
        if (
            not self.tile_id
            or not self.species
            or not self.evidence_reference
            or len(self.heights_m) < 2
            or len(self.heights_m) != len(self.mole_fractions)
        ):
            raise ValueError("Cal perfil gasós explícit per espècie i tile")
        if (
            any(not math.isfinite(x) for x in (*self.heights_m, *self.mole_fractions))
            or any(b <= a for a, b in zip(self.heights_m, self.heights_m[1:]))
            or any(not 0 <= x <= 1 for x in self.mole_fractions)
        ):
            raise ValueError("Perfil de fracció molar invàlid")

    def fraction(self, height_m: float) -> float:
        if not self.heights_m[0] <= height_m <= self.heights_m[-1]:
            raise ValueError("Perfil gasós sense cobertura vertical")
        return float(np.interp(height_m, self.heights_m, self.mole_fractions))


@dataclass(frozen=True, slots=True)
class GasAbsorptionModel:
    revision: str
    composition_description: str
    luts: tuple[GasCrossSectionLut, ...]
    profiles: tuple[GasMixingProfile, ...]

    def __post_init__(self) -> None:
        if (
            not self.revision
            or not self.composition_description
            or not self.luts
            or len({g.species for g in self.luts}) != len(self.luts)
        ):
            raise ValueError("Cal composició prescrita i LUTs úniques")
        keys = {(p.tile_id, p.species) for p in self.profiles}
        if len(keys) != len(self.profiles) or {p.species for p in self.profiles} != {
            g.species for g in self.luts
        }:
            raise ValueError("Espècie gasosa desconeguda o duplicada")

    @property
    def signature(self) -> str:
        return fingerprint(asdict(self))

    def profile(self, tile_id: str, species: str) -> GasMixingProfile:
        for profile in self.profiles:
            if (profile.tile_id, profile.species) == (tile_id, species):
                return profile
        raise ValueError("Absorció gasosa desconeguda: falta perfil del tile")


def effective_band_transmission(
    spectral_weights: np.ndarray, optical_depth: np.ndarray
) -> np.ndarray:
    """T_eff per interval; arrays (intervals, nodes), sense exp(-mitjana τ)."""
    if (
        spectral_weights.shape != optical_depth.shape
        or np.any(~np.isfinite(spectral_weights))
        or np.any(spectral_weights < 0)
        or np.any(~np.isfinite(optical_depth))
        or np.any(optical_depth < 0)
    ):
        raise ValueError("Pesos o profunditats òptiques invàlids")
    denominator = spectral_weights.sum(axis=1)
    # Una banda sense emissió no té T_eff definit; no es transforma en u.
    return np.divide(
        (spectral_weights * np.exp(-optical_depth)).sum(axis=1),
        denominator,
        out=np.full_like(denominator, np.nan),
        where=denominator > 0,
    )
