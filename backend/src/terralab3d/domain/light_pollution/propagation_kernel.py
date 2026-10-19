"""Frontera de propagació: geometria B0, columnes i dispersió simple B1."""

from __future__ import annotations

import hashlib
import json
import math
from bisect import bisect_right
from contextlib import nullcontext
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
from .source_model import (
    DefinedSpectrum,
    GeodeticPosition,
    PointSourceGeometry,
    SourceModel,
)
from .optical_field import (
    OpticalDependency,
    OpticalField,
    OpticalPathSegment,
    OpticalState,
    fingerprint,
)
from .scattering import ScatteringConfiguration
from .single_scattering import SingleScatteringTransport, TransportDiagnostics
from .spectral_transport import (
    SpectralOperator,
    SpectralScatteringTransport,
    SpectralTransportConfiguration,
    SPECTRAL_TRANSPORT_REVISION,
)
from .transport_profiling import TransportProfiler

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
    optical_field: OpticalField | None = None
    scattering: ScatteringConfiguration | None = None
    spectral: SpectralTransportConfiguration | None = None

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
        if (
            self.optical_field is not None
            and self.optical_field.radius_m != self.options.earth_radius_m
        ):
            raise ValueError(
                "Camp atmosfèric i geometria amb referencials incompatibles"
            )
        if self.spectral is not None:
            if self.scattering is not None or self.optical_field is None:
                raise ValueError(
                    "La ruta espectral requereix camp i exclou B1 simultani"
                )
            self.spectral.validate_field(self.optical_field)
        if self.scattering is not None or self.spectral is not None:
            if self.optical_field is None:
                raise ValueError("La dispersió requereix un camp atmosfèric")
            if self.scattering is not None and {
                t.tile_id for t in self.optical_field.tiles
            } != {a.tile_id for a in self.scattering.band.aerosols}:
                raise ValueError("La cobertura aerosol ha de correspondre als tiles")
            if (
                len({s.amplitude.unit for s in self.sources}) != 1
                or len(
                    {
                        s.amplitude.parameter_name
                        for s in self.sources
                        if s.amplitude.unit == "relative"
                    }
                )
                > 1
            ):
                raise ValueError("No es barregen escales radiomètriques incompatibles")


@dataclass(frozen=True, slots=True)
class GeometrySample:
    distance_observer_m: float
    position_ecef_m: Vector3
    source_anchor_distance_m: float
    optical_state: OpticalState | None = None


def unit_integrand(sample: GeometrySample, source: SourceModel) -> float:
    """Funció de diagnòstic 1: ∫1 ds retorna metres, no radiància."""
    return 1.0


def number_density_integrand(sample: GeometrySample, source: SourceModel) -> float:
    """Diagnòstic ∫n ds en m⁻²; cap emissió ni scattering."""
    if sample.optical_state is None:
        raise ValueError("La columna molecular requereix un OpticalField")
    return sample.optical_state.number_density_m3


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
    optical_field_signature: str | None = None
    optical_dependency_signature: str | None = None
    optical_traces: tuple[OpticalRayTrace, ...] = ()
    scattering: ScatteringConfiguration | None = None
    transport_diagnostics: tuple[TransportDiagnostics, ...] = ()
    spectral_metadata: dict[str, object] | None = None

    def to_dict(self) -> dict[str, object]:
        values = asdict(self)
        if self.spectral_metadata is None:
            values.pop("spectral_metadata")
        if self.scattering is None:
            values.pop("scattering")
            if self.spectral_metadata is None:
                values.pop("transport_diagnostics")
        if self.optical_field_signature is None:
            for key in (
                "optical_field_signature",
                "optical_dependency_signature",
                "optical_traces",
            ):
                values.pop(key)
        return {
            "schemaVersion": 4
            if self.spectral_metadata is not None
            else 3
            if self.scattering is not None
            else (2 if self.optical_field_signature is not None else 1),
            **values,
            "stage": ("single_scattering_spectral_direct_B2" if self.spectral_metadata and self.spectral_metadata["gasStatus"] == "disabled_explicit_B2_diagnostic" else "single_scattering_spectral_direct_B4")
            if self.spectral_metadata is not None
            else "single_scattering_monochromatic_B1"
            if self.scattering is not None
            else "optical_field_column_diagnostic_not_radiance"
            if self.optical_field_signature is not None
            else "geometry_B0_not_radiance",
            "physicalTransportStatus": "spectral_prescribed_medium;gas_status_explicit_in_metadata;terrain_visibility_pending;not_full_terrestrial_air"
            if self.spectral_metadata is not None
            else "monochromatic_prescribed_medium;gas_absorption_not_computed;terrain_visibility_pending"
            if self.scattering is not None
            else "pending_step_7.9",
            "numericalErrorMeaning": "GK15_minus_G7_with_roundoff_floor;estimated_not_rigorous",
            "coordinateModel": "sphere_geocentric_ENU;not_WGS84_ellipsoid_or_DEM",
            "runtimeRadiometricGate": "not_evaluated_step_7.12",
            **(
                {
                    "numericalErrorMeaning": "outer_GK_estimate;inner_tau_error_reported_separately;area_error_not_quantified",
                    "empiricalValidation": "not_evaluated;H_pending",
                }
                if self.scattering is not None
                else {}
            ),
        }


@dataclass(frozen=True, slots=True)
class OpticalRayTrace:
    source_id: str
    direction_id: str
    traversed_segments: tuple[OpticalPathSegment, ...]
    sampled_dependencies: tuple[OpticalDependency, ...]


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
        profiler: TransportProfiler | None = None,
    ) -> PropagationResult:
        if not integrand_id or not integral_unit:
            raise ValueError("Cal identitat i unitat de l'integrand de diagnòstic")
        if request.scattering is not None:
            if integrand is not unit_integrand:
                raise ValueError(
                    "La ruta B1 no admet un integrand diagnòstic substitut"
                )
            integrand_id = request.scattering.band.revision
            integral_unit = f"{request.sources[0].amplitude.unit} m^-2 sr^-1 nm^-1"
        if request.spectral is not None:
            if integrand is not unit_integrand:
                raise ValueError("La ruta espectral no admet integrands substituts")
            integrand_id = SPECTRAL_TRANSPORT_REVISION
            integral_unit = f"{request.sources[0].amplitude.unit} m^-2 sr^-1"
            profiler = profiler or TransportProfiler()

        def measure(stage: str):
            return profiler.measure(stage) if profiler is not None else nullcontext()

        def checkpoint() -> None:
            if is_current is not None and not is_current():
                raise StalePropagationError("Revisió geomètrica obsoleta")
            if cancelled is not None and cancelled():
                raise PropagationCancelledError("Propagació geomètrica cancel·lada")

        checkpoint()
        frame = SphericalFrame(request.observer, request.options.earth_radius_m)
        origin = frame.position_ecef(request.observer)
        rows = []
        traces: list[OpticalRayTrace] = []
        field = request.optical_field
        diagnostics: list[TransportDiagnostics] = []
        spectral_sets: dict[str, object] = {}
        operators: dict[DefinedSpectrum, SpectralOperator] = {}
        for source in request.sources:
            checkpoint()
            operator = None
            if request.spectral is not None:
                with measure("spectral_integration"):
                    operator = operators.get(source.spectrum)
                    if operator is None:
                        operator = SpectralOperator(source, request.spectral)
                        operators[source.spectrum] = operator
                    spectral_sets[source.source_model_id] = asdict(operator.band_set)
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
                with measure("geometry"):
                    ray = make_ray(frame, direction, request.options.top_m)
                optical_segments: tuple[OpticalPathSegment, ...] = ()
                sampled: set[OpticalDependency] = set()
                if field is None:
                    with measure("geometry"):
                        segments = request.options.partition.segments(
                            ray,
                            request.options.top_m,
                            request.options.max_segments_per_ray,
                        )
                    intervals = tuple((s.start_m, s.end_m) for s in segments)
                    geometric_cells = tuple(s.cell_id for s in segments)
                else:
                    with measure("geometry"):
                        optical_segments = field.traverse(
                            ray, request.options.max_segments_per_ray, checkpoint
                        )
                    intervals = tuple((s.start_m, s.end_m) for s in optical_segments)
                    geometric_cells = ()
                segment_ends = tuple(segment.end_m for segment in optical_segments)
                transport: SingleScatteringTransport | None = None
                if request.scattering is not None and field is not None:
                    transport = SingleScatteringTransport(
                        source,
                        field,
                        request.scattering,
                        ray,
                        request.options.max_segments_per_ray,
                        checkpoint,
                        sampled,
                        profiler,
                    )
                if (
                    request.spectral is not None
                    and field is not None
                    and operator is not None
                    and profiler is not None
                ):
                    transport = SpectralScatteringTransport(
                        source,
                        field,
                        request.spectral,
                        ray,
                        request.options.max_segments_per_ray,
                        checkpoint,
                        sampled,
                        profiler,
                        operator,
                    )
                if transport is not None:
                    cuts = sorted(
                        {
                            *(x for pair in intervals for x in pair),
                            *transport.break_distances,
                        }
                    )
                    intervals = tuple(zip(cuts, cuts[1:]))
                    if len(intervals) > request.options.max_segments_per_ray:
                        raise ValueError("Pressupost de segments LOS B1 excedit")

                def function(s: float) -> float:
                    with measure("geometry"):
                        position = ray.point(s)
                    state = None
                    if field is not None:
                        # GK avalua els panells en qualsevol ordre; cap cursor mutable.
                        index = min(
                            bisect_right(segment_ends, s),
                            len(optical_segments) - 1,
                        )
                        with measure("atmospheric_sampling"):
                            state = field.sample(position, optical_segments[index])
                        sampled.add(state.dependency)
                    sample = GeometrySample(
                        s, position, math.dist(position, anchor), state
                    )
                    if transport is not None and state is not None:
                        return transport.value(s, position, state)
                    return integrand(sample, source)

                with measure("quadrature"):
                    q = integrate_gk15(
                        function,
                        intervals,
                        request.spectral.monochromatic().radiance_quadrature
                        if request.spectral is not None
                        else request.scattering.radiance_quadrature
                        if request.scattering is not None
                        else request.options.quadrature,
                        checkpoint=checkpoint,
                    )
                counters = KernelCounters(
                    1, len(intervals), q.evaluations, q.subdivisions, q.leaf_intervals
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
                        geometric_cells,
                        counters,
                    )
                )
                if field is not None:
                    traces.append(
                        OpticalRayTrace(
                            source.source_model_id,
                            view.direction_id,
                            optical_segments,
                            tuple(sorted(sampled)),
                        )
                    )
                if transport is not None:
                    diagnostics.append(transport.diagnostics())
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
                    **(
                        {"opticalFieldSignature": field.signature}
                        if field is not None
                        else {}
                    ),
                    **(
                        {"scattering": asdict(request.scattering)}
                        if request.scattering is not None
                        else {}
                    ),
                    **(
                        {"spectral": request.spectral.signature}
                        if request.spectral is not None
                        else {}
                    ),
                },
                sort_keys=True,
                allow_nan=False,
            ).encode()
        ).hexdigest()
        dependencies = tuple(d for trace in traces for d in trace.sampled_dependencies)
        used_signature = (
            field.dependency_signature(dependencies) if field is not None else None
        )
        if request.scattering is not None:
            used_tiles = {d.tile_id for d in dependencies}
            band = request.scattering.band
            used_signature = fingerprint(
                {
                    "atmosphere": used_signature,
                    "band": {
                        **asdict(band),
                        "aerosols": [
                            asdict(a) for a in band.aerosols if a.tile_id in used_tiles
                        ],
                    },
                }
            )
        if request.spectral is not None:
            used_signature = fingerprint(
                {
                    "atmosphere": used_signature,
                    "spectral": request.spectral.signature,
                    "sources": [s.to_dict() for s in request.sources],
                }
            )
        checkpoint()
        return PropagationResult(
            request.revision,
            signature,
            integrand_id,
            integral_unit,
            tuple(rows),
            total,
            model_version=SPECTRAL_TRANSPORT_REVISION
            if request.spectral is not None
            else request.scattering.band.revision
            if request.scattering is not None
            else MODEL_VERSION,
            optical_field_signature=field.signature if field is not None else None,
            optical_dependency_signature=used_signature,
            optical_traces=tuple(traces),
            scattering=request.scattering,
            transport_diagnostics=tuple(diagnostics),
            spectral_metadata={
                "configurationSignature": request.spectral.signature,
                "bandSets": spectral_sets,
                "gasStatus": request.spectral.gas_status,
                "gasModelSignature": request.spectral.gas.signature
                if request.spectral.gas
                else None,
                "wavelengthConvention": "vacuum_nm",
                "responseIds": [r.source_id for r in request.spectral.responses],
                "errorMeaning": "outer_GK_estimate;columns_componentwise_estimates;area_unquantified;spectral_budget_separate",
            }
            if request.spectral is not None
            else None,
        )
