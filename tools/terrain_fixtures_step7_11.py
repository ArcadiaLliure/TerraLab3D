"""Fixtures sintètiques explícites: no són relleu observacional."""

from __future__ import annotations

import math
from dataclasses import replace

from benchmark_skyglow_spectral import fixture as spectral_fixture
from terralab3d.domain.light_pollution.geometric_transport import (
    SphericalFrame,
    ViewDirection,
)
from terralab3d.domain.light_pollution.propagation_kernel import DirectionSet
from terralab3d.domain.light_pollution.source_model import (
    GeodeticPosition,
    PointSourceGeometry,
    RectangularAreaGeometry,
)
from terralab3d.domain.light_pollution.terrain_visibility import TerrainSurface


def grid_surface(easts, norths, heights, *, label="fixture prescrita"):
    frame = SphericalFrame(GeodeticPosition(0, 0, 0))
    vertices = tuple(
        frame.position_ecef(
            GeodeticPosition(
                math.degrees(n / frame.radius_m),
                math.degrees(e / frame.radius_m),
                float(heights[j][i]),
            )
        )
        for j, n in enumerate(norths)
        for i, e in enumerate(easts)
    )
    nx, ny = len(easts), len(norths)
    faces = []
    for j in range(ny - 1):
        for i in range(nx - 1):
            sw = j * nx + i
            faces.extend(((sw, sw + 1, sw + nx + 1), (sw, sw + nx + 1, sw + nx)))
    boundary = tuple(
        list(range(nx))
        + [j * nx + nx - 1 for j in range(1, ny)]
        + list(range(nx * ny - 2, nx * (ny - 1) - 1, -1))
        + [j * nx for j in range(ny - 2, 0, -1)]
    )
    return TerrainSurface(
        vertices,
        tuple(faces),
        boundary,
        frame.radius_m,
        max(max(row) for row in heights),
        label,
        "altura radial esfèrica prescrita; no datum vertical real",
    )


def mountain_surface(height=1200.0):
    easts = (-20000.0, 0.0, 2000.0, 2500.0, 3000.0, 5000.0, 20000.0)
    norths = (-20000.0, 0.0, 20000.0)
    return grid_surface(
        easts,
        norths,
        [[height if e == 2500 else 0.0 for e in easts] for _ in norths],
        label="muntanya triangular de 1200 m; graella explícita v1",
    )


def request(mode="B1", *, mountain=True, area=False, elevation=90.0):
    req = spectral_fixture(1, mode)
    source = req.sources[0]
    position = GeodeticPosition(0, math.degrees(5000 / req.options.earth_radius_m), 10)
    geometry = (
        RectangularAreaGeometry(position, 400.0, 400.0, 0.0)
        if area
        else PointSourceGeometry(position)
    )
    source = replace(source, geometry=geometry)
    return replace(
        req,
        sources=(source,),
        optical_field=replace(req.optical_field, origin=GeodeticPosition(0, 0, 100))
        if req.optical_field
        else None,
        observer=GeodeticPosition(0, 0, 100),
        directions=DirectionSet((ViewDirection("view", 90, elevation),)),
        terrain=mountain_surface(1200 if mountain else 0),
    )
