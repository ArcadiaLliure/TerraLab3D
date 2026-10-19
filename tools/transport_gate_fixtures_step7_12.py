"""Entrades explícites del gate congelat 7.12; cap resultat inferit."""

from __future__ import annotations

import json
import math
from dataclasses import replace
from pathlib import Path

from benchmark_skyglow_spectral import fixture
from terrain_fixtures_step7_11 import request as terrain_request
from terralab3d.application.ports.atmospheric_optics import (
    OpticalFieldRequest,
    OpticalTileSpec,
)
from terralab3d.domain.light_pollution.gauss_kronrod import QuadratureSettings
from terralab3d.domain.light_pollution.geometric_transport import ViewDirection
from terralab3d.domain.light_pollution.propagation_kernel import DirectionSet
from terralab3d.domain.light_pollution.source_model import (
    GeodeticPosition,
    PointSourceGeometry,
)
from terralab3d.domain.light_pollution.terrain_visibility import TerrainSurface
from terralab3d.infrastructure.adapters.atmosphere.standard_optics import (
    ExtendedStandardAtmosphericOpticsProvider,
)

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "docs/evidencies/pas7.12/criteri-transport-preregistrat-v1.json"


def standardize(req, *, step=1000.0, original=False):
    assert req.optical_field
    old = req.optical_field
    field = ExtendedStandardAtmosphericOpticsProvider().resolve(
        OpticalFieldRequest(
            old.origin,
            old.time_utc,
            tuple(OpticalTileSpec(t.tile_id, t.version, t.bounds) for t in old.tiles),
            top_m=75000.0,
            vertical_step_m=step,
            radius_m=old.radius_m,
        )
    )
    if req.scattering:
        config = replace(
            req.scattering,
            band=replace(
                req.scattering.band,
                aerosols=tuple(
                    replace(a, scale_height_m=1200.0)
                    for a in req.scattering.band.aerosols
                ),
            ),
        )
        return replace(
            req,
            optical_field=field,
            scattering=config,
            options=replace(req.options, top_m=75000.0),
        )
    assert req.spectral and req.spectral.gas
    gas = req.spectral.gas
    h = (
        0.0,
        10000.0,
        15000.0,
        20000.0,
        25000.0,
        30000.0,
        40000.0,
        50000.0,
        60000.0,
        70000.0,
        75000.0,
    )
    q = (
        4e-8,
        4e-8,
        1e-6,
        5e-6,
        8e-6,
        7e-6,
        3e-6,
        5e-7,
        *(5e-7 * math.exp(-(z - 50000) / 8000) for z in h[-3:]),
    )
    gas = replace(
        gas,
        profiles=tuple(
            replace(
                p,
                heights_m=h,
                mole_fractions=q,
                evidence_reference="O3 prescrit 7.10 fins a50km; extensió exponencial H8km prescrita, no observada",
            )
            for p in gas.profiles
        ),
    )
    config = replace(
        req.spectral,
        gas=gas,
        aerosols=tuple(
            replace(a, reference=replace(a.reference, scale_height_m=1200.0))
            for a in req.spectral.aerosols
        ),
    )
    return replace(
        req,
        optical_field=field,
        spectral=config,
        options=replace(req.options, top_m=75000.0),
    )


def settings(req):
    config = req.scattering or req.spectral.monochromatic()
    config = replace(
        config,
        path_quadrature=QuadratureSettings(1e-8, 1e-12, 4096),
        radiance_quadrature=QuadratureSettings(1e-7, 1e-30, 4096),
        area_order=2,
    )
    return (
        replace(req, scattering=config)
        if req.scattering
        else replace(
            req, spectral=replace(req.spectral, reference_configuration=config)
        )
    )


def primary(spec):
    req = terrain_request(
        spec["mode"],
        mountain=spec["terrain"] == "mountain",
        area=spec["area"],
        elevation=spec["elevationDeg"],
    )
    assert req.optical_field
    if spec["terrain"] == "none":
        req = replace(req, terrain=None)
    if spec["terrain"] == "pas7.11_snapshot":
        data = json.loads(
            (ROOT / "docs/evidencies/pas7.11/dem-real-snapshot.json").read_text(
                encoding="utf-8"
            )
        )
        for key in ("vertices", "faces"):
            data[key] = tuple(tuple(row) for row in data[key])
        data["boundary"] = tuple(data["boundary"])
        surface = TerrainSurface(**data)
        highest = max(math.hypot(*v) - surface.radius_m for v in surface.vertices)
        obs = GeodeticPosition(41.3875, 2.1666667, highest + 100)
        source = replace(
            req.sources[0],
            geometry=PointSourceGeometry(
                GeodeticPosition(
                    obs.latitude_deg, obs.longitude_deg + 0.005, highest + 10
                )
            ),
        )
        assert req.optical_field
        req = replace(
            req,
            observer=obs,
            sources=(source,),
            optical_field=replace(req.optical_field, origin=obs),
            terrain=surface,
        )
    else:
        source = req.sources[0]
        position = GeodeticPosition(
            0, math.degrees(spec["distanceM"] / req.options.earth_radius_m), 10
        )
        source = replace(
            source,
            geometry=replace(source.geometry, center=position)
            if spec["area"]
            else PointSourceGeometry(position),
        )
        req = replace(req, sources=(source,))
    if spec["standard"]:
        req = standardize(req, step=spec["stepM"])
    return settings(req)


def vertical(name, mode):
    if name == "pas7.10_original_B4_standard":
        req = fixture(1, mode, standard=True)
        req = replace(req, directions=DirectionSet((ViewDirection("zenith", 0, 90),)))
        return standardize(req)
    return primary(
        dict(
            mode=mode,
            standard=True,
            stepM=1000,
            area=False,
            distanceM=5000 if name == "S_near5km" else 200000,
            elevationDeg=90,
            terrain="none",
        )
    )
