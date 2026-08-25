"""Build the versioned bridge DTOs for categorical surface resources."""

from __future__ import annotations

from typing import Any

from terralab3d.domain.surface.land_cover import LandCoverLegend, LandCoverTile


def build_land_cover_tile_publication(tile: LandCoverTile) -> tuple[dict[str, Any], bytes]:
    code_length = len(tile.source_code_buffer)
    validity_length = len(tile.sample_validity_buffer)
    metadata: dict[str, Any] = {
        "role": "land_cover_tile",
        "resourceId": tile.resource_id,
        "version": tile.provenance.generation,
        "bounds": [tile.min_x, tile.min_y, tile.max_x, tile.max_y],
        "width": tile.width,
        "height": tile.height,
        "resolution": tile.resolution,
        "sourceId": tile.provenance.source_id,
        "sourceName": tile.provenance.source_name,
        "schemeKey": tile.provenance.scheme_key,
        "schemeVersion": tile.provenance.scheme_version,
        "mappingRevision": tile.provenance.mapping_revision,
        "taxonomyKey": tile.provenance.taxonomy_key,
        "taxonomyVersion": tile.provenance.taxonomy_version,
        "sourceDtype": tile.provenance.source_dtype,
        "dtype": tile.buffer_dtype,
        "sourceCodeOffset": 0,
        "sourceCodeByteLength": code_length,
        "sampleValidityOffset": code_length,
        "sampleValidityByteLength": validity_length,
        "validityEncoding": tile.validity_encoding,
        "validityRowBytes": (tile.width + 3) // 4,
        "validPixels": tile.valid_pixels,
    }
    return metadata, tile.binary_payload


def build_land_cover_legend_message(legend: LandCoverLegend) -> dict[str, Any]:
    return {
        "type": "land_cover_legend",
        "schemeKey": legend.scheme_key,
        "schemeVersion": legend.scheme_version,
        "mappingRevision": legend.mapping_revision,
        "sourceName": legend.source_name,
        "taxonomyKey": legend.taxonomy_key,
        "taxonomyVersion": legend.taxonomy_version,
        "entries": [
            {
                "sourceCode": entry.source_code,
                "sourceValue": entry.source_value,
                "sourceLabel": entry.source_label,
                "sourceLabelKey": entry.source_label_key,
                "colorRgba": entry.color_rgba,
                "sampleValidity": (
                    entry.sample_validity.name.lower()
                    if entry.sample_validity is not None
                    else None
                ),
                "classificationStatus": (
                    entry.classification_status.value
                    if entry.classification_status is not None
                    else None
                ),
                "categoryKey": entry.category_key,
                "categoryLabelKey": entry.category_label_key,
                "categoryLabel": entry.category_label,
                "qualifiers": {
                    qualifier.key: str(qualifier.value)
                    for qualifier in entry.qualifiers
                },
                "mappingKind": entry.mapping_kind,
                "resolvedPath": list(entry.resolved_path),
                "semanticDepth": entry.semantic_depth,
                "unresolvedChildren": list(entry.unresolved_children),
            }
            for entry in legend.entries
        ],
    }
