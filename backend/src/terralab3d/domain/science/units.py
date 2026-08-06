"""Tipus d’unitat i convencions explícites per als càlculs científics."""
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class Angle:
    value: float
    unit: str

@dataclass(frozen=True, slots=True)
class Distance:
    value: float
    unit: str

@dataclass(frozen=True, slots=True)
class RadiometricValue:
    value: float
    unit: str
