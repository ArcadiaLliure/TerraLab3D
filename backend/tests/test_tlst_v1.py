from __future__ import annotations

import json
from decimal import Decimal

import numpy as np
import pytest

from terralab3d.domain.surface.tlst import (
    ClassificationStatus,
    ComponentWeight,
    CompositeSurface,
    ObservationState,
    QualifierAssignment,
    SampleValidity,
    SingleSurface,
    SourceClassification,
    SurfaceComponent,
    SurfaceObservation,
    TlstValidationError,
    pack_sample_validity,
    unpack_sample_validity,
)
from terralab3d.domain.surface.land_cover import LandCoverProvenance, LandCoverTile
from terralab3d.application.land_cover_publication import (
    build_land_cover_legend_message,
    build_land_cover_tile_publication,
)
from terralab3d.infrastructure.adapters.surface.adapter import ConfiguredSurfaceSampler
from terralab3d.infrastructure.adapters.surface.land_cover_port import RasterioLandCoverPort
from terralab3d.infrastructure.adapters.surface.tlst_catalog import (
    load_builtin_land_cover_registry,
)


def test_tlst_catalog_is_frozen_and_uses_canonical_public_keys() -> None:
    registry = load_builtin_land_cover_registry()
    catalog = registry.taxonomy

    assert catalog.taxonomy_key == "TLST"
    assert catalog.taxonomy_version == "1.0"
    assert "agriculture.cropland.unspecified" in catalog.category_keys
    assert "agriculture.cropland.permanent_crop.vineyard" in catalog.category_keys
    assert "agriculture.cropland_unspecified" not in catalog.category_keys
    assert "low_vegetation.shrub.unspecified" in catalog.category_keys
    assert "snow_ice.permanent.unspecified" in catalog.category_keys
    assert "snow_ice.unspecified" in catalog.category_keys
    assert "artificial.built.residential" not in catalog.category_keys
    assert "wetland.coastal.salt_pan" in catalog.category_keys
    assert set(registry.category_presentations_ca) == catalog.category_keys
    presentation = registry.category_presentation("artificial.unspecified")
    assert presentation.label_key == "tlst.category.artificial.unspecified"
    assert presentation.label == "Superfície artificial sense especificar"


def test_derived_qualifier_is_not_stored_twice_or_contradicted() -> None:
    catalog = load_builtin_land_cover_registry().taxonomy

    assert catalog.derived_qualifiers("tree_cover.broadleaf") == {
        "leaf_type": "broadleaf"
    }
    with pytest.raises(TlstValidationError, match="redundant"):
        catalog.validate_single_surface(
            SingleSurface(
                "tree_cover.broadleaf",
                (QualifierAssignment("leaf_type", "broadleaf"),),
            )
        )
    with pytest.raises(TlstValidationError, match="contradictory"):
        catalog.validate_single_surface(
            SingleSurface(
                "tree_cover.broadleaf",
                (QualifierAssignment("leaf_type", "needleleaf"),),
            )
        )


def test_absent_qualifier_differs_from_explicit_unknown() -> None:
    catalog = load_builtin_land_cover_registry().taxonomy
    absent = SingleSurface("tree_cover.unspecified")
    explicit_unknown = SingleSurface(
        "tree_cover.unspecified",
        (QualifierAssignment("phenology", "unknown"),),
    )

    catalog.validate_single_surface(absent)
    catalog.validate_single_surface(explicit_unknown)
    assert absent != explicit_unknown


def test_composite_intervals_require_a_possible_sum_of_one_without_normalizing() -> None:
    composite = CompositeSurface(
        (
            SurfaceComponent(
                SingleSurface("agriculture.cropland.unspecified"),
                ComponentWeight(Decimal("0.50"), Decimal("0.70")),
            ),
            SurfaceComponent(
                SingleSurface("low_vegetation.unspecified"),
                ComponentWeight(Decimal("0.30"), Decimal("0.50")),
            ),
        )
    )

    assert composite.components[0].weight.minimum == Decimal("0.50")
    assert composite.components[0].weight.maximum == Decimal("0.70")
    with pytest.raises(TlstValidationError, match="summing to one"):
        CompositeSurface(
            (
                SurfaceComponent(
                    SingleSurface("agriculture.cropland.unspecified"),
                    ComponentWeight.exact("0.2"),
                ),
                SurfaceComponent(
                    SingleSurface("low_vegetation.unspecified"),
                    ComponentWeight.exact("0.3"),
                ),
            )
        )


def test_invalid_sample_cannot_have_translation_and_valid_sample_requires_one() -> None:
    source = SourceClassification("s2glc_europe", "2017-v1.2", 75, "Vineyards")

    with pytest.raises(TlstValidationError, match="cannot carry"):
        SurfaceObservation(
            source,
            SampleValidity.MASKED,
            SingleSurface("agriculture.cropland.permanent_crop.vineyard"),
        )
    with pytest.raises(TlstValidationError, match="requires"):
        SurfaceObservation(source, SampleValidity.VALID, None)

    unknown = SurfaceObservation(
        source,
        SampleValidity.VALID,
        ObservationState(ClassificationStatus.UNKNOWN),
    )
    assert unknown.classification_status is ClassificationStatus.UNKNOWN


def test_source_code_zero_depends_on_scheme_and_never_reaches_semantic_mapper() -> None:
    registry = load_builtin_land_cover_registry()
    s2glc = registry.get("s2glc_europe", "2017-v1.2")
    worldcover = registry.get("esa_worldcover", "2021-v200")

    s2glc_zero = s2glc.resolve_observation(0)
    worldcover_zero = worldcover.resolve_observation(0)

    assert s2glc_zero.validity is SampleValidity.MASKED
    assert s2glc_zero.translation is None
    assert worldcover_zero.validity is SampleValidity.NODATA
    assert worldcover_zero.translation is None


@pytest.mark.parametrize(
    ("code", "expected_category"),
    [
        (73, "agriculture.cropland.unspecified"),
        (75, "agriculture.cropland.permanent_crop.vineyard"),
        (103, "low_vegetation.shrub.unspecified"),
        (123, "snow_ice.permanent.unspecified"),
    ],
)
def test_s2glc_precision_is_never_invented(code: int, expected_category: str) -> None:
    scheme = load_builtin_land_cover_registry().get("s2glc_europe", "2017-v1.2")

    observation = scheme.resolve_observation(code)

    assert observation.validity is SampleValidity.VALID
    assert isinstance(observation.translation, SingleSurface)
    assert observation.translation.category_key == expected_category


def test_s2glc_mapping_is_exhaustive() -> None:
    scheme = load_builtin_land_cover_registry().get("s2glc_europe", "2017-v1.2")
    expected = {
        0: SampleValidity.MASKED,
        62: "artificial.unspecified",
        73: "agriculture.cropland.unspecified",
        75: "agriculture.cropland.permanent_crop.vineyard",
        82: "tree_cover.broadleaf",
        83: "tree_cover.needleleaf",
        102: "low_vegetation.herbaceous.unspecified",
        103: "low_vegetation.shrub.unspecified",
        104: "low_vegetation.shrub.sclerophyllous",
        105: "wetland.marsh",
        106: "wetland.inland.peat_bog",
        121: "bare_sparse.unspecified",
        123: "snow_ice.permanent.unspecified",
        162: "water.unspecified",
    }

    assert {definition.source_code for definition in scheme.classes} == set(expected)
    for source_code, target in expected.items():
        observation = scheme.resolve_observation(source_code)
        if isinstance(target, SampleValidity):
            assert observation.validity is target
            assert observation.translation is None
        else:
            assert isinstance(observation.translation, SingleSurface)
            assert observation.translation.category_key == target


@pytest.mark.parametrize("version", ["2020-v100", "2021-v200"])
def test_worldcover_versions_are_registered_independently(version: str) -> None:
    scheme = load_builtin_land_cover_registry().get("esa_worldcover", version)

    crops = scheme.resolve_observation(40)
    snow_ice = scheme.resolve_observation(70)
    water = scheme.resolve_observation(80)

    assert isinstance(crops.translation, SingleSurface)
    assert crops.translation.category_key == "agriculture.cropland.unspecified"
    assert isinstance(snow_ice.translation, SingleSurface)
    assert snow_ice.translation.category_key == "snow_ice.unspecified"
    assert isinstance(water.translation, SingleSurface)
    assert water.translation.qualifiers == (
        QualifierAssignment("water_regime", "permanent"),
    )


@pytest.mark.parametrize("version", ["2020-v100", "2021-v200"])
def test_worldcover_mapping_is_exhaustive(version: str) -> None:
    scheme = load_builtin_land_cover_registry().get("esa_worldcover", version)
    expected = {
        0: SampleValidity.NODATA,
        10: "tree_cover.unspecified",
        20: "low_vegetation.shrub.shrubland",
        30: "low_vegetation.herbaceous.unspecified",
        40: "agriculture.cropland.unspecified",
        50: "artificial.unspecified",
        60: "bare_sparse.unspecified",
        70: "snow_ice.unspecified",
        80: "water.unspecified",
        90: "wetland.herbaceous_wetland",
        95: "wetland.coastal.mangrove",
        100: "low_vegetation.moss_lichen",
    }

    assert {definition.source_code for definition in scheme.classes} == set(expected)
    for source_code, target in expected.items():
        observation = scheme.resolve_observation(source_code)
        if isinstance(target, SampleValidity):
            assert observation.validity is target
            assert observation.translation is None
        else:
            assert isinstance(observation.translation, SingleSurface)
            assert observation.translation.category_key == target


def test_two_bit_validity_round_trip_is_row_aligned() -> None:
    raw = bytes(
        [
            SampleValidity.OUTSIDE_COVERAGE,
            SampleValidity.VALID,
            SampleValidity.NODATA,
            SampleValidity.MASKED,
            SampleValidity.VALID,
            SampleValidity.MASKED,
            SampleValidity.NODATA,
            SampleValidity.VALID,
            SampleValidity.OUTSIDE_COVERAGE,
            SampleValidity.VALID,
        ]
    )

    packed = pack_sample_validity(raw, width=5, height=2)

    assert len(packed) == 4
    assert unpack_sample_validity(packed, width=5, height=2) == raw


def test_mosaic_priority_is_semantic_not_numeric() -> None:
    destination_codes = np.asarray([[0, 0, 40, 50]], dtype=np.uint16)
    destination_validity = np.asarray(
        [[
            SampleValidity.OUTSIDE_COVERAGE,
            SampleValidity.NODATA,
            SampleValidity.VALID,
            SampleValidity.MASKED,
        ]],
        dtype=np.uint8,
    )
    fragment_codes = np.asarray([[20, 30, 99, 60]], dtype=np.uint16)
    fragment_validity = np.asarray(
        [[
            SampleValidity.NODATA,
            SampleValidity.MASKED,
            SampleValidity.MASKED,
            SampleValidity.VALID,
        ]],
        dtype=np.uint8,
    )

    RasterioLandCoverPort._merge_fragment(
        destination_codes,
        destination_validity,
        fragment_codes,
        fragment_validity,
        raster_path="fixture.tif",
    )

    assert destination_validity.tolist() == [[2, 3, 1, 1]]
    assert destination_codes.tolist() == [[20, 30, 40, 60]]


def test_only_exact_legacy_alias_is_accepted(tmp_path) -> None:
    config = tmp_path / "data_sources.json"
    config.write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "id": "my-s2glc-looking-name",
                        "layer_type": "land_cover_categorical",
                        "enabled": True,
                        "path": str(tmp_path / "missing.tif"),
                    }
                ],
                "selections": {
                    "land_cover": {
                        "mode": "manual",
                        "source_id": "my-s2glc-looking-name",
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    assert ConfiguredSurfaceSampler((config,)).resolve_land_cover_source() is None


def test_bridge_publication_keeps_source_buffers_and_tlst_lookup_separate() -> None:
    tile = LandCoverTile(
        resource_id="landcover.fixture.g7",
        provenance=LandCoverProvenance(
            source_id="fixture",
            source_name="Fixture layer",
            generation=7,
            scheme_key="s2glc_europe",
            scheme_version="2017-v1.2",
            taxonomy_key="TLST",
            taxonomy_version="1.0",
            source_dtype="uint8",
        ),
        min_x=0,
        min_y=0,
        max_x=20,
        max_y=20,
        width=2,
        height=2,
        resolution=10,
        crs="EPSG:3035",
        valid_pixels=2,
        source_code_buffer=np.asarray([75, 0, 75, 0], dtype="<u2").tobytes(),
        sample_validity_buffer=pack_sample_validity(
            bytes([1, 3, 1, 0]),
            width=2,
            height=2,
        ),
    )

    metadata, payload = build_land_cover_tile_publication(tile)

    assert metadata["sourceDtype"] == "uint8"
    assert metadata["dtype"] == "uint16"
    assert metadata["sourceCodeOffset"] == 0
    assert metadata["sampleValidityOffset"] == len(tile.source_code_buffer)
    assert metadata["taxonomyKey"] == "TLST"
    assert "nodataValue" not in metadata
    assert payload == tile.source_code_buffer + tile.sample_validity_buffer

    port = RasterioLandCoverPort(ConfiguredSurfaceSampler())
    legend = port.legend("s2glc_europe", "2017-v1.2")
    assert legend is not None
    message = build_land_cover_legend_message(legend)
    vineyard = next(entry for entry in message["entries"] if entry["sourceCode"] == 75)
    assert vineyard["sourceLabel"] == "Vineyards"
    assert vineyard["categoryKey"] == "agriculture.cropland.permanent_crop.vineyard"
    assert vineyard["categoryLabelKey"] == (
        "tlst.category.agriculture.cropland.permanent_crop.vineyard"
    )
    assert vineyard["categoryLabel"] == "Vinya"
    assert message["taxonomyVersion"] == "1.0"
