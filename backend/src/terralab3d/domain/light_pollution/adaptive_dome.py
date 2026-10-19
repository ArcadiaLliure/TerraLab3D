"""Mostreig angular adaptatiu v2; el transport és una dependència explícita."""

from __future__ import annotations

import math
from bisect import bisect_right
from dataclasses import dataclass
from typing import Callable

from .dome_profile import DomeProfile, pchip_value

ADAPTIVE_REVISION = "adaptive-pchip-log-az-el-v2"
INITIAL_ELEVATIONS = (0.5, 2.0, 5.0, 10.0, 20.0, 30.0, 45.0, 60.0, 90.0)
AZIMUTH_TEST_ELEVATIONS = (
    0.5,
    0.75,
    1.0,
    1.5,
    2.0,
    3.5,
    5.0,
    7.5,
    10.0,
    15.0,
    20.0,
    25.0,
    30.0,
    37.5,
    45.0,
    52.5,
    60.0,
    75.0,
    90.0,
)


class AngularBudgetExceededError(RuntimeError):
    """No es publica una reconstrucció sense completar-ne el refinament."""


def magnitude_error(candidate: float | None, direct: float) -> float:
    if candidate is None:
        return math.inf
    if direct == 0:
        return 0.0 if candidate == 0 else math.inf
    return abs(2.5 * math.log10(candidate / direct)) if candidate > 0 else math.inf


@dataclass(frozen=True, slots=True)
class AdaptiveSettings:
    internal_magnitude_maximum: float = 0.002
    maximum_samples: int = 8000
    maximum_azimuth_profiles: int = 128
    maximum_vertical_iterations: int = 12
    maximum_azimuth_iterations: int = 10

    def __post_init__(self) -> None:
        if (
            not math.isfinite(self.internal_magnitude_maximum)
            or self.internal_magnitude_maximum <= 0
            or any(
                type(v) is not int or v < 1
                for v in (
                    self.maximum_samples,
                    self.maximum_azimuth_profiles,
                    self.maximum_vertical_iterations,
                    self.maximum_azimuth_iterations,
                )
            )
            or self.maximum_azimuth_profiles < 8
        ):
            raise ValueError("Pressupost angular invàlid")


@dataclass(frozen=True, slots=True)
class AdaptiveDomeField:
    profiles: tuple[DomeProfile, ...]
    radiance_unit: str
    provenance: str
    revision: int
    top_m: float
    blocked_azimuth_intervals: tuple[bool, ...] = ()
    direct_only: bool = False

    def __post_init__(self) -> None:
        az = [p.azimuth_deg for p in self.profiles]
        if (
            len(az) < 4
            or any(not 0 <= a < 360 for a in az)
            or any(b <= a for a, b in zip(az, az[1:]))
            or any(
                (p.elevations_deg[0], p.elevations_deg[-1]) != (0.5, 90.0)
                for p in self.profiles
            )
            or not self.radiance_unit
            or not self.provenance
            or type(self.revision) is not int
            or self.revision < 0
            or not math.isfinite(self.top_m)
            or self.top_m <= 0
            or (
                self.blocked_azimuth_intervals
                and (
                    len(self.blocked_azimuth_intervals) != len(az)
                    or any(type(v) is not bool for v in self.blocked_azimuth_intervals)
                )
            )
        ):
            raise ValueError("Camp adaptatiu invàlid")
        zenith = [p.radiances[-1] for p in self.profiles]
        if max(zenith) - min(zenith) > 1e-12 * max(zenith):
            raise ValueError("El zenit no és coherent entre perfils")

    def evaluate(self, azimuth_deg: float, elevation_deg: float) -> float | None:
        if (
            not math.isfinite(azimuth_deg)
            or not math.isfinite(elevation_deg)
            or not 0.5 <= elevation_deg <= 90
        ):
            raise ValueError("Direcció fora del domini adaptatiu")
        q = azimuth_deg % 360
        az = tuple(p.azimuth_deg for p in self.profiles)
        if q in az:
            p = self.profiles[az.index(q)]
            if self.direct_only and elevation_deg not in p.elevations_deg:
                return None
            return p.evaluate(elevation_deg)
        if self.direct_only:
            return None
        i, n = bisect_right(az, q) - 1, len(az)
        if self.blocked_azimuth_intervals and self.blocked_azimuth_intervals[i % n]:
            return None
        indices = tuple(range(i - 1, i + 3))
        values = tuple(self.profiles[k % n].evaluate(elevation_deg) for k in indices)
        if any(v is None or v <= 0 for v in values):
            return None
        positive = tuple(float(v) for v in values if v is not None)
        epsilon = min(positive) * 1e-15
        x = tuple(az[k % n] + 360 * (k // n) for k in indices)
        logs = tuple(math.log(v + epsilon) for v in positive)
        return max(0.0, math.exp(pchip_value(x, logs, q)) - epsilon)

    def to_dict(self) -> dict[str, object]:
        return dict(
            schemaVersion=2,
            strategy=ADAPTIVE_REVISION,
            interpolation="PCHIP_LOG",
            azimuthInterpolation="PERIODIC_PCHIP_LOG",
            radianceUnit=self.radiance_unit,
            provenance=self.provenance,
            revision=self.revision,
            topM=self.top_m,
            directOnly=self.direct_only,
            blockedAzimuthIntervals=self.blocked_azimuth_intervals,
            profiles=[
                dict(
                    azimuthDeg=p.azimuth_deg,
                    elevationSamplesDeg=p.elevations_deg,
                    radianceSamples=p.radiances,
                    epsilonRadiance=p.epsilon_radiance,
                    blockedIntervals=p.blocked_intervals,
                )
                for p in self.profiles
            ],
        )


@dataclass(frozen=True, slots=True)
class AdaptiveSamplingResult:
    field: AdaptiveDomeField
    samples: tuple[tuple[float, float, float], ...]
    maximum_vertical_probe_error_mag: float
    maximum_azimuth_probe_error_mag: float
    azimuth_iterations: int


def build_adaptive_dome(
    sample: Callable[[float, float], float],
    *,
    radiance_unit: str,
    provenance: str,
    revision: int,
    top_m: float,
    settings: AdaptiveSettings = AdaptiveSettings(),
    checkpoint: Callable[[int, float, float], None] | None = None,
) -> AdaptiveSamplingResult:
    # Registre de nodes locals d'una sola construcció; no persisteix entre peticions.
    ledger: dict[tuple[float, float], float] = {}
    vertical_checks: dict[float, float] = {}
    candidates: dict[float, DomeProfile] = {}

    def direct(a: float, e: float) -> float:
        a %= 360
        key = a, e
        if key not in ledger:
            if len(ledger) >= settings.maximum_samples:
                raise AngularBudgetExceededError("Límit de mostres angulars exhaurit")
            value = sample(a, e)
            if not math.isfinite(value) or value < 0:
                raise ValueError("El transport ha retornat radiància invàlida")
            ledger[key] = value
            if checkpoint is not None:
                checkpoint(len(ledger), a, e)
        return ledger[key]

    def profile(a: float) -> DomeProfile:
        a %= 360
        if a in candidates:
            return candidates[a]
        knots = set(INITIAL_ELEVATIONS)
        for _ in range(settings.maximum_vertical_iterations):
            x = tuple(sorted(knots))
            b = tuple(direct(a, e) for e in x)
            positives = [v for v in b if v > 0]
            p = DomeProfile(a, x, b, min(positives) * 1e-15 if positives else 1e-300)
            additions = set()
            worst = 0.0
            for lo, hi in zip(x, x[1:]):
                # No es prova continuïtat travessant un zero conegut.
                if direct(a, lo) == 0 or direct(a, hi) == 0:
                    raise ValueError(
                        "Un zero requereix domini segmentat o transport directe"
                    )
                for fraction in (0.25, 0.5, 0.75):
                    e = lo + fraction * (hi - lo)
                    err = magnitude_error(p.evaluate(e), direct(a, e))
                    worst = max(worst, err)
                    if err > settings.internal_magnitude_maximum:
                        additions.add((lo + hi) / 2)
            if not additions:
                candidates[a] = p
                vertical_checks[a] = worst
                return p
            knots.update(additions)
        raise AngularBudgetExceededError("No convergeix el refinament vertical")

    profiles = {float(a): profile(float(a)) for a in range(0, 360, 45)}
    for iteration in range(settings.maximum_azimuth_iterations):
        az = tuple(sorted(profiles))
        field = AdaptiveDomeField(
            tuple(profiles[a] for a in az), radiance_unit, provenance, revision, top_m
        )
        additions: dict[float, DomeProfile] = {}
        worst = 0.0
        for i, lo in enumerate(az):
            hi = az[(i + 1) % len(az)] + (360 if i == len(az) - 1 else 0)
            middle = ((lo + hi) / 2) % 360
            mid_profile = profile(middle)
            failed = False
            for fraction in (0.25, 0.5, 0.75):
                a = (lo + fraction * (hi - lo)) % 360
                for e in AZIMUTH_TEST_ELEVATIONS:
                    err = magnitude_error(field.evaluate(a, e), direct(a, e))
                    worst = max(worst, err)
                    if err > settings.internal_magnitude_maximum:
                        failed = True
            if failed:
                additions[middle] = mid_profile
        if not additions:
            return AdaptiveSamplingResult(
                field,
                tuple((a, e, v) for (a, e), v in ledger.items()),
                max(vertical_checks.values()),
                worst,
                iteration + 1,
            )
        if len(profiles) + len(additions) > settings.maximum_azimuth_profiles:
            raise AngularBudgetExceededError("Límit de perfils azimutals exhaurit")
        profiles.update(additions)
    raise AngularBudgetExceededError("No convergeix el refinament azimutal")
