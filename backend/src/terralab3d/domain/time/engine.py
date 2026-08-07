"""Motor d'alta precisió per a càlculs astronòmics de temps.
Implementació anàloga a AstroEngine de TerraLab.
"""

import math
from datetime import datetime

class AstronomicalEngine:
    """Calcula JD, LST i paràmetres solars bàsics (per a la UI)."""

    DEG_TO_RAD = math.pi / 180.0
    RAD_TO_DEG = 180.0 / math.pi

    def julian_day(self, dt_utc: datetime) -> float:
        """Calcula el Dia Julià (JD) a partir d'un instant UTC."""
        a = (14 - dt_utc.month) // 12
        y = dt_utc.year + 4800 - a
        m = dt_utc.month + 12 * a - 3

        jd = (
            dt_utc.day
            + ((153 * m + 2) // 5)
            + 365 * y
            + y // 4
            - y // 100
            + y // 400
            - 32045
        )
        jd += (
            (dt_utc.hour - 12) / 24.0
            + dt_utc.minute / 1440.0
            + dt_utc.second / 86400.0
            + dt_utc.microsecond / 86400000000.0
        )
        return jd

    def julian_centuries(self, dt_utc: datetime) -> float:
        """Calcula els segles julians (T) des de J2000.0 incloent Delta T."""
        jd = self.julian_day(dt_utc)
        # Delta T aproximat per a 2026 (~72 s)
        delta_t_days = 72.0 / 86400.0
        jd_tdb = jd + delta_t_days
        t = (jd_tdb - 2451545.0) / 36525.0
        return t

    def local_sidereal_angle_deg(self, dt_utc: datetime, longitude_deg: float) -> float:
        """Calcula el Temps Sideral Local (LST) en graus."""
        jd = self.julian_day(dt_utc)
        t = (jd - 2451545.0) / 36525.0
        gmst = (
            280.46061837
            + 360.98564736629 * (jd - 2451545.0)
            + 0.000387933 * (t ** 2)
        )
        lst = (gmst + longitude_deg) % 360.0
        return lst

    def fast_sun_altitude_for_day(self, dt_utc: datetime, lat: float, lon: float, hour: float) -> float:
        """Càlcul ràpid de l'altura del sol usat exclusivament pel gradient de la UI."""
        # 1. UTC Estimate
        ut_hour = hour % 24.0
        day_of_year = dt_utc.timetuple().tm_yday

        # 2. Declination
        dec_deg = -23.44 * math.cos(math.radians(360 / 365 * (day_of_year + 10)))
        dec_rad = math.radians(dec_deg)
        lat_rad = math.radians(lat)

        # 3. Hour Angle
        solar_time = ut_hour + lon / 15.0
        ha_deg = (solar_time - 12.0) * 15.0
        ha_rad = math.radians(ha_deg)

        # 4. Altitude
        sin_alt = math.sin(dec_rad) * math.sin(lat_rad) + math.cos(dec_rad) * math.cos(lat_rad) * math.cos(ha_rad)
        return math.degrees(math.asin(max(-1.0, min(1.0, sin_alt))))

    def generate_sun_altitude_samples(self, dt_utc: datetime, lat: float, lon: float, steps: int = 96) -> list[float]:
        """Genera mostres de l'altura del sol per a tot el dia (per defecte cada 15 minuts = 96 mostres)."""
        samples = []
        step_hours = 24.0 / steps
        for i in range(steps + 1):
            h = min(i * step_hours, 24.0)
            alt = self.fast_sun_altitude_for_day(dt_utc, lat, lon, h)
            samples.append(round(alt, 2))
        return samples
