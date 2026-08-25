"""Rasterio implementation of the neutral raster port.

There is deliberately no extension whitelist. GDAL determines whether a URI
is a dataset and the adapter reports the concrete driver/capability failure.
"""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from threading import RLock
from typing import Any, Mapping

import numpy as np
import rasterio
from affine import Affine
from rasterio.enums import Resampling
from rasterio.windows import Window, transform as window_transform

from terralab3d.domain.raster.models import (
    RasterBandDescriptor,
    RasterDatasetDescriptor,
    RasterDatasetError,
    RasterDatasetSelection,
    RasterMetadataOverride,
    RasterWindow,
    RasterWindowRequest,
    RasterSelectionRequired,
    TransformTuple,
)


class RasterioRasterReader:
    def __init__(self, *, max_open_datasets: int = 8) -> None:
        self._max_open_datasets = max(1, int(max_open_datasets))
        self._datasets: OrderedDict[str, Any] = OrderedDict()
        self._lock = RLock()
        self._closed = False

    def drivers(self) -> Mapping[str, str]:
        with rasterio.Env() as environment:
            return dict(environment.drivers())

    def inspect(
        self,
        uri: str,
        *,
        subdataset: str | None = None,
    ) -> RasterDatasetDescriptor:
        selected_uri = subdataset or uri
        try:
            with rasterio.open(selected_uri) as dataset:
                return self._descriptor(uri, dataset, selected_uri=selected_uri)
        except (OSError, rasterio.errors.RasterioError) as exc:
            available = ", ".join(sorted(self.drivers()))
            raise RasterDatasetError(
                f"GDAL cannot open dataset {selected_uri!r}. The dataset is incompatible "
                f"or its driver is unavailable. Installed drivers: {available}"
            ) from exc

    def validate_selection(self, selection: RasterDatasetSelection) -> RasterDatasetDescriptor:
        container = self.inspect(selection.uri)
        if container.subdatasets and selection.subdataset is None:
            raise RasterSelectionRequired(
                f"Dataset exposes {len(container.subdatasets)} subdatasets; select one explicitly"
            )
        if selection.subdataset is not None and selection.subdataset not in container.subdatasets:
            raise RasterDatasetError("Selected subdataset does not belong to the inspected container")
        descriptor = self.inspect(selection.uri, subdataset=selection.subdataset)
        if len(descriptor.bands) != 1 and selection.band_index is None:
            raise RasterSelectionRequired(
                f"Dataset exposes {len(descriptor.bands)} bands; select one explicitly"
            )
        band_index = selection.band_index or 1
        if band_index < 1 or band_index > len(descriptor.bands):
            raise RasterDatasetError(f"Raster band {band_index} is outside the available range")
        return _apply_descriptor_overrides(descriptor, selection.overrides)

    def read_window(self, request: RasterWindowRequest) -> RasterWindow:
        descriptor = self.validate_selection(request.selection)
        band_index = request.selection.band_index or 1
        dataset = self._dataset(request.selection.selected_uri)
        if (
            request.column_offset + request.width > dataset.width
            or request.row_offset + request.height > dataset.height
        ):
            raise RasterDatasetError("Raster window exceeds dataset dimensions")
        window = Window(
            request.column_offset,
            request.row_offset,
            request.width,
            request.height,
        )
        output_shape = (
            request.output_height or request.height,
            request.output_width or request.width,
        )
        values = dataset.read(
            band_index,
            window=window,
            out_shape=output_shape,
            masked=False,
            resampling=Resampling.nearest,
        )
        overrides = request.selection.overrides
        mask_is_only_source_nodata = {
            flag.name for flag in dataset.mask_flag_enums[band_index - 1]
        } == {"nodata"}
        if overrides is not None and overrides.nodata_is_set and mask_is_only_source_nodata:
            valid = np.ones(output_shape, dtype=np.bool_)
        else:
            mask = dataset.read_masks(
                band_index,
                window=window,
                out_shape=output_shape,
                resampling=Resampling.nearest,
            )
            valid = mask != 0
        band = descriptor.bands[band_index - 1]
        if band.nodata is not None:
            if isinstance(band.nodata, float) and np.isnan(band.nodata):
                valid &= ~np.isnan(values)
            else:
                valid &= values != band.nodata
        base_transform = Affine(*descriptor.transform)
        selected_transform = window_transform(window, base_transform)
        if output_shape != (request.height, request.width):
            selected_transform *= Affine.scale(
                request.width / output_shape[1],
                request.height / output_shape[0],
            )
        return RasterWindow(
            values=values,
            valid_mask=valid,
            source_dtype=band.dtype,
            transform=_transform_tuple(selected_transform),
        )

    def close(self) -> None:
        with self._lock:
            for dataset in self._datasets.values():
                dataset.close()
            self._datasets.clear()
            self._closed = True

    def release(self, selection: RasterDatasetSelection) -> None:
        """Release one cached GDAL handle without closing the reusable reader."""
        with self._lock:
            dataset = self._datasets.pop(selection.selected_uri, None)
            if dataset is not None:
                dataset.close()

    def _dataset(self, uri: str) -> Any:
        with self._lock:
            if self._closed:
                raise RasterDatasetError("Raster reader is closed")
            existing = self._datasets.pop(uri, None)
            if existing is not None:
                self._datasets[uri] = existing
                return existing
            try:
                dataset = rasterio.open(uri)
            except (OSError, rasterio.errors.RasterioError) as exc:
                raise RasterDatasetError(f"Unable to open selected raster dataset {uri!r}") from exc
            self._datasets[uri] = dataset
            while len(self._datasets) > self._max_open_datasets:
                _, evicted = self._datasets.popitem(last=False)
                evicted.close()
            return dataset

    @staticmethod
    def _descriptor(uri: str, dataset: Any, *, selected_uri: str) -> RasterDatasetDescriptor:
        bands_list: list[RasterBandDescriptor] = []
        for index in range(1, int(dataset.count) + 1):
            try:
                raw_colormap = dataset.colormap(index)
            except (ValueError, rasterio.errors.RasterioError):
                raw_colormap = {}
            bands_list.append(RasterBandDescriptor(
                index=index,
                dtype=str(dataset.dtypes[index - 1]),
                description=dataset.descriptions[index - 1],
                nodata=dataset.nodatavals[index - 1],
                scale=float(dataset.scales[index - 1]),
                offset=float(dataset.offsets[index - 1]),
                unit=dataset.units[index - 1] or None,
                mask_flags=tuple(flag.name for flag in dataset.mask_flag_enums[index - 1]),
                overviews=tuple(int(value) for value in dataset.overviews(index)),
                block_shape=tuple(int(value) for value in dataset.block_shapes[index - 1]),
                metadata=dict(dataset.tags(index)),
                color_interpretation=dataset.colorinterp[index - 1].name,
                color_map={
                    int(code): tuple(int(channel) for channel in color[:4])
                    for code, color in raw_colormap.items()
                },
            ))
        bands = tuple(bands_list)
        transform = dataset.transform
        bounds = dataset.bounds
        return RasterDatasetDescriptor(
            uri=uri,
            driver=str(dataset.driver),
            width=int(dataset.width),
            height=int(dataset.height),
            crs=str(dataset.crs) if dataset.crs is not None else None,
            transform=_transform_tuple(transform),
            bounds=(float(bounds.left), float(bounds.bottom), float(bounds.right), float(bounds.top)),
            resolution=(abs(float(transform.a)), abs(float(transform.e))),
            bands=bands,
            subdatasets=tuple(str(value) for value in dataset.subdatasets),
            metadata=dict(dataset.tags()),
            original_metadata={"selected_uri": selected_uri},
        )


def _apply_descriptor_overrides(
    descriptor: RasterDatasetDescriptor,
    overrides: RasterMetadataOverride | None,
) -> RasterDatasetDescriptor:
    if overrides is None:
        return descriptor
    transform_tuple = overrides.transform
    if transform_tuple is None and overrides.bounds is not None:
        transform_tuple = _transform_tuple(rasterio.transform.from_bounds(
            *overrides.bounds,
            descriptor.width,
            descriptor.height,
        ))
    transform_tuple = transform_tuple or descriptor.transform
    transform = Affine(*transform_tuple)
    bounds = rasterio.transform.array_bounds(descriptor.height, descriptor.width, transform)
    bands = descriptor.bands
    if overrides.nodata_is_set:
        bands = tuple(
            RasterBandDescriptor(
                index=band.index,
                dtype=band.dtype,
                description=band.description,
                nodata=overrides.nodata,
                scale=band.scale,
                offset=band.offset,
                unit=band.unit,
                mask_flags=band.mask_flags,
                overviews=band.overviews,
                block_shape=band.block_shape,
                metadata=band.metadata,
                color_interpretation=band.color_interpretation,
                color_map=band.color_map,
            )
            for band in bands
        )
    return RasterDatasetDescriptor(
        uri=descriptor.uri,
        driver=descriptor.driver,
        width=descriptor.width,
        height=descriptor.height,
        crs=overrides.crs or descriptor.crs,
        transform=transform_tuple,
        bounds=tuple(float(value) for value in bounds),
        resolution=(abs(float(transform.a)), abs(float(transform.e))),
        bands=bands,
        subdatasets=descriptor.subdatasets,
        metadata=descriptor.metadata,
        original_metadata={
            **descriptor.original_metadata,
            "overrides": {
                "crs": overrides.crs,
                "transform": overrides.transform,
                "bounds": overrides.bounds,
                "nodata": overrides.nodata if overrides.nodata_is_set else None,
                "nodata_is_set": overrides.nodata_is_set,
                "provenance": overrides.provenance,
            },
        },
    )


def _transform_tuple(transform: Affine) -> TransformTuple:
    return (
        float(transform.a),
        float(transform.b),
        float(transform.c),
        float(transform.d),
        float(transform.e),
        float(transform.f),
    )
