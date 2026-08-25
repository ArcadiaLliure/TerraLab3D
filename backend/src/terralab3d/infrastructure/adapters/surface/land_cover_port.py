"""Rasterio adapter for versioned categorical surface schemes."""

from __future__ import annotations

import logging
import math

import numpy as np
import rasterio
from rasterio.transform import from_bounds
from rasterio.warp import Resampling, reproject, transform_bounds
from rasterio.windows import Window, from_bounds as window_from_bounds

from terralab3d.application.ports.land_cover import LandCoverPort
from terralab3d.domain.surface.land_cover import (
    LandCoverLegend,
    LandCoverLegendEntry,
    LandCoverProvenance,
    LandCoverTile,
    LandCoverTileRequest,
)
from terralab3d.domain.surface.tlst import (
    ClassificationStatus,
    ObservationState,
    SAMPLE_VALIDITY_MOSAIC_PRIORITY,
    SampleValidity,
    SingleSurface,
    SourceScheme,
    TlstValidationError,
    pack_sample_validity,
)
from terralab3d.infrastructure.adapters.surface.adapter import ConfiguredSurfaceSampler
from terralab3d.infrastructure.adapters.surface.tlst_catalog import LandCoverSchemeRegistry


log = logging.getLogger("terralab3d.land_cover_port")

_UINT16_MAX = int(np.iinfo(np.uint16).max)
_MOSAIC_PRIORITY_BY_ENCODING = np.asarray(
    [
        SAMPLE_VALIDITY_MOSAIC_PRIORITY[SampleValidity.OUTSIDE_COVERAGE],
        SAMPLE_VALIDITY_MOSAIC_PRIORITY[SampleValidity.VALID],
        SAMPLE_VALIDITY_MOSAIC_PRIORITY[SampleValidity.NODATA],
        SAMPLE_VALIDITY_MOSAIC_PRIORITY[SampleValidity.MASKED],
    ],
    dtype=np.uint8,
)


class RasterioLandCoverPort(LandCoverPort):
    """Read source codes and physical validity without embedding TLST IDs."""

    def __init__(
        self,
        sampler: ConfiguredSurfaceSampler,
        scheme_registry: LandCoverSchemeRegistry | None = None,
    ) -> None:
        self._sampler = sampler
        self._scheme_registry = scheme_registry or sampler.scheme_registry

    def read_tile(self, request: LandCoverTileRequest) -> LandCoverTile | None:
        log.info("MGP: RasterioLandCoverPort.read_tile [INICI]")
        resolved = self._sampler.resolve_land_cover_source(
            override_mode=request.source_mode,
            override_source_id=request.source_id,
        )
        if not resolved or not resolved.raster_paths:
            log.info("MGP: RasterioLandCoverPort.read_tile [FI]")
            return None

        scheme = self._scheme_registry.get(
            resolved.scheme_key,
            resolved.scheme_version,
            resolved.mapping_revision,
        )
        width = max(1, int(round((request.max_x - request.min_x) / request.resolution)))
        height = max(1, int(round((request.max_y - request.min_y) / request.resolution)))
        destination_transform = from_bounds(
            request.min_x,
            request.min_y,
            request.max_x,
            request.max_y,
            width,
            height,
        )

        destination_codes = np.zeros((height, width), dtype=np.uint16)
        destination_validity = np.full(
            (height, width),
            int(SampleValidity.OUTSIDE_COVERAGE),
            dtype=np.uint8,
        )

        readable_fragments = 0
        for raster_path in resolved.raster_paths:
            try:
                with rasterio.open(raster_path) as source:
                    if source.dtypes[0] != resolved.payload_dtype:
                        raise TlstValidationError(
                            "All fragments in one categorical source must share source_dtype"
                        )
                    self._validate_source_dtype(source.dtypes[0])
                    fragment_codes, fragment_validity = self._read_fragment(
                        source,
                        request,
                        destination_transform,
                        width,
                        height,
                    )
                    self._apply_scheme_validity(fragment_codes, fragment_validity, scheme)
                    self._merge_fragment(
                        destination_codes,
                        destination_validity,
                        fragment_codes,
                        fragment_validity,
                        raster_path=str(raster_path),
                    )
                    readable_fragments += 1
            except (OSError, rasterio.errors.RasterioError) as exc:
                log.warning("Error reprojectant %s: %s", raster_path, exc)

        if readable_fragments == 0:
            log.info("MGP: RasterioLandCoverPort.read_tile [FI]")
            return None

        valid_pixels = int(np.count_nonzero(destination_validity == SampleValidity.VALID))
        tile = LandCoverTile(
            resource_id=f"landcover_{resolved.source_id}",
            provenance=LandCoverProvenance(
                source_id=resolved.source_id,
                source_name=resolved.display_name,
                generation=0,
                scheme_key=scheme.scheme_key,
                scheme_version=scheme.scheme_version,
                taxonomy_key=scheme.taxonomy_key,
                taxonomy_version=scheme.taxonomy_version,
                source_dtype=resolved.source_dtype,
                mapping_revision=scheme.mapping_revision,
            ),
            min_x=request.min_x,
            min_y=request.min_y,
            max_x=request.max_x,
            max_y=request.max_y,
            width=width,
            height=height,
            resolution=request.resolution,
            crs=request.crs,
            valid_pixels=valid_pixels,
            source_code_buffer=destination_codes.astype("<u2", copy=False).tobytes(),
            sample_validity_buffer=pack_sample_validity(
                destination_validity.reshape(-1).tobytes(),
                width,
                height,
            ),
        )
        log.info("MGP: RasterioLandCoverPort.read_tile [FI]")
        return tile

    def legend(
        self,
        scheme_key: str,
        scheme_version: str,
        mapping_revision: str | None = None,
    ) -> LandCoverLegend | None:
        scheme = self._scheme_registry.get(
            scheme_key,
            scheme_version,
            mapping_revision,
        )
        entries = []
        for definition in scheme.classes:
            category_key = None
            category_label_key = None
            category_label = None
            qualifiers = ()
            classification_status = None
            mapping_kind = "observation_state"
            resolved_path = ()
            semantic_depth = None
            unresolved_children = ()
            if definition.translation is not None:
                if isinstance(definition.translation, SingleSurface):
                    category_key = definition.translation.category_key
                    presentation = self._scheme_registry.category_presentation(category_key)
                    category_label_key = presentation.label_key
                    category_label = presentation.label
                    qualifiers = definition.translation.qualifiers
                    classification_status = ClassificationStatus.CLASSIFIED
                    mapping_kind = "single"
                    coverage = self._scheme_registry.taxonomy.hierarchy_coverage(
                        category_key,
                    )
                    resolved_path = coverage.resolved_path
                    semantic_depth = coverage.semantic_depth
                    unresolved_children = coverage.unresolved_children
                elif isinstance(definition.translation, ObservationState):
                    classification_status = definition.translation.status
                else:
                    classification_status = ClassificationStatus.CLASSIFIED
                    mapping_kind = "composite"
                    category_label_key = "tlst.state.composite"
                    category_label = "Superfície composta"
            entries.append(
                LandCoverLegendEntry(
                    source_code=definition.source_code,
                    source_label=definition.source_label,
                    source_label_key=definition.source_label_key,
                    color_rgba=definition.color_rgba,
                    sample_validity=definition.sample_validity,
                    classification_status=classification_status,
                    category_key=category_key,
                    category_label_key=category_label_key,
                    category_label=category_label,
                    qualifiers=qualifiers,
                    source_value=definition.source_value,
                    mapping_kind=mapping_kind,
                    resolved_path=resolved_path,
                    semantic_depth=semantic_depth,
                    unresolved_children=unresolved_children,
                )
            )
        return LandCoverLegend(
            scheme_key=scheme.scheme_key,
            scheme_version=scheme.scheme_version,
            source_name=scheme.display_name,
            taxonomy_key=scheme.taxonomy_key,
            taxonomy_version=scheme.taxonomy_version,
            entries=tuple(entries),
            mapping_revision=scheme.mapping_revision,
        )

    def close(self) -> None:
        pass

    @staticmethod
    def _validate_source_dtype(dtype_name: str) -> None:
        dtype = np.dtype(dtype_name)
        if dtype.kind not in {"u", "i"}:
            raise TlstValidationError(
                f"Categorical source_dtype must be integral, received {dtype_name!r}"
            )

    @staticmethod
    def _read_fragment(
        source: rasterio.io.DatasetReader,
        request: LandCoverTileRequest,
        destination_transform,
        width: int,
        height: int,
    ) -> tuple[np.ndarray, np.ndarray]:
        if source.crs is None:
            raise TlstValidationError(f"Categorical raster {source.name!r} has no CRS")

        source_bounds = transform_bounds(
            request.crs,
            source.crs,
            request.min_x,
            request.min_y,
            request.max_x,
            request.max_y,
            densify_pts=21,
        )
        raw_window = window_from_bounds(*source_bounds, transform=source.transform)
        expanded = Window(
            math.floor(raw_window.col_off) - 1,
            math.floor(raw_window.row_off) - 1,
            math.ceil(raw_window.width) + 2,
            math.ceil(raw_window.height) + 2,
        )
        try:
            window = expanded.intersection(Window(0, 0, source.width, source.height))
        except rasterio.errors.WindowError:
            return (
                np.zeros((height, width), dtype=np.uint16),
                np.full(
                    (height, width),
                    int(SampleValidity.OUTSIDE_COVERAGE),
                    dtype=np.uint8,
                ),
            )
        if window.width <= 0 or window.height <= 0:
            return (
                np.zeros((height, width), dtype=np.uint16),
                np.full(
                    (height, width),
                    int(SampleValidity.OUTSIDE_COVERAGE),
                    dtype=np.uint8,
                ),
            )

        source_values = source.read(1, window=window, masked=False)
        source_mask = source.read_masks(1, window=window)
        source_validity = np.full(source_values.shape, int(SampleValidity.VALID), dtype=np.uint8)

        nodata_mask = np.zeros(source_values.shape, dtype=bool)
        if source.nodata is not None:
            if isinstance(source.nodata, float) and math.isnan(source.nodata):
                nodata_mask = np.isnan(source_values)
            else:
                nodata_mask = source_values == source.nodata
            source_validity[nodata_mask] = int(SampleValidity.NODATA)
        source_validity[(source_mask == 0) & ~nodata_mask] = int(SampleValidity.MASKED)

        destination_raw = np.zeros((height, width), dtype=np.float64)
        destination_validity = np.full(
            (height, width),
            int(SampleValidity.OUTSIDE_COVERAGE),
            dtype=np.uint8,
        )
        window_transform = source.window_transform(window)
        reproject(
            source=source_values,
            destination=destination_raw,
            src_transform=window_transform,
            src_crs=source.crs,
            dst_transform=destination_transform,
            dst_crs=request.crs,
            resampling=Resampling.nearest,
            src_nodata=None,
            dst_nodata=0,
            init_dest_nodata=True,
        )
        reproject(
            source=source_validity,
            destination=destination_validity,
            src_transform=window_transform,
            src_crs=source.crs,
            dst_transform=destination_transform,
            dst_crs=request.crs,
            resampling=Resampling.nearest,
            src_nodata=None,
            dst_nodata=int(SampleValidity.OUTSIDE_COVERAGE),
            init_dest_nodata=True,
        )

        semantically_eligible = destination_validity == SampleValidity.VALID
        eligible_values = destination_raw[semantically_eligible]
        if eligible_values.size > 0:
            if not np.all(np.isfinite(eligible_values)):
                raise TlstValidationError("Categorical source contains non-finite codes")
            if not np.all(eligible_values == np.floor(eligible_values)):
                raise TlstValidationError("Categorical source contains non-integral codes")
            if np.any(eligible_values < 0) or np.any(eligible_values > _UINT16_MAX):
                raise TlstValidationError(
                    "This categorical publisher only supports source codes representable as uint16"
                )

        destination_codes = np.zeros((height, width), dtype=np.uint16)
        representable = (
            np.isfinite(destination_raw)
            & (destination_raw == np.floor(destination_raw))
            & (destination_raw >= 0)
            & (destination_raw <= _UINT16_MAX)
        )
        destination_codes[representable] = destination_raw[representable].astype(
            np.uint16,
            copy=False,
        )
        return destination_codes, destination_validity

    @staticmethod
    def _apply_scheme_validity(
        codes: np.ndarray,
        validity: np.ndarray,
        scheme: SourceScheme,
    ) -> None:
        physically_valid = validity == SampleValidity.VALID
        for raw_code in np.unique(codes[physically_valid]):
            source_code = int(raw_code)
            definition = scheme.class_definition(source_code)
            if definition.sample_validity is not None:
                validity[physically_valid & (codes == source_code)] = int(
                    definition.sample_validity
                )

    @staticmethod
    def _merge_fragment(
        destination_codes: np.ndarray,
        destination_validity: np.ndarray,
        fragment_codes: np.ndarray,
        fragment_validity: np.ndarray,
        *,
        raster_path: str,
    ) -> None:
        destination_priority = _MOSAIC_PRIORITY_BY_ENCODING[destination_validity]
        fragment_priority = _MOSAIC_PRIORITY_BY_ENCODING[fragment_validity]
        replace_mask = fragment_priority > destination_priority

        conflicting_valid = (
            (fragment_validity == SampleValidity.VALID)
            & (destination_validity == SampleValidity.VALID)
            & (fragment_codes != destination_codes)
        )
        conflict_count = int(np.count_nonzero(conflicting_valid))
        if conflict_count:
            log.warning(
                "Mosaic fragment %s disagrees with the first valid fragment at %d pixels; "
                "the configured first fragment remains authoritative",
                raster_path,
                conflict_count,
            )

        destination_codes[replace_mask] = fragment_codes[replace_mask]
        destination_validity[replace_mask] = fragment_validity[replace_mask]
