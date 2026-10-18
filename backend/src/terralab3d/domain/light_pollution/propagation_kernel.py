"""Frontera única de propagació: etapa geomètrica B0, encara sense radiància."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from typing import Callable, Literal

from .gauss_kronrod import QuadratureSettings, integrate_gk15
from .geometric_transport import (
    GeometricPartition,
    SphericalFrame,
    Vector3,
    ViewDirection,
    make_ray,
)
from .source_model import GeodeticPosition, PointSourceGeometry, SourceModel

MODEL_VERSION = "propagation-geometry-b0-v1"


class PropagationCancelledError(Exception):
    """Cancel·lació cooperativa, sense resultat parcial publicable."""


class StalePropagationError(Exception):
    """La revisió ja no és vigent; es descarta el resultat."""


@dataclass(frozen=True, slots=True)
class DirectionSet:
    directions: tuple[ViewDirection, ...]
    azimuth_mode: Literal["absolute", "source_bearing"] = "absolute"

    def __post_init__(self) -> None:
        if (
            not self.directions
            or len({d.direction_id for d in self.directions}) != len(self.directions)
            or self.azimuth_mode not in {"absolute", "source_bearing"}
        ):
            raise ValueError(
                "DirectionSet buit, amb identificadors duplicats o modalitat invàlida"
            )


@dataclass(frozen=True, slots=True)
class PropagationOptions:
    top_m: float = 10000.0
    earth_radius_m: float = 6371008.8
    partition: GeometricPartition = GeometricPartition()
    quadrature: QuadratureSettings = QuadratureSettings()
    max_segments_per_ray: int = 4096
    model_version: str = MODEL_VERSION

    def __post_init__(self) -> None:
        if (
            any(
                not math.isfinite(x) or x <= 0
                for x in (self.top_m, self.earth_radius_m)
            )
            or type(self.max_segments_per_ray) is not int
            or self.max_segments_per_ray < 1
            or self.model_version != MODEL_VERSION
        ):
            raise ValueError("Opcions geomètriques o versió B0 incompatibles")


@dataclass(frozen=True, slots=True)
class PropagationRequest:
    sources: tuple[SourceModel, ...]
    observer: GeodeticPosition
    directions: DirectionSet
    options: PropagationOptions = PropagationOptions()
    revision: int = 0

    def __post_init__(self) -> None:
        if (
            not self.sources
            or len({s.source_model_id for s in self.sources}) != len(self.sources)
            or type(self.revision) is not int
            or self.revision < 0
        ):
            raise ValueError("Fonts buides/duplicades o revisió invàlida")
        if not 0 <= self.observer.altitude_m < self.options.top_m:
            raise ValueError("Observador fora del domini geomètric B0")


@dataclass(frozen=True, slots=True)
class GeometrySample:
    distance_observer_m: float
    position_ecef_m: Vector3
    source_anchor_distance_m: float


def unit_integrand(sample: GeometrySample, source: SourceModel) -> float:
    """Funció de diagnòstic 1: ∫1 ds retorna metres, no radiància."""
    return 1.0


@dataclass(frozen=True, slots=True)
class KernelCounters:
    los_count: int
    segment_count: int
    quadrature_node_count: int
    gk_subdivision_count: int
    leaf_interval_count: int


@dataclass(frozen=True, slots=True)
class GeometricRayResult:
    source_id: str
    direction_id: str
    azimuth_deg: float
    elevation_deg: float
    path_length_m: float
    integral: float
    estimated_error: float
    geometric_cells: tuple[tuple[int, int, int], ...]
    counters: KernelCounters


@dataclass(frozen=True, slots=True)
class PropagationResult:
    revision: int
    input_signature: str
    integrand_id: str
    integral_unit: str
    rays: tuple[GeometricRayResult, ...]
    counters: KernelCounters
    model_version: str = MODEL_VERSION

    def to_dict(self) -> dict[str, object]:
        return {
            "schemaVersion": 1,
            **asdict(self),
            "stage": "geometry_B0_not_radiance",
            "physicalTransportStatus": "pending_step_7.9",
            "numericalErrorMeaning": "GK15_minus_G7_with_roundoff_floor;estimated_not_rigorous",
            "coordinateModel": "sphere_geocentric_ENU;not_WGS84_ellipsoid_or_DEM",
            "runtimeRadiometricGate": "not_evaluated_step_7.12",
        }


class PropagationKernel:
    def evaluate(
        self,
        request: PropagationRequest,
        integrand: Callable[[GeometrySample, SourceModel], float] = unit_integrand,
        *,
        integrand_id: str = "unit-v1",
        integral_unit: str = "m",
        cancelled: Callable[[], bool] | None = None,
        is_current: Callable[[], bool] | None = None,
    ) -> PropagationResult:
        if not integrand_id or not integral_unit:
            raise ValueError("Cal identitat i unitat de l'integrand de diagnòstic")

        def checkpoint() -> None:
            if is_current is not None and not is_current():
                raise StalePropagationError("Revisió geomètrica obsoleta")
            if cancelled is not None and cancelled():
                raise PropagationCancelledError("Propagació geomètrica cancel·lada")

        checkpoint()
        frame = SphericalFrame(request.observer, request.options.earth_radius_m)
        origin = frame.position_ecef(request.observer)
        rows = []
        for source in request.sources:
            checkpoint()
            geometry = source.geometry
            anchor = frame.position_ecef(
                geometry.position
                if isinstance(geometry, PointSourceGeometry)
                else geometry.center
            )
            # El centre només orienta la diagnosi B0: no aproxima l'emissió d'àrea.
            offset = (
                anchor[0] - origin[0],
                anchor[1] - origin[1],
                anchor[2] - origin[2],
            )
            east, north, _ = frame.ecef_to_enu(offset)
            if (
                request.directions.azimuth_mode == "source_bearing"
                and math.hypot(east, north) < 1e-8
            ):
                raise ValueError("Rumb de font indefinit; cal DirectionSet absolut")
            bearing = (
                math.degrees(math.atan2(east, north))
                if request.directions.azimuth_mode == "source_bearing"
                else 0.0
            )
            for view in request.directions.directions:
                direction = ViewDirection(
                    view.direction_id,
                    (view.azimuth_deg + bearing) % 360,
                    view.elevation_deg,
                )
                ray = make_ray(frame, direction, request.options.top_m)
                segments = request.options.partition.segments(
                    ray, request.options.top_m, request.options.max_segments_per_ray
                )

                def function(s: float) -> float:
                    position = ray.point(s)
                    sample = GeometrySample(s, position, math.dist(position, anchor))
                    return integrand(sample, source)

                q = integrate_gk15(
                    function,
                    tuple((s.start_m, s.end_m) for s in segments),
                    request.options.quadrature,
                    checkpoint=checkpoint,
                )
                counters = KernelCounters(
                    1, len(segments), q.evaluations, q.subdivisions, q.leaf_intervals
                )
                rows.append(
                    GeometricRayResult(
                        source.source_model_id,
                        view.direction_id,
                        direction.azimuth_deg,
                        direction.elevation_deg,
                        ray.length_m,
                        q.value,
                        q.estimated_error,
                        tuple(s.cell_id for s in segments),
                        counters,
                    )
                )
        checkpoint()
        total = KernelCounters(
            *(
                sum(getattr(row.counters, name) for row in rows)
                for name in KernelCounters.__dataclass_fields__
            )
        )
        signature = hashlib.sha256(
            json.dumps(
                {
                    "sources": [s.to_dict() for s in request.sources],
                    "observer": asdict(request.observer),
                    "directions": asdict(request.directions),
                    "options": asdict(request.options),
                    "revision": request.revision,
                    "integrandId": integrand_id,
                    "integralUnit": integral_unit,
                },
                sort_keys=True,
                allow_nan=False,
            ).encode()
        ).hexdigest()
        checkpoint()
        return PropagationResult(
            request.revision, signature, integrand_id, integral_unit, tuple(rows), total
        )
