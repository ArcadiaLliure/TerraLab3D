"""Contractes de càlcul científic pur per a Sol, Lluna i planetes."""

from typing import Protocol


class SolarSystemCalculator(Protocol):
    """Defineix els càlculs purs de Sol, Lluna i planetes sense I/O ni renderitzat."""
    def angular_diameter_deg(self, physical_radius_km: float, distance_km: float) -> float: ...
    def illuminated_fraction(self, phase_angle_deg: float) -> float: ...
