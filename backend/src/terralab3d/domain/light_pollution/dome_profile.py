"""Reconstrucció angular explícita; cap extrapolació ni llum inventada als zeros."""

from __future__ import annotations

import math
from bisect import bisect_right
from dataclasses import dataclass


def pchip_slopes(x: tuple[float, ...], y: tuple[float, ...]) -> tuple[float, ...]:
    """Derivades PCHIP: mitjana harmònica ponderada i extrems limitats."""
    if (
        len(x) != len(y)
        or len(x) < 2
        or any(not math.isfinite(v) for v in (*x, *y))
        or any(b <= a for a, b in zip(x, x[1:]))
    ):
        raise ValueError("PCHIP requereix nusos finits estrictament creixents")
    h = [b - a for a, b in zip(x, x[1:])]
    d = [(b - a) / s for a, b, s in zip(y, y[1:], h)]
    if len(x) == 2:
        return d[0], d[0]

    def edge(h0, h1, d0, d1):
        value = ((2 * h0 + h1) * d0 - h0 * d1) / (h0 + h1)
        if value == 0 or d0 == 0 or (value > 0) != (d0 > 0):
            return 0.0
        return 3 * d0 if (d0 > 0) != (d1 > 0) and abs(value) > 3 * abs(d0) else value

    slopes = [edge(h[0], h[1], d[0], d[1])]
    for i in range(1, len(x) - 1):
        if d[i - 1] == 0 or d[i] == 0 or (d[i - 1] > 0) != (d[i] > 0):
            slopes.append(0.0)
        else:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            slopes.append((w1 + w2) / (w1 / d[i - 1] + w2 / d[i]))
    slopes.append(edge(h[-1], h[-2], d[-1], d[-2]))
    return tuple(slopes)


def pchip_value(x: tuple[float, ...], y: tuple[float, ...], query: float) -> float:
    slopes = pchip_slopes(x, y)
    if not math.isfinite(query) or not x[0] <= query <= x[-1]:
        raise ValueError("PCHIP no extrapola")
    i = min(bisect_right(x, query) - 1, len(x) - 2)
    h = x[i + 1] - x[i]
    t = (query - x[i]) / h
    return (
        (2 * t**3 - 3 * t**2 + 1) * y[i]
        + (t**3 - 2 * t**2 + t) * h * slopes[i]
        + (-2 * t**3 + 3 * t**2) * y[i + 1]
        + (t**3 - t**2) * h * slopes[i + 1]
    )


@dataclass(frozen=True, slots=True)
class DomeProfile:
    azimuth_deg: float
    elevations_deg: tuple[float, ...]
    radiances: tuple[float, ...]
    epsilon_radiance: float
    # Barrera entre nusos: l'usuari ha de recórrer al transport directe.
    blocked_intervals: tuple[bool, ...] = ()

    def __post_init__(self) -> None:
        pchip_slopes(self.elevations_deg, self.radiances)
        if (
            not math.isfinite(self.azimuth_deg)
            or not 0.5 <= self.elevations_deg[0] < self.elevations_deg[-1] <= 90
            or any(v < 0 for v in self.radiances)
            or not math.isfinite(self.epsilon_radiance)
            or self.epsilon_radiance <= 0
            or (
                self.blocked_intervals
                and (
                    len(self.blocked_intervals) != len(self.radiances) - 1
                    or any(type(v) is not bool for v in self.blocked_intervals)
                )
            )
        ):
            raise ValueError("DomeProfile invàlid")
        positives = [v for v in self.radiances if v > 0]
        if positives and self.epsilon_radiance > min(positives) * 1e-12:
            raise ValueError(
                "Èpsilon logarítmic massa gran respecte del senyal mostrejat"
            )

    def evaluate(self, elevation_deg: float) -> float | None:
        """None exigeix ruta directa; no és zero ni una transparència parcial."""
        x, b = self.elevations_deg, self.radiances
        if not math.isfinite(elevation_deg) or not x[0] <= elevation_deg <= x[-1]:
            raise ValueError("Elevació fora del perfil")
        if elevation_deg in x:
            return b[x.index(elevation_deg)]
        i = bisect_right(x, elevation_deg) - 1

        def usable(k):
            return (
                b[k] > 0
                and b[k + 1] > 0
                and not (self.blocked_intervals and self.blocked_intervals[k])
            )

        if not usable(i):
            return None
        lo, hi = i, i + 1
        while lo > 0 and usable(lo - 1):
            lo -= 1
        while hi < len(b) - 1 and usable(hi):
            hi += 1
        # Cada tram positiu queda desacoblat dels zeros i barreres veïns.
        y = tuple(math.log(v + self.epsilon_radiance) for v in b[lo : hi + 1])
        value = (
            math.exp(pchip_value(x[lo : hi + 1], y, elevation_deg))
            - self.epsilon_radiance
        )
        return max(0.0, value)  # Només protegeix arrodoniment exp/log.


@dataclass(frozen=True, slots=True)
class DomeField:
    profiles: tuple[DomeProfile, ...]
    radiance_unit: str
    provenance: str
    revision: int
    top_m: float
    # Amb DEM no s'infereix continuïtat angular de visibilitat entre raigs.
    direct_only: bool = False

    def __post_init__(self) -> None:
        az = [p.azimuth_deg for p in self.profiles]
        if (
            len(az) < 2
            or not 0 <= az[0] < az[-1] < 360
            or any(b <= a for a, b in zip(az, az[1:]))
            or any(
                p.elevations_deg != self.profiles[0].elevations_deg
                for p in self.profiles
            )
            or not self.radiance_unit
            or not self.provenance
            or type(self.revision) is not int
            or self.revision < 0
            or not math.isfinite(self.top_m)
            or self.top_m <= 0
        ):
            raise ValueError("Camp angular sense geometria/unitats/procedència vàlides")

    def evaluate(self, azimuth_deg: float, elevation_deg: float) -> float | None:
        x = self.profiles[0].elevations_deg
        if (
            not math.isfinite(azimuth_deg)
            or not math.isfinite(elevation_deg)
            or not x[0] <= elevation_deg <= x[-1]
        ):
            raise ValueError("Direcció fora del camp angular")
        azimuth_deg %= 360
        az = [p.azimuth_deg for p in self.profiles]
        if azimuth_deg in az:
            p = self.profiles[az.index(azimuth_deg)]
            if self.direct_only and elevation_deg not in p.elevations_deg:
                return None
            return p.evaluate(elevation_deg)
        if self.direct_only:
            return None
        # Interpolació periòdica lineal en radiància; no s'inventen amplades de font.
        i = (bisect_right(az, azimuth_deg) - 1) % len(az)
        j = (i + 1) % len(az)
        a, c = (
            self.profiles[i].evaluate(elevation_deg),
            self.profiles[j].evaluate(elevation_deg),
        )
        if a is None or c is None or a <= 0 or c <= 0:
            return None
        weight = ((azimuth_deg - az[i]) % 360) / ((az[j] - az[i]) % 360)
        return (1 - weight) * a + weight * c

    def to_dict(self) -> dict[str, object]:
        return dict(
            schemaVersion=1,
            interpolation="PCHIP_LOG",
            azimuthInterpolation="PERIODIC_LINEAR_RADIANCE",
            radianceUnit=self.radiance_unit,
            provenance=self.provenance,
            revision=self.revision,
            topM=self.top_m,
            directOnly=self.direct_only,
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
