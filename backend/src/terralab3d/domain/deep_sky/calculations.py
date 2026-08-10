"""Contractes i càlculs científics purs per a objectes de cel profund."""

from __future__ import annotations

import math
import re
from typing import Optional, List, Protocol
from terralab3d.domain.deep_sky.models import DeepSkyObject


class DeepSkyVisibilityCalculator(Protocol):
    """Defineix els càlculs purs de objectes de cel profund sense I/O ni renderitzat."""
    def visible(self, item: DeepSkyObject, limiting_magnitude: float, minimum_surface_brightness: float) -> bool: ...
    def apparent_extent_deg(self, item: DeepSkyObject) -> tuple[float, float]: ...


def to_opt_float(value: object) -> Optional[float]:
    try:
        out = float(value)
    except Exception:
        return None
    if not math.isfinite(out):
        return None
    return out


def to_opt_int(value: object) -> Optional[int]:
    try:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        try:
            return int(float(text))
        except Exception:
            m = re.search(r"-?\d+", text)
            if not m:
                return None
            return int(m.group(0))
    except Exception:
        return None


def split_sexagesimal(text: str) -> Optional[List[str]]:
    raw = str(text or "").strip()
    if not raw:
        return None
    t = (
        raw.replace("h", ":")
        .replace("m", ":")
        .replace("s", "")
        .replace("d", ":")
        .replace("'", ":")
        .replace('"', "")
    )
    if ":" in t:
        parts = [p.strip() for p in t.split(":") if str(p).strip()]
        return parts if len(parts) >= 2 else None
    parts = [p.strip() for p in re.split(r"\s+", t) if str(p).strip()]
    return parts if len(parts) >= 2 else None


def parse_ra_deg(value: object, *, assume_hours_for_scalar: bool = False) -> Optional[float]:
    """Parseja Ascensió Recta a graus decimals des de sexagesimal o escalar."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None

    sexa = split_sexagesimal(text)
    if sexa is not None:
        try:
            hh = abs(float(sexa[0]))
            mm = abs(float(sexa[1])) if len(sexa) >= 2 else 0.0
            ss = abs(float(sexa[2])) if len(sexa) >= 3 else 0.0
            return float((hh + mm / 60.0 + ss / 3600.0) * 15.0) % 360.0
        except Exception:
            pass

    out = to_opt_float(text)
    if out is None:
        return None
    if assume_hours_for_scalar and 0.0 <= out <= 24.0:
        return float(out * 15.0) % 360.0
    return float(out) % 360.0


def parse_dec_deg(value: object) -> Optional[float]:
    """Parseja Declinació a graus decimals des de sexagesimal o escalar."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None

    sexa = split_sexagesimal(text)
    if sexa is not None:
        try:
            sign = -1.0 if str(sexa[0]).strip().startswith("-") else 1.0
            dd = abs(float(sexa[0]))
            mm = abs(float(sexa[1])) if len(sexa) >= 2 else 0.0
            ss = abs(float(sexa[2])) if len(sexa) >= 3 else 0.0
            out = sign * (dd + mm / 60.0 + ss / 3600.0)
            return float(max(-90.0, min(90.0, out)))
        except Exception:
            pass

    out = to_opt_float(text)
    if out is None:
        return None
    return float(max(-90.0, min(90.0, out)))


def compute_equatorial_triad(ra_deg: float, dec_deg: float) -> tuple[list[float], list[float], list[float]]:
    """Calcula el vector posició unitari equatorial i els seus tangents Nord i Est."""
    ra_rad = math.radians(ra_deg)
    dec_rad = math.radians(dec_deg)

    eq_dir = [
        math.cos(dec_rad) * math.cos(ra_rad),
        math.cos(dec_rad) * math.sin(ra_rad),
        math.sin(dec_rad),
    ]
    north_tangent = [
        -math.sin(dec_rad) * math.cos(ra_rad),
        -math.sin(dec_rad) * math.sin(ra_rad),
        math.cos(dec_rad),
    ]
    east_tangent = [
        -math.sin(ra_rad),
        math.cos(ra_rad),
        0.0,
    ]
    return eq_dir, north_tangent, east_tangent


def parse_axis_dimensions(
    maj_raw: object, min_raw: object, maj_key: str, min_key: str
) -> tuple[float, float]:
    """Calcula les dimensions angulars principals i secundàries en graus decimals."""
    maj_val = to_opt_float(maj_raw)
    min_val = to_opt_float(min_raw)

    if maj_val is None:
        maj = 0.10
    elif maj_key == "majax":
        maj = max(0.02, float(maj_val) / 60.0)
    else:
        maj = max(0.02, float(maj_val))

    if min_val is None:
        min_ax = maj
    elif min_key == "minax":
        min_ax = max(0.01, float(min_val) / 60.0)
    else:
        min_ax = max(0.01, float(min_val))

    if min_ax > maj:
        maj, min_ax = min_ax, maj

    return maj, min_ax
