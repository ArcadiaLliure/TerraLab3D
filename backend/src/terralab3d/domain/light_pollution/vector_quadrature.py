"""GK7/15 vectorial directe: comparteix nodes i subdivisió entre components."""

from __future__ import annotations

import heapq
from dataclasses import dataclass
from typing import Callable

import numpy as np

from .gauss_kronrod import _G, _K, _X, QuadratureConvergenceError, QuadratureSettings


@dataclass(frozen=True, slots=True)
class VectorQuadratureResult:
    value: np.ndarray
    estimated_error: np.ndarray
    evaluations: int


def integrate_vector_gk15(
    function: Callable[[float], np.ndarray],
    left: float,
    right: float,
    settings: QuadratureSettings,
    checkpoint: Callable[[], None],
) -> VectorQuadratureResult:
    if not np.isfinite(left + right) or not left < right:
        raise ValueError("Interval vectorial invàlid")
    evaluations = 0

    def sample(x: float) -> np.ndarray:
        nonlocal evaluations
        checkpoint()
        y = function(x)
        evaluations += 1
        if y.ndim != 1 or not np.all(np.isfinite(y)):
            raise QuadratureConvergenceError("Integrand vectorial no finit")
        return y

    def panel(a: float, b: float) -> tuple[np.ndarray, np.ndarray]:
        m, h = (a + b) / 2, (b - a) / 2
        c = sample(m)
        k, g, absolute = _K[7] * c, _G[3] * c, _K[7] * np.abs(c)
        for i in range(7):
            lo, hi = sample(m - h * _X[i]), sample(m + h * _X[i])
            k += _K[i] * (lo + hi)
            absolute += _K[i] * (np.abs(lo) + np.abs(hi))
            if i % 2:
                g += _G[i // 2] * (lo + hi)
        return h * k, np.maximum(
            h * np.abs(k - g), 50 * np.finfo(float).eps * h * absolute
        )

    # La cua ordena per error relatiu local; la sortida comprova totes les
    # components amb el mateix criteri global, inclosos els zeros exactes.
    heap: list[tuple[float, int, float, float, np.ndarray, np.ndarray]] = []
    serial = 0

    def push(a: float, b: float) -> None:
        nonlocal serial
        v, e = panel(a, b)
        priority = float(
            np.max(
                e
                / (
                    settings.absolute_tolerance
                    + settings.relative_tolerance * np.abs(v)
                )
            )
        )
        heapq.heappush(heap, (-priority, serial, a, b, v, e))
        serial += 1

    push(left, right)
    while True:
        v = np.sum([item[4] for item in heap], axis=0)
        e = np.sum([item[5] for item in heap], axis=0)
        if np.all(
            e <= settings.absolute_tolerance + settings.relative_tolerance * np.abs(v)
        ):
            return VectorQuadratureResult(v, e, evaluations)
        if len(heap) >= settings.max_intervals:
            raise QuadratureConvergenceError("GK vectorial sense convergència")
        _, _, a, b, _, _ = heapq.heappop(heap)
        middle = (a + b) / 2
        if middle in (a, b):
            raise QuadratureConvergenceError("Resolució flotant vectorial esgotada")
        push(a, middle)
        push(middle, b)
