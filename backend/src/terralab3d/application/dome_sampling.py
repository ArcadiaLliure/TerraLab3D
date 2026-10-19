"""Mostreig directe offline; el kernel conserva l'autoritat física i la cancel·lació."""

import math
from dataclasses import replace
from typing import Callable

from terralab3d.domain.light_pollution.dome_profile import DomeField, DomeProfile
from terralab3d.domain.light_pollution.geometric_transport import ViewDirection
from terralab3d.domain.light_pollution.propagation_kernel import (
    DirectionSet,
    PropagationKernel,
    PropagationRequest,
)

INITIAL_ELEVATIONS_DEG = (0.5, 2.0, 5.0, 10.0, 20.0, 30.0, 45.0, 60.0, 90.0)


def sample_dome(
    request: PropagationRequest,
    azimuths_deg: tuple[float, ...],
    *,
    elevations_deg: tuple[float, ...] = INITIAL_ELEVATIONS_DEG,
    cancelled: Callable[[], bool] | None = None,
    is_current: Callable[[], bool] | None = None,
) -> DomeField:
    if request.scattering is None and request.spectral is None:
        raise ValueError("B0 no és un camp de radiància")
    az = tuple(sorted(a % 360 for a in azimuths_deg))
    if len(az) < 2 or len(set(az)) != len(az) or any(not math.isfinite(a) for a in az):
        raise ValueError("Calen almenys dos azimuts finits diferents")
    # Valida abans del primer càlcul costós.
    DomeProfile(az[0], elevations_deg, tuple(1.0 for _ in elevations_deg), 1e-15)
    directions = tuple(
        ViewDirection(f"dome-{i}-{j}", a, e)
        for i, a in enumerate(az)
        for j, e in enumerate(elevations_deg)
    )
    result = PropagationKernel().evaluate(
        replace(request, directions=DirectionSet(directions)),
        cancelled=cancelled,
        is_current=is_current,
    )
    grouped: dict[str, list[float]] = {}
    for ray in result.rays:
        grouped.setdefault(ray.direction_id, []).append(ray.integral)
    profiles = []
    for i, a in enumerate(az):
        # Suma lineal de totes les fonts abans de logaritmes.
        values = tuple(
            math.fsum(grouped[f"dome-{i}-{j}"]) for j in range(len(elevations_deg))
        )
        positive = [v for v in values if v > 0]
        epsilon = min(positive) * 1e-15 if positive else 1e-300
        if epsilon == 0:
            raise ValueError("Radiància subnormal incompatible amb PCHIP_LOG")
        profiles.append(DomeProfile(a, elevations_deg, values, epsilon))
    return DomeField(
        tuple(profiles),
        result.integral_unit,
        f"inputSignature={result.input_signature}; fonts="
        + ",".join(s.source_model_id for s in request.sources),
        request.revision,
        request.options.top_m,
        request.terrain is not None,
    )
