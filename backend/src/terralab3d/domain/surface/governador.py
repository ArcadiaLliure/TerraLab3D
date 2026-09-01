"""Seleccio espacial pura del categoric que governa una posicio."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from terralab3d.domain.datasets.models import FontTerritorial, SourceRole
from terralab3d.domain.observer.models import GeoLocation
from terralab3d.domain.surface.tlst import (
    ClassificationStatus,
    SampleValidity,
    SurfaceObservation,
)


class SenseBaseCategoricaActivaError(ValueError):
    """Indica que l'arbre TLST no pot comencar sense una base activa."""


class MostrejadorFontCategorica(Protocol):
    """Frontera de lectura espacial; Rasterio queda fora del domini."""

    def cobreix(self, font: FontTerritorial, posicio: GeoLocation) -> bool: ...

    def observar(
        self,
        font: FontTerritorial,
        posicio: GeoLocation,
    ) -> SurfaceObservation: ...


@dataclass(frozen=True, slots=True)
class SeleccioGovernador:
    font: FontTerritorial
    observacio: SurfaceObservation


def validar_inici_arbre_tlst(fonts: Sequence[FontTerritorial]) -> None:
    """Impedeix aplicar refinaments o iniciar TLST sense categoric base."""

    if any(
        font.activa and font.source_role is SourceRole.BASE_CATEGORICAL
        for font in fonts
    ):
        return
    raise SenseBaseCategoricaActivaError(
        "No es pot iniciar l'arbre TLST sense una font BASE_CATEGORICAL activa"
    )


class GovernadorEspacial:
    """Escull la primera observacio base valida segons l'ordre V5."""

    def __init__(self, mostrejador: MostrejadorFontCategorica) -> None:
        self._mostrejador = mostrejador

    def seleccionar(
        self,
        posicio: GeoLocation,
        fonts: Sequence[FontTerritorial],
    ) -> SeleccioGovernador | None:
        validar_inici_arbre_tlst(fonts)
        candidates = sorted(
            (
                font
                for font in fonts
                if font.activa
                and font.source_role is SourceRole.BASE_CATEGORICAL
                and self._mostrejador.cobreix(font, posicio)
            ),
            key=lambda font: (
                self._resolucio_base(font),
                -font.priority,
                font.stable_id,
            ),
        )

        for font in candidates:
            observacio = self._mostrejador.observar(font, posicio)
            if self._es_semanticament_valida(observacio):
                return SeleccioGovernador(font=font, observacio=observacio)
        return None

    @staticmethod
    def _es_semanticament_valida(observacio: SurfaceObservation) -> bool:
        return (
            observacio.validity is SampleValidity.VALID
            and observacio.classification_status is ClassificationStatus.CLASSIFIED
        )

    @staticmethod
    def _resolucio_base(font: FontTerritorial) -> float:
        assert font.spatial_resolution_m is not None
        return float(font.spatial_resolution_m)
