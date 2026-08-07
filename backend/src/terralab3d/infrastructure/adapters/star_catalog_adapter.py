"""Adaptadors de catàleg estel·lar per a TerraLab3D.

Implementa StarCatalogPort amb dos adaptadors:
- GaiaStarCatalogAdapter: catàleg Gaia real (tiles NPZ i manifest) + suplement d'estrelles brillants del fallback (< min_mag)
- FallbackStarCatalogAdapter: catàleg fallback inclòs (~9000 estrelles)

El descobriment de la ruta Gaia es fa via `resolve_gaia_data_dir()`, que llegeix
la llibreria de dades configurada per l'usuari (ex. `I:\\TerraLab\\data\\sky\\gaia`).
"""

from __future__ import annotations

import hashlib
import logging
import math
import os
from pathlib import Path
from typing import Iterator

import numpy as np

from terralab3d.domain.stars.models import (
    GaiaAvailability,
    StarBatch,
)
from terralab3d.infrastructure.app_paths import resolve_gaia_data_dir

log = logging.getLogger("terralab3d.catalog")

# ─── Helpers ──────────────────────────────────────────────────────────

def _read_tile_npz(path: Path) -> dict[str, np.ndarray]:
    """Llegeix una tesela .npz i retorna arrays en memòria."""
    tile_path = Path(path).expanduser().resolve()
    with np.load(tile_path, allow_pickle=False) as data:
        ra = np.asarray(data.get("ra", data.get("RA", np.empty(0, dtype=np.float64))), dtype=np.float64)
        dec = np.asarray(data.get("dec", data.get("DEC", np.empty(0, dtype=np.float64))), dtype=np.float64)
        mag_key = "phot_g_mean_mag" if "phot_g_mean_mag" in data else "mag"
        mag = np.asarray(data.get(mag_key, np.empty(0, dtype=np.float32)), dtype=np.float32)
        bp_rp = np.asarray(
            data.get("bp_rp", np.full(len(ra), 0.8, dtype=np.float32)),
            dtype=np.float32,
        )
        source_id = np.asarray(
            data.get("source_id", np.full(len(ra), -1, dtype=np.int64)),
            dtype=np.int64,
        )
    return {"ra": ra, "dec": dec, "mag": mag, "bp_rp": bp_rp, "source_id": source_id}


def _normalize_arrays(payload: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """Normalitza arrays: dtype correctes, filtra NaN, ordena per magnitud."""
    ra = np.asarray(payload.get("ra", np.empty(0)), dtype=np.float64)
    dec = np.asarray(payload.get("dec", np.empty(0)), dtype=np.float64)
    mag = np.asarray(payload.get("mag", np.empty(0)), dtype=np.float32)
    bp_rp = np.asarray(
        payload.get("bp_rp", np.full(len(mag), 0.8, dtype=np.float32)),
        dtype=np.float32,
    )
    source_id = np.asarray(
        payload.get("source_id", np.full(len(mag), -1, dtype=np.int64)),
        dtype=np.int64,
    )

    row_count = min(len(ra), len(dec), len(mag), len(bp_rp), len(source_id))
    if row_count <= 0:
        return _empty_arrays()

    ra = ra[:row_count]
    dec = dec[:row_count]
    mag = mag[:row_count]
    bp_rp = bp_rp[:row_count]
    source_id = source_id[:row_count]

    # Filtrar no finits
    valid = np.isfinite(ra) & np.isfinite(dec) & np.isfinite(mag)
    if not np.all(valid):
        ra = ra[valid]
        dec = dec[valid]
        mag = mag[valid]
        bp_rp = bp_rp[valid]
        source_id = source_id[valid]

    # BP-RP NaN → fallback 0.8
    bp_rp = np.nan_to_num(bp_rp, nan=0.8, posinf=2.5, neginf=-0.5).astype(np.float32)

    # Ordenar per magnitud
    if mag.size > 1 and bool(np.any(mag[1:] < mag[:-1])):
        order = np.argsort(mag, kind="mergesort")
        ra = ra[order]
        dec = dec[order]
        mag = mag[order]
        bp_rp = bp_rp[order]
        source_id = source_id[order]

    return {"ra": ra, "dec": dec, "mag": mag, "bp_rp": bp_rp, "source_id": source_id}


def _empty_arrays() -> dict[str, np.ndarray]:
    return {
        "ra": np.empty(0, dtype=np.float64),
        "dec": np.empty(0, dtype=np.float64),
        "mag": np.empty(0, dtype=np.float32),
        "bp_rp": np.empty(0, dtype=np.float32),
        "source_id": np.empty(0, dtype=np.int64),
    }


def _merge_bright_supplement(
    gaia_arrays: dict[str, np.ndarray],
    fallback_arrays: dict[str, np.ndarray],
) -> dict[str, np.ndarray]:
    """Combina Gaia amb les estrelles del fallback més brillants que la min_mag de Gaia.

    En catàlegs Gaia DR2/DR3, estrelles molts brillants (mag < ~1.73 com Sirius, Rigel, Betelgeuse)
    estan saturades i falten. Aquesta funció les afegeix des del catàleg fallback.
    """
    gaia_mags = gaia_arrays.get("mag", np.empty(0))
    if gaia_mags.size == 0:
        return gaia_arrays

    min_gaia_mag = float(np.min(gaia_mags))
    fb_mags = fallback_arrays.get("mag", np.empty(0))
    fb_mask = fb_mags < (min_gaia_mag - 1e-4)

    if not np.any(fb_mask):
        log.info(
            "MGP: [catalog] [_merge_bright_supplement] "
            "[Gaia té estrelles fins mag %.2f; no cal suplement]",
            min_gaia_mag,
        )
        return gaia_arrays

    # Extraure suplement bright stars
    supp_ra = fallback_arrays["ra"][fb_mask]
    supp_dec = fallback_arrays["dec"][fb_mask]
    supp_mag = fallback_arrays["mag"][fb_mask]
    supp_bprp = fallback_arrays["bp_rp"][fb_mask]
    supp_sid = fallback_arrays["source_id"][fb_mask]

    n_supp = supp_ra.size
    log.info(
        "MGP: [catalog] [_merge_bright_supplement] "
        "[Afegint %d estrelles brillants del fallback (mag < %.2f: Sirius, Betelgeuse...)]",
        n_supp, min_gaia_mag,
    )

    # Concatenar suplement + Gaia (suplement primer perquè són més brillants)
    merged_ra = np.concatenate([supp_ra, gaia_arrays["ra"]])
    merged_dec = np.concatenate([supp_dec, gaia_arrays["dec"]])
    merged_mag = np.concatenate([supp_mag, gaia_arrays["mag"]])
    merged_bprp = np.concatenate([supp_bprp, gaia_arrays["bp_rp"]])
    merged_sid = np.concatenate([supp_sid, gaia_arrays["source_id"]])

    # Reordenar per magnitud
    order = np.argsort(merged_mag, kind="mergesort")

    return {
        "ra": merged_ra[order],
        "dec": merged_dec[order],
        "mag": merged_mag[order],
        "bp_rp": merged_bprp[order],
        "source_id": merged_sid[order],
    }


def _arrays_to_batch(arrays: dict[str, np.ndarray]) -> StarBatch | None:
    if len(arrays.get("ra", ())) == 0:
        return None
    return StarBatch(
        ra=arrays["ra"],
        dec=arrays["dec"],
        mag=arrays["mag"],
        bp_rp=arrays["bp_rp"],
        source_id=arrays["source_id"],
    )


def _exact_cone_mask(
    ra: np.ndarray, dec: np.ndarray,
    ra_deg: float, dec_deg: float, radius_deg: float,
) -> np.ndarray:
    ra_rad = np.radians(np.asarray(ra, dtype=np.float64))
    dec_rad = np.radians(np.asarray(dec, dtype=np.float64))
    center_ra = math.radians(float(ra_deg))
    center_dec = math.radians(float(dec_deg))
    cos_sep = (
        np.sin(dec_rad) * math.sin(center_dec)
        + np.cos(dec_rad) * math.cos(center_dec) * np.cos(ra_rad - center_ra)
    )
    return cos_sep >= math.cos(math.radians(float(radius_deg)))


# ─── Fallback Adapter ─────────────────────────────────────────────────

class FallbackStarCatalogAdapter:
    """Catàleg fallback inclòs — sempre disponible."""

    def __init__(self) -> None:
        self._data: dict[str, np.ndarray] | None = None
        self._path = Path(__file__).resolve().parents[2] / "data" / "fallback_catalog.npz"

    def get_availability(self) -> GaiaAvailability:
        return GaiaAvailability.NOT_CONFIGURED

    def load_general_catalog(self, *, mag_limit: float = 8.0) -> StarBatch | None:
        return None

    def load_fallback_catalog(self) -> StarBatch | None:
        if self._data is not None:
            return _arrays_to_batch(self._data)

        if not self._path.exists():
            log.warning(
                "MGP: [FallbackAdapter] [load_fallback_catalog] "
                "[Fitxer fallback no trobat: %s]",
                self._path,
            )
            return None

        try:
            raw = _read_tile_npz(self._path)
            self._data = _normalize_arrays(raw)
            n = len(self._data["ra"])
            log.info(
                "MGP: [FallbackAdapter] [load_fallback_catalog] "
                "[Fallback carregat: %d estrelles]",
                n,
            )
            return _arrays_to_batch(self._data)
        except Exception as exc:
            log.error(
                "MGP: [FallbackAdapter] [load_fallback_catalog] "
                "[Error carregant fallback: %s]",
                exc,
            )
            return None

    def query_cone(
        self, ra_deg: float, dec_deg: float, radius_deg: float, mag_limit: float,
        *, max_batch_rows: int = 1_000_000,
    ) -> Iterator[StarBatch]:
        return iter(())

    def close(self) -> None:
        self._data = None


# ─── Gaia Adapter ─────────────────────────────────────────────────────

class GaiaStarCatalogAdapter:
    """Adaptador Gaia real amb tiles NPZ, manifest i suplement d'estrelles brillants.

    Gaia es resol prioritàriament des del path especificat, o automàticament des de
    `resolve_gaia_data_dir()` (ex. `I:\\TerraLab\\data\\sky\\gaia`).
    """

    def __init__(self, gaia_path: str | Path | None = None) -> None:
        self._gaia_dir: Path | None = None
        self._availability = GaiaAvailability.NOT_CONFIGURED
        self._manifest = None
        self._general_data: dict[str, np.ndarray] | None = None
        self._closed = False

        if gaia_path is None:
            # Resoldre automàticament des de la llibreria de dades
            resolved = resolve_gaia_data_dir()
            if resolved.exists():
                candidate = resolved
            else:
                self._availability = GaiaAvailability.NOT_CONFIGURED
                return
        else:
            candidate = Path(gaia_path).expanduser().resolve()

        if not candidate.exists():
            self._availability = GaiaAvailability.UNAVAILABLE
            log.warning(
                "MGP: [GaiaAdapter] [__init__] [Ruta Gaia no trobada: %s]",
                candidate,
            )
            return

        # Determinar directori base
        if candidate.is_file():
            self._gaia_dir = candidate.parent
            manifest_file = candidate
        else:
            self._gaia_dir = candidate
            manifest_file = candidate / "tile_manifest.json"

        # Intentar carregar manifest
        if not manifest_file.exists():
            general_npz = self._gaia_dir / "tile_all.npz"
            if general_npz.exists():
                self._availability = GaiaAvailability.AVAILABLE
                log.info(
                    "MGP: [GaiaAdapter] [__init__] [Gaia disponible sense manifest: %s]",
                    general_npz,
                )
            else:
                self._availability = GaiaAvailability.MANIFEST_MISSING
                log.warning(
                    "MGP: [GaiaAdapter] [__init__] [Manifest absent: %s]",
                    manifest_file,
                )
            return

        try:
            from terralab3d.infrastructure.adapters.tile_manifest import TileManifest
            self._manifest = TileManifest()
            self._manifest.load(manifest_file)
            self._availability = GaiaAvailability.AVAILABLE
            log.info(
                "MGP: [GaiaAdapter] [__init__] [Gaia disponible amb manifest a %s: %d deep tiles]",
                self._gaia_dir,
                len(self._manifest.deep_tiles),
            )
        except Exception as exc:
            self._availability = GaiaAvailability.MANIFEST_INVALID
            log.error(
                "MGP: [GaiaAdapter] [__init__] [Manifest invàlid: %s]", exc
            )

    def get_availability(self) -> GaiaAvailability:
        return self._availability

    def load_general_catalog(self, *, mag_limit: float = 8.0) -> StarBatch | None:
        if self._closed:
            return None
        if self._general_data is not None:
            return _arrays_to_batch(self._general_data)
        if self._availability not in (
            GaiaAvailability.AVAILABLE,
            GaiaAvailability.READY,
            GaiaAvailability.PARTIAL,
        ):
            return None

        try:
            if self._manifest is not None:
                general_tile = self._manifest.get_general_tile()
                path = general_tile.file_path
            elif self._gaia_dir is not None:
                path = self._gaia_dir / "tile_all.npz"
            else:
                return None

            if not path.exists():
                self._availability = GaiaAvailability.UNAVAILABLE
                log.warning(
                    "MGP: [GaiaAdapter] [load_general_catalog] "
                    "[Fitxer general absent: %s]", path,
                )
                return None

            raw = _read_tile_npz(path)
            normalized = _normalize_arrays(raw)

            # Carregar el suplement d'estrelles brillants (< min_mag Gaia) des del catàleg fallback
            fallback_adapter = FallbackStarCatalogAdapter()
            fb_batch = fallback_adapter.load_fallback_catalog()
            if fb_batch is not None:
                fb_arrays = {
                    "ra": fb_batch.ra,
                    "dec": fb_batch.dec,
                    "mag": fb_batch.mag,
                    "bp_rp": fb_batch.bp_rp,
                    "source_id": fb_batch.source_id,
                }
                normalized = _merge_bright_supplement(normalized, fb_arrays)

            # Aplicar límit de magnitud si s'indica
            if mag_limit < 99.0:
                mask = normalized["mag"] <= float(mag_limit) + 1e-6
                if not np.all(mask):
                    for key in normalized:
                        normalized[key] = normalized[key][mask]

            self._general_data = normalized
            self._availability = GaiaAvailability.READY
            n = len(normalized["ra"])
            log.info(
                "MGP: [GaiaAdapter] [load_general_catalog] "
                "[General carregat: %d estrelles, mag ≤ %.1f]",
                n, mag_limit,
            )
            return _arrays_to_batch(normalized)

        except Exception as exc:
            self._availability = GaiaAvailability.ERROR
            log.error(
                "MGP: [GaiaAdapter] [load_general_catalog] [Error: %s]", exc
            )
            return None

    def load_fallback_catalog(self) -> StarBatch | None:
        return None

    def query_cone(
        self, ra_deg: float, dec_deg: float, radius_deg: float, mag_limit: float,
        *, max_batch_rows: int = 1_000_000,
    ) -> Iterator[StarBatch]:
        """Consulta de con per deep tiles (out-of-core)."""
        if self._closed or self._manifest is None:
            return

        entries = self._manifest.get_tiles_for_region(ra_deg, dec_deg, radius_deg)
        for entry in entries:
            if self._closed:
                return
            if not entry.file_path.exists():
                continue
            try:
                raw = _read_tile_npz(entry.file_path)
                normalized = _normalize_arrays(raw)
                if len(normalized["ra"]) == 0:
                    continue

                mask = normalized["mag"] <= float(mag_limit) + 1e-6
                cone = _exact_cone_mask(
                    normalized["ra"], normalized["dec"],
                    ra_deg, dec_deg, radius_deg,
                )
                combined = mask & cone
                if not np.any(combined):
                    continue

                batch_arrays = {
                    k: v[combined] for k, v in normalized.items()
                }
                batch = _arrays_to_batch(batch_arrays)
                if batch is not None:
                    yield batch

            except Exception as exc:
                log.warning(
                    "MGP: [GaiaAdapter] [query_cone] [Error tile %s: %s]",
                    entry.tile_id, exc,
                )

    def close(self) -> None:
        self._closed = True
        self._general_data = None
        self._manifest = None
        log.info("MGP: [GaiaAdapter] [close] [Adapter tancat]")


# ─── Factory ──────────────────────────────────────────────────────────

def create_star_catalog_adapter(
    gaia_path: str | Path | None = None,
) -> GaiaStarCatalogAdapter | FallbackStarCatalogAdapter:
    """Crea l'adaptador de catàleg apropiat.

    Sense arguments, resol automàticament la ruta Gaia via `resolve_gaia_data_dir()`.
    Si Gaia està disponible a la llibreria de dades (ex. `I:\\TerraLab\\data\\sky\\gaia`),
    retorna GaiaStarCatalogAdapter. Si no, retorna FallbackStarCatalogAdapter.
    """
    adapter = GaiaStarCatalogAdapter(gaia_path)
    if adapter.get_availability() in (
        GaiaAvailability.NOT_CONFIGURED,
        GaiaAvailability.UNAVAILABLE,
        GaiaAvailability.MANIFEST_MISSING,
        GaiaAvailability.MANIFEST_INVALID,
    ):
        log.info(
            "MGP: [create_star_catalog_adapter] [Gaia=%s → fallback]",
            adapter.get_availability().value,
        )
        return FallbackStarCatalogAdapter()

    return adapter
