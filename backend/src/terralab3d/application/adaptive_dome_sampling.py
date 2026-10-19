"""Cas d'ús adaptatiu serial, mateix kernel i precisions, sense caches de producte."""

from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import asdict, replace
from typing import Callable

from terralab3d.domain.light_pollution.adaptive_dome import (
    AdaptiveSamplingResult,
    AdaptiveSettings,
    AngularBudgetExceededError,
    build_adaptive_dome,
)
from terralab3d.domain.light_pollution.geometric_transport import ViewDirection
from terralab3d.domain.light_pollution.propagation_kernel import (
    DirectionSet,
    PropagationKernel,
    PropagationRequest,
)
from terralab3d.domain.light_pollution.source_model import PointSourceGeometry


def sample_adaptive_dome(
    request: PropagationRequest,
    *,
    settings: AdaptiveSettings = AdaptiveSettings(),
    maximum_wall_seconds: float = 1800.0,
    cancelled: Callable[[], bool] | None = None,
    is_current: Callable[[], bool] | None = None,
    checkpoint: Callable[[int, float, float], None] | None = None,
) -> AdaptiveSamplingResult:
    if request.scattering is None and request.spectral is None:
        raise ValueError("B0 no és radiància")
    if request.terrain is not None or any(
        not isinstance(s.geometry, PointSourceGeometry) for s in request.sources
    ):
        raise ValueError(
            "DEM i fonts extenses exigeixen ruta directa fins a acreditar el seu domini angular"
        )
    if not math.isfinite(maximum_wall_seconds) or maximum_wall_seconds <= 0:
        raise ValueError("Cal pressupost de temps positiu")
    signature = hashlib.sha256(
        json.dumps(
            asdict(request),
            sort_keys=True,
            default=lambda x: x.isoformat(),
            allow_nan=False,
        ).encode()
    ).hexdigest()
    unit = (
        request.sources[0].amplitude.unit
        + " m^-2 sr^-1"
        + (" nm^-1" if request.scattering else "")
    )
    start = time.perf_counter()

    def sample(az: float, el: float) -> float:
        if time.perf_counter() - start > maximum_wall_seconds:
            raise AngularBudgetExceededError("Pressupost temporal del camp exhaurit")
        req = replace(
            request,
            directions=DirectionSet((ViewDirection("adaptive-sample", az, el),)),
        )
        result = PropagationKernel().evaluate(
            req, cancelled=cancelled, is_current=is_current
        )
        assert result.integral_unit == unit
        return math.fsum(r.integral for r in result.rays)

    return build_adaptive_dome(
        sample,
        radiance_unit=unit,
        provenance="inputSignature=" + signature,
        revision=request.revision,
        top_m=request.options.top_m,
        settings=settings,
        checkpoint=checkpoint,
    )
