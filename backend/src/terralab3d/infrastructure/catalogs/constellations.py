"""Carregador read-only del catàleg empaquetat de constel·lacions."""

from __future__ import annotations

import json
import math
from importlib.resources import files
from typing import Any

from terralab3d.domain.constellations.models import (
    ConstellationCatalog,
    ConstellationCatalogEntry,
    ConstellationVisualComponent,
)
from terralab3d.domain.geometry import EquatorialCoordinate
from terralab3d.domain.identifiers import ConstellationId


IAU_CONSTELLATION_IDS = frozenset(
    "And Ant Aps Aql Aqr Ara Ari Aur Boo CMa CMi CVn Cae Cam Cap Car Cas Cen Cep Cet "
    "Cha Cir Cnc Col Com CrA CrB Crt Cru Crv Cyg Del Dor Dra Equ Eri For Gem Gru Her "
    "Hor Hya Hyi Ind LMi Lac Leo Lep Lib Lup Lyn Lyr Men Mic Mon Mus Nor Oct Oph Ori "
    "Pav Peg Per Phe Pic PsA Psc Pup Pyx Ret Scl Sco Sct Ser Sex Sge Sgr Tau Tel TrA "
    "Tri Tuc UMa UMi Vel Vir Vol Vul".split()
)
EXPECTED_SOURCE_HASHES = {
    "constellations.lines.json": "294f66bef5d5cf50b1e17f16d2efa1d97a15131612c68dd935adef6e7373e13c",
    "constellations.json": "ab4ae692027cbc042c0d6791a84456a65eb7c55656107fd00c58ff6e55d4d8b2",
}
EXPECTED_CATALOG_VERSION = "d3-celestial-7e720a3de062-icrs-v1"


class PackagedConstellationCatalog:
    def __init__(self) -> None:
        resource = files("terralab3d.infrastructure.catalogs").joinpath("constellations.v1.json")
        payload = json.loads(resource.read_text(encoding="utf-8"))
        self._raw: dict[str, Any] = payload
        self.catalog = self._parse(payload)
        self._by_id = {str(entry.constellation_id): entry for entry in self.catalog.entries}

    def find(self, constellation_id: str) -> ConstellationCatalogEntry | None:
        return self._by_id.get(constellation_id)

    def snapshot_payload(self) -> dict[str, Any]:
        return {"type": "constellation_catalog", **self._raw}

    def search_records(self) -> list[dict[str, Any]]:
        return [
            {
                "constellation_id": str(entry.constellation_id),
                "name": entry.name,
                "ra": entry.center.right_ascension_deg,
                "dec": entry.center.declination_deg,
                "angular_radius_deg": entry.angular_radius_deg,
            }
            for entry in self.catalog.entries
        ]

    @staticmethod
    def _parse(payload: dict[str, Any]) -> ConstellationCatalog:
        if int(payload.get("schemaVersion", 0)) != 1:
            raise ValueError("versió de catàleg de constel·lacions no compatible")
        if payload.get("catalogVersion") != EXPECTED_CATALOG_VERSION:
            raise ValueError("versió de dades de constel·lacions no compatible")
        source = payload.get("source")
        raw_entries = payload.get("constellations")
        if not isinstance(source, dict) or not isinstance(raw_entries, list) or len(raw_entries) != 88:
            raise ValueError("catàleg de constel·lacions incomplet")
        if source.get("sourceFrame") != "FK5_J2000" or source.get("frame") != "ICRS":
            raise ValueError("frames del catàleg de constel·lacions incompatibles")
        if float(source.get("maxArcStepDeg", math.inf)) > 1.0:
            raise ValueError("mostreig angular del catàleg massa groller")
        source_hashes = {
            str(item.get("url", "")).rsplit("/", 1)[-1]: str(item.get("sha256", ""))
            for item in source.get("files", [])
            if isinstance(item, dict)
        }
        if source_hashes != EXPECTED_SOURCE_HASHES:
            raise ValueError("hashes de procedència del catàleg incompatibles")
        entries = []
        for raw in raw_entries:
            center = _coordinate(raw["center"])
            radius = float(raw["angularRadiusDeg"])
            if not math.isfinite(radius) or radius <= 0.0:
                raise ValueError(f"radi invàlid per {raw.get('id')}")
            components = []
            for component in raw["visualComponents"]:
                strokes = tuple(
                    tuple(_coordinate(point) for point in stroke)
                    for stroke in component["strokes"]
                )
                components.append(ConstellationVisualComponent(
                    component_id=str(component["componentId"]),
                    source_name=str(component["sourceName"]),
                    rank=int(component["rank"]),
                    strokes=strokes,
                ))
            entries.append(ConstellationCatalogEntry(
                constellation_id=ConstellationId(str(raw["id"])),
                name=str(raw["name"]),
                center=center,
                angular_radius_deg=radius,
                visual_components=tuple(components),
                frame=str(raw["frame"]),
            ))
            if entries[-1].frame != "ICRS":
                raise ValueError(f"frame invàlid per {raw.get('id')}")
        serpens = [entry for entry in entries if str(entry.constellation_id) == "Ser"]
        identifiers = {str(entry.constellation_id) for entry in entries}
        if identifiers != IAU_CONSTELLATION_IDS:
            missing = sorted(IAU_CONSTELLATION_IDS - identifiers)
            extra = sorted(identifiers - IAU_CONSTELLATION_IDS)
            raise ValueError(f"identitats IAU invàlides: absents={missing}; sobrants={extra}")
        if len(serpens) != 1 or {item.component_id for item in serpens[0].visual_components} != {"caput", "cauda"}:
            raise ValueError("Serpens no conserva Caput i Cauda com a components separats")
        return ConstellationCatalog(
            catalog_version=str(payload["catalogVersion"]),
            source_frame=str(source["sourceFrame"]),
            frame=str(source["frame"]),
            entries=tuple(entries),
        )


def _coordinate(value: Any) -> EquatorialCoordinate:
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError("coordenada de catàleg invàlida")
    ra = float(value[0])
    dec = float(value[1])
    if not math.isfinite(ra) or not math.isfinite(dec) or not 0.0 <= ra < 360.0 or not -90.0 <= dec <= 90.0:
        raise ValueError("coordenada de catàleg fora de rang")
    return EquatorialCoordinate(ra, dec)
