"""Transport espectral directe B2/B4 amb columnes independents de λ.

No hi ha cache entre peticions ni taula de transport. Es comparteixen
interseccions, mostres P/T, columnes i geometria angular dins d'un node LOS.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Callable

import numpy as np

from .gas_absorption import GasAbsorptionModel
from .geometric_transport import RayGeometry, Vector3, dot
from .optical_field import OpticalDependency, OpticalField, OpticalState, fingerprint
from .optical_paths import segment_path
from .scattering import (
    AerosolReference,
    ScatteringBand,
    ScatteringConfiguration,
    dry_air_rayleigh,
)
from .single_scattering import SingleScatteringTransport
from .source_model import SourceModel
from .spectral_bandset import (
    SpectralBandSet,
    _one_sided_endpoints,
    build_spectral_band_set,
)
from .spectral_oracle import RELATIVE_UNIT, SpectralCurve
from .transport_profiling import TransportProfiler
from .vector_quadrature import integrate_vector_gk15

SPECTRAL_TRANSPORT_REVISION = "single-scattering-spectral-direct-v1"
TRANSPORT_BAND_STRATEGY = "tl3d-sky-v1-transport-knot-union-simpson-1"


@dataclass(frozen=True, slots=True)
class SpectralAerosol:
    reference: AerosolReference
    angstrom_exponent: float
    reference_wavelength_nm: float = 550.0

    def __post_init__(self) -> None:
        if (
            not math.isfinite(self.angstrom_exponent)
            or not math.isfinite(self.reference_wavelength_nm)
            or self.reference_wavelength_nm <= 0
        ):
            raise ValueError("Llei espectral aerosol invàlida")


@dataclass(frozen=True, slots=True)
class SpectralTransportConfiguration:
    aerosols: tuple[SpectralAerosol, ...]
    responses: tuple[SpectralCurve, ...]
    gas: GasAbsorptionModel | None
    gas_status: str  # No es pot ometre absorció accidentalment a B2.
    wavelength_start_nm: float = 380.0
    wavelength_end_nm: float = 780.0
    reference_configuration: ScatteringConfiguration | None = None

    def __post_init__(self) -> None:
        if self.gas_status != (
            "prescribed_composition"
            if self.gas is not None
            else "disabled_explicit_B2_diagnostic"
        ):
            raise ValueError("Cal declarar l'estat de l'absorció")
        if not self.aerosols or len(
            {a.reference.tile_id for a in self.aerosols}
        ) != len(self.aerosols):
            raise ValueError("Cal aerosol explícit per tile")
        if not 200 <= self.wavelength_start_nm < self.wavelength_end_nm <= 1000:
            raise ValueError("Domini fora de Rayleigh Chance–Spurr")
        # El constructor homologat valida suport i unitats de les respostes.
        dummy = SpectralCurve(
            "validation",
            (self.wavelength_start_nm, self.wavelength_end_nm),
            (1.0, 1.0),
            RELATIVE_UNIT,
        )
        build_spectral_band_set(
            dummy, self.responses, self.wavelength_start_nm, self.wavelength_end_nm
        )
        if any(x < 0 for r in self.responses for x in r.values):
            raise ValueError(
                "La ruta positiva de transport no admet respostes signades"
            )

    @property
    def signature(self) -> str:
        return fingerprint(asdict(self))

    def monochromatic(self) -> ScatteringConfiguration:
        sigma, phase = dry_air_rayleigh(550.0)
        band = ScatteringBand(
            550.0,
            sigma,
            phase,
            tuple(a.reference for a in self.aerosols),
            "Geometria compartida espectral; banda auxiliar, no resultat monocromàtic",
        )
        return self.reference_configuration or ScatteringConfiguration(band)

    def validate_field(self, field: OpticalField) -> None:
        if {t.tile_id for t in field.tiles} != {
            a.reference.tile_id for a in self.aerosols
        }:
            raise ValueError("Cobertura aerosol incompatible")
        if self.gas is None:
            return
        expected = {(t.tile_id, g.species) for t in field.tiles for g in self.gas.luts}
        if {(p.tile_id, p.species) for p in self.gas.profiles} != expected:
            raise ValueError("Cobertura gasosa incompleta o incompatible")
        for tile in field.tiles:
            for lut in self.gas.luts:
                p = self.gas.profile(tile.tile_id, lut.species)
                if (
                    p.heights_m[0] > tile.profile.heights_m[0]
                    or p.heights_m[-1] < tile.profile.heights_m[-1]
                ):
                    raise ValueError("Perfil gasós sense cobertura atmosfèrica")
                if (
                    min(tile.profile.temperature_k) < lut.temperatures_k[0]
                    or max(tile.profile.temperature_k) > lut.temperatures_k[-1]
                ):
                    raise ValueError("Camp atmosfèric fora del domini tèrmic gasós")
                if (
                    self.wavelength_start_nm < lut.wavelengths_nm[0]
                    or self.wavelength_end_nm > lut.wavelengths_nm[-1]
                ):
                    raise ValueError("Absorció desconeguda fora de la LUT")
                if any(
                    tile.profile.heights_m[0] < h < tile.profile.heights_m[-1]
                    and h not in tile.profile.heights_m
                    for h in p.heights_m
                ):
                    raise ValueError(
                        "Cal partir el camp als nusos de composició gasosa"
                    )


class SpectralOperator:
    def __init__(
        self, source: SourceModel, config: SpectralTransportConfiguration
    ) -> None:
        curve = SpectralCurve(
            source.spectrum.spectrum_id,
            source.spectrum.wavelengths_nm,
            tuple(
                float(v / source.spectrum.raw_integral_nm)
                for v in source.spectrum.relative_power
            ),
            RELATIVE_UNIT,
            "zero",
        )
        base = build_spectral_band_set(
            curve,
            config.responses,
            config.wavelength_start_nm,
            config.wavelength_end_nm,
        )
        knots = tuple(
            sorted(
                set(base.knots_nm)
                | {
                    w
                    for g in (config.gas.luts if config.gas else ())
                    for w in g.wavelengths_nm
                    if config.wavelength_start_nm < w < config.wavelength_end_nm
                }
            )
        )
        identity = fingerprint({"strategy": TRANSPORT_BAND_STRATEGY, "knots": knots})
        self.band_set = SpectralBandSet(
            f"{TRANSPORT_BAND_STRATEGY}:{identity}",
            TRANSPORT_BAND_STRATEGY,
            knots,
            fingerprint({"source": base.input_signature, "config": config.signature}),
        )
        x = np.array(knots)
        left, right = x[:-1], x[1:]
        self.wavelengths = np.column_stack((left, (left + right) / 2, right)).ravel()
        weights = np.ones((len(left), 3))
        for c in (curve, *config.responses):
            weights *= np.column_stack(_one_sided_endpoints(c, left, right))
        self.weights = (
            weights * (right - left)[:, None] * np.array([1.0, 4.0, 1.0]) / 6
        ).ravel()
        self.sigma = np.array([dry_air_rayleigh(float(w))[0] for w in self.wavelengths])
        delta = np.array(
            [
                dry_air_rayleigh(float(w))[1].depolarization_delta
                for w in self.wavelengths
            ]
        )
        self.phase_constant = 3 * (1 + 3 * delta) / (16 * np.pi * (1 + 2 * delta))
        self.phase_cosine = 3 * (1 - delta) / (16 * np.pi * (1 + 2 * delta))
        self.aerosols = {a.reference.tile_id: a for a in config.aerosols}
        self.aerosol_ext = {
            key: a.reference.extinction_per_m
            * (self.wavelengths / a.reference_wavelength_nm) ** (-a.angstrom_exponent)
            for key, a in self.aerosols.items()
        }
        self.gas_matrices = tuple(
            g.matrix(self.wavelengths) for g in (config.gas.luts if config.gas else ())
        )


class SpectralScatteringTransport(SingleScatteringTransport):
    def __init__(
        self,
        source: SourceModel,
        field: OpticalField,
        config: SpectralTransportConfiguration,
        ray: RayGeometry,
        max_segments: int,
        checkpoint: Callable[[], None],
        dependencies: set[OpticalDependency],
        profiler: TransportProfiler,
        operator: SpectralOperator,
    ) -> None:
        with profiler.measure("geometry"):
            super().__init__(
                source,
                field,
                config.monochromatic(),
                ray,
                max_segments,
                checkpoint,
                dependencies,
            )
        self.spectral_config, self.profiler, self.operator = config, profiler, operator
        self.column_paths = 0
        self.column_error_max = 0.0
        self.constant_extinction: dict[tuple[str, int], np.ndarray] = {}
        self.thermal_heights: dict[str, tuple[float, ...]] = {}
        # Les bases lineals en T canvien de derivada als nusos de la LUT.
        # Partició geomètrica exacta, compartida entre totes les λ; sense
        # interpolar trajectes ni guardar resultats entre peticions.
        if config.gas is not None:
            with profiler.measure("atmospheric_sampling"):
                temperatures = {t for g in config.gas.luts for t in g.temperatures_k}
                for tile in field.tiles:
                    heights = set()
                    profile = tile.profile
                    for i, (a, b) in enumerate(zip(profile.temperature_k, profile.temperature_k[1:])):
                        for t in temperatures:
                            if min(a, b) < t < max(a, b):
                                fraction = (t - a) / (b - a)
                                heights.add(profile.heights_m[i] + fraction * (profile.heights_m[i + 1] - profile.heights_m[i]))
                    if heights:
                        self.thermal_heights[tile.tile_id] = tuple(sorted(heights))

    def _depth(self, start: Vector3, end: Vector3) -> np.ndarray:
        p, op, gas = self.profiler, self.operator, self.spectral_config.gas
        with p.measure("geometry"):
            if self.thermal_heights:
                _, direction, segments = segment_path(self.field, start, end, self.max_segments, self.checkpoint, self.thermal_heights)
            else:
                _, direction, segments = segment_path(
                    self.field, start, end, self.max_segments, self.checkpoint
                )
        self.column_paths += 1
        tau = np.zeros_like(op.wavelengths)
        for segment in segments:
            self.dependencies.add(segment.dependency)
            tile = self.field.tile(segment.dependency.tile_id)
            aerosol = op.aerosols[tile.tile_id].reference
            i = segment.dependency.layer_index
            self.work.segments += 1

            def sample(s: float) -> np.ndarray:
                with p.measure("geometry"):
                    point: Vector3 = tuple(x + s * d for x, d in zip(start, direction))  # type: ignore[assignment]
                with p.measure("atmospheric_sampling"):
                    state = self.field.sample(point, segment)
                    n, h = state.number_density_m3, state.altitude_m
                    values = [
                        n,
                        1.0
                        if aerosol.scale_height_m is None
                        else math.exp(-h / aerosol.scale_height_m),
                    ]
                    if gas:
                        for g in gas.luts:
                            values.extend(
                                n
                                * gas.profile(tile.tile_id, g.species).fraction(h)
                                * g.temperature_weights(state.temperature_k)
                            )
                    return np.array(values)

            homogeneous = (
                tile.profile.pressure_pa[i] == tile.profile.pressure_pa[i + 1]
                and tile.profile.temperature_k[i] == tile.profile.temperature_k[i + 1]
                and aerosol.scale_height_m is None
                and (
                    gas is None
                    or all(
                        len(set(gas.profile(tile.tile_id, g.species).mole_fractions))
                        == 1
                        for g in gas.luts
                    )
                )
            )
            if homogeneous:
                # Mateixa branca analítica de B1; coeficients constants del
                # medi, locals a aquesta LOS. Cap taula ni cache de transport.
                key = (tile.tile_id, i)
                if key not in self.constant_extinction:
                    with p.measure("atmospheric_sampling"):
                        temperature = tile.profile.temperature_k[i]
                        n = tile.profile.pressure_pa[i] / (1.380649e-23 * temperature)
                    with p.measure("transmissions"):
                        ext = n * op.sigma + op.aerosol_ext[tile.tile_id]
                        if gas:
                            for g, matrix in zip(gas.luts, op.gas_matrices):
                                fractions = g.temperature_weights(temperature)
                                active = fractions != 0
                                ext += (
                                    n
                                    * gas.profile(
                                        tile.tile_id, g.species
                                    ).mole_fractions[0]
                                    * np.sum(
                                        fractions[active, None] * matrix[active], axis=0
                                    )
                                )
                        self.constant_extinction[key] = ext
                with p.measure("transmissions"):
                    tau += self.constant_extinction[key] * (
                        segment.end_m - segment.start_m
                    )
                continue
            else:
                with p.measure("quadrature"):
                    q = integrate_vector_gk15(
                        sample,
                        segment.start_m,
                        segment.end_m,
                        self.config.path_quadrature,
                        self.checkpoint,
                    )
                columns, error = q.value, q.estimated_error
                self.work.nodes += q.evaluations
            with p.measure("transmissions"):
                contribution = (
                    columns[0] * op.sigma + columns[1] * op.aerosol_ext[tile.tile_id]
                )
                error_tau = (
                    error[0] * op.sigma + error[1] * op.aerosol_ext[tile.tile_id]
                )
                cursor = 2
                if gas:
                    for matrix in op.gas_matrices:
                        count = len(matrix)
                        active = columns[cursor:cursor + count] != 0
                        contribution += np.sum(columns[cursor:cursor + count][active, None] * matrix[active], axis=0)
                        active_error = error[cursor:cursor + count] != 0
                        error_tau += np.sum(error[cursor:cursor + count][active_error, None] * matrix[active_error], axis=0)
                        cursor += count
                tau += contribution
                self.column_error_max = max(
                    self.column_error_max, float(np.max(error_tau))
                )
        self.work.max_optical_depth_error = max(
            self.work.max_optical_depth_error, self.column_error_max * len(segments)
        )
        return tau

    def value(self, distance: float, point: Vector3, state: OpticalState) -> float:
        p, op = self.profiler, self.operator
        observer_tau = self._depth(self.ray.origin_ecef_m, point)
        result = 0.0
        for node, weight in self.emission_nodes(distance, point):
            self.checkpoint()
            with p.measure("geometry"):
                incoming = tuple(a - b for a, b in zip(point, node))
                radius = math.hypot(*incoming)
                if radius < 1e-7:
                    raise ValueError("Node spectral singular")
                unit: Vector3 = tuple(x / radius for x in incoming)  # type: ignore[assignment]
                vertical = dot(unit, self.basis[2])
                if vertical < 0:
                    continue
                theta = math.degrees(math.acos(min(1.0, vertical)))
                azimuth = math.degrees(
                    math.atan2(dot(unit, self.basis[0]), dot(unit, self.basis[1]))
                )
                mu = -dot(unit, self.ray.direction_ecef)
                angular = self.source.angular.density_per_sr(theta, azimuth)
            source_tau = self._depth(node, point)
            with p.measure("transmissions"):
                a = op.aerosols[state.dependency.tile_id].reference
                local_aer = op.aerosol_ext[state.dependency.tile_id] * (
                    1.0
                    if a.scale_height_m is None
                    else math.exp(-state.altitude_m / a.scale_height_m)
                )
                gamma = state.number_density_m3 * op.sigma * (
                    op.phase_constant + op.phase_cosine * mu * mu
                ) + local_aer * a.single_scattering_albedo * a.phase.density(mu)
                transmission = np.exp(-observer_tau - source_tau)
                self.phase_evaluations += 2 * len(op.wavelengths)
            with p.measure("spectral_integration"):
                result += (
                    weight
                    * self.source.amplitude.value
                    * angular
                    / (radius * radius)
                    * float(np.dot(op.weights, gamma * transmission))
                )
        return result
