"""Pure, deterministic eclipse and occultation geometry.

Contact solvers deliberately use the smooth spherical limb.  LOLA terrain is
accepted only by :func:`solar_totality_appearance` for Baily beads and the
diamond ring, never by the C1--C4 equations.
"""

from __future__ import annotations

import math

from .models import (
    ApparentEventBody,
    AstronomicalEventEphemeris,
    BailyBead,
    CoronaStructure,
    DiscOverlap,
    EclipseSceneAppearance,
    GeometryQuality,
    LunarEclipseClassification,
    LunarEclipseState,
    LunarLimbProfile,
    OccultationClassification,
    OccultationState,
    SolarAppearancePhase,
    SolarCoronaState,
    SolarEclipseClassification,
    SolarEclipseState,
    SolarTotalityAppearance,
    TerrainCorrectedLimbState,
    Vector3,
)

SUN_RADIUS_KM = 695_700.0
EARTH_EQUATORIAL_RADIUS_KM = 6_378.1366
MOON_RADIUS_KM = 1_737.4
# Danjon's traditional 1/50 enlargement of the geometric terrestrial shadow.
# It is an explicit, approximate visual/observational correction, not DE440.
DEFAULT_EARTH_SHADOW_ATMOSPHERE_FACTOR = 1.02
# Visual transfer floors and widths.  These never participate in eclipse
# classification or in the numerical contact solver.
MINIMUM_TOTALITY_SKY_DIMMING = 0.06
CORONA_INTERNAL_CONTACT_WIDTH_SOLAR_RADII = 0.005


def normalize_vector(vector: Vector3) -> Vector3:
    length = math.sqrt(dot(vector, vector))
    if length <= 1.0e-15:
        raise ValueError("Cannot normalize a zero-length direction")
    return tuple(component / length for component in vector)  # type: ignore[return-value]


def dot(first: Vector3, second: Vector3) -> float:
    return sum(a * b for a, b in zip(first, second, strict=True))


def cross(first: Vector3, second: Vector3) -> Vector3:
    return (
        first[1] * second[2] - first[2] * second[1],
        first[2] * second[0] - first[0] * second[2],
        first[0] * second[1] - first[1] * second[0],
    )


def angular_separation_deg(first: Vector3, second: Vector3) -> float:
    """Stable great-circle separation, including parallel/antiparallel vectors.

    ``atan2(|a×b|, a·b)`` avoids the loss of precision that a raw ``acos`` has
    for sub-arcminute separations while remaining defined at 0 and 180 degrees.
    """

    a = normalize_vector(first)
    b = normalize_vector(second)
    sine = math.sqrt(dot(cross(a, b), cross(a, b)))
    cosine = max(-1.0, min(1.0, dot(a, b)))
    return math.degrees(math.atan2(sine, cosine))


def horizontal_direction_enu(azimuth_deg: float, altitude_deg: float) -> Vector3:
    """Return canonical East/North/Up for a horizontal coordinate."""

    azimuth = math.radians(azimuth_deg)
    altitude = math.radians(altitude_deg)
    horizontal = math.cos(altitude)
    return (
        horizontal * math.sin(azimuth),
        horizontal * math.cos(azimuth),
        math.sin(altitude),
    )


def position_angle_deg(center_icrf: Vector3, target_icrf: Vector3) -> float:
    """Position angle eastward from celestial north around ``center_icrf``."""

    line = normalize_vector(center_icrf)
    north_reference: Vector3 = (0.0, 0.0, 1.0)
    north = _reject(north_reference, line)
    if dot(north, north) <= 1.0e-20:
        north = _reject((1.0, 0.0, 0.0), line)
    north = normalize_vector(north)
    east = normalize_vector(cross(north, line))
    target = _reject(normalize_vector(target_icrf), line)
    if dot(target, target) <= 1.0e-30:
        return 0.0
    target = normalize_vector(target)
    return math.degrees(math.atan2(dot(target, east), dot(target, north))) % 360.0


def disc_overlap(
    center_separation: float,
    foreground_radius: float,
    background_radius: float,
) -> DiscOverlap:
    """Robust area overlap of two circles in any consistent angular unit."""

    distance = _finite_non_negative(center_separation, "center_separation")
    foreground = _finite_positive(foreground_radius, "foreground_radius")
    background = _finite_positive(background_radius, "background_radius")
    foreground_area = math.pi * foreground * foreground
    background_area = math.pi * background * background
    if distance >= foreground + background:
        area = 0.0
    elif distance <= abs(foreground - background):
        area = math.pi * min(foreground, background) ** 2
    else:
        first_cosine = _clamp(
            (distance * distance + foreground * foreground - background * background)
            / (2.0 * distance * foreground),
            -1.0,
            1.0,
        )
        second_cosine = _clamp(
            (distance * distance + background * background - foreground * foreground)
            / (2.0 * distance * background),
            -1.0,
            1.0,
        )
        radical = max(
            0.0,
            (-distance + foreground + background)
            * (distance + foreground - background)
            * (distance - foreground + background)
            * (distance + foreground + background),
        )
        area = (
            foreground * foreground * math.acos(first_cosine)
            + background * background * math.acos(second_cosine)
            - 0.5 * math.sqrt(radical)
        )
    return DiscOverlap(
        overlap_area_square_deg=area,
        foreground_area_fraction=_clamp(area / foreground_area, 0.0, 1.0),
        background_area_fraction=_clamp(area / background_area, 0.0, 1.0),
    )


def solar_eclipse_state(
    sun: ApparentEventBody,
    moon: ApparentEventBody,
    *,
    separation_rate_deg_s: float | None = None,
    quality: GeometryQuality = GeometryQuality.SCIENTIFIC,
) -> SolarEclipseState:
    separation = angular_separation_deg(sun.direction_icrf, moon.direction_icrf)
    sun_radius = _finite_positive(sun.angular_radius_deg, "sun angular radius")
    moon_radius = _finite_positive(moon.angular_radius_deg, "moon angular radius")
    overlap = disc_overlap(separation, moon_radius, sun_radius)
    external = sun_radius + moon_radius
    internal = abs(sun_radius - moon_radius)
    # Classification is strictly geometric.  Obscuration is deliberately not
    # consulted: 99.9% remains partial until the internal-contact equation is
    # actually satisfied for this specific topocentric observer.
    if separation >= external:
        classification = SolarEclipseClassification.NONE
    elif separation > internal:
        classification = SolarEclipseClassification.PARTIAL
    elif moon_radius < sun_radius:
        classification = SolarEclipseClassification.ANNULAR
    else:
        classification = SolarEclipseClassification.TOTAL
    magnitude = max(0.0, (sun_radius + moon_radius - separation) / (2.0 * sun_radius))
    obscuration = overlap.background_area_fraction
    return SolarEclipseState(
        classification=classification,
        sun_angular_radius_deg=sun_radius,
        moon_angular_radius_deg=moon_radius,
        moon_to_sun_radius_ratio=moon_radius / sun_radius,
        center_separation_deg=separation,
        moon_position_angle_deg=position_angle_deg(sun.direction_icrf, moon.direction_icrf),
        eclipse_magnitude=magnitude,
        obscuration=obscuration,
        solar_disc_transmission=_clamp(1.0 - obscuration, 0.0, 1.0),
        source_altitude_deg=sun.altitude_deg,
        locally_visible=(sun.altitude_deg + sun_radius > 0.0),
        separation_rate_deg_s=separation_rate_deg_s,
        geometry_quality=quality,
    )


def lunar_eclipse_state(
    ephemeris: AstronomicalEventEphemeris,
    *,
    atmosphere_enlargement_factor: float = DEFAULT_EARTH_SHADOW_ATMOSPHERE_FACTOR,
) -> LunarEclipseState:
    moon = ephemeris.body("moon")
    earth_to_sun = ephemeris.earth_to_sun_icrf_km
    earth_to_moon = ephemeris.earth_to_moon_icrf_km
    if moon is None or earth_to_sun is None or earth_to_moon is None:
        return unavailable_lunar_eclipse_state(ephemeris.quality)
    sun_distance = math.sqrt(dot(earth_to_sun, earth_to_sun))
    moon_distance = math.sqrt(dot(earth_to_moon, earth_to_moon))
    if sun_distance <= SUN_RADIUS_KM or moon_distance <= MOON_RADIUS_KM:
        return unavailable_lunar_eclipse_state(GeometryQuality.UNAVAILABLE)

    axis = tuple(-value for value in normalize_vector(earth_to_sun))
    axial_distance = dot(earth_to_moon, axis)
    axis_point = tuple(axis[index] * axial_distance for index in range(3))
    offset_vector = tuple(axis_point[index] - earth_to_moon[index] for index in range(3))
    offset = math.sqrt(dot(offset_vector, offset_vector))
    if axial_distance <= 0.0:
        return unavailable_lunar_eclipse_state(ephemeris.quality)

    geometric_umbra = EARTH_EQUATORIAL_RADIUS_KM - (
        axial_distance * (SUN_RADIUS_KM - EARTH_EQUATORIAL_RADIUS_KM) / sun_distance
    )
    geometric_penumbra = EARTH_EQUATORIAL_RADIUS_KM + (
        axial_distance * (SUN_RADIUS_KM + EARTH_EQUATORIAL_RADIUS_KM) / sun_distance
    )
    factor = _finite_positive(atmosphere_enlargement_factor, "atmosphere factor")
    umbra = max(0.0, geometric_umbra * factor)
    penumbra = max(umbra, geometric_penumbra * factor)
    moon_radius = moon.physical_radius_km
    if offset >= penumbra + moon_radius:
        classification = LunarEclipseClassification.NONE
    elif offset >= umbra + moon_radius:
        classification = LunarEclipseClassification.PENUMBRAL
    elif umbra >= moon_radius and offset <= umbra - moon_radius:
        classification = LunarEclipseClassification.TOTAL
    else:
        classification = LunarEclipseClassification.PARTIAL

    penumbral_magnitude = max(0.0, (penumbra + moon_radius - offset) / (2.0 * moon_radius))
    umbral_magnitude = max(0.0, (umbra + moon_radius - offset) / (2.0 * moon_radius))
    pen_overlap = disc_overlap(offset, penumbra, moon_radius).background_area_fraction
    umb_overlap = disc_overlap(offset, max(umbra, 1.0e-9), moon_radius).background_area_fraction
    penumbra_only = max(0.0, pen_overlap - umb_overlap)
    mean_transmission = _clamp(1.0 - 0.45 * penumbra_only - 0.92 * umb_overlap, 0.02, 1.0)
    observer_position = ephemeris.observer_position_icrf_km or (0.0, 0.0, 0.0)
    shadow_center_direction = normalize_vector(
        tuple(
            axis_point[index] - observer_position[index]
            for index in range(3)
        )
    )
    return LunarEclipseState(
        classification=classification,
        penumbra_radius_km=penumbra,
        umbra_radius_km=umbra,
        moon_radius_km=moon_radius,
        shadow_axis_offset_km=offset,
        penumbral_magnitude=penumbral_magnitude,
        umbral_magnitude=umbral_magnitude,
        penumbra_radius_moon_radii=penumbra / moon_radius,
        umbra_radius_moon_radii=umbra / moon_radius,
        shadow_offset_moon_radii=offset / moon_radius,
        shadow_offset_position_angle_deg=position_angle_deg(
            moon.direction_icrf, shadow_center_direction
        ),
        mean_lunar_light_transmission=mean_transmission,
        source_altitude_deg=moon.altitude_deg,
        locally_visible=moon.altitude_deg + moon.angular_radius_deg > 0.0,
        atmosphere_enlargement_factor=factor,
        geometry_quality=ephemeris.quality,
    )


def occultation_state(
    foreground: ApparentEventBody,
    background: ApparentEventBody,
) -> OccultationState:
    separation = angular_separation_deg(
        foreground.direction_icrf, background.direction_icrf
    )
    front_radius = foreground.angular_radius_deg
    back_radius = background.angular_radius_deg
    if foreground.distance_km >= background.distance_km or separation >= front_radius + back_radius:
        classification = OccultationClassification.NONE
    elif separation <= abs(front_radius - back_radius):
        classification = (
            OccultationClassification.TOTAL
            if front_radius >= back_radius
            else OccultationClassification.TRANSIT
        )
    else:
        classification = OccultationClassification.PARTIAL
    return OccultationState(
        foreground=foreground.body_id,
        background=background.body_id,
        classification=classification,
        separation_deg=separation,
        foreground_radius_deg=front_radius,
        background_radius_deg=back_radius,
        foreground_distance_km=foreground.distance_km,
        background_distance_km=background.distance_km,
    )


def sky_eclipse_dimming_factor(solar: SolarEclipseState) -> float:
    """Approximate atmosphere response, separate from geometric transmission."""

    transmission = solar.solar_disc_transmission
    if not solar.locally_visible or transmission >= 0.999999:
        return 1.0
    # Scattered daylight does not track direct disc area linearly.  This visual
    # transfer is continuous and explicit; it does not alter altitude or Bortle.
    return _clamp(
        MINIMUM_TOTALITY_SKY_DIMMING
        + (1.0 - MINIMUM_TOTALITY_SKY_DIMMING) * transmission**0.42,
        MINIMUM_TOTALITY_SKY_DIMMING,
        1.0,
    )


def eclipse_scene_appearance(
    solar: SolarEclipseState,
    sky_dimming: float,
) -> EclipseSceneAppearance:
    strength = _smoothstep(0.88, 0.9995, solar.obscuration) if solar.locally_visible else 0.0
    return EclipseSceneAppearance(
        quality="visual",
        strength=strength,
        saturation=1.0 - 0.18 * strength,
        color_temperature_shift=-0.12 * strength,
        contrast=1.0 + 0.16 * strength,
        midtone_exposure=1.0 - 0.22 * strength,
        direct_to_diffuse_ratio=1.0 + (0.22 - 0.22 * sky_dimming) * strength,
    )


def magnetic_procedural_corona(
    solar: SolarEclipseState,
    solar_north_position_angle_deg: float,
) -> SolarCoronaState:
    visibility = _central_contact_appearance_proximity(solar)
    # Structures are expressed in the IAU_SUN frame.  Polar plumes are narrow
    # and radial; helmet/equatorial streamers are broader and longer.
    structures = (
        CoronaStructure("polar_plume", 2.0, 7.0, 1.85, 0.55),
        CoronaStructure("polar_plume", 178.0, 6.0, 1.78, 0.52),
        CoronaStructure("polar_plume", 14.0, 5.0, 1.62, 0.42),
        CoronaStructure("polar_plume", 194.0, 5.5, 1.66, 0.44),
        CoronaStructure("helmet_streamer", 82.0, 31.0, 3.45, 0.82),
        CoronaStructure("equatorial_streamer", 264.0, 25.0, 3.75, 0.88),
        CoronaStructure("mid_latitude_streamer", 122.0, 18.0, 2.65, 0.62),
        CoronaStructure("mid_latitude_streamer", 306.0, 20.0, 2.82, 0.66),
    )
    return SolarCoronaState(
        mode="magnetic_procedural_fallback",
        quality="approximate",
        solar_north_position_angle_deg=solar_north_position_angle_deg,
        visibility=visibility,
        structures=structures,
    )


def solar_totality_appearance(
    solar: SolarEclipseState,
    profile: LunarLimbProfile | None,
    *,
    solar_north_position_angle_deg: float,
) -> SolarTotalityAppearance:
    beads = _baily_beads(solar, profile)
    ingress = solar.separation_rate_deg_s is None or solar.separation_rate_deg_s <= 0.0
    if solar.classification is SolarEclipseClassification.TOTAL and not beads:
        phase = SolarAppearancePhase.TOTALITY
    else:
        phase = _terrain_contact_phase(beads, solar, ingress)
    proximity = _central_contact_appearance_proximity(solar)
    if phase in (
        SolarAppearancePhase.DIAMOND_INGRESS,
        SolarAppearancePhase.DIAMOND_EGRESS,
    ):
        visible_beads = (
            max(beads, key=lambda bead: bead.exposed_photosphere_area_square_deg),
        )
    elif phase is SolarAppearancePhase.PARTIAL:
        visible_beads = ()
    else:
        visible_beads = beads
    exposed_area = sum(
        bead.exposed_photosphere_area_square_deg for bead in visible_beads
    )
    return SolarTotalityAppearance(
        phase=phase,
        limb_quality=profile.quality if profile is not None else "unavailable",
        beads=visible_beads,
        dominant_photosphere_region_count=len(visible_beads),
        exposed_photosphere_area_square_deg=exposed_area,
        corona=magnetic_procedural_corona(solar, solar_north_position_angle_deg),
        chromosphere_visibility=proximity if phase is not SolarAppearancePhase.PARTIAL else 0.0,
        prominence_quality="visual/approximate",
        terrain_corrected_limb=_terrain_corrected_limb_state(solar, profile),
    )


def _terrain_contact_phase(
    beads: tuple[BailyBead, ...],
    solar: SolarEclipseState,
    ingress: bool,
) -> SolarAppearancePhase:
    """Separate a normal crescent, Baily beads and the final diamond region."""

    if not beads or _central_contact_appearance_proximity(solar) <= 0.0:
        return SolarAppearancePhase.PARTIAL
    widest = max(bead.angular_width_deg for bead in beads)
    if widest > 45.0:
        return SolarAppearancePhase.PARTIAL
    total_area = sum(bead.exposed_photosphere_area_square_deg for bead in beads)
    dominant_area = max(bead.exposed_photosphere_area_square_deg for bead in beads)
    if widest <= 25.0 and dominant_area >= total_area * 0.5:
        return (
            SolarAppearancePhase.DIAMOND_INGRESS
            if ingress
            else SolarAppearancePhase.DIAMOND_EGRESS
        )
    return (
        SolarAppearancePhase.BAILY_INGRESS
        if ingress
        else SolarAppearancePhase.BAILY_EGRESS
    )


def _terrain_corrected_limb_state(
    solar: SolarEclipseState,
    profile: LunarLimbProfile | None,
) -> TerrainCorrectedLimbState | None:
    if profile is None or not profile.samples or solar.moon_angular_radius_deg <= 0.0:
        return None
    scales = tuple(
        sample.angular_radius_deg / solar.moon_angular_radius_deg
        for sample in profile.samples
    )
    return TerrainCorrectedLimbState(
        dataset_id=profile.dataset_id,
        asset_sha256=profile.asset_sha256,
        radius_scale_samples=scales,
        maximum_radius_scale=max(scales),
    )


def unavailable_solar_eclipse_state(
    quality: GeometryQuality = GeometryQuality.UNAVAILABLE,
) -> SolarEclipseState:
    return SolarEclipseState(
        classification=SolarEclipseClassification.NONE,
        sun_angular_radius_deg=0.0,
        moon_angular_radius_deg=0.0,
        moon_to_sun_radius_ratio=0.0,
        center_separation_deg=180.0,
        moon_position_angle_deg=0.0,
        eclipse_magnitude=0.0,
        obscuration=0.0,
        solar_disc_transmission=1.0,
        source_altitude_deg=-90.0,
        locally_visible=False,
        separation_rate_deg_s=None,
        geometry_quality=quality,
    )


def _central_contact_appearance_proximity(solar: SolarEclipseState) -> float:
    """Visual ramp across only the last few seconds around internal contact.

    The smooth width controls appearance convergence; it is deliberately
    separate from the exact ``d <= |Rm - Rs|`` classification comparison.
    An annular eclipse never exposes a totality corona.
    """

    if (
        not solar.locally_visible
        or solar.moon_angular_radius_deg < solar.sun_angular_radius_deg
    ):
        return 0.0
    internal_gap = solar.center_separation_deg - abs(
        solar.moon_angular_radius_deg - solar.sun_angular_radius_deg
    )
    if internal_gap <= 0.0:
        return 1.0
    transition_width = (
        solar.sun_angular_radius_deg * CORONA_INTERNAL_CONTACT_WIDTH_SOLAR_RADII
    )
    return 1.0 - _smoothstep(0.0, transition_width, internal_gap)


def unavailable_lunar_eclipse_state(
    quality: GeometryQuality = GeometryQuality.UNAVAILABLE,
) -> LunarEclipseState:
    return LunarEclipseState(
        classification=LunarEclipseClassification.NONE,
        penumbra_radius_km=0.0,
        umbra_radius_km=0.0,
        moon_radius_km=MOON_RADIUS_KM,
        # Keep the wire contract valid JSON even in an unavailable fallback.
        shadow_axis_offset_km=1.0e30,
        penumbral_magnitude=0.0,
        umbral_magnitude=0.0,
        penumbra_radius_moon_radii=0.0,
        umbra_radius_moon_radii=0.0,
        shadow_offset_moon_radii=1.0e9,
        shadow_offset_position_angle_deg=0.0,
        mean_lunar_light_transmission=1.0,
        source_altitude_deg=-90.0,
        locally_visible=False,
        atmosphere_enlargement_factor=DEFAULT_EARTH_SHADOW_ATMOSPHERE_FACTOR,
        geometry_quality=quality,
    )


def _baily_beads(
    solar: SolarEclipseState,
    profile: LunarLimbProfile | None,
) -> tuple[BailyBead, ...]:
    if (
        profile is None
        or not profile.samples
        or solar.obscuration < 0.96
        or solar.classification is SolarEclipseClassification.TOTAL
    ):
        return ()
    # Sun centre relative to the Moon.  Position angles are east from north.
    sun_pa = (solar.moon_position_angle_deg + 180.0) % 360.0
    sun_pa_rad = math.radians(sun_pa)
    center_east = solar.center_separation_deg * math.sin(sun_pa_rad)
    center_north = solar.center_separation_deg * math.cos(sun_pa_rad)
    exposed: list[tuple[int, float, float]] = []
    for index, sample in enumerate(profile.samples):
        angle = math.radians(sample.position_angle_deg)
        ray_east = math.sin(angle)
        ray_north = math.cos(angle)
        along = center_east * ray_east + center_north * ray_north
        perpendicular_sq = max(
            0.0,
            solar.center_separation_deg**2 - along**2,
        )
        if perpendicular_sq >= solar.sun_angular_radius_deg**2:
            continue
        half_chord = math.sqrt(solar.sun_angular_radius_deg**2 - perpendicular_sq)
        inner = along - half_chord
        outer = along + half_chord
        radial_gap = outer - max(inner, sample.angular_radius_deg)
        if radial_gap <= 0.0:
            continue
        midpoint = max(inner, sample.angular_radius_deg) + radial_gap * 0.5
        solar_distance = math.sqrt(
            (midpoint * ray_east - center_east) ** 2
            + (midpoint * ray_north - center_north) ** 2
        )
        mu = math.sqrt(max(0.0, 1.0 - (solar_distance / solar.sun_angular_radius_deg) ** 2))
        limb_darkening = 0.4 + 0.6 * mu
        exposed.append((index, radial_gap, limb_darkening))
    if not exposed:
        return ()

    groups: list[list[tuple[int, float, float]]] = []
    current = [exposed[0]]
    for value in exposed[1:]:
        if value[0] == current[-1][0] + 1:
            current.append(value)
        else:
            groups.append(current)
            current = [value]
    groups.append(current)
    if len(groups) > 1 and groups[0][0][0] == 0 and groups[-1][-1][0] == len(profile.samples) - 1:
        groups[0] = groups[-1] + groups[0]
        groups.pop()

    step = 360.0 / len(profile.samples)
    beads: list[BailyBead] = []
    for group in groups:
        weights = [item[1] for item in group]
        weight_sum = sum(weights)
        if weight_sum <= 0.0:
            continue
        angles = [math.radians(profile.samples[item[0]].position_angle_deg) for item in group]
        east = sum(math.sin(angle) * weight for angle, weight in zip(angles, weights, strict=True))
        north = sum(math.cos(angle) * weight for angle, weight in zip(angles, weights, strict=True))
        pa = math.degrees(math.atan2(east, north)) % 360.0
        area = sum(item[1] * step * math.pi / 180.0 * solar.moon_angular_radius_deg for item in group)
        brightness = _clamp(
            sum(item[1] * item[2] for item in group) / weight_sum,
            0.0,
            1.0,
        )
        beads.append(BailyBead(pa, len(group) * step, area, brightness))
    return tuple(sorted(beads, key=lambda bead: bead.lunar_position_angle_deg))


def _reject(vector: Vector3, axis: Vector3) -> Vector3:
    projection = dot(vector, axis)
    return tuple(vector[index] - projection * axis[index] for index in range(3))  # type: ignore[return-value]


def _finite_positive(value: float, field: str) -> float:
    result = float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise ValueError(f"{field} must be finite and positive")
    return result


def _finite_non_negative(value: float, field: str) -> float:
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise ValueError(f"{field} must be finite and non-negative")
    return result


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _smoothstep(low: float, high: float, value: float) -> float:
    if high <= low:
        return 1.0 if value >= high else 0.0
    fraction = _clamp((value - low) / (high - low), 0.0, 1.0)
    return fraction * fraction * (3.0 - 2.0 * fraction)
