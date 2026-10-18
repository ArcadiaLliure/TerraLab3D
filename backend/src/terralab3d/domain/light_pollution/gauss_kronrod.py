"""GK7/15 escalar propi; coeficients matemàtics contrastats amb Netlib DQK15.

No s'importa el codi Fortran ni SciPy. L'error és estimat, no una cota
rigorosa; discontinuïtats conegudes s'han de passar com a segments.
"""

from __future__ import annotations

import heapq
import math
import sys
from dataclasses import dataclass
from typing import Callable

# Nodes positius i centre de Kronrod; Gauss usa índexs 1,3,5 i el centre.
_X = (
    0.9914553711208126392,
    0.9491079123427585245,
    0.8648644233597690728,
    0.7415311855993944399,
    0.5860872354676911303,
    0.4058451513773971669,
    0.2077849550078984676,
    0.0,
)
_K = (
    0.0229353220105292250,
    0.0630920926299785533,
    0.1047900103222501838,
    0.1406532597155259187,
    0.1690047266392679028,
    0.1903505780647854099,
    0.2044329400752988924,
    0.2094821410847278280,
)
_G = (
    0.1294849661688696933,
    0.2797053914892766679,
    0.3818300505051189450,
    0.4179591836734693878,
)


class QuadratureConvergenceError(ValueError):
    """Pressupost esgotat, integrand no finit o precisió no assolida."""


@dataclass(frozen=True, slots=True)
class QuadratureSettings:
    relative_tolerance: float = 1e-9
    absolute_tolerance: float = 1e-6
    max_intervals: int = 4096

    def __post_init__(self) -> None:
        if (
            any(
                not math.isfinite(x) or x <= 0
                for x in (self.relative_tolerance, self.absolute_tolerance)
            )
            or type(self.max_intervals) is not int
            or self.max_intervals < 1
        ):
            raise ValueError("Toleràncies o límit GK7/15 invàlids")


@dataclass(frozen=True, slots=True)
class QuadratureResult:
    value: float
    estimated_error: float
    evaluations: int
    subdivisions: int
    leaf_intervals: int


def integrate_gk15(
    function: Callable[[float], float],
    segments: tuple[tuple[float, float], ...],
    settings: QuadratureSettings = QuadratureSettings(),
    *,
    checkpoint: Callable[[], None] | None = None,
) -> QuadratureResult:
    if not segments or len(segments) > settings.max_intervals:
        raise ValueError("Cal partició no buida dins del límit d'intervals")
    if any(
        not math.isfinite(a) or not math.isfinite(b) or a >= b for a, b in segments
    ) or any(left[1] != right[0] for left, right in zip(segments, segments[1:])):
        raise ValueError("Segments GK no finits, discontinus, solapats o buits")
    evaluations = 0

    def panel(a: float, b: float) -> tuple[float, float]:
        nonlocal evaluations
        middle = a + (b - a) / 2
        half = (b - a) / 2

        def sample(x: float) -> float:
            nonlocal evaluations
            if checkpoint is not None:
                checkpoint()
            value = function(x)
            evaluations += 1
            if not math.isfinite(value):
                raise QuadratureConvergenceError("Integrand GK7/15 no finit")
            return value

        center = sample(middle)
        kronrod = [_K[7] * center]
        gauss = [_G[3] * center]
        absolute = [_K[7] * abs(center)]
        for i in range(7):
            left, right = sample(middle - half * _X[i]), sample(middle + half * _X[i])
            kronrod.append(_K[i] * (left + right))
            absolute.append(_K[i] * (abs(left) + abs(right)))
            if i % 2 == 1:
                gauss.append(_G[i // 2] * (left + right))
        k, g = half * math.fsum(kronrod), half * math.fsum(gauss)
        error = max(
            abs(k - g), 50 * sys.float_info.epsilon * half * math.fsum(absolute)
        )
        if not math.isfinite(k) or not math.isfinite(error):
            raise QuadratureConvergenceError("Integral GK7/15 no finita")
        return k, error

    heap: list[tuple[float, int, float, float, float]] = []
    serial = 0
    for a, b in segments:
        value, error = panel(a, b)
        heapq.heappush(heap, (-error, serial, a, b, value))
        serial += 1
    subdivisions = 0
    while True:
        value = math.fsum(item[4] for item in heap)
        error = math.fsum(-item[0] for item in heap)
        if error <= settings.absolute_tolerance + settings.relative_tolerance * abs(
            value
        ):
            return QuadratureResult(value, error, evaluations, subdivisions, len(heap))
        if len(heap) >= settings.max_intervals:
            raise QuadratureConvergenceError("GK7/15 no convergeix dins del pressupost")
        _, _, a, b, _ = heapq.heappop(heap)
        middle = a + (b - a) / 2
        if middle == a or middle == b:
            raise QuadratureConvergenceError(
                "GK7/15 arriba al límit de resolució flotant"
            )
        for lo, hi in ((a, middle), (middle, b)):
            estimate, err = panel(lo, hi)
            heapq.heappush(heap, (-err, serial, lo, hi, estimate))
            serial += 1
        subdivisions += 1
