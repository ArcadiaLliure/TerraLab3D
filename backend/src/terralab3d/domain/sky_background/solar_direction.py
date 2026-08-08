"""Direcció solar, fase de crepuscle i càlculs solars reutilitzables.

Mòdul autoritat per a la posició solar dins de TerraLab3D.
Reutilitzable pel futur pas del Sistema Solar.

Semàntica del vector ENU:
    x = Est
    y = Amunt (zenit)
    z = Nord

No és radiative transfer — és un model geomètric precís
per a la posició aparent del Sol des de la superfície terrestre.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class TwilightPhase(str, Enum):
    """Fase categòrica del crepuscle basada en l'altitud solar."""
    DAY = "day"
    CIVIL = "civil"
    NAUTICAL = "nautical"
    ASTRONOMICAL = "astronomical"
    NIGHT = "night"


@dataclass(frozen=True, slots=True)
class SolarDirection:
    """Posició solar aparent des de l'observador.

    Atributs:
        altitude_deg: Altitud sobre l'horitzó [-90, +90].
        azimuth_deg: Azimut des del nord, sentit horari [0, 360).
        direction_enu: Vector unitari normalitzat (est, amunt, nord).
    """
    altitude_deg: float
    azimuth_deg: float
    direction_enu: tuple[float, float, float]


class SolarDirectionPort(Protocol):
    """Port abstracte per a la direcció solar aparent.

    Permet substituir l'algoritme solar sense canviar els consumidors.
    El futur pas del Sistema Solar pot proporcionar una implementació
    amb efemèrides completes.
    """

    def apparent_direction(
        self,
        utc_year: int,
        utc_month: int,
        utc_day: int,
        utc_hour: float,
        latitude_deg: float,
        longitude_deg: float,
    ) -> SolarDirection:
        """Retorna la direcció solar aparent per a un instant i ubicació."""
        ...


def twilight_phase(sun_altitude_deg: float) -> TwilightPhase:
    """Determina la fase categòrica de crepuscle.

    Llindars estàndard IAU:
        >= 0°        → day
        -6° .. 0°    → civil
        -12° .. -6°  → nautical
        -18° .. -12° → astronomical
        < -18°       → night
    """
    if sun_altitude_deg >= 0.0:
        return TwilightPhase.DAY
    if sun_altitude_deg >= -6.0:
        return TwilightPhase.CIVIL
    if sun_altitude_deg >= -12.0:
        return TwilightPhase.NAUTICAL
    if sun_altitude_deg >= -18.0:
        return TwilightPhase.ASTRONOMICAL
    return TwilightPhase.NIGHT


def twilight_factor(sun_altitude_deg: float) -> float:
    """Factor continu de nit [0, 1].

    0.0 = dia ple (sol >= 0°)
    1.0 = nit astronòmica (sol <= -18°)

    La transició és suau (smoothstep) per evitar salts visuals
    als boundaries -6°/-12°/-18°.
    """
    if sun_altitude_deg >= 0.0:
        return 0.0
    if sun_altitude_deg <= -18.0:
        return 1.0
    # Transició suau de 0° a -18° amb smoothstep
    t = -sun_altitude_deg / 18.0  # [0, 1] lineal
    # smoothstep: 3t² - 2t³
    return t * t * (3.0 - 2.0 * t)


def sun_direction_enu(altitude_deg: float, azimuth_deg: float) -> tuple[float, float, float]:
    """Converteix altitud/azimut solar a vector unitari ENU.

    Convencions:
        Azimut 0° = Nord, creix en sentit horari
        ENU: x=Est, y=Amunt, z=Nord
    """
    alt_rad = math.radians(altitude_deg)
    az_rad = math.radians(azimuth_deg)

    cos_alt = math.cos(alt_rad)
    east = cos_alt * math.sin(az_rad)
    up = math.sin(alt_rad)
    north = cos_alt * math.cos(az_rad)

    # Normalitzar per seguretat numèrica
    length = math.sqrt(east * east + up * up + north * north)
    if length < 1e-12:
        return (0.0, 0.0, 0.0)
    return (east / length, up / length, north / length)


class SolarSkyCalculator:
    """Calculador solar autoritatiu per al cel de TerraLab3D.

    Usa l'algoritme simplificat de l'AstronomicalEngine existent
    però retorna altitud, azimut i vector ENU complets.
    """

    def solar_position(
        self,
        utc_year: int,
        utc_month: int,
        utc_day: int,
        utc_hour: float,
        latitude_deg: float,
        longitude_deg: float,
    ) -> SolarDirection:
        """Calcula la posició solar aparent per a un instant UTC.

        Algoritme: posició solar simplificada amb declinació i angle horari.
        Precisió suficient per al cel visual (< 1° d'error).
        """
        # Dia de l'any (aproximat)
        # Ús de la fórmula de l'engine existent
        day_of_year = self._day_of_year(utc_year, utc_month, utc_day)

        # Declinació solar
        dec_deg = -23.44 * math.cos(math.radians(360.0 / 365.0 * (day_of_year + 10)))
        dec_rad = math.radians(dec_deg)
        lat_rad = math.radians(latitude_deg)

        # Temps solar i angle horari
        solar_time = utc_hour + longitude_deg / 15.0
        ha_deg = (solar_time - 12.0) * 15.0
        ha_rad = math.radians(ha_deg)

        # Altitud solar
        sin_alt = (
            math.sin(dec_rad) * math.sin(lat_rad)
            + math.cos(dec_rad) * math.cos(lat_rad) * math.cos(ha_rad)
        )
        sin_alt = max(-1.0, min(1.0, sin_alt))
        altitude = math.degrees(math.asin(sin_alt))

        # Azimut solar
        cos_alt = math.cos(math.radians(altitude))
        if abs(cos_alt) < 1e-10:
            # Sol al zenit o nadir — azimut indefinit, usar 0
            azimuth = 0.0
        else:
            cos_az = (math.sin(dec_rad) - sin_alt * math.sin(lat_rad)) / (
                cos_alt * math.cos(lat_rad)
            )
            cos_az = max(-1.0, min(1.0, cos_az))
            azimuth = math.degrees(math.acos(cos_az))
            # Correcció del quadrant: si l'angle horari és positiu (tarda), az > 180
            if math.sin(ha_rad) > 0:
                azimuth = 360.0 - azimuth

        # Normalitzar azimut a [0, 360)
        azimuth = azimuth % 360.0

        direction = sun_direction_enu(altitude, azimuth)

        return SolarDirection(
            altitude_deg=round(altitude, 4),
            azimuth_deg=round(azimuth, 4),
            direction_enu=direction,
        )

    @staticmethod
    def _day_of_year(year: int, month: int, day: int) -> int:
        """Calcula el dia de l'any (1-366)."""
        days_in_month = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        # Any de traspàs
        if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0):
            days_in_month[2] = 29
        return sum(days_in_month[:month]) + day
