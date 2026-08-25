"""Renderer-neutral contracts for categorical raster encodings."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from terralab3d.domain.surface.tlst import SourceValue


class CategoricalEncoding(str, Enum):
    INTEGER = "integer"
    PALETTE = "palette"
    RGB = "rgb"
    RGBA = "rgba"


@dataclass(frozen=True, slots=True)
class CategoricalValueCount:
    source_value: SourceValue
    pixel_count: int
    color_rgba: tuple[int, int, int, int] | None = None

    def __post_init__(self) -> None:
        if self.pixel_count < 1:
            raise ValueError("Categorical values must occur at least once")


@dataclass(frozen=True, slots=True)
class CategoricalRasterAnalysis:
    encoding: CategoricalEncoding
    band_indices: tuple[int, ...]
    source_dtype: str
    values: tuple[CategoricalValueCount, ...]
    valid_pixels: int
    invalid_pixels: int

    def __post_init__(self) -> None:
        expected_bands = {
            CategoricalEncoding.INTEGER: 1,
            CategoricalEncoding.PALETTE: 1,
            CategoricalEncoding.RGB: 3,
            CategoricalEncoding.RGBA: 4,
        }[self.encoding]
        if len(self.band_indices) != expected_bands:
            raise ValueError(
                f"{self.encoding.value} categorical data requires {expected_bands} bands"
            )
        if len(set(self.band_indices)) != len(self.band_indices):
            raise ValueError("Categorical band indices must be distinct")
        if self.valid_pixels < 0 or self.invalid_pixels < 0:
            raise ValueError("Categorical pixel counts cannot be negative")


def rgba_source_value(channels: tuple[int, ...]) -> str:
    if len(channels) not in {3, 4} or any(value < 0 or value > 255 for value in channels):
        raise ValueError("RGB source values require three or four bytes")
    return "#" + "".join(f"{value:02X}" for value in channels)


def source_value_rgba(value: str) -> tuple[int, int, int, int]:
    normalized = value.strip().upper()
    if len(normalized) not in {7, 9} or not normalized.startswith("#"):
        raise ValueError(f"Invalid RGB/RGBA source value: {value!r}")
    try:
        channels = tuple(
            int(normalized[index:index + 2], 16)
            for index in range(1, len(normalized), 2)
        )
    except ValueError as exc:
        raise ValueError(f"Invalid RGB/RGBA source value: {value!r}") from exc
    return (*channels, 255) if len(channels) == 3 else channels  # type: ignore[return-value]
