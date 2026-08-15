"""Predictive refresh policy for the scientific flight horizon.

The visible DEM mesh is a long-lived GPU resource.  This policy therefore
never treats an aircraft stop or a landing as a reason to recompute terrain.
While moving, it starts a profile refresh early enough for the measured local
preparation time, with a bounded lead distance.
"""

from __future__ import annotations

from dataclasses import dataclass
import math


_MIN_MOVING_SPEED_MPS = 0.5
_MIN_LEAD_SECONDS = 12.0
_MAX_LEAD_SECONDS = 45.0
_MIN_REFRESH_DISTANCE_M = 1_000.0
_MAX_REFRESH_DISTANCE_M = 10_000.0
_MIN_EYE_DELTA_M = 25.0
# A sweep remains useful through ordinary steering. Only a turn of more than
# 60 degrees makes its predicted detail chunk unsuitable for the new route.
_STREAM_DIRECTION_DOT_MIN = 0.5


@dataclass(frozen=True, slots=True)
class FlightTerrainRefreshDecision:
    """Reasoned result so callers can log or expose refresh intent."""

    should_refresh: bool
    lead_distance_m: float
    reason: str


@dataclass(frozen=True, slots=True)
class FlightTerrainStreamDecision:
    """Whether a running DEM detail sweep remains useful to the flight."""

    keep_active_build: bool
    reason: str


@dataclass(frozen=True, slots=True)
class FlightVisibilityWindowDecision:
    """Whether the resident visual window still honours the live settings."""

    should_refresh: bool
    requested_radius_m: float
    remaining_radius_m: float
    reason: str


def decide_flight_profile_refresh(
    *,
    distance_since_profile_m: float,
    eye_delta_m: float,
    speed_mps: float,
    measured_prepare_ms: float,
) -> FlightTerrainRefreshDecision:
    """Decide a profile refresh from live velocity and measured capacity.

    A stopped camera returns ``should_refresh=False`` by construction.  The
    first measured terrain/profile preparation supplies the lead time for the
    next moving refresh; a conservative 12-second lead is used until that
    measurement exists.
    """

    speed = max(0.0, float(speed_mps))
    if speed < _MIN_MOVING_SPEED_MPS:
        return FlightTerrainRefreshDecision(False, 0.0, "stationary")
    measured_seconds = max(0.0, float(measured_prepare_ms)) / 1_000.0
    lead_seconds = min(
        _MAX_LEAD_SECONDS,
        max(_MIN_LEAD_SECONDS, measured_seconds * 1.5),
    )
    lead_distance_m = min(
        _MAX_REFRESH_DISTANCE_M,
        max(_MIN_REFRESH_DISTANCE_M, speed * lead_seconds),
    )
    if abs(float(eye_delta_m)) >= _MIN_EYE_DELTA_M:
        return FlightTerrainRefreshDecision(True, lead_distance_m, "eye-height")
    if float(distance_since_profile_m) >= lead_distance_m:
        return FlightTerrainRefreshDecision(True, lead_distance_m, "predicted-boundary")
    return FlightTerrainRefreshDecision(False, lead_distance_m, "inside-lead-window")


def decide_flight_stream_continuation(
    *,
    active_velocity_east_mps: float,
    active_velocity_north_mps: float,
    current_velocity_east_mps: float,
    current_velocity_north_mps: float,
) -> FlightTerrainStreamDecision:
    """Keep a running sweep unless the aircraft has made it obsolete.

    Progress is more valuable than repeatedly chasing the current camera
    position. Stopping, slowing down, or modest steering therefore preserves
    the running worker. A substantial route change may cancel it so the next
    request prepares terrain in the new direction.
    """

    active_length = math.hypot(active_velocity_east_mps, active_velocity_north_mps)
    current_length = math.hypot(current_velocity_east_mps, current_velocity_north_mps)
    if current_length < _MIN_MOVING_SPEED_MPS:
        return FlightTerrainStreamDecision(True, "stationary")
    if active_length < _MIN_MOVING_SPEED_MPS:
        return FlightTerrainStreamDecision(True, "no-direction")
    direction_dot = (
        active_velocity_east_mps * current_velocity_east_mps
        + active_velocity_north_mps * current_velocity_north_mps
    ) / (active_length * current_length)
    if direction_dot >= _STREAM_DIRECTION_DOT_MIN:
        return FlightTerrainStreamDecision(True, "compatible-heading")
    return FlightTerrainStreamDecision(False, "route-diverged")


def decide_visibility_window_refresh(
    *,
    distance_from_loaded_center_m: float,
    loaded_radius_m: float,
    requested_radius_m: float,
    lead_distance_m: float,
    force: bool = False,
) -> FlightVisibilityWindowDecision:
    """Keep the user-selected radius centred on successive live positions.

    A range change invalidates the spatial window even while the camera is
    still well inside the old one. Otherwise the next window starts before
    the observer consumes the loaded radius. The caller decides whether a
    stationary observer may launch work (explicit regeneration does; normal
    streaming does not).
    """

    requested = max(1.0, float(requested_radius_m))
    loaded = max(0.0, float(loaded_radius_m))
    distance = max(0.0, float(distance_from_loaded_center_m))
    lead = max(0.0, float(lead_distance_m))
    remaining = max(0.0, loaded - distance)
    if force:
        return FlightVisibilityWindowDecision(True, requested, remaining, "forced")
    if loaded <= 0.0:
        return FlightVisibilityWindowDecision(True, requested, remaining, "uninitialized")
    tolerance = max(1.0, requested * 1e-6)
    if abs(loaded - requested) > tolerance:
        return FlightVisibilityWindowDecision(True, requested, remaining, "range-changed")
    if remaining <= lead:
        return FlightVisibilityWindowDecision(True, requested, remaining, "predicted-boundary")
    return FlightVisibilityWindowDecision(False, requested, remaining, "inside-visible-window")
