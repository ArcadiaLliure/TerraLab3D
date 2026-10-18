"""Guard de revisions B0; cap cua, prefetch ni scheduler de cache."""

from __future__ import annotations

import threading
from dataclasses import replace
from typing import Callable

from terralab3d.domain.light_pollution.propagation_kernel import (
    GeometrySample,
    PropagationCancelledError,
    PropagationKernel,
    PropagationRequest,
    PropagationResult,
    StalePropagationError,
    unit_integrand,
)
from terralab3d.domain.light_pollution.source_model import SourceModel


class GeometricPropagationSession:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._revision = 0
        self._cancel = threading.Event()
        self._closed = False
        self._result: PropagationResult | None = None
        self.cancelled_jobs = 0
        self.stale_results_discarded = 0

    @property
    def result(self) -> PropagationResult | None:
        with self._lock:
            return self._result

    def begin(self, request: PropagationRequest) -> PropagationRequest:
        with self._lock:
            if self._closed:
                raise RuntimeError("Sessió geomètrica tancada")
            self._revision += 1
            self._cancel.set()
            self._cancel = threading.Event()
            self._result = None
            return replace(request, revision=self._revision)

    def cancel(self) -> None:
        with self._lock:
            self._cancel.set()
            self._result = None

    def close(self) -> None:
        with self._lock:
            self._closed = True
            self._revision += 1
            self._cancel.set()
            self._result = None

    def compute(
        self,
        request: PropagationRequest,
        integrand: Callable[[GeometrySample, SourceModel], float] = unit_integrand,
        *,
        integrand_id: str = "unit-v1",
        integral_unit: str = "m",
    ) -> PropagationResult:
        with self._lock:
            token = self._cancel

        def is_current() -> bool:
            with self._lock:
                return not self._closed and self._revision == request.revision

        try:
            result = PropagationKernel().evaluate(
                request,
                integrand,
                integrand_id=integrand_id,
                integral_unit=integral_unit,
                cancelled=token.is_set,
                is_current=is_current,
            )
            with self._lock:
                if self._closed or self._revision != request.revision:
                    raise StalePropagationError("Resultat obsolet abans de publicar-lo")
                if token.is_set():
                    raise PropagationCancelledError(
                        "Resultat cancel·lat abans de publicar-lo"
                    )
                self._result = result
            return result
        except StalePropagationError:
            with self._lock:
                self.stale_results_discarded += 1
            raise
        except PropagationCancelledError:
            with self._lock:
                self.cancelled_jobs += 1
            raise
