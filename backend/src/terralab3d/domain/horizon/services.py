"""Domain services which apply the one active horizon authority."""

from __future__ import annotations

from dataclasses import replace

from terralab3d.domain.horizon.models import HorizonProfile
from terralab3d.domain.solar_system.models import ApparentBodyState, SolarSystemSnapshot


class HorizonVisibilityEnricher:
    """Enrich ephemerides after SPICE/Skyfield; raster never enters ephemeris."""

    def enrich(self, snapshot: SolarSystemSnapshot, profile: HorizonProfile) -> SolarSystemSnapshot:
        def enrich_body(body: ApparentBodyState | None) -> ApparentBodyState | None:
            if body is None:
                return None
            horizon = profile.elevation_at_azimuth(body.horizontal.azimuth_deg)
            return replace(
                body,
                geometric_elevation_deg=float(body.horizontal.altitude_deg),
                horizon_elevation_deg=float(horizon),
                horizon_visible=bool(
                    body.horizontal.altitude_deg + body.angular_radius_deg > horizon
                ),
            )

        sun = enrich_body(snapshot.sun)
        assert sun is not None
        moon = enrich_body(snapshot.moon)
        planets = tuple(body for item in snapshot.planets if (body := enrich_body(item)) is not None)
        satellites = tuple(body for item in snapshot.satellites if (body := enrich_body(item)) is not None)
        return replace(
            snapshot,
            sun=sun,
            moon=moon,
            planets=planets,
            satellites=satellites,
            satellite_visible_count=sum(int(body.horizon_visible) for body in satellites),
        )
