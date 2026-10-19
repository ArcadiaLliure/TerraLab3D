"""SG-REF, fonts S/C, Jensen i truncament atmosfèric: diagnòstics reproduïbles."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from dataclasses import asdict, replace
from pathlib import Path

import numpy as np

from benchmark_skyglow_spectral import fixture
from terralab3d.application.ports.atmospheric_optics import OpticalFieldRequest, OpticalTileSpec
from terralab3d.infrastructure.adapters.atmosphere.standard_optics import StandardAtmosphericOpticsProvider
from terralab3d.domain.light_pollution.geometric_transport import ViewDirection
from terralab3d.domain.light_pollution.propagation_kernel import (
    DirectionSet,
    PropagationKernel,
)
from terralab3d.domain.light_pollution.reference_single_scattering import (
    solve_reference_b1,
)
from terralab3d.domain.light_pollution.reference_spectral_transport import (
    solve_reference_spectral,
)
from terralab3d.domain.light_pollution.source_model import (
    AngularEmissionProfile,
    DefinedSpectrum,
    EmissionAmplitude,
    GeodeticPosition,
    RectangularAreaGeometry,
    SourceModel,
)
from terralab3d.domain.light_pollution.spectral_transport import SpectralOperator
from terralab3d.domain.light_pollution.gas_absorption import effective_band_transmission
from terralab3d.domain.light_pollution.transport_profiling import TransportProfiler
from terralab3d.infrastructure.adapters.atmosphere.gas_catalog import load_ozone_lut

ROOT = Path(__file__).resolve().parents[1]


def ceiling_fixture(mode: str):
    base = fixture(1, "B1" if mode.startswith("B1") else "B4", standard="standard" in mode)
    assert base.optical_field
    if "standard" in mode:
        old = base.optical_field
        extended = StandardAtmosphericOpticsProvider().resolve(OpticalFieldRequest(old.origin, old.time_utc, tuple(OpticalTileSpec(t.tile_id, t.version, t.bounds) for t in old.tiles), top_m=50000., vertical_step_m=1000., radius_m=old.radius_m))
        base = replace(base, optical_field=extended)
        if base.scattering is not None:
            band = replace(base.scattering.band, aerosols=tuple(replace(a, scale_height_m=1200.) for a in base.scattering.band.aerosols))
            base = replace(base, scattering=replace(base.scattering, band=band))
    return base


def conditional_source(path: Path) -> SourceModel:
    s = json.loads(path.read_text(encoding="utf-8"))[0]["source"]
    g, d, a, amplitude = s["geometry"], s["spectrum"], s["angular"], s["amplitude"]
    assert g["kind"] == "rectangular_area" and a["kind"] == "axial"
    pos = g["center"]
    geometry = RectangularAreaGeometry(
        GeodeticPosition(pos["latitudeDeg"], pos["longitudeDeg"], pos["altitudeM"]),
        g["eastWidthM"],
        g["northHeightM"],
        g["orientationDeg"],
    )
    spectrum = DefinedSpectrum(
        d["spectrumId"],
        d["evidenceReference"],
        d["license"],
        tuple(d["wavelengthsNm"]),
        tuple(d["relativePower"]),
        d["assetSha256"],
        tuple(
            (p["spectrumId"], p["assetSha256"], p["weight"]) for p in d["components"]
        ),
        d["originKind"],
    )
    return SourceModel(
        s["sourceModelId"],
        s["revision"],
        s["definitionReference"],
        geometry,
        spectrum,
        AngularEmissionProfile(
            a["profileId"],
            a["evidenceReference"],
            tuple(a["zenithDeg"]),
            tuple(a["relativeIntensity"]),
        ),
        EmissionAmplitude(
            amplitude["value"],
            amplitude["unit"],
            amplitude["absoluteCalibrationStatus"],
            amplitude["evidenceReference"],
            amplitude["parameterName"],
        ),
        s["sourceMode"],
    )


def run(output: Path, *, resume: bool = False) -> None:
    output.mkdir(parents=True, exist_ok=True)
    result = {
        "transportGate": "diagnostic_only;step7.12_not_executed",
        "referenceCases": [],
        "ceilingCases": [],
        "above50km": "contribució desconeguda; no assumida nul·la; provider limitat a 50 km",
        "inputHashes": {},
    }
    if resume:
        result = json.loads((output / "diagnostics-transport-i-sostre.json").read_text(encoding="utf-8"))
    req = fixture(1)
    cfg = req.spectral
    assert cfg and cfg.gas and req.optical_field
    kernel = PropagationKernel()
    req = replace(req, directions=DirectionSet((ViewDirection("zenith", 0, 90),)))
    fine_gas = replace(cfg.gas, luts=(load_ozone_lut(fine=True),))
    for name in ("S_point_LED_B3", "C_realistic_NOAA20", "C_kelvin3000_NOAA20"):
        if any(r["case"] == name for r in result["referenceCases"]):
            continue
        case = req
        if name.startswith("C_"):
            filename = (
                "barcelona-realista.json"
                if "realistic" in name
                else "barcelona-kelvin-3000.json"
            )
            path = ROOT / "docs/evidencies/pas7.5.1" / filename
            source = conditional_source(path)
            result["inputHashes"][filename] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
            case = replace(
                req,
                sources=(source,),
                observer=replace(
                    req.observer, latitude_deg=req.observer.latitude_deg + 0.1
                ),
            )
        assert case.spectral and case.optical_field
        start = time.perf_counter()
        runtime = kernel.evaluate(case)
        refinements = []
        # S: dades gasoses originals; C: mateixa LUT, separant-ne l'error
        # ja quantificat per l'oracle espectral del cost d'àrea/transport.
        reference_config = replace(cfg, gas=fine_gas) if name.startswith("S_") else cfg
        orders = (
            ((8, 8), (16, 12), (32, 16))
            if name.startswith("S_")
            else ((2, 8), (4, 12), (8, 16))
        )
        for order, area in orders:
            ref = solve_reference_spectral(
                case.sources[0],
                case.observer,
                case.optical_field,
                reference_config,
                0.0,
                90.0,
                10000.0,
                spectral_order=order,
                area_order=area,
            )
            refinements.append(asdict(ref))
        row = {
            "case": name,
            "unit": runtime.integral_unit,
            "runtime": runtime.rays[0].integral,
            "referenceGasInput": "raw_0.01nm"
            if name.startswith("S_")
            else "same_0.5nm_LUT;raw_error_separate_spectral_ledger",
            "refinements": refinements,
            "relativeResidual": runtime.rays[0].integral / refinements[-1]["value"] - 1,
            "successiveReferenceChanges": [
                refinements[i]["value"] / refinements[i - 1]["value"] - 1
                for i in (1, 2)
            ],
            "durationSeconds": time.perf_counter() - start,
            "sourceId": case.sources[0].source_model_id,
        }
        result["referenceCases"].append(row)
        print("SG-REF", name, row["relativeResidual"], flush=True)
        (output / "diagnostics-transport-i-sostre.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    # Sanity per banda sense emissió inventada: la banda buida té NaN intern,
    # es compta a part; només es comparen bandes il·luminades.
    op = SpectralOperator(req.sources[0], cfg)
    weights = op.weights.reshape(-1, 3)
    matrix = op.gas_matrices[0]
    fractions = cfg.gas.luts[0].temperature_weights(288.15)
    sigma = np.sum(fractions[:, None] * matrix, axis=0)
    tau = (1e24 * sigma).reshape(-1, 3)
    t = effective_band_transmission(weights, tau)
    mean_tau = np.divide(
        (weights * tau).sum(axis=1),
        weights.sum(axis=1),
        out=np.zeros(len(weights)),
        where=weights.sum(axis=1) > 0,
    )
    lit = weights.sum(axis=1) > 0
    result["jensen"] = {
        "columnM2": 1e24,
        "litBands": int(lit.sum()),
        "unlitBands": int((~lit).sum()),
        "minimumTeffMinusExpMeanTau": float(np.min(t[lit] - np.exp(-mean_tau[lit]))),
        "maximumTeffMinusExpMeanTau": float(np.max(t[lit] - np.exp(-mean_tau[lit]))),
        "teffRange": [float(np.nanmin(t)), float(np.nanmax(t))],
        "weights": "SPD times declared positive CIE V diagnostic response; no mean optical depth replacement",
    }
    for mode in ("B1_homogeneous_extension", "B1_standard", "B4_standard"):
        base = ceiling_fixture(mode)
        assert base.optical_field
        for elevation in (0.5, 5.0, 30.0, 90.0):
            for top in (10000.0, 20000.0, 30000.0, 50000.0):
                if any(r["mode"] == mode and r["elevationDeg"] == elevation and r["topM"] == top for r in result["ceilingCases"]):
                    continue
                field = base.optical_field
                if mode == "B1_homogeneous_extension":
                    field = replace(
                        field,
                        tiles=tuple(
                            replace(
                                tile,
                                profile=replace(tile.profile, heights_m=(0.0, top)),
                            )
                            for tile in field.tiles
                        ),
                    )
                case = replace(
                    base,
                    optical_field=field,
                    options=replace(base.options, top_m=top),
                    directions=DirectionSet(
                        (ViewDirection("ceiling", 0.0, elevation),), "source_bearing"
                    ),
                )
                p = TransportProfiler()
                start = time.perf_counter()
                r = kernel.evaluate(case, profiler=p)
                row = {
                    "mode": mode,
                    "topM": top,
                    "elevationDeg": elevation,
                    "azimuthDeg": r.rays[0].azimuth_deg,
                    "radiance": r.rays[0].integral,
                    "unit": r.integral_unit,
                    "wallMs": (time.perf_counter() - start) * 1000,
                    "counters": asdict(r.counters),
                    "profiling": p.to_dict(),
                    "estimatedError": r.rays[0].estimated_error,
                }
                # Convergència independent del nou gas en columnes variables.
                if (
                    mode == "B4_standard"
                    and elevation == 90.0
                    and top in (10000.0, 50000.0)
                ):
                    assert case.spectral and case.spectral.gas
                    spectral = case.spectral
                    assert spectral.gas is not None
                    mono = spectral.monochromatic().band
                    ref_rows = []
                    narrow = replace(
                        spectral, wavelength_start_nm=549.999, wavelength_end_nm=550.001
                    )
                    narrow_runtime = (
                        kernel.evaluate(replace(case, spectral=narrow)).rays[0].integral
                        / 0.002
                    )
                    reference_gas = replace(
                        spectral.gas, luts=(load_ozone_lut(fine=True),)
                    )
                    for order in (8, 12, 16):
                        ref = solve_reference_b1(
                            case.sources[0],
                            case.observer,
                            row["azimuthDeg"],
                            elevation,
                            field,
                            mono,
                            top,
                            gas=reference_gas,
                            path_order=order,
                        )
                        ref_rows.append(asdict(ref))
                    response = np.interp(
                        550.0,
                        spectral.responses[0].wavelengths_nm,
                        spectral.responses[0].values,
                    )
                    row["variableColumnReference550"] = {
                        "runtimePerNm": narrow_runtime,
                        "response": float(response),
                        "refinements": ref_rows,
                        "relativeResidual": narrow_runtime
                        / (ref_rows[-1]["value"] * response)
                        - 1,
                    }
                result["ceilingCases"].append(row)
                print("Sostre", mode, elevation, top, row["wallMs"], flush=True)
                (output / "diagnostics-transport-i-sostre.json").write_text(
                    json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )
    for row in result["ceilingCases"]:
        maximum = next(
            r["radiance"]
            for r in result["ceilingCases"]
            if r["mode"] == row["mode"]
            and r["elevationDeg"] == row["elevationDeg"]
            and r["topM"] == 50000.0
        )
        row["fractionOf50km"] = row["radiance"] / maximum
        row["missingFractionTo50km"] = 1 - row["fractionOf50km"]
    (output / "diagnostics-transport-i-sostre.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    run(args.output, resume=args.resume)
