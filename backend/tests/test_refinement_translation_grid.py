from __future__ import annotations

from decimal import Decimal

import pytest

from terralab3d.domain.refinement import (
    GridAlignmentError,
    ObservationStatus,
    RefinementValidationError,
    ResamplingPolicy,
    TargetGridSpec,
    TemporalPolicy,
    TlstTranslation,
    TranslationKind,
)
from terralab3d.domain.surface.tlst import (
    ComponentWeight,
    CompositeSurface,
    QualifierAssignment,
    SingleSurface,
    SurfaceComponent,
)
from terralab3d.infrastructure.adapters.surface.tlst_catalog import (
    load_builtin_land_cover_registry,
)


def _grid(*, origin_x: float = 0.0, min_x: float = 0.0) -> TargetGridSpec:
    return TargetGridSpec(
        crs="EPSG:3035",
        resolution_x=10.0,
        resolution_y=10.0,
        origin_x=origin_x,
        origin_y=0.0,
        min_x=min_x,
        min_y=0.0,
        max_x=min_x + 100.0,
        max_y=100.0,
        width=10,
        height=10,
        dtype="uint16",
        nodata=0,
        resampling=ResamplingPolicy.NEAREST,
        tlst_version="1.0",
        temporal_policy=TemporalPolicy("latest_in_window", 365),
    )


@pytest.mark.parametrize(
    "category_key",
    [
        "agriculture",
        "agriculture.cropland",
        "agriculture.cropland.permanent_crop",
        "agriculture.cropland.permanent_crop.vineyard",
    ],
)
def test_single_translation_preserves_deepest_justified_tlst_node(category_key: str) -> None:
    taxonomy = load_builtin_land_cover_registry().taxonomy
    translation = TlstTranslation.from_single(SingleSurface(category_key))

    translation.validate_against(taxonomy)

    assert translation.kind is TranslationKind.SINGLE
    assert translation.category_keys == (category_key,)


def test_continuous_qualifier_remains_separate_from_tlst_category() -> None:
    taxonomy = load_builtin_land_cover_registry().taxonomy
    surface = SingleSurface(
        "artificial.unspecified",
        (QualifierAssignment("imperviousness", Decimal("0.72")),),
    )
    translation = TlstTranslation.from_single(surface)

    translation.validate_against(taxonomy)

    assert translation.category_keys == ("artificial.unspecified",)
    assert surface.qualifiers[0].value == Decimal("0.72")


def test_composite_translation_is_explicit_and_validated() -> None:
    taxonomy = load_builtin_land_cover_registry().taxonomy
    composite = CompositeSurface(
        (
            SurfaceComponent(
                SingleSurface("agriculture.cropland.unspecified"),
                ComponentWeight.exact("0.6"),
            ),
            SurfaceComponent(
                SingleSurface("tree_cover.unspecified"),
                ComponentWeight.exact("0.4"),
            ),
        )
    )
    translation = TlstTranslation.from_composite(composite)

    translation.validate_against(taxonomy)

    assert translation.kind is TranslationKind.COMPOSITE
    assert translation.category_keys == (
        "agriculture.cropland.unspecified",
        "tree_cover.unspecified",
    )


def test_translation_rejects_single_and_composite_at_the_same_time() -> None:
    composite = CompositeSurface(
        (
            SurfaceComponent(SingleSurface("agriculture"), ComponentWeight.exact("0.5")),
            SurfaceComponent(SingleSurface("tree_cover"), ComponentWeight.exact("0.5")),
        )
    )

    with pytest.raises(RefinementValidationError, match="exactly one"):
        TlstTranslation(single=SingleSurface("agriculture"), composite=composite)


def test_observation_states_are_not_tlst_categories() -> None:
    taxonomy = load_builtin_land_cover_registry().taxonomy

    assert {value.value for value in ObservationStatus} >= {
        "nodata",
        "unknown",
        "unclassified",
        "read_error",
        "outside_coverage",
    }
    assert not ({value.value for value in ObservationStatus} & taxonomy.category_keys)


def test_equal_grid_specs_are_aligned() -> None:
    assert _grid().is_aligned_with(_grid())


def test_same_crs_and_resolution_with_half_pixel_offset_is_rejected() -> None:
    canonical = _grid()
    displaced = _grid(origin_x=5.0, min_x=5.0)

    assert not canonical.is_aligned_with(displaced)
    with pytest.raises(GridAlignmentError, match="not aligned"):
        canonical.require_aligned_with(displaced)
