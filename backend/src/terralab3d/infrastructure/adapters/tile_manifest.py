"""Lector del manifest de teseles Gaia.

Adaptat de TerraLab/data/tile_manifest.py per a TerraLab3D.
Defineix el contracte comú entre descàrrega i càrrega de teseles.
No fa IO de render ni cap lògica de UI.
"""

from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger("terralab3d.manifest")


def build_tile_identifier(ra_min: float, dec_min: float) -> str:
    """Construeix l'identificador canònic d'una tesela profunda."""
    ra_norm = int(round(float(ra_min))) % 360
    dec_norm = int(round(float(dec_min)))
    return f"tile_{ra_norm:04d}_{dec_norm:+03d}"


@dataclass(frozen=True)
class TileEntry:
    """Representa una tesela del catàleg Gaia."""
    tile_id: str
    file_path: Path
    ra_min: float
    ra_max: float
    dec_min: float
    dec_max: float
    mag_min: float
    mag_max: float | None
    star_count: int


class TileManifest:
    """Lector i consulta del fitxer tile_manifest.json."""

    def __init__(self) -> None:
        self.version: int = 1
        self.tile_size_deg: float = 5.0
        self._manifest_path: Path | None = None
        self._general_tile: TileEntry | None = None
        self._deep_tiles: list[TileEntry] = []
        self._tiles_by_id: dict[str, TileEntry] = {}

    @property
    def manifest_path(self) -> Path | None:
        return self._manifest_path

    @property
    def deep_tiles(self) -> tuple[TileEntry, ...]:
        return tuple(self._deep_tiles)

    def load(self, path: Path) -> None:
        """Llegeix el manifest des del disc i el deixa en memòria."""
        manifest_path = Path(path).expanduser().resolve()
        if not manifest_path.exists():
            raise FileNotFoundError(f"Manifest no trobat: {manifest_path}")

        with manifest_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        if not isinstance(payload, dict):
            raise ValueError("El manifest de teseles ha de ser un objecte JSON.")

        self.version = int(payload.get("version", 1) or 1)
        self.tile_size_deg = float(payload.get("tile_size_deg", 5.0) or 5.0)
        self._manifest_path = manifest_path

        base_dir = manifest_path.parent
        general_raw = payload.get("general_tile") or {}
        if not isinstance(general_raw, dict):
            raise ValueError("'general_tile' ha de ser un objecte JSON.")

        general_file = Path(str(general_raw.get("file", "tile_all.npz")))
        if not general_file.is_absolute():
            general_file = (base_dir / general_file).resolve()

        general_mag_limit = float(general_raw.get("mag_limit", 8.0) or 8.0)
        general_star_count = int(general_raw.get("star_count", 0) or 0)
        general_tile_id = str(general_raw.get("id", "tile_all") or "tile_all")

        self._general_tile = TileEntry(
            tile_id=general_tile_id,
            file_path=general_file,
            ra_min=0.0,
            ra_max=360.0,
            dec_min=-90.0,
            dec_max=90.0,
            mag_min=-99.0,
            mag_max=general_mag_limit,
            star_count=max(0, general_star_count),
        )

        deep_entries: list[TileEntry] = []
        for raw_item in payload.get("deep_tiles", []) or []:
            if not isinstance(raw_item, dict):
                continue

            file_name = Path(str(raw_item.get("file", "")).strip())
            if str(file_name) == "":
                continue
            if not file_name.is_absolute():
                file_name = (base_dir / file_name).resolve()

            ra_min = _float_or_default(raw_item.get("ra_min"), 0.0) % 360.0
            ra_max = _float_or_default(
                raw_item.get("ra_max"), ra_min + self.tile_size_deg
            )
            dec_min = _float_or_default(raw_item.get("dec_min"), -90.0)
            dec_max = _float_or_default(
                raw_item.get("dec_max"), dec_min + self.tile_size_deg
            )

            tile_id = str(raw_item.get("id", "") or "").strip()
            if not tile_id:
                tile_id = build_tile_identifier(ra_min=ra_min, dec_min=dec_min)

            deep_entries.append(
                TileEntry(
                    tile_id=tile_id,
                    file_path=file_name,
                    ra_min=ra_min,
                    ra_max=ra_max,
                    dec_min=dec_min,
                    dec_max=dec_max,
                    mag_min=float(raw_item.get("mag_min", self._general_tile.mag_max) or self._general_tile.mag_max),
                    mag_max=_optional_float(raw_item.get("mag_max", None)),
                    star_count=max(0, int(raw_item.get("star_count", 0) or 0)),
                )
            )

        self._deep_tiles = deep_entries
        self._tiles_by_id = {entry.tile_id: entry for entry in self._deep_tiles}
        log.info(
            "MGP: [tile_manifest] [load] [Manifest carregat: %d deep tiles, general=%s]",
            len(self._deep_tiles),
            general_tile_id,
        )

    def get_general_tile(self) -> TileEntry:
        if self._general_tile is None:
            raise RuntimeError("Cal cridar load() abans de consultar la tesela general.")
        return self._general_tile

    def get_tiles_for_region(
        self,
        ra_center: float,
        dec_center: float,
        radius_deg: float,
    ) -> list[TileEntry]:
        """Retorna teseles profundes que solapen una regió celeste."""
        if not self._deep_tiles:
            return []

        ra_center_norm = float(ra_center) % 360.0
        dec_center_clamped = max(-90.0, min(90.0, float(dec_center)))
        radius = max(0.0, float(radius_deg))

        ra_min = (ra_center_norm - radius) % 360.0
        ra_max = (ra_center_norm + radius) % 360.0
        dec_min = max(-90.0, dec_center_clamped - radius)
        dec_max = min(90.0, dec_center_clamped + radius)

        matched: list[TileEntry] = []
        for tile in self._deep_tiles:
            if not _dec_overlap(dec_min, dec_max, tile.dec_min, tile.dec_max):
                continue
            if _ra_overlap_wrap(ra_min, ra_max, tile.ra_min, tile.ra_max):
                matched.append(tile)

        return matched

    def get_adjacent_tiles(self, tile_id: str) -> list[TileEntry]:
        """Retorna les 8 teseles veïnes de la tesela indicada."""
        center = self._tiles_by_id.get(str(tile_id))
        if center is None:
            return []

        tile_size = max(0.1, float(self.tile_size_deg))
        neighbors: list[TileEntry] = []
        seen: set[str] = set()

        for ra_step in (-1, 0, 1):
            for dec_step in (-1, 0, 1):
                if ra_step == 0 and dec_step == 0:
                    continue
                target_ra = (center.ra_min + ra_step * tile_size) % 360.0
                target_dec = center.dec_min + dec_step * tile_size
                if target_dec < -90.0 or target_dec >= 90.0:
                    continue
                target_id = build_tile_identifier(target_ra, target_dec)
                neighbor = self._tiles_by_id.get(target_id)
                if neighbor is None or neighbor.tile_id in seen:
                    continue
                seen.add(neighbor.tile_id)
                neighbors.append(neighbor)

        return neighbors


# ─── Helpers ──────────────────────────────────────────────────────────

def _dec_overlap(a_min: float, a_max: float, b_min: float, b_max: float) -> bool:
    return (a_min <= b_max) and (b_min <= a_max)


def _ra_overlap_wrap(a_min: float, a_max: float, b_min: float, b_max: float) -> bool:
    a_ranges = _normalize_ra_interval(a_min, a_max)
    b_ranges = _normalize_ra_interval(b_min, b_max)
    for a_lo, a_hi in a_ranges:
        for b_lo, b_hi in b_ranges:
            if a_lo <= b_hi and b_lo <= a_hi:
                return True
    return False


def _normalize_ra_interval(ra_min: float, ra_max: float) -> list[tuple[float, float]]:
    lo = float(ra_min) % 360.0
    hi_raw = float(ra_max)
    if math.isclose((hi_raw - float(ra_min)) % 360.0, 0.0, abs_tol=1e-9) and hi_raw != float(ra_min):
        return [(0.0, 360.0)]
    hi = hi_raw % 360.0
    if lo <= hi:
        return [(lo, hi)]
    return [(0.0, hi), (lo, 360.0)]


def _float_or_default(value: object, default: float) -> float:
    if value is None:
        return float(default)
    return float(value)


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    try:
        parsed = float(text)
    except Exception:
        return None
    if not math.isfinite(parsed):
        return None
    return float(parsed)
