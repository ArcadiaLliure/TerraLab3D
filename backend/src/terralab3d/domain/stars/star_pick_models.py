"""Models de domini per al picking estel·lar (Pas 6).

Defineix els contractes per a la resolució d'estrelles seleccionades
al frontend. El source_id Gaia és int64 i es serialitza com string decimal.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class ResolvedStarPick:
    """Resultat de la resolució d'una estrella seleccionada."""
    resource_id: str
    version: str
    catalog_index: int
    source_id: int  # int64 — serialitzar com string al JSON
    ra_deg: float
    dec_deg: float
    magnitude: float
    bp_rp: float | None
    source_role: str  # "general" | "fallback" | "supplement" | "deep_tile"


@dataclass(frozen=True, slots=True)
class StarPickRequest:
    """Petició de resolució d'una estrella seleccionada."""
    request_id: str
    generation: int
    resource_id: str
    resource_version: str
    catalog_index: int
    purpose: Literal["select", "hover"]


@dataclass(frozen=True, slots=True)
class StarPickResponse:
    """Resposta de resolució d'una estrella seleccionada."""
    request_id: str
    generation: int
    status: Literal["ok", "stale", "missing", "invalid"]
    resolved: ResolvedStarPick | None = None
