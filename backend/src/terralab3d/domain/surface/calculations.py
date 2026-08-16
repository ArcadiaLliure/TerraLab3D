"""Pure scientific calculations for categorical land-cover surfaces.

All functions are stateless, take plain arrays/scalars, and return plain
arrays/scalars.  No I/O, no rasterio, no pyproj, no Three.js.
"""

from __future__ import annotations

from typing import Protocol

# pyrefly: ignore [missing-import]
import numpy as np

from terralab3d.domain.surface.models import (
    LandCoverLegend,
    SurfaceMaterialDescriptor,
    SurfaceSampleGrid,
)


# ─── Protocols (kept for compatibility) ───────────────────────────────

class SurfaceSamplingCalculator(Protocol):
    """Defineix els càlculs purs de superfícies sense I/O ni renderitzat."""
    def resample(self, grid: SurfaceSampleGrid, target_width: int, target_height: int) -> SurfaceSampleGrid: ...
    def material(self, grid: SurfaceSampleGrid, style_key: str, version: int) -> SurfaceMaterialDescriptor: ...


# ─── Categorical modal downsample ─────────────────────────────────────

def categorical_modal_downsample(
    class_ids: np.ndarray,
    valid: np.ndarray,
    block_size: int,
    *,
    protected_classes: frozenset[int] = frozenset(),
) -> tuple[np.ndarray, np.ndarray]:
    """Downsample categorical class IDs using mode (majority vote).

    Unlike continuous data, class IDs cannot be averaged or interpolated.
    This function computes the most frequent class in each block.

    Protected classes are preserved even when they are not the majority
    within a block, as long as they appear at least once.  This prevents
    small but semantically important features (e.g. water bodies, urban
    pixels) from disappearing during LOD reduction.

    Parameters
    ----------
    class_ids : uint16 array of shape (N,)
    valid : bool array of shape (N,)
    block_size : number of contiguous samples per block
    protected_classes : class IDs that survive even as minorities

    Returns
    -------
    reduced_class_ids : uint16 array of shape (ceil(N / block_size),)
    reduced_valid : bool array of shape (ceil(N / block_size),)
    """
    n = class_ids.shape[0]
    if block_size <= 1 or n == 0:
        return class_ids.copy(), valid.copy()

    blocks = int(np.ceil(n / block_size))
    result_ids = np.zeros(blocks, dtype=np.uint16)
    result_valid = np.zeros(blocks, dtype=bool)

    for i in range(blocks):
        start = i * block_size
        stop = min(start + block_size, n)
        block_valid = valid[start:stop]
        if not np.any(block_valid):
            continue

        block_classes = class_ids[start:stop][block_valid]

        # Check for protected classes first
        for pc in protected_classes:
            if np.any(block_classes == pc):
                result_ids[i] = pc
                result_valid[i] = True
                break
        else:
            # Modal vote: most frequent class wins
            unique, counts = np.unique(block_classes, return_counts=True)
            winner_idx = int(np.argmax(counts))
            result_ids[i] = unique[winner_idx]
            result_valid[i] = True

    return result_ids, result_valid


# ─── RGB categorical decode ──────────────────────────────────────────

def decode_rgb_to_class(
    rgb: np.ndarray,
    legend: LandCoverLegend,
) -> tuple[np.ndarray, np.ndarray]:
    """Decode exact RGB(A) pixel values to class IDs using a legend.

    This is NOT an ortho-photo interpretation.  Only lossless exact color
    matches are accepted.  An unknown color becomes nodata/unresolved.

    Parameters
    ----------
    rgb : uint8 array of shape (N, 3) or (N, 4)
    legend : the legend providing color → class_id mapping

    Returns
    -------
    class_ids : uint16 array of shape (N,)
    valid : bool array of shape (N,)
    """
    n = rgb.shape[0]
    class_ids = np.zeros(n, dtype=np.uint16)
    valid = np.zeros(n, dtype=bool)

    if n == 0 or not legend.entries:
        return class_ids, valid

    # Build lookup: pack RGB(A) into a single int64 key
    color_to_class: dict[int, int] = {}
    nodata_classes: set[int] = set()
    for entry in legend.entries:
        if entry.is_nodata or entry.is_transparent:
            nodata_classes.add(entry.class_id)
            continue
        r, g, b, a = entry.rgba
        key = (r << 24) | (g << 16) | (b << 8) | a
        color_to_class[key] = entry.class_id

    # Pack sample colors
    if rgb.shape[1] >= 4:
        keys = (
            rgb[:, 0].astype(np.int64) << 24
            | rgb[:, 1].astype(np.int64) << 16
            | rgb[:, 2].astype(np.int64) << 8
            | rgb[:, 3].astype(np.int64)
        )
    else:
        keys = (
            rgb[:, 0].astype(np.int64) << 24
            | rgb[:, 1].astype(np.int64) << 16
            | rgb[:, 2].astype(np.int64) << 8
            | np.int64(255)
        )

    for color_key, cid in color_to_class.items():
        mask = keys == color_key
        class_ids[mask] = cid
        valid[mask] = True

    return class_ids, valid


# ─── Palette index mapping ────────────────────────────────────────────

def build_palette_index_map(
    class_ids: np.ndarray,
    source_slots: np.ndarray,
    legend: LandCoverLegend | None,
) -> tuple[np.ndarray, list[tuple[int, int, int, int, int, int]]]:
    """Map (rawClassId, sourceSlot) pairs to compact palette indices.

    Different sources may reuse the same numeric class ID for different
    semantic categories.  This function assigns a unique palette index
    to each (classId, sourceSlot) pair.

    Returns
    -------
    palette_indices : uint16 array of shape (N,)
    palette_entries : list of (paletteIndex, classId, r, g, b, a)
        Index 0 is always reserved for nodata/invalid/fallback-base.
    """
    n = class_ids.shape[0]
    if n == 0:
        return np.zeros(0, dtype=np.uint16), [(0, 0, 0, 0, 0, 0)]

    c_arr = np.asarray(class_ids, dtype=np.uint16).reshape(-1)
    s_arr = np.asarray(source_slots, dtype=np.int16).reshape(-1)

    # Preserve appearance order via unique with return_index
    packed = (c_arr.astype(np.uint32) << 16) | (s_arr.view(np.uint16).astype(np.uint32))
    _, first_indices, inverse = np.unique(packed, return_index=True, return_inverse=True)

    order = np.argsort(first_indices)
    unique_ordered = packed[first_indices[order]]
    remap = np.empty(len(first_indices), dtype=np.uint16)
    remap[order] = np.arange(1, len(first_indices) + 1, dtype=np.uint16)
    palette_indices = remap[inverse]

    palette_entries: list[tuple[int, int, int, int, int, int]] = [
        (0, 0, 0, 0, 0, 0),  # index 0 = nodata/invalid
    ]

    for idx, p in enumerate(unique_ordered, start=1):
        cid = int(p >> 16)
        r, g, b, a = 128, 128, 128, 255
        if legend is not None:
            entry = legend.entry_by_class(cid)
            if entry is not None:
                r, g, b, a = entry.rgba
        elif cid == 0:
            r, g, b, a = 0, 0, 0, 0
        palette_entries.append((idx, cid, r, g, b, a))

    return palette_indices, palette_entries




# ─── sRGB ↔ linear ───────────────────────────────────────────────────

def srgb_to_linear_float(srgb: np.ndarray) -> np.ndarray:
    """Convert sRGB [0,255] uint8 to linear [0,1] float32."""
    normalized = np.asarray(srgb, dtype=np.float32) / 255.0
    return np.where(
        normalized <= 0.04045,
        normalized / 12.92,
        ((normalized + 0.055) / 1.055) ** 2.4,
    ).astype(np.float32)


def srgb_u8_to_linear_u8(rgb: np.ndarray) -> np.ndarray:
    """Convert sRGB [0,255] uint8 to linear [0,255] uint8."""
    linear = srgb_to_linear_float(rgb)
    return np.rint(np.clip(linear, 0.0, 1.0) * 255.0).astype(np.uint8)


def linear_u8_to_srgb_u8(linear: np.ndarray) -> np.ndarray:
    """Convert linear [0,255] uint8 back to sRGB [0,255] uint8."""
    normalized = np.asarray(linear, dtype=np.float32) / 255.0
    srgb = np.where(
        normalized <= 0.0031308,
        normalized * 12.92,
        1.055 * (normalized ** (1.0 / 2.4)) - 0.055,
    )
    return np.rint(np.clip(srgb, 0.0, 1.0) * 255.0).astype(np.uint8)
