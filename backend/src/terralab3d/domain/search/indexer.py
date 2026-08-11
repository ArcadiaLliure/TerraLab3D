"""Cerca astronòmica: índex en memòria."""

from __future__ import annotations
import math
from typing import Sequence, Iterator, Any
from terralab3d.domain.geometry import EquatorialCoordinate
from .models import SearchTargetKind, SearchResult, SearchQuery
from .calculations import SearchNormalizationCalculator

class AstronomicalSearchIndex:
    """Índex en memòria de noms, àlies i cross-referències per a cerca astronòmica."""
    
    def __init__(self, normalization_calculator: SearchNormalizationCalculator) -> None:
        self._calculator = normalization_calculator
        # Llistes internes (només lectura després de construir)
        self._entries: list[dict[str, Any]] = []

    def build_index(
        self,
        named_stars: Sequence[dict[str, Any]],
        ngc_objects: Sequence[Any],
        planets: Sequence[dict[str, Any]],
    ) -> None:
        """Construeix l'índex amb els objectes proporcionats."""
        self._entries.clear()
        
        # 1. Planetes / Sistema Solar
        # `planets` ha de tenir: body_id, canon_name, aliases, RA, Dec (snapshot si escau)
        for p in planets:
            aliases = p.get("aliases", [])
            for alias in aliases:
                self._add_entry(
                    target_ref=p["body_id"],
                    kind=SearchTargetKind.BODY,
                    display_name=p["canon_name"],
                    search_key=self._calculator.normalize_query(alias),
                    is_exact_alias=(alias == p["canon_name"] or alias in aliases),
                    original_alias=alias,
                    coordinate_snapshot=p.get("coordinate_snapshot")
                )
                
        # 2. Estrelles amb nom (Named stars)
        for s in named_stars:
            name = s.get("name", "").strip()
            if not name:
                continue
            coord = EquatorialCoordinate(right_ascension_deg=float(s["ra"]), declination_deg=float(s["dec"]))
            self._add_entry(
                target_ref=str(s.get("source_id", "")),
                kind=SearchTargetKind.STAR,
                display_name=name,
                search_key=self._calculator.normalize_query(name),
                is_exact_alias=True,
                original_alias=name,
                coordinate_snapshot=coord,
                resource_id="sky.stars.catalog" # Assumim que les named stars hi són
            )
            
        # 3. Objectes NGC/IC (Deep Sky)
        for obj in ngc_objects:
            canon = getattr(obj, "common_name", None) or getattr(obj, "name", "NGC")
            coord = EquatorialCoordinate(right_ascension_deg=float(obj.ra_deg), declination_deg=float(obj.dec_deg))
            target_ref = obj.name
            
            # Recollir àlies
            def iter_aliases() -> Iterator[str]:
                yield obj.name
                if getattr(obj, "common_name", None):
                    yield obj.common_name
                # Podríem afegir Messier
                if getattr(obj, "messier_nr", None):
                    yield f"M{obj.messier_nr}"
                    yield f"Messier {obj.messier_nr}"
                    
            for alias in iter_aliases():
                self._add_entry(
                    target_ref=target_ref,
                    kind=SearchTargetKind.DEEP_SKY,
                    display_name=canon,
                    search_key=self._calculator.normalize_query(alias),
                    is_exact_alias=True,
                    original_alias=alias,
                    coordinate_snapshot=coord,
                    resource_id="sky.ngc"
                )

    def _add_entry(self, **kwargs: Any) -> None:
        self._entries.append(kwargs)

    def search(self, query: SearchQuery, active_ngc: bool = True) -> Sequence[SearchResult]:
        if not query.text:
            return []
            
        norm_query = self._calculator.normalize_query(query.text)
        if not norm_query:
            return []

        results: list[SearchResult] = []
        seen_refs = set()

        for entry in self._entries:
            if entry["kind"] not in query.kinds:
                continue

            search_key = entry["search_key"]
            
            # Ranking:
            # 1. Exact match (score 100)
            # 2. Starts with (score 50)
            # 3. Contains (score 10)
            score = 0
            if search_key == norm_query:
                score = 100
            elif search_key.startswith(norm_query):
                score = 50
            elif norm_query in search_key:
                score = 10
                
            if score > 0:
                target_ref = entry["target_ref"]
                if target_ref in seen_refs:
                    continue
                seen_refs.add(target_ref)
                
                # Política de dataset absent:
                availability = "available"
                if entry["kind"] == SearchTargetKind.DEEP_SKY and not active_ngc:
                    availability = "unavailable"
                    
                results.append(
                    SearchResult(
                        target_ref=target_ref,
                        kind=entry["kind"],
                        display_name=entry["display_name"],
                        score=score,
                        availability=availability,
                        coordinate_snapshot=entry["coordinate_snapshot"],
                        resource_id=entry.get("resource_id"),
                        matched_alias=entry["original_alias"] if entry["original_alias"] != entry["display_name"] else None
                    )
                )

        # Ordenar per score (descendent) i després alfabèticament per nom per tie-break
        results.sort(key=lambda x: (-x.score, x.display_name))
        
        return results[:query.limit]
