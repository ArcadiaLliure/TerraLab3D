"""Escenaris angulars prescrits; C conserva escala i procedència relatives."""

from dataclasses import replace

from diagnose_spectral_transport_step7_10 import conditional_source
from transport_gate_fixtures_step7_12 import ROOT, primary


def fixture(name):
    chamber = "chamber" in name
    req = primary(
        dict(
            mode="B4",
            standard=not chamber,
            stepM=1000,
            area=False,
            distanceM=5000,
            elevationDeg=90,
            terrain="mountain" if "mountain" in name else "none",
        )
    )
    if chamber:
        assert req.optical_field and req.spectral and req.spectral.gas
        field = replace(
            req.optical_field,
            tiles=tuple(
                replace(
                    t,
                    profile=replace(
                        t.profile,
                        heights_m=(0.0, 75000.0),
                        revision="angular-homogeneous-chamber-75km-v1",
                    ),
                )
                for t in req.optical_field.tiles
            ),
        )
        gas = replace(
            req.spectral.gas,
            profiles=tuple(
                replace(p, heights_m=(0.0, 75000.0)) for p in req.spectral.gas.profiles
            ),
        )
        req = replace(
            req,
            optical_field=field,
            spectral=replace(req.spectral, gas=gas),
            options=replace(req.options, top_m=75000.0),
        )
    if name.startswith("C_"):
        asset = (
            ROOT
            / "docs/evidencies/pas7.5.1"
            / (
                "barcelona-realista.json"
                if "realista" in name
                else "barcelona-kelvin-3000.json"
            )
        )
        source = replace(conditional_source(asset), geometry=req.sources[0].geometry)
        req = replace(req, sources=(source,))
    return req
