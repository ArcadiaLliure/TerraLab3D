"""Colorimetria i família LED tabulada; mai es fabrica una SPD de cos negre."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import numpy as np

from .source_model import DefinedSpectrum, mix_defined_spectra


def weighted_integral(
    spectrum: DefinedSpectrum, wavelengths: tuple[float, ...], values: tuple[float, ...]
) -> float:
    """Integral exacta del producte de dues taules lineals al suport de l'SPD."""
    lo, hi = spectrum.wavelengths_nm[0], spectrum.wavelengths_nm[-1]
    knots = np.array(
        sorted(
            {lo, hi}
            | {x for x in (*wavelengths, *spectrum.wavelengths_nm) if lo < x < hi}
        )
    )
    s = (
        np.interp(knots, spectrum.wavelengths_nm, spectrum.relative_power)
        / spectrum.raw_integral_nm
    )
    # Límits interns a cada interval: zero fora del suport no crea rampes.
    midpoint = (knots[:-1] + knots[1:]) / 2
    inside = (midpoint >= wavelengths[0]) & (midpoint <= wavelengths[-1])
    c = np.where(inside, np.interp(knots[:-1], wavelengths, values), 0.0)
    d = np.where(inside, np.interp(knots[1:], wavelengths, values), 0.0)
    a, b = s[:-1], s[1:]
    return float(np.sum(np.diff(knots) * (2 * a * c + a * d + b * c + 2 * b * d) / 6))


@dataclass(frozen=True, slots=True)
class Chromaticity:
    cct_k: float
    distance_uv: float
    method: str = "nearest_planckian_CIE1960uv_CIE1931_2deg"


@dataclass(frozen=True, slots=True)
class SpectralLibrary:
    revision: str
    spectra: dict[str, DefinedSpectrum]
    technologies: dict[str, str]
    cmf_wavelengths: tuple[float, ...]
    cmf_xyz: tuple[tuple[float, ...], ...]
    photopic_wavelengths: tuple[float, ...]
    photopic_values: tuple[float, ...]

    def efficacy(self, spectrum: DefinedSpectrum) -> float:
        """lm/W dins el suport publicat; no pressuposa emissions fora de taula."""
        return 683 * weighted_integral(
            spectrum, self.photopic_wavelengths, self.photopic_values
        )

    def describe(self, spectrum_id: str) -> dict[str, object]:
        spectrum = self.spectra[spectrum_id]
        color = self.colorimetry(spectrum)
        return {
            "spectrum": asdict(spectrum),
            "technology": self.technologies[spectrum_id],
            "revision": self.revision,
            "relativePowerUnit": "dimensionless",
            "wavelengthUnit": "nm",
            "validDomainNm": [spectrum.wavelengths_nm[0], spectrum.wavelengths_nm[-1]],
            "cctK": color.cct_k if color.distance_uv <= 0.02 else None,
            "cctMethod": color.method,
            "distanceUv": color.distance_uv,
            "cctIsCalculatedNotManufacturerSpecification": True,
        }

    def meaningful_cct(
        self, spectrum: DefinedSpectrum, technology: str
    ) -> float | None:
        """El punt més proper al locus no fa significativa la CCT del sodi LPS."""
        if technology == "low_pressure_sodium":
            return None
        color = self.colorimetry(spectrum)
        return color.cct_k if color.distance_uv <= 0.02 else None

    def colorimetry(self, spectrum: DefinedSpectrum) -> Chromaticity:
        xyz = [
            weighted_integral(spectrum, self.cmf_wavelengths, c) for c in self.cmf_xyz
        ]
        denom = xyz[0] + 15 * xyz[1] + 3 * xyz[2]
        if denom <= 0:
            raise ValueError("L'espectre no té cromaticitat visible")
        uv = np.array([4 * xyz[0] / denom, 6 * xyz[1] / denom])
        waves = np.array(self.cmf_wavelengths)
        cmfs = np.array(self.cmf_xyz)

        def distance(k: float) -> float:
            # Llei de Planck només per al locus colorimètric de referència.
            planck = waves**-5 / np.expm1(1.438776877e7 / (waves * k))
            pxyz = [float(np.trapezoid(cmf * planck, waves)) for cmf in cmfs]
            den = pxyz[0] + 15 * pxyz[1] + 3 * pxyz[2]
            puv = np.array([4 * pxyz[0] / den, 6 * pxyz[1] / den])
            return float(np.sum((puv - uv) ** 2))

        left, right = 1000.0, 25000.0
        ratio = (math.sqrt(5) - 1) / 2
        for _ in range(64):
            a, b = right - ratio * (right - left), left + ratio * (right - left)
            if distance(a) < distance(b):
                right = b
            else:
                left = a
        k = (left + right) / 2
        return Chromaticity(k, math.sqrt(distance(k)))

    def kelvin_spectrum(
        self, kelvin: float, family: str = "CIE_LED_B1_B5"
    ) -> DefinedSpectrum:
        if (
            family != "CIE_LED_B1_B5"
            or not math.isfinite(kelvin)
            or not 2800 <= kelvin <= 6500
        ):
            raise ValueError("La família LED CIE admet 2.800–6.500 K; no s'extrapola")
        members = [
            (
                self.spectra[f"LED-B{i}"],
                self.colorimetry(self.spectra[f"LED-B{i}"]).cct_k,
            )
            for i in range(1, 6)
        ]
        for (first, low), (second, high) in zip(members, members[1:]):
            if low <= kelvin <= high:
                left, right = 0.0, 1.0
                for _ in range(30):
                    weight = (left + right) / 2
                    mixture = mix_defined_spectra(
                        f"{family}:{kelvin:g}K:{self.revision}",
                        ((first, 1 - weight), (second, weight)),
                        "Interpolació radiant convexa entre LED de fòsfor CIE; CCT resolta en CIE 1960 uv",
                    )
                    result = self.colorimetry(mixture)
                    if abs(result.cct_k - kelvin) < 0.1:
                        if result.distance_uv > 0.02:
                            raise ValueError(
                                "Interpolació massa lluny del locus de Planck"
                            )
                        return mixture
                    if result.cct_k < kelvin:
                        left = weight
                    else:
                        right = weight
                raise ValueError("La CCT interpolada no convergeix")
        raise ValueError("La temperatura supera les SPD verificades")

    def mix(
        self, name: str, weights: tuple[tuple[str, float], ...], basis: str
    ) -> DefinedSpectrum:
        if basis not in {"radiant_flux", "photopic_flux"}:
            raise ValueError("Els pesos han de ser fraccions de flux radiant o fotòpic")
        if not weights or any(not math.isfinite(w) or w < 0 for _, w in weights):
            raise ValueError("Pesos de mescla invàlids")
        if not math.isclose(math.fsum(w for _, w in weights), 1, abs_tol=1e-9):
            raise ValueError("Les fraccions han de sumar u")
        components = tuple(
            (
                self.spectra[key],
                weight
                if basis == "radiant_flux"
                else weight / self.efficacy(self.spectra[key]),
            )
            for key, weight in weights
        )
        return mix_defined_spectra(
            name,
            components,
            f"Escenari explícit; pesos {basis}: {weights!r}; {self.revision}",
        )
