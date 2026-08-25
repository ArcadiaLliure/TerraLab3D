from __future__ import annotations

from terralab3d.infrastructure.adapters.refinement.providers.rollout import (
    ProviderRolloutState,
    refinement_provider_rollout,
)
from terralab3d.infrastructure.adapters.refinement.providers.clms import (
    clms_refinement_products,
)
from terralab3d.infrastructure.adapters.refinement.providers.corine import (
    CORINE_2018_TRANSLATION,
)
from terralab3d.infrastructure.adapters.refinement.providers.icgc import (
    ICGC_MCSC_2024_TRANSLATION,
)
from terralab3d.infrastructure.adapters.refinement.providers.water_wetness import (
    WATER_WETNESS_2018_TRANSLATION,
)
from terralab3d.infrastructure.adapters.surface.tlst_catalog import (
    load_builtin_land_cover_registry,
)


def test_every_provider_family_has_an_explicit_unambiguous_rollout_state() -> None:
    records = refinement_provider_rollout()
    assert len(records) == 15
    assert len({record.provider_key for record in records}) == len(records)
    assert all(record.datasets and record.reason and record.license_status for record in records)
    assert all(record.state in ProviderRolloutState for record in records)


def test_only_verified_automatic_families_are_enabled() -> None:
    by_key = {record.provider_key: record for record in refinement_provider_rollout()}
    assert by_key["icgc-mcsc"].state is ProviderRolloutState.ENABLED
    assert by_key["copernicus-corine"].state is ProviderRolloutState.ENABLED
    assert by_key["copernicus-clms-grassland"].state is ProviderRolloutState.ENABLED
    assert by_key["copernicus-clms-snow"].state is ProviderRolloutState.ENABLED
    assert by_key["copernicus-global-dynamic"].state is ProviderRolloutState.ENABLED
    assert by_key["copernicus-water-wetness"].state is ProviderRolloutState.ENABLED
    assert by_key["inspire-hvd-buildings"].state is ProviderRolloutState.DISABLED


def test_enabled_datasets_publish_an_explicit_leaf_level_coverage_audit() -> None:
    taxonomy = load_builtin_land_cover_registry().taxonomy
    mapped = set(ICGC_MCSC_2024_TRANSLATION.values())
    mapped.update(CORINE_2018_TRANSLATION.values())
    mapped.update(WATER_WETNESS_2018_TRANSLATION.values())
    mapped.update(
        node
        for product in clms_refinement_products()
        for node in product.tlst_nodes
    )
    leaves = {
        key
        for key in taxonomy.category_keys
        if not any(other.startswith(f"{key}.") for other in taxonomy.category_keys)
    }
    semantically_covered = {
        leaf
        for leaf in leaves
        if any(leaf == node or leaf.startswith(f"{node}.") for node in mapped)
    }
    assert len(leaves) == 75
    assert len(semantically_covered) == 64
    assert leaves - semantically_covered == {
        "artificial.extraction.unspecified",
        "bare_sparse.saline_bare",
        "low_vegetation.shrub.unspecified",
        "low_vegetation.unspecified",
        "snow_ice.permanent.unspecified",
        "water.artificial.unspecified",
        "water.coastal.unspecified",
        "water.inland.unspecified",
        "wetland.herbaceous_wetland",
        "wetland.inland.shrub_wetland",
        "wetland.marsh",
    }
