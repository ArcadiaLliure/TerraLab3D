"""Port de domini per l'accés a dades de cobertura categòrica."""

from typing import Protocol

from terralab3d.domain.surface.land_cover import LandCoverLegend, LandCoverTile, LandCoverTileRequest


class LandCoverPort(Protocol):
    """Port per a proveir dades de cobertura terrestre categòrica (Land Cover)."""

    def read_tile(self, request: LandCoverTileRequest) -> LandCoverTile | None: ...
    def legend(
        self,
        scheme_key: str,
        scheme_version: str,
        mapping_revision: str | None = None,
    ) -> LandCoverLegend | None: ...
    def close(self) -> None: ...
