"""Mesures exclusives opcionals; cap dada de temps participa en identitats."""

from __future__ import annotations

from contextlib import contextmanager
from time import perf_counter_ns
from typing import Iterator


class TransportProfiler:
    def __init__(self) -> None:
        self.nanoseconds = dict.fromkeys(
            (
                "geometry",
                "occlusion",
                "atmospheric_sampling",
                "transmissions",
                "quadrature",
                "spectral_integration",
            ),
            0,
        )
        self.calls = dict.fromkeys(self.nanoseconds, 0)
        self._stack: list[list[int]] = []

    @contextmanager
    def measure(self, stage: str) -> Iterator[None]:
        if stage not in self.nanoseconds:
            raise ValueError("Etapa de mesura desconeguda")
        frame = [perf_counter_ns(), 0]
        self._stack.append(frame)
        try:
            yield
        finally:
            elapsed = perf_counter_ns() - frame[0]
            self._stack.pop()
            self.nanoseconds[stage] += elapsed - frame[1]
            self.calls[stage] += 1
            if self._stack:
                self._stack[-1][1] += elapsed

    def to_dict(self) -> dict[str, object]:
        return {
            "exclusiveMs": {k: v / 1e6 for k, v in self.nanoseconds.items()},
            "calls": dict(self.calls),
        }
