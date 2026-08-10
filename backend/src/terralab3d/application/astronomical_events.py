"""Use cases for instantaneous events, contact searches and eclipse footprint."""

from __future__ import annotations

import asyncio
import logging
import math
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Awaitable, Callable

from terralab3d.application.ports.astronomical_events import (
    AstronomicalEventEphemerisPort,
)
from terralab3d.application.ports.lunar_limb import LunarLimbProfileProvider
from terralab3d.domain.eclipses.calculations import (
    angular_separation_deg,
    lunar_eclipse_state,
    occultation_state,
    solar_eclipse_state,
)
from terralab3d.domain.eclipses.models import (
    AstronomicalEventSearchResult,
    AstronomicalEventSnapshot,
    AngularSeparationMeasurement,
    ApparentPairResult,
    EclipseContact,
    EclipseKind,
    LunarEclipseState,
    SolarEclipseClassification,
    SolarEclipseState,
)
from terralab3d.domain.eclipses.services import AstronomicalEventCalculator
from terralab3d.domain.solar_system.models import ScientificObserver

log = logging.getLogger("terralab3d.astronomical_events")


class EventSearchCancelled(RuntimeError):
    """Expected cancellation state; callers should not log it as a failure."""


@dataclass(frozen=True, slots=True)
class CentralBandLimits:
    south_latitude_deg: float
    north_latitude_deg: float
    longitude_deg: float
    utc: datetime
    angular_tolerance_deg: float
    latitude_tolerance_deg: float


class AstronomicalEventService:
    """Readable instantaneous use case over the lightweight SPICE boundary."""

    def __init__(
        self,
        ephemeris: AstronomicalEventEphemerisPort,
        limb_provider: LunarLimbProfileProvider | None = None,
    ) -> None:
        self._ephemeris = ephemeris
        self._limb_provider = limb_provider
        self._calculator = AstronomicalEventCalculator()
        self.compute_count = 0
        self.compute_ms_samples: list[float] = []

    def snapshot(
        self,
        utc: datetime,
        observer: ScientificObserver,
        *,
        observer_generation: int,
        source_solar_system_generation: int,
    ) -> AstronomicalEventSnapshot:
        started = time.perf_counter()
        state = self._ephemeris.event_ephemeris(
            _as_utc(utc),
            observer,
            ("sun", "moon"),
            include_lunar_shadow_geometry=True,
        )
        sun = state.body("sun")
        moon = state.body("moon")
        separation_rate = None
        limb_profile = None
        if sun is not None and moon is not None:
            instant = solar_eclipse_state(sun, moon, quality=state.quality)
            if instant.classification is not SolarEclipseClassification.NONE:
                separation_rate = self._separation_rate(utc, observer)
            if instant.obscuration >= 0.94 and self._limb_provider is not None:
                limb_profile = self._limb_provider.profile(moon)
        result = self._calculator.calculate(
            state,
            observer_generation=observer_generation,
            source_solar_system_generation=source_solar_system_generation,
            separation_rate_deg_s=separation_rate,
            limb_profile=limb_profile,
        )
        elapsed = (time.perf_counter() - started) * 1000.0
        self.compute_count += 1
        self.compute_ms_samples.append(elapsed)
        if len(self.compute_ms_samples) > 256:
            del self.compute_ms_samples[:-256]
        return result

    def metrics(self) -> dict[str, float | int]:
        samples = sorted(self.compute_ms_samples)
        return {
            "event_instant_compute_count": self.compute_count,
            "event_instant_compute_ms_p50": _percentile(samples, 0.50),
            "event_instant_compute_ms_p95": _percentile(samples, 0.95),
            "event_ephemeris_query_count": getattr(
                self._ephemeris, "event_query_count", 0
            ),
        }

    def measure_pair(
        self,
        request_id: str,
        utc: datetime,
        observer: ScientificObserver,
        body_a_id: str,
        body_b_id: str,
    ) -> ApparentPairResult:
        if body_a_id == body_b_id:
            raise ValueError("A separation requires two distinct bodies")
        ephemeris = self._ephemeris.event_ephemeris(
            _as_utc(utc), observer, (body_a_id, body_b_id)
        )
        first = ephemeris.body(body_a_id)
        second = ephemeris.body(body_b_id)
        if first is None or second is None:
            raise RuntimeError("Requested apparent pair is unavailable")
        separation = angular_separation_deg(first.direction_icrf, second.direction_icrf)
        foreground, background = (
            (first, second)
            if first.distance_km < second.distance_km
            else (second, first)
        )
        return ApparentPairResult(
            request_id=request_id,
            measurement=AngularSeparationMeasurement(
                body_a=body_a_id,
                body_b=body_b_id,
                timestamp_utc=ephemeris.timestamp_utc,
                separation_deg=separation,
                limb_separation_deg=(
                    separation - first.angular_radius_deg - second.angular_radius_deg
                ),
                quality=ephemeris.quality,
            ),
            occultation=occultation_state(foreground, background),
            kernel_generation=ephemeris.kernel_generation,
        )

    def _separation_rate(
        self,
        utc: datetime,
        observer: ScientificObserver,
    ) -> float:
        values = []
        for offset in (-1.0, 1.0):
            sample = self._ephemeris.event_ephemeris(
                _as_utc(utc) + timedelta(seconds=offset),
                observer,
                ("sun", "moon"),
            )
            sun = sample.body("sun")
            moon = sample.body("moon")
            if sun is None or moon is None:
                return 0.0
            values.append(
                solar_eclipse_state(sun, moon, quality=sample.quality).center_separation_deg
            )
        return (values[1] - values[0]) * 0.5


class AstronomicalEventSearcher:
    """Coarse scan, bracket and numerical refinement over the event port."""

    def __init__(
        self,
        ephemeris: AstronomicalEventEphemerisPort,
        *,
        temporal_tolerance_seconds: float = 0.25,
        angular_tolerance_deg: float = 1.0e-8,
    ) -> None:
        if temporal_tolerance_seconds <= 0.0 or angular_tolerance_deg <= 0.0:
            raise ValueError("Search tolerances must be positive")
        self._ephemeris = ephemeris
        self.temporal_tolerance_seconds = temporal_tolerance_seconds
        self.angular_tolerance_deg = angular_tolerance_deg

    def search_solar(
        self,
        request_id: str,
        observer: ScientificObserver,
        observer_generation: int,
        start_utc: datetime,
        end_utc: datetime,
        *,
        coarse_step_seconds: float = 60.0,
        cancel: threading.Event | None = None,
    ) -> AstronomicalEventSearchResult:
        started = time.perf_counter()
        start, end = _validated_interval(start_utc, end_utc)
        query_start = getattr(self._ephemeris, "event_query_count", 0)
        cache: dict[float, SolarEclipseState] = {}

        def state_at(timestamp: float) -> SolarEclipseState:
            _check_cancel(cancel)
            key = round(timestamp, 6)
            if key not in cache:
                sample = self._ephemeris.event_ephemeris(
                    datetime.fromtimestamp(timestamp, timezone.utc),
                    observer,
                    ("sun", "moon"),
                )
                sun = sample.body("sun")
                moon = sample.body("moon")
                if sun is None or moon is None:
                    raise RuntimeError("Solar event ephemeris is unavailable")
                cache[key] = solar_eclipse_state(sun, moon, quality=sample.quality)
            return cache[key]

        times = _coarse_times(start.timestamp(), end.timestamp(), coarse_step_seconds)
        states = [state_at(value) for value in times]
        greatest_index = min(range(len(states)), key=lambda index: states[index].center_separation_deg)
        greatest_timestamp = _refine_minimum(
            lambda value: state_at(value).center_separation_deg,
            times[max(0, greatest_index - 1)],
            times[min(len(times) - 1, greatest_index + 1)],
            self.temporal_tolerance_seconds,
            cancel,
        )
        maximum = state_at(greatest_timestamp)

        external_values = [
            state.center_separation_deg
            - state.sun_angular_radius_deg
            - state.moon_angular_radius_deg
            for state in states
        ]
        external_roots = self._refine_roots(
            times,
            external_values,
            lambda value: (
                state_at(value).center_separation_deg
                - state_at(value).sun_angular_radius_deg
                - state_at(value).moon_angular_radius_deg
            ),
            cancel,
        )
        internal_values = [
            state.center_separation_deg
            - abs(state.sun_angular_radius_deg - state.moon_angular_radius_deg)
            for state in states
        ]
        internal_roots = self._refine_roots(
            times,
            internal_values,
            lambda value: (
                state_at(value).center_separation_deg
                - abs(
                    state_at(value).sun_angular_radius_deg
                    - state_at(value).moon_angular_radius_deg
                )
            ),
            cancel,
        )
        contacts: list[EclipseContact] = []
        if len(external_roots) >= 2:
            contacts.extend(
                (
                    _solar_contact("C1", external_roots[0], state_at),
                    _solar_contact("C4", external_roots[-1], state_at),
                )
            )
        if len(internal_roots) >= 2:
            contacts.extend(
                (
                    _solar_contact("C2", internal_roots[0], state_at),
                    _solar_contact("C3", internal_roots[-1], state_at),
                )
            )
        contacts.sort(key=lambda item: item.instant_utc)
        event_exists = maximum.classification is not SolarEclipseClassification.NONE
        locally_visible = maximum.locally_visible or any(item.locally_visible for item in contacts)
        return AstronomicalEventSearchResult(
            request_id=request_id,
            event_type=EclipseKind.SOLAR,
            classification=maximum.classification.value,
            interval_start_utc=start,
            interval_end_utc=end,
            greatest_utc=datetime.fromtimestamp(greatest_timestamp, timezone.utc),
            contacts=tuple(contacts),
            event_exists=event_exists,
            locally_visible=locally_visible,
            maximum_magnitude=maximum.eclipse_magnitude,
            maximum_obscuration=maximum.obscuration,
            observer_generation=observer_generation,
            kernel_generation=self._ephemeris.kernel_generation,
            quality=maximum.geometry_quality,
            ephemeris_query_count=(
                getattr(self._ephemeris, "event_query_count", query_start) - query_start
            ),
            duration_ms=(time.perf_counter() - started) * 1000.0,
            temporal_tolerance_seconds=self.temporal_tolerance_seconds,
            angular_tolerance_deg=self.angular_tolerance_deg,
        )

    def search_lunar(
        self,
        request_id: str,
        observer: ScientificObserver,
        observer_generation: int,
        start_utc: datetime,
        end_utc: datetime,
        *,
        coarse_step_seconds: float = 180.0,
        cancel: threading.Event | None = None,
    ) -> AstronomicalEventSearchResult:
        started = time.perf_counter()
        start, end = _validated_interval(start_utc, end_utc)
        query_start = getattr(self._ephemeris, "event_query_count", 0)
        cache: dict[float, LunarEclipseState] = {}

        def state_at(timestamp: float) -> LunarEclipseState:
            _check_cancel(cancel)
            key = round(timestamp, 6)
            if key not in cache:
                sample = self._ephemeris.event_ephemeris(
                    datetime.fromtimestamp(timestamp, timezone.utc),
                    observer,
                    ("moon",),
                    include_lunar_shadow_geometry=True,
                )
                cache[key] = lunar_eclipse_state(sample)
            return cache[key]

        times = _coarse_times(start.timestamp(), end.timestamp(), coarse_step_seconds)
        states = [state_at(value) for value in times]
        greatest_index = min(range(len(states)), key=lambda index: states[index].shadow_axis_offset_km)
        greatest_timestamp = _refine_minimum(
            lambda value: state_at(value).shadow_axis_offset_km,
            times[max(0, greatest_index - 1)],
            times[min(len(times) - 1, greatest_index + 1)],
            self.temporal_tolerance_seconds,
            cancel,
        )
        maximum = state_at(greatest_timestamp)
        equations = (
            ("P1", "P4", lambda state: state.shadow_axis_offset_km - state.penumbra_radius_km - state.moon_radius_km),
            ("U1", "U4", lambda state: state.shadow_axis_offset_km - state.umbra_radius_km - state.moon_radius_km),
            ("U2", "U3", lambda state: state.shadow_axis_offset_km - abs(state.umbra_radius_km - state.moon_radius_km)),
        )
        contacts: list[EclipseContact] = []
        for ingress_name, egress_name, equation in equations:
            roots = self._refine_roots(
                times,
                [equation(state) for state in states],
                lambda value, fn=equation: fn(state_at(value)),
                cancel,
            )
            if len(roots) >= 2:
                contacts.extend(
                    (
                        _lunar_contact(ingress_name, roots[0], state_at),
                        _lunar_contact(egress_name, roots[-1], state_at),
                    )
                )
        contacts.sort(key=lambda item: item.instant_utc)
        event_exists = maximum.penumbral_magnitude > 0.0
        return AstronomicalEventSearchResult(
            request_id=request_id,
            event_type=EclipseKind.LUNAR,
            classification=maximum.classification.value,
            interval_start_utc=start,
            interval_end_utc=end,
            greatest_utc=datetime.fromtimestamp(greatest_timestamp, timezone.utc),
            contacts=tuple(contacts),
            event_exists=event_exists,
            locally_visible=maximum.locally_visible or any(item.locally_visible for item in contacts),
            maximum_magnitude=maximum.umbral_magnitude,
            maximum_obscuration=None,
            observer_generation=observer_generation,
            kernel_generation=self._ephemeris.kernel_generation,
            quality=maximum.geometry_quality,
            ephemeris_query_count=(
                getattr(self._ephemeris, "event_query_count", query_start) - query_start
            ),
            duration_ms=(time.perf_counter() - started) * 1000.0,
            temporal_tolerance_seconds=self.temporal_tolerance_seconds,
            angular_tolerance_deg=self.angular_tolerance_deg,
        )

    def _refine_roots(
        self,
        times: list[float],
        values: list[float],
        equation: Callable[[float], float],
        cancel: threading.Event | None,
    ) -> list[float]:
        roots = []
        for index in range(len(times) - 1):
            first = values[index]
            second = values[index + 1]
            if first == 0.0:
                roots.append(times[index])
            if first * second < 0.0:
                roots.append(
                    _refine_root(
                        equation,
                        times[index],
                        times[index + 1],
                        self.temporal_tolerance_seconds,
                        self.angular_tolerance_deg,
                        cancel,
                    )
                )
        if values[-1] == 0.0:
            roots.append(times[-1])
        return _deduplicate_roots(roots, self.temporal_tolerance_seconds)


class SolarEclipseFootprintSolver:
    """Topocentric classification and central-band boundaries at one UTC."""

    def __init__(
        self,
        ephemeris: AstronomicalEventEphemerisPort,
        *,
        angular_tolerance_deg: float = 1.0e-8,
        latitude_tolerance_deg: float = 1.0e-6,
    ) -> None:
        self._ephemeris = ephemeris
        self.angular_tolerance_deg = angular_tolerance_deg
        self.latitude_tolerance_deg = latitude_tolerance_deg
        self.classification_count = 0

    def classify_observer(
        self,
        latitude_deg: float,
        longitude_deg: float,
        elevation_m: float,
        utc: datetime,
    ) -> SolarEclipseState:
        observer = ScientificObserver(latitude_deg, longitude_deg, elevation_m)
        # Every invocation performs its own topocentric Sun/Moon query.  No
        # global classification or interpolated centre separation is reused.
        sample = self._ephemeris.event_ephemeris(
            _as_utc(utc), observer, ("sun", "moon")
        )
        sun = sample.body("sun")
        moon = sample.body("moon")
        if sun is None or moon is None:
            raise RuntimeError("Topocentric Sun/Moon ephemeris unavailable")
        self.classification_count += 1
        return solar_eclipse_state(sun, moon, quality=sample.quality)

    def central_band_limits(
        self,
        longitude_deg: float,
        elevation_m: float,
        utc: datetime,
        *,
        scan_step_deg: float = 0.05,
    ) -> CentralBandLimits | None:
        if scan_step_deg <= 0.0 or scan_step_deg > 1.0:
            raise ValueError("scan_step_deg must be in (0, 1]")

        def internal_contact(latitude: float) -> float:
            state = self.classify_observer(
                latitude, longitude_deg, elevation_m, utc
            )
            return state.center_separation_deg - abs(
                state.moon_angular_radius_deg - state.sun_angular_radius_deg
            )

        samples: list[tuple[float, float]] = []
        latitude = -89.95
        while latitude <= 89.9500001:
            samples.append((latitude, internal_contact(latitude)))
            latitude += scan_step_deg
        brackets = []
        for first, second in zip(samples, samples[1:]):
            if first[1] == 0.0:
                brackets.append((first[0], first[0]))
            elif first[1] * second[1] < 0.0:
                brackets.append((first[0], second[0]))
        if len(brackets) < 2:
            return None
        roots = [
            _refine_scalar_root(
                internal_contact,
                low,
                high,
                self.latitude_tolerance_deg,
                self.angular_tolerance_deg,
            )
            for low, high in brackets
        ]
        return CentralBandLimits(
            south_latitude_deg=min(roots),
            north_latitude_deg=max(roots),
            longitude_deg=longitude_deg,
            utc=_as_utc(utc),
            angular_tolerance_deg=self.angular_tolerance_deg,
            latitude_tolerance_deg=self.latitude_tolerance_deg,
        )


SearchPublisher = Callable[[AstronomicalEventSearchResult], Awaitable[int | None]]


class EventSearchCoordinator:
    """Cancelable latest-wins async search using the process default executor."""

    def __init__(
        self,
        searcher: AstronomicalEventSearcher,
        publisher: SearchPublisher,
    ) -> None:
        self._searcher = searcher
        self._publisher = publisher
        self._task: asyncio.Task[None] | None = None
        self._tasks: set[asyncio.Task[None]] = set()
        self._cancel: threading.Event | None = None
        self._latest_request_id = ""
        self.request_count = 0
        self.cancel_count = 0
        self.stale_count = 0
        self.last_duration_ms = 0.0
        self.last_query_count = 0

    def request(
        self,
        *,
        request_id: str,
        event_type: EclipseKind,
        observer: ScientificObserver,
        observer_generation: int,
        start_utc: datetime,
        end_utc: datetime,
    ) -> None:
        if self._cancel is not None:
            self._cancel.set()
            self.cancel_count += 1
        cancel = threading.Event()
        self._cancel = cancel
        self._latest_request_id = request_id
        self.request_count += 1
        self._task = asyncio.create_task(
            self._run(
                request_id,
                event_type,
                observer,
                observer_generation,
                start_utc,
                end_utc,
                cancel,
            ),
            name=f"event-search-{request_id}",
        )
        self._tasks.add(self._task)
        self._task.add_done_callback(self._tasks.discard)

    async def close(self) -> None:
        if self._cancel is not None:
            self._cancel.set()
        if self._tasks:
            await asyncio.gather(*tuple(self._tasks), return_exceptions=True)

    def metrics(self) -> dict[str, int | float]:
        return {
            "event_search_request_count": self.request_count,
            "event_search_cancel_count": self.cancel_count,
            "event_search_stale_count": self.stale_count,
            "event_search_duration_ms": self.last_duration_ms,
            "event_search_ephemeris_query_count": self.last_query_count,
        }

    async def _run(
        self,
        request_id: str,
        event_type: EclipseKind,
        observer: ScientificObserver,
        observer_generation: int,
        start_utc: datetime,
        end_utc: datetime,
        cancel: threading.Event,
    ) -> None:
        try:
            method = (
                self._searcher.search_solar
                if event_type is EclipseKind.SOLAR
                else self._searcher.search_lunar
            )
            result = await asyncio.to_thread(
                method,
                request_id,
                observer,
                observer_generation,
                start_utc,
                end_utc,
                cancel=cancel,
            )
        except EventSearchCancelled:
            return
        except Exception:
            log.exception("Astronomical event search failed request=%s", request_id)
            return
        if cancel.is_set() or request_id != self._latest_request_id:
            self.stale_count += 1
            return
        self.last_duration_ms = result.duration_ms
        self.last_query_count = result.ephemeris_query_count
        await self._publisher(result)


def _solar_contact(
    name: str,
    timestamp: float,
    state_at: Callable[[float], SolarEclipseState],
) -> EclipseContact:
    state = state_at(timestamp)
    return EclipseContact(
        name=name,
        instant_utc=datetime.fromtimestamp(timestamp, timezone.utc),
        locally_visible=state.locally_visible,
        source_altitude_deg=state.source_altitude_deg,
    )


def _lunar_contact(
    name: str,
    timestamp: float,
    state_at: Callable[[float], LunarEclipseState],
) -> EclipseContact:
    state = state_at(timestamp)
    return EclipseContact(
        name=name,
        instant_utc=datetime.fromtimestamp(timestamp, timezone.utc),
        locally_visible=state.locally_visible,
        source_altitude_deg=state.source_altitude_deg,
    )


def _coarse_times(start: float, end: float, step: float) -> list[float]:
    if step <= 0.0:
        raise ValueError("Coarse step must be positive")
    count = max(1, math.ceil((end - start) / step))
    return [start + (end - start) * index / count for index in range(count + 1)]


def _refine_root(
    equation: Callable[[float], float],
    low: float,
    high: float,
    temporal_tolerance: float,
    angular_tolerance: float,
    cancel: threading.Event | None,
) -> float:
    low_value = equation(low)
    high_value = equation(high)
    if low_value == 0.0:
        return low
    if high_value == 0.0:
        return high
    if low_value * high_value > 0.0:
        raise ValueError("Root refinement requires a bracket")
    for _ in range(96):
        _check_cancel(cancel)
        middle = (low + high) * 0.5
        value = equation(middle)
        if abs(value) <= angular_tolerance or high - low <= temporal_tolerance:
            return middle
        if low_value * value <= 0.0:
            high = middle
            high_value = value
        else:
            low = middle
            low_value = value
    return (low + high) * 0.5


def _refine_scalar_root(
    equation: Callable[[float], float],
    low: float,
    high: float,
    coordinate_tolerance: float,
    value_tolerance: float,
) -> float:
    if low == high:
        return low
    low_value = equation(low)
    high_value = equation(high)
    if low_value * high_value > 0.0:
        raise ValueError("Scalar root requires a bracket")
    for _ in range(96):
        middle = (low + high) * 0.5
        value = equation(middle)
        if abs(value) <= value_tolerance or high - low <= coordinate_tolerance:
            return middle
        if low_value * value <= 0.0:
            high = middle
            high_value = value
        else:
            low = middle
            low_value = value
    return (low + high) * 0.5


def _refine_minimum(
    objective: Callable[[float], float],
    low: float,
    high: float,
    temporal_tolerance: float,
    cancel: threading.Event | None,
) -> float:
    if high <= low:
        return low
    inverse_phi = (math.sqrt(5.0) - 1.0) * 0.5
    first = high - (high - low) * inverse_phi
    second = low + (high - low) * inverse_phi
    first_value = objective(first)
    second_value = objective(second)
    while high - low > temporal_tolerance:
        _check_cancel(cancel)
        if first_value <= second_value:
            high, second, second_value = second, first, first_value
            first = high - (high - low) * inverse_phi
            first_value = objective(first)
        else:
            low, first, first_value = first, second, second_value
            second = low + (high - low) * inverse_phi
            second_value = objective(second)
    return (low + high) * 0.5


def _deduplicate_roots(values: list[float], tolerance: float) -> list[float]:
    result = []
    for value in sorted(values):
        if not result or value - result[-1] > tolerance:
            result.append(value)
    return result


def _validated_interval(start: datetime, end: datetime) -> tuple[datetime, datetime]:
    first = _as_utc(start)
    second = _as_utc(end)
    if second <= first:
        raise ValueError("Event search interval must be positive")
    if second - first > timedelta(days=31):
        raise ValueError("Event search interval is limited to 31 days")
    return first, second


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("Event instants must be timezone-aware")
    return value.astimezone(timezone.utc)


def _check_cancel(cancel: threading.Event | None) -> None:
    if cancel is not None and cancel.is_set():
        raise EventSearchCancelled()


def _percentile(samples: list[float], fraction: float) -> float:
    if not samples:
        return 0.0
    return float(samples[round((len(samples) - 1) * fraction)])
