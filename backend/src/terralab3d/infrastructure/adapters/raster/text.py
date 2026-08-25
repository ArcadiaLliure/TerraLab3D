"""Strict TXT/CSV matrix and regular XYZ materialization for raster import."""

from __future__ import annotations

import csv
import hashlib
import re
from pathlib import Path

import numpy as np
import rasterio
from affine import Affine

from terralab3d.domain.raster.models import TextRasterOptions


class TextRasterError(ValueError):
    pass


class TextRasterMaterializer:
    DELIMITERS = (",", ";", "\t", " ")

    def materialize(
        self,
        source_path: Path | str,
        cache_dir: Path | str,
        options: TextRasterOptions,
    ) -> Path:
        source = Path(source_path)
        if not source.is_file():
            raise TextRasterError(f"Text raster does not exist: {source}")
        rows, delimiter, had_header = self._read_rows(source, options)
        layout = options.layout
        if layout not in {"matrix", "xyz"}:
            if rows and len(rows[0]) == 3:
                raise TextRasterError("Text layout is ambiguous; confirm matrix or XYZ")
            raise TextRasterError("Text layout must be confirmed explicitly")

        if layout == "matrix":
            if options.transform is None or options.crs is None:
                raise TextRasterError("Matrix rasters require explicit CRS and transform")
            values = _numeric_matrix(rows)
            transform = Affine(*options.transform)
        else:
            values, transform = _regular_xyz(rows)
            if options.crs is None:
                raise TextRasterError("XYZ rasters require an explicit CRS")

        cache_root = Path(cache_dir)
        cache_root.mkdir(parents=True, exist_ok=True)
        signature = hashlib.blake2b(digest_size=16)
        signature.update(source.read_bytes())
        signature.update(repr(options).encode("utf-8"))
        target = cache_root / f"text-raster-{signature.hexdigest()}.tif"
        if target.exists():
            return target
        temp = target.with_suffix(".tmp.tif")
        with rasterio.open(
            temp,
            "w",
            driver="GTiff",
            width=values.shape[1],
            height=values.shape[0],
            count=1,
            dtype=values.dtype,
            crs=options.crs,
            transform=transform,
            nodata=options.nodata,
        ) as dataset:
            dataset.write(values, 1)
            dataset.update_tags(
                TERRALAB_SOURCE=str(source.resolve(strict=False)),
                TERRALAB_TEXT_LAYOUT=layout,
                TERRALAB_TEXT_DELIMITER=repr(delimiter),
                TERRALAB_TEXT_HEADER=str(had_header).lower(),
            )
        temp.replace(target)
        return target

    def _read_rows(
        self,
        source: Path,
        options: TextRasterOptions,
    ) -> tuple[list[list[str]], str, bool]:
        lines = [line.strip() for line in source.read_text(encoding="utf-8-sig").splitlines()]
        lines = [line for line in lines if line and not line.startswith("#")]
        if not lines:
            raise TextRasterError("Text raster is empty")
        delimiter = options.delimiter or _detect_delimiter(lines[:8])
        if delimiter not in self.DELIMITERS:
            raise TextRasterError("Unsupported text delimiter")
        parsed = [_split_line(line, delimiter) for line in lines]
        widths = {len(row) for row in parsed}
        if len(widths) != 1:
            raise TextRasterError("Text raster rows have inconsistent column counts")
        inferred_header = not all(_is_number(value) for value in parsed[0])
        if options.has_header is None and inferred_header:
            raise TextRasterError("Text header presence must be confirmed")
        has_header = options.has_header if options.has_header is not None else False
        if has_header:
            parsed = parsed[1:]
        if not parsed:
            raise TextRasterError("Text raster has no numeric rows")
        return parsed, delimiter, bool(has_header)


def _detect_delimiter(lines: list[str]) -> str:
    candidates: list[tuple[int, str]] = []
    for delimiter in TextRasterMaterializer.DELIMITERS:
        widths = [len(_split_line(line, delimiter)) for line in lines]
        if min(widths) > 1 and len(set(widths)) == 1:
            candidates.append((widths[0], delimiter))
    if not candidates:
        raise TextRasterError("Unable to determine the text delimiter")
    best_width = max(width for width, _ in candidates)
    best = [delimiter for width, delimiter in candidates if width == best_width]
    if len(best) != 1:
        raise TextRasterError("Text delimiter is ambiguous; confirm it explicitly")
    return best[0]


def _split_line(line: str, delimiter: str) -> list[str]:
    if delimiter == " ":
        return [value for value in re.split(r"\s+", line.strip()) if value]
    return next(csv.reader([line], delimiter=delimiter, skipinitialspace=True))


def _is_number(value: str) -> bool:
    try:
        float(value)
        return True
    except ValueError:
        return False


def _numeric_matrix(rows: list[list[str]]) -> np.ndarray:
    if not all(_is_number(value) for row in rows for value in row):
        raise TextRasterError("Text raster contains non-numeric cells")
    integer = all(re.fullmatch(r"[-+]?\d+", value.strip()) is not None for row in rows for value in row)
    try:
        return np.asarray(rows, dtype=np.int64 if integer else np.float64)
    except (TypeError, ValueError) as exc:
        raise TextRasterError("Text raster values cannot be represented losslessly") from exc


def _regular_xyz(rows: list[list[str]]) -> tuple[np.ndarray, Affine]:
    if any(len(row) != 3 for row in rows):
        raise TextRasterError("XYZ rows must contain exactly x, y and z")
    values = _numeric_matrix(rows).astype(np.float64, copy=False)
    x_values = np.unique(values[:, 0])
    y_values = np.unique(values[:, 1])
    if x_values.size < 2 or y_values.size < 2:
        raise TextRasterError("XYZ requires at least a 2×2 regular grid")
    if values.shape[0] != x_values.size * y_values.size:
        raise TextRasterError("XYZ points are duplicated or do not fill a regular grid")
    x_steps = np.diff(x_values)
    y_steps = np.diff(y_values)
    if not np.allclose(x_steps, x_steps[0], rtol=1e-10, atol=1e-12) or not np.allclose(
        y_steps, y_steps[0], rtol=1e-10, atol=1e-12
    ):
        raise TextRasterError("Irregular XYZ points are a point cloud, not a raster")
    by_coordinate: dict[tuple[float, float], float] = {}
    for x, y, z in values:
        key = (float(x), float(y))
        if key in by_coordinate:
            raise TextRasterError("XYZ contains duplicate coordinates")
        by_coordinate[key] = float(z)
    descending_y = y_values[::-1]
    grid = np.asarray(
        [[by_coordinate[(float(x), float(y))] for x in x_values] for y in descending_y],
        dtype=np.float64,
    )
    x_resolution = float(x_steps[0])
    y_resolution = float(y_steps[0])
    transform = Affine(
        x_resolution,
        0.0,
        float(x_values[0]) - x_resolution / 2.0,
        0.0,
        -y_resolution,
        float(y_values[-1]) + y_resolution / 2.0,
    )
    return grid, transform
