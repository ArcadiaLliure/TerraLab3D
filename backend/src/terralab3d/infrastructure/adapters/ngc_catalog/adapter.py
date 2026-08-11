"""Adaptador per al catàleg OpenNGC i post-processat a binari."""

from __future__ import annotations

import csv
from dataclasses import dataclass
import hashlib
import json
import logging
import re
import struct
from pathlib import Path
from typing import Any, Optional

from terralab3d.application.ports.catalogs import DeepSkyCatalogPort
from terralab3d.application.ports.resource_processing import ProcessedResource, ResourcePostProcessor
from terralab3d.domain.deep_sky.calculations import (
    compute_equatorial_triad,
    parse_axis_dimensions,
    parse_dec_deg,
    parse_ra_deg,
    to_opt_float,
)
from terralab3d.domain.deep_sky.models import DeepSkyKind
from terralab3d.domain.identifiers import ResourceId, VariantId
from terralab3d.domain.resources.models import ResourceInstallState
from terralab3d.infrastructure.app_paths import resolve_data_root, resolve_derived_resource_dir

log = logging.getLogger("terralab3d.ngc_adapter")


class NgcFlags:
    HAS_MAJOR = 1 << 0
    HAS_MINOR = 1 << 1
    HAS_PA = 1 << 2
    HAS_MAG = 1 << 3
    MAG_IS_V = 1 << 4
    MAG_IS_B = 1 << 5
    HAS_SURFACE_BRIGHTNESS = 1 << 6
    RENDER_ELIGIBLE = 1 << 7


def _map_type(type_str: str) -> tuple[DeepSkyKind, bool]:
    s = type_str.strip()
    if s in ("G", "GPair", "GTrpl", "GGroup"):
        return DeepSkyKind.GALAXY, True
    if s == "OCl":
        return DeepSkyKind.OPEN_CLUSTER, True
    if s == "GCl":
        return DeepSkyKind.GLOBULAR_CLUSTER, True
    if s in ("PN", "HII", "DrkN", "EmN", "Neb", "RfN", "SNR"):
        return DeepSkyKind.NEBULA, True
    if s == "Cl+N":
        return DeepSkyKind.CLUSTER_NEBULA, True
    if s == "*Ass":
        return DeepSkyKind.STELLAR_ASSOCIATION, True
    if s in ("*", "**", "Dup", "NonEx"):
        return DeepSkyKind.OTHER, False
    return DeepSkyKind.OTHER, True


def _normalized_key(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").strip().lower())


def _row_map(row: dict) -> dict:
    out = {}
    for k, v in row.items():
        nk = _normalized_key(k)
        if nk and nk not in out:
            out[nk] = v
    return out


def _pick_value(mapped: dict, *keys: str):
    for k in keys:
        nk = _normalized_key(k)
        if nk in mapped:
            return mapped[nk]
    return None


def _pick_key_value(mapped: dict, *keys: str):
    for k in keys:
        nk = _normalized_key(k)
        if nk in mapped:
            return nk, mapped[nk]
    return "", None



_NAME_RE = re.compile(r"^(NGC|IC)\s*0*([0-9]+[A-Za-z]?)$", re.IGNORECASE)

def _to_opt_int(value: object) -> 'int | None':
    try:
        if value is None: return None
        text = str(value).strip()
        if not text: return None
        try: return int(float(text))
        except Exception:
            m = re.search(r"-?\d+", text)
            return int(m.group(0)) if m else None
    except Exception: return None

def _first_common_name(value: object) -> 'str | None':
    text = str(value or "").strip()
    if not text: return None
    for sep in ("|", ";"): text = text.replace(sep, ",")
    parts = [p.strip() for p in text.split(",") if p.strip()]
    return parts[0] if parts else None

def _normalize_obj_name(name: str) -> str:
    text = str(name or "").strip()
    if not text: return ""
    compact = re.sub(r"\s+", "", text)
    match = _NAME_RE.match(compact)
    if not match: return text
    return f"{match.group(1).upper()}{match.group(2).upper()}"

class NgcCatalogPostProcessor(ResourcePostProcessor):

    """Processa el CSV d'OpenNGC cap a un payload binari compacte i persistent."""

    def process(self, source_path: Path, output_dir: Path) -> ProcessedResource:
        output_dir.mkdir(parents=True, exist_ok=True)
        bin_path = output_dir / "ngc_index.bin"

        equatorial_dirs: list[list[float]] = []
        north_tangents: list[list[float]] = []
        east_tangents: list[list[float]] = []
        major_axis: list[float] = []
        minor_axis: list[float] = []
        position_angle: list[float] = []
        magnitude: list[float] = []
        surface_brightness: list[float] = []
        family_code: list[int] = []
        flags: list[int] = []
        catalog_index: list[int] = []
        object_labels: list[str] = []

        record_count = 0
        renderable_count = 0
        type_counts = {k.name: 0 for k in DeepSkyKind}

        family_code_map = {
            "GALAXY": 0,
            "OPEN_CLUSTER": 1,
            "GLOBULAR_CLUSTER": 2,
            "NEBULA": 3,
            "CLUSTER_NEBULA": 4,
            "STELLAR_ASSOCIATION": 5,
            "OTHER": 6,
        }

        with open(source_path, "r", encoding="utf-8-sig", newline="") as f:
            sample = f.read(8192)
            f.seek(0)
            delimiter = ","
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",;|\t")
                delimiter = str(getattr(dialect, "delimiter", ",") or ",")
            except Exception:
                if ";" in sample and "," not in sample.splitlines()[0]:
                    delimiter = ";"
            reader = csv.DictReader(f, delimiter=delimiter)

            for row in reader:
                if not isinstance(row, dict):
                    continue

                mapped = _row_map(row)
                record_count += 1

                type_str = str(_pick_value(mapped, "obj_type", "type") or "").strip()
                family, eligible = _map_type(type_str)

                ra_deg = parse_ra_deg(_pick_value(mapped, "raj2000", "ra_deg", "radeg"), assume_hours_for_scalar=False)
                if ra_deg is None:
                    ra_deg = parse_ra_deg(_pick_value(mapped, "ra"), assume_hours_for_scalar=True)

                dec_deg = parse_dec_deg(_pick_value(mapped, "dej2000", "dec_deg", "decj2000", "dec"))

                if ra_deg is None or dec_deg is None or not eligible:
                    continue

                # Càlculs purs de domini: triad d'unitats equatorials i tangents
                eq_dir, north, east = compute_equatorial_triad(ra_deg, dec_deg)

                maj_key, maj_raw = _pick_key_value(mapped, "maj_ax_deg", "majaxdeg", "majax")
                min_key, min_raw = _pick_key_value(mapped, "min_ax_deg", "minaxdeg", "minax")

                # Càlcul pur de domini: dimensions angulars
                maj_deg, min_deg = parse_axis_dimensions(maj_raw, min_raw, maj_key, min_key)

                pa = to_opt_float(_pick_value(mapped, "pos_ang", "posang"))
                v_mag = to_opt_float(_pick_value(mapped, "mag_v", "vmag"))
                b_mag = to_opt_float(_pick_value(mapped, "mag_b", "bmag"))
                surf_br = to_opt_float(_pick_value(mapped, "surf_br_B", "surfbrb", "surfbr"))

                # Convertir a minuts d'arc per al buffer binari
                maj_arcmin = maj_deg * 60.0
                min_arcmin = min_deg * 60.0

                f_flags = 0
                f_flags |= NgcFlags.RENDER_ELIGIBLE
                renderable_count += 1
                type_counts[family.name] += 1

                maj_val = to_opt_float(maj_raw)
                min_val = to_opt_float(min_raw)
                if maj_val is not None:
                    f_flags |= NgcFlags.HAS_MAJOR
                if min_val is not None:
                    f_flags |= NgcFlags.HAS_MINOR
                if pa is not None:
                    f_flags |= NgcFlags.HAS_PA

                mag = -1.0
                if v_mag is not None:
                    mag = v_mag
                    f_flags |= NgcFlags.HAS_MAG | NgcFlags.MAG_IS_V
                elif b_mag is not None:
                    mag = b_mag
                    f_flags |= NgcFlags.HAS_MAG | NgcFlags.MAG_IS_B

                if surf_br is not None:
                    f_flags |= NgcFlags.HAS_SURFACE_BRIGHTNESS

                raw_name = str(_pick_value(mapped, "name") or "").strip()
                if not raw_name:
                    ngc_nr = _to_opt_int(_pick_value(mapped, "ngc"))
                    ic_nr = _to_opt_int(_pick_value(mapped, "ic"))
                    if ngc_nr is not None and ngc_nr > 0:
                        raw_name = f"NGC {ngc_nr}"
                    elif ic_nr is not None and ic_nr > 0:
                        raw_name = f"IC {ic_nr}"
                
                name_clean = _normalize_obj_name(raw_name) if raw_name else ""
                messier = _to_opt_int(_pick_value(mapped, "messier_nr", "m"))
                comname = _first_common_name(_pick_value(mapped, "comname", "common_names", "common names"))

                label_parts = []
                if messier and messier > 0:
                    label_parts.append(f"M{messier}")
                if name_clean:
                    label_parts.append(name_clean)
                if comname and comname not in label_parts:
                    label_parts.append(comname)
                
                final_label = " · ".join(label_parts) if label_parts else "NGC"

                equatorial_dirs.append(eq_dir)

                north_tangents.append(north)
                east_tangents.append(east)
                major_axis.append(maj_arcmin)
                minor_axis.append(min_arcmin)
                position_angle.append(pa if pa is not None else -1.0)
                magnitude.append(mag)
                surface_brightness.append(surf_br if surf_br is not None else -1.0)
                family_code.append(family_code_map.get(family.name, 6))
                flags.append(f_flags)
                catalog_index.append(record_count - 1)
                object_labels.append(final_label)

        out_buf = bytearray()
        for eq in equatorial_dirs:
            out_buf.extend(struct.pack("<fff", *eq))
        l_eq = len(out_buf)

        for no in north_tangents:
            out_buf.extend(struct.pack("<fff", *no))
        l_no = len(out_buf) - l_eq

        for ea in east_tangents:
            out_buf.extend(struct.pack("<fff", *ea))
        l_ea = len(out_buf) - l_eq - l_no

        for ma in major_axis:
            out_buf.extend(struct.pack("<f", ma))
        l_ma = len(out_buf) - l_eq - l_no - l_ea

        for mi in minor_axis:
            out_buf.extend(struct.pack("<f", mi))
        l_mi = len(out_buf) - l_eq - l_no - l_ea - l_ma

        for pa in position_angle:
            out_buf.extend(struct.pack("<f", pa))
        l_pa = len(out_buf) - l_eq - l_no - l_ea - l_ma - l_mi

        for mag in magnitude:
            out_buf.extend(struct.pack("<f", mag))
        l_mg = len(out_buf) - l_eq - l_no - l_ea - l_ma - l_mi - l_pa

        for sb in surface_brightness:
            out_buf.extend(struct.pack("<f", sb))
        l_su = len(out_buf) - l_eq - l_no - l_ea - l_ma - l_mi - l_pa - l_mg

        for fa in family_code:
            out_buf.extend(struct.pack("<I", fa))
        l_fa = len(out_buf) - l_eq - l_no - l_ea - l_ma - l_mi - l_pa - l_mg - l_su

        for fl in flags:
            out_buf.extend(struct.pack("<I", fl))
        l_fl = len(out_buf) - l_eq - l_no - l_ea - l_ma - l_mi - l_pa - l_mg - l_su - l_fa

        for ci in catalog_index:
            out_buf.extend(struct.pack("<I", ci))
        l_id = len(out_buf) - l_eq - l_no - l_ea - l_ma - l_mi - l_pa - l_mg - l_su - l_fa - l_fl

        with open(bin_path, "wb") as f_out:
            f_out.write(out_buf)

        content_sha256 = hashlib.sha256(out_buf).hexdigest()[:16]

        metadata = {
            "role": "deep_sky_catalog",
            "version": 4,
            "resourceId": "sky.ngc",
            "recordCount": record_count,
            "renderableCount": renderable_count,
            "typeCounts": type_counts,
            "processedIndexSha256": content_sha256,
            "objectLabels": object_labels,
            "bufferLayout": {
                "equatorialDirections": {"offset": 0, "length": l_eq, "dtype": "float32", "components": 3},
                "northTangents": {"offset": l_eq, "length": l_no, "dtype": "float32", "components": 3},
                "eastTangents": {"offset": l_eq + l_no, "length": l_ea, "dtype": "float32", "components": 3},
                "majorAxisArcmin": {"offset": l_eq + l_no + l_ea, "length": l_ma, "dtype": "float32", "components": 1},
                "minorAxisArcmin": {"offset": l_eq + l_no + l_ea + l_ma, "length": l_mi, "dtype": "float32", "components": 1},
                "positionAngleDeg": {"offset": l_eq + l_no + l_ea + l_ma + l_mi, "length": l_pa, "dtype": "float32", "components": 1},
                "magnitude": {"offset": l_eq + l_no + l_ea + l_ma + l_mi + l_pa, "length": l_mg, "dtype": "float32", "components": 1},
                "surfaceBrightness": {"offset": l_eq + l_no + l_ea + l_ma + l_mi + l_pa + l_mg, "length": l_su, "dtype": "float32", "components": 1},
                "familyCode": {"offset": l_eq + l_no + l_ea + l_ma + l_mi + l_pa + l_mg + l_su, "length": l_fa, "dtype": "uint32", "components": 1},
                "flags": {"offset": l_eq + l_no + l_ea + l_ma + l_mi + l_pa + l_mg + l_su + l_fa, "length": l_fl, "dtype": "uint32", "components": 1},
                "catalogIndex": {"offset": l_eq + l_no + l_ea + l_ma + l_mi + l_pa + l_mg + l_su + l_fa + l_fl, "length": l_id, "dtype": "uint32", "components": 1},
            },
        }

        meta_file = output_dir / "sky.ngc.json"
        with open(meta_file, "w", encoding="utf-8") as f_meta:
            json.dump(metadata, f_meta, indent=2)

        return ProcessedResource(bin_path, metadata)


@dataclass
class NgcSearchItem:
    name: str
    common_name: str | None
    messier_nr: int | None
    ra_deg: float
    dec_deg: float


class NgcCatalogAdapter(DeepSkyCatalogPort):
    """Adaptador per llegir l'índex binari d'NGC del repositori de recursos."""

    def __init__(self, resource_repo: Any):
        self._resource_repo = resource_repo

    def _resolve_csv_source(self) -> Path | None:
        data_root = resolve_data_root()
        for p in [
            data_root / "data" / "sky" / "managed" / "NGC.csv",
            data_root / "data" / "sky" / "openngc_catalog.csv",
            data_root / "data" / "sky" / "ngc" / "NGC.csv",
        ]:
            if p.exists():
                return p
        return None

    def load_search_objects(self) -> list[NgcSearchItem]:
        source_path = self._resolve_csv_source()
        if not source_path:
            return []

        items: list[NgcSearchItem] = []
        try:
            with open(source_path, "r", encoding="utf-8-sig", newline="") as f:
                sample = f.read(8192)
                f.seek(0)
                delimiter = ";" if ";" in sample and "," not in sample.splitlines()[0] else ","
                try:
                    dialect = csv.Sniffer().sniff(sample, delimiters=",;|\t")
                    delimiter = str(getattr(dialect, "delimiter", ",") or ",")
                except Exception:
                    pass
                reader = csv.DictReader(f, delimiter=delimiter)
                for row in reader:
                    if not isinstance(row, dict):
                        continue
                    mapped = _row_map(row)
                    ra_deg = parse_ra_deg(_pick_value(mapped, "raj2000", "ra_deg", "radeg"), assume_hours_for_scalar=False)
                    if ra_deg is None:
                        ra_deg = parse_ra_deg(_pick_value(mapped, "ra"), assume_hours_for_scalar=True)
                    dec_deg = parse_dec_deg(_pick_value(mapped, "dej2000", "dec_deg", "decj2000", "dec"))
                    if ra_deg is None or dec_deg is None:
                        continue

                    raw_name = str(_pick_value(mapped, "name") or "").strip()
                    if not raw_name:
                        ngc_nr = _to_opt_int(_pick_value(mapped, "ngc"))
                        ic_nr = _to_opt_int(_pick_value(mapped, "ic"))
                        if ngc_nr is not None and ngc_nr > 0:
                            raw_name = f"NGC {ngc_nr}"
                        elif ic_nr is not None and ic_nr > 0:
                            raw_name = f"IC {ic_nr}"
                    
                    name_clean = _normalize_obj_name(raw_name) if raw_name else ""
                    messier = _to_opt_int(_pick_value(mapped, "messier_nr", "m"))
                    comname = _first_common_name(_pick_value(mapped, "comname", "common_names", "common names"))

                    if name_clean or comname or messier:
                        items.append(NgcSearchItem(
                            name=name_clean or (f"M{messier}" if messier else "NGC"),
                            common_name=comname,
                            messier_nr=messier,
                            ra_deg=ra_deg,
                            dec_deg=dec_deg,
                        ))
        except Exception as e:
            log.error("MGP: [NgcCatalogAdapter] Error carregant objectes de cerca NGC: %s", e)
        return items

    def load_index(self) -> tuple[dict[str, Any], bytes] | None:
        resource_id = ResourceId("sky.ngc")
        state = self._resource_repo.get_resource_state(resource_id)

        bin_file = self._resource_repo.resolve_render_asset(resource_id)

        if not bin_file or not bin_file.exists():
            source_path = self._resolve_csv_source()
            if not source_path and state and state.get("resolvedPath"):
                p = Path(state["resolvedPath"])
                if p.exists():
                    source_path = p

            if not source_path:
                log.warning("MGP: [NgcCatalogAdapter] No s'ha trobat cap font CSV per a sky.ngc")
                return None

            cache_dir = resolve_derived_resource_dir(resource_id)
            post_processor = NgcCatalogPostProcessor()
            processed = post_processor.process(source_path, cache_dir)

            self._resource_repo.set_resource_state(
                resource_id,
                ResourceInstallState.READY,
                variant_id=VariantId("pinned"),
                resolved_path=str(source_path),
                downloaded_bytes=source_path.stat().st_size if source_path.exists() else 0,
                manifest_data={
                    "renderPath": str(processed.render_path),
                    "sourcePath": str(source_path),
                    **processed.metadata
                }
            )
            bin_file = processed.render_path

        cache_dir = bin_file.parent
        meta_file = cache_dir / "sky.ngc.json"

        if not meta_file.exists() or not bin_file.exists():
            log.warning("MGP: [NgcCatalogAdapter] Els fitxers sky.ngc.json o ngc_index.bin no existeixen a %s", cache_dir)
            return None

        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)
            with open(bin_file, "rb") as f:
                data = f.read()
            return meta, data
        except Exception as e:
            log.error("MGP: [NgcCatalogAdapter] Error llegint índex NGC: %s", e)
            return None
