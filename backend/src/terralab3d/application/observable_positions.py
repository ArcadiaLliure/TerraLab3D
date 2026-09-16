"""Adapters that expose all supported object families through one position port."""

from __future__ import annotations

import math
from datetime import datetime

from terralab3d.application.ports.astronomical_events import (
    AstronomicalEventEphemerisPort,
)
from terralab3d.domain.geometry import CartesianDirection
from terralab3d.domain.solar_system.models import ScientificObserver
from terralab3d.domain.stars.calculations import equatorial_to_enu_matrix
from terralab3d.domain.time.engine import AstronomicalEngine
from terralab3d.domain.visibility.models import (
    ApparentPosition,
    ObservableFamily,
    ObservableObject,
)


class ObservablePositionService:
    """Route a typed observable to its real scientific adapter."""

    def __init__(
        self,
        ephemeris: AstronomicalEventEphemerisPort | None,
        time_engine: AstronomicalEngine | None = None,
    ) -> None:
        self._ephemeris = ephemeris
        self._time = time_engine or AstronomicalEngine()

    @property
    def generation(self) -> str:
        if self._ephemeris is None:
            return "fixed-equatorial-v1"
        return self._ephemeris.kernel_generation

    def position_at(
        self,
        observable: ObservableObject,
        instant_utc: datetime,
        observer: ScientificObserver,
    ) -> ApparentPosition:
        if observable.family in (
            ObservableFamily.SOLAR_SYSTEM,
            ObservableFamily.SATELLITE,
        ):
            return self._solar_system_position(observable, instant_utc, observer)
        if observable.family is ObservableFamily.CONSTELLATION:
            raise ValueError("Constellation geometry is unavailable until Pas 23")
        return self._fixed_equatorial_position(observable, instant_utc, observer)

    def _solar_system_position(
        self,
        observable: ObservableObject,
        instant_utc: datetime,
        observer: ScientificObserver,
    ) -> ApparentPosition:
        if self._ephemeris is None or not observable.body_id:
            raise ValueError("This solar-system observable has no ephemeris adapter")
        snapshot = self._ephemeris.event_ephemeris(
            instant_utc,
            observer,
            (observable.body_id,),
            include_body_orientation=False,
            allow_unknown_radius=True,
        )
        body = snapshot.body(observable.body_id)
        if body is None:
            raise RuntimeError(f"Body {observable.body_id!r} is absent from ephemeris")
        east, up, north = body.direction_enu
        altitude, azimuth = _horizontal_from_enu(east, up, north)
        return ApparentPosition(
            instant_utc=instant_utc,
            direction_enu=CartesianDirection(east, up, north),
            azimuth_deg=azimuth,
            altitude_deg=altitude,
            valid=True,
            quality=snapshot.quality.value,
        )

    def _fixed_equatorial_position(
        self,
        observable: ObservableObject,
        instant_utc: datetime,
        observer: ScientificObserver,
    ) -> ApparentPosition:
        if observable.right_ascension_deg is None or observable.declination_deg is None:
            raise ValueError("Fixed observable requires right ascension and declination")
        ra = math.radians(observable.right_ascension_deg)
        dec = math.radians(observable.declination_deg)
        cos_dec = math.cos(dec)
        equatorial = (
            cos_dec * math.cos(ra),
            cos_dec * math.sin(ra),
            math.sin(dec),
        )
        lst = self._time.local_sidereal_angle_deg(instant_utc, observer.longitude_deg)
        matrix = equatorial_to_enu_matrix(
            math.radians(observer.latitude_deg),
            math.radians(lst),
        )
        east = float(matrix[0, 0] * equatorial[0] + matrix[0, 1] * equatorial[1])
        north = float(
            matrix[1, 0] * equatorial[0]
            + matrix[1, 1] * equatorial[1]
            + matrix[1, 2] * equatorial[2]
        )
        up = float(
            matrix[2, 0] * equatorial[0]
            + matrix[2, 1] * equatorial[1]
            + matrix[2, 2] * equatorial[2]
        )
        altitude, azimuth = _horizontal_from_enu(east, up, north)
        return ApparentPosition(
            instant_utc=instant_utc,
            direction_enu=CartesianDirection(east, up, north),
            azimuth_deg=azimuth,
            altitude_deg=altitude,
            valid=True,
            quality="scientific",
        )


def _horizontal_from_enu(east: float, up: float, north: float) -> tuple[float, float]:
    length = math.sqrt(east * east + up * up + north * north)
    if length <= 0.0:
        raise ValueError("Apparent direction must be non-zero")
    altitude = math.degrees(math.asin(max(-1.0, min(1.0, up / length))))
    azimuth = math.degrees(math.atan2(east, north)) % 360.0
    return altitude, azimuth
