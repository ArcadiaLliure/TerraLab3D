"""Connexió real, contractes, invalidació i errors separats de la ciència."""

from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from terralab3d.application.skyglow_configuration import SkyglowConfigurationController
from terralab3d.domain.light_pollution.simulation import (
    SkyglowConfiguration,
    build_conditional_scenarios,
)
from terralab3d.domain.light_pollution.vnp46 import Vnp46Policy
from terralab3d.infrastructure.adapters.light_pollution.black_marble_sources import (
    noaa20_policy,
)
from terralab3d.infrastructure.adapters.light_pollution.spectral_library import (
    load_spectral_library,
)
from terralab3d.infrastructure.adapters.light_pollution.viirs_rsr import (
    LocalViirsSpectralResponseRepository,
    RsrUnavailableError,
)
from terralab3d.infrastructure.adapters.light_pollution.vnp46 import (
    Vnp46GranuleAdapter,
    Vnp46QuarantineError,
    Vnp46UnavailableError,
)
from terralab3d.infrastructure.app_paths import resolve_data_root


ROOT = Path(__file__).resolve().parents[2]
SHA = "2537a64667a440deb099cf08b47a39744c9127abb742419ce256d38b62d0b762"
DAY = date(2026, 9, 13)


def read_real_pair():
    root = resolve_data_root() / "data/earth/light-pollution"
    path = root / "vj146a2/2026/256/VJ146A2.A2026256.h18v04.002.2026264085938.h5"
    manifest = (
        root / "viirs-rsr/research/noaa-multisat/prepared/noaa-20-diagnostic-rsr.json"
    )
    if not path.exists() or not manifest.exists():
        pytest.skip(
            "Assets científics reals no instal·lats; no se substitueixen per una fixture"
        )
    policy = Vnp46Policy.from_profile(
        json.loads(
            (ROOT / "docs/skyglow/skyglow-v1-profile.json").read_text(encoding="utf-8")
        )
    )
    with Vnp46GranuleAdapter(
        path, policy=noaa20_policy(policy), expected_sha256=SHA
    ) as reader:
        observation = reader.read_pixel(DAY, 2067, 520)
        assert reader.read_pixel(DAY, 0, 0).is_fill
        with pytest.raises(Vnp46UnavailableError):
            reader.read_pixel(date(2026, 9, 14), 2067, 520)
    assert reader._file is None
    with pytest.raises(Vnp46QuarantineError):
        with Vnp46GranuleAdapter(path, policy=policy, expected_sha256=SHA):
            pass
    repo = LocalViirsSpectralResponseRepository(manifest)
    return (
        observation,
        repo.resolve_reference(platform="NOAA-20", gain_stage="MGS"),
        repo,
    )


def test_real_qa_identity_reference_not_certification():
    obs, rsr, repo = read_real_pair()
    assert obs.raw_radiance == pytest.approx(139.34158325195312)
    assert obs.quality_flag == 0 and obs.qf_cloud_mask == 34 and obs.snow_flag == 0
    assert obs.product_id == "VJ146A2" and obs.provenance.sha256 == SHA
    assert rsr.valid_through == date(2017, 11, 18)
    assert rsr.valid_through < obs.acquisition_date
    assert (
        not rsr.validated_l3_basis_candidate and not rsr.product_homologation_candidate
    )
    with pytest.raises(RsrUnavailableError):
        repo.resolve_reference(platform="NOAA-21", gain_stage="MGS")
    with pytest.raises(RsrUnavailableError):
        repo.resolve_reference(platform="NOAA-20", gain_stage="HGS")


def test_realistic_reproducibility_sensitivity_and_cache():
    obs, rsr, repo = read_real_pair()
    library = load_spectral_library()
    config = SkyglowConfiguration()
    assert (
        SkyglowConfiguration.from_dict(json.loads(json.dumps(config.to_dict())))
        == config
    )
    first = build_conditional_scenarios(obs, rsr, library, config)
    second = build_conditional_scenarios(obs, rsr, library, config)
    assert [s.to_dict() for s in first] == [s.to_dict() for s in second]
    assert len(first) == 6 and len({s.cache_key for s in first}) == 6
    assert len({s.source.spectrum.spectrum_id for s in first}) == 3
    assert (
        first[0].source.spectral_radiant_intensity(450, 70).value
        != first[1].source.spectral_radiant_intensity(450, 70).value
    )
    lgs = build_conditional_scenarios(
        obs,
        repo.resolve_reference(platform="NOAA-20", gain_stage="LGS"),
        library,
        config,
    )
    assert first[0].source.amplitude.value != pytest.approx(
        lgs[0].source.amplitude.value
    )
    for updated in [
        replace(config, kelvin=4000),
        replace(config, mode="kelvin"),
        replace(config, normalization="constant_radiant_power"),
    ]:
        assert updated.cache_key != config.cache_key
    assert first[0].cache_key != lgs[0].cache_key
    dto = json.loads(json.dumps(first[0].to_dict(), allow_nan=False))
    assert dto["skyRadiance"] is None and dto["quality"] == "conditional_relative"
    assert dto["rsr"]["l3LinkStatus"] == "unverified"
    assert dto["source"]["sourceMode"] == "CONDITIONAL_L3"


@pytest.mark.parametrize(
    "change",
    [
        {"raw_radiance": -1},
        {"raw_radiance": float("nan")},
        {"raw_radiance": 0},
        {"quality_flag": 1},
        {"is_fill": True},
        {"product_id": "VJ246A2"},
        {"radiance_unit": "W"},
    ],
)
def test_invalid_observation_rejected(change):
    obs, rsr, _ = read_real_pair()
    with pytest.raises(ValueError):
        build_conditional_scenarios(
            replace(obs, **change), rsr, load_spectral_library(), SkyglowConfiguration()
        )


@pytest.mark.parametrize(
    "payload",
    [
        {"mode": "rgb"},
        {"kelvin": 1800},
        {"kelvin": float("nan")},
        {"spectral_family": "mercury"},
        {"normalization": "L3_to_W"},
        {"revision": "unversioned"},
    ],
)
def test_invalid_configuration_rejected(payload):
    with pytest.raises(ValueError):
        SkyglowConfiguration.from_dict(payload)


def test_authoritative_configuration_invalidates_and_never_fakes_transport():
    async def run():
        controller = SkyglowConfigurationController(load_spectral_library())
        before = controller.snapshot()
        await controller.configure(
            SkyglowConfiguration(mode="kelvin", kelvin=5000).to_dict()
        )
        after = controller.snapshot()
        assert after["generation"] > before["generation"]
        assert after["configurationKey"] != before["configurationKey"]
        assert abs(after["effectiveSpectrum"]["effectiveCctK"] - 5000) < 0.1
        assert (
            after["skyRadiance"] is None
            and after["calculationStatus"] == "transport_pending"
        )
        assert after["blackMarble"] is None and after["rsr"] is None
        with pytest.raises(ValueError):
            await controller.configure({"kelvin": 1000})
        assert controller.configuration.kelvin == 5000

    asyncio.run(run())
