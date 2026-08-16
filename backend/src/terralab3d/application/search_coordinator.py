"""Coordinador de cerca astronòmica (Pas 12)."""

import logging
from typing import Sequence, Any, Callable, Awaitable
from terralab3d.domain.search.calculations import DefaultSearchNormalizationCalculator
from terralab3d.domain.search.indexer import AstronomicalSearchIndex
from terralab3d.domain.search.models import SearchQuery, SearchTargetKind

log = logging.getLogger("terralab3d.search")

class AstronomicalSearchCoordinator:
    def __init__(
        self,
        publish_results: Callable[[str, int, str, list[dict[str, Any]]], Awaitable[None]],
    ) -> None:
        self._publish = publish_results
        self._calculator = DefaultSearchNormalizationCalculator()
        self._index = AstronomicalSearchIndex(self._calculator)
        self._active_ngc = True
        self._is_index_built = False
        
    @property
    def is_index_built(self) -> bool:
        return self._is_index_built
        
    def set_active_ngc(self, active: bool) -> None:
        self._active_ngc = active

    def build_index(
        self,
        named_stars: Sequence[dict[str, Any]],
        ngc_objects: Sequence[Any],
        planets: Sequence[dict[str, Any]],
    ) -> None:
        log.debug(
            "MGP: [AstronomicalSearchCoordinator] [build_index] "
            "[stars=%d, ngc=%d, planets=%d]",
            len(named_stars), len(ngc_objects), len(planets)
        )
        self._index.build_index(named_stars, ngc_objects, planets)
        self._is_index_built = True

    async def search(self, request_id: str, generation: int, query_text: str, limit: int = 20) -> None:
        if not query_text:
            await self._publish(request_id, generation, "invalid", [])
            return
            
        # Intentem parsejar-ho com RA/Dec primer
        coord = self._calculator.coordinate_query(query_text)
        if coord is not None:
            results = [{
                "targetRef": "coordinate",
                "kind": "coordinate",
                "displayName": f"RA {coord.right_ascension_deg:.4f}° Dec {coord.declination_deg:.4f}°",
                "score": 100,
                "availability": "available",
                "coordinateSnapshot": {"raDeg": coord.right_ascension_deg, "decDeg": coord.declination_deg},
            }]
            await self._publish(request_id, generation, "ok", results)
            return

        # Si no és coordenada, cerca de text
        query = SearchQuery(
            text=query_text,
            kinds=frozenset([SearchTargetKind.STAR, SearchTargetKind.BODY, SearchTargetKind.DEEP_SKY]),
            limit=limit,
        )
        
        search_results = self._index.search(query, active_ngc=self._active_ngc)
        
        results = []
        for r in search_results:
            d = {
                "targetRef": r.target_ref,
                "kind": r.kind.value,
                "displayName": r.display_name,
                "score": r.score,
                "availability": r.availability,
            }
            if r.coordinate_snapshot is not None:
                d["coordinateSnapshot"] = {
                    "raDeg": r.coordinate_snapshot.right_ascension_deg,
                    "decDeg": r.coordinate_snapshot.declination_deg,
                }
            if r.resource_id:
                d["resourceId"] = r.resource_id
            if r.matched_alias:
                d["matchedAlias"] = r.matched_alias
            results.append(d)
            
        await self._publish(request_id, generation, "ok", results)
