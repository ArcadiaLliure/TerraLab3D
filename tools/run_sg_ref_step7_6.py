"""SG-REF offline: fixtures reproduïbles, convergència i contrast F5.

Executar des de l'arrel, amb el backend instal·lat en mode editable.
Cap resultat no es publica si falla una comprovació o es cancel·la el càlcul.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
from dataclasses import asdict, replace
from datetime import date
from pathlib import Path

import numpy as np
import scipy
from scipy.special import exp1

from terralab3d.domain.light_pollution.reference_multiple_scattering import (
    estimate_multiple_scattering,
)
from terralab3d.domain.light_pollution.reference_transport import (
    ReferenceOptics,
    ReferencePhase,
    ReferenceSettings,
    solve_reference,
)
from terralab3d.domain.light_pollution.simulation import (
    SkyglowConfiguration,
    build_conditional_scenarios,
)
from terralab3d.domain.light_pollution.source_model import (
    AngularEmissionProfile,
    DefinedSpectrum,
    EmissionAmplitude,
    GeodeticPosition,
    PointSourceGeometry,
    RectangularAreaGeometry,
    SourceModel,
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
)
from terralab3d.infrastructure.adapters.light_pollution.vnp46 import Vnp46GranuleAdapter
from terralab3d.infrastructure.app_paths import resolve_data_root

ROOT = Path(__file__).resolve().parents[1]
RADIUS = 6371008.8


def fixture_source(east_m: float, width_m: float | None = None) -> SourceModel:
    position = GeodeticPosition(0, math.degrees(east_m / RADIUS), 0)
    geometry = (
        PointSourceGeometry(position)
        if width_m is None
        else RectangularAreaGeometry(position, width_m, width_m)
    )
    return SourceModel(
        "sgref-defined-fixture",
        "sgref-fixtures-v1",
        "Fixture definida, cap mesura urbana",
        geometry,
        DefinedSpectrum(
            "flat-400-700",
            "Definició analítica constant",
            "CC0-1.0",
            (400.0, 700.0),
            (1.0, 1.0),
        ),
        AngularEmissionProfile(
            "linear-bounded",
            "Perfil lineal en angle amb radiància superficial limitada",
            (0.0, 90.0),
            (1.0, 0.0),
        ),
        EmissionAmplitude(
            1000.0, "W", "defined_absolute", "Potència definida per al benchmark"
        ),
    )


def optics(
    tau: float = 0.3,
    phase: ReferencePhase = ReferencePhase("isotropic"),
    waves: tuple[float, ...] = (550.0,),
) -> ReferenceOptics:
    return ReferenceOptics(
        waves,
        (tau / 10000,) * len(waves),
        (0.8 * tau / 10000,) * len(waves),
        10000.0,
        phase,
        "Slab homogeni definit; no atmosfera urbana mesurada",
    )


def analytical_check(settings: ReferenceSettings) -> dict:
    source = fixture_source(0)
    observer = GeodeticPosition(0, 0, 100.0)
    medium = optics()
    result = solve_reference((source,), observer, 0, 90, medium, settings)
    k = medium.extinction_per_m[0]
    h, b = observer.altitude_m, medium.top_m
    a = 2 * k
    integral = math.exp(k * h) * (
        math.exp(-a * h) / h - math.exp(-a * b) / b + a * (exp1(a * b) - exp1(a * h))
    )
    expected = (
        source.spectral_flux(550).value
        * source.angular.density_per_sr(0)
        * medium.scattering_per_m[0]
        / (4 * math.pi)
        * integral
    )
    # Contrast LOS amb Gauss-Legendre compost en s, sense canvi sinh ni GK.
    x, w = np.polynomial.legendre.leggauss(32)
    edges = np.geomspace(h, b, 257) - h
    s = (edges[:-1, None] + edges[1:, None]) / 2 + (
        edges[1:, None] - edges[:-1, None]
    ) * x / 2
    gl = float(
        np.sum(
            np.exp(-k * (h + 2 * s))
            / (h + s) ** 2
            * w
            * (edges[1:, None] - edges[:-1, None])
            / 2
        )
    )
    gl *= (
        source.spectral_flux(550).value
        * source.angular.density_per_sr(0)
        * medium.scattering_per_m[0]
        / (4 * math.pi)
    )
    observed = result.values[0]
    budget = settings.absolute_tolerance + settings.los_relative_tolerance * expected
    if abs(observed - expected) > budget or abs(observed - gl) > budget:
        raise ValueError("Fallada del contrast analític E1")
    return {
        "source": source.to_dict(),
        "observer": asdict(observer),
        "optics": asdict(medium),
        "result": result.to_dict(),
        "closedFormE1": float(expected),
        "independentCompositeGL": gl,
        "relativeErrorE1": abs(observed / expected - 1),
        "relativeErrorCompositeGL": abs(observed / gl - 1),
    }


def spatial_check(settings: ReferenceSettings) -> dict:
    source = fixture_source(3000, 2000)
    observer = GeodeticPosition(0, 0, 0)
    medium = optics(phase=ReferencePhase("rayleigh"))
    whole = solve_reference((source,), observer, 30, 60, medium, settings)
    cells = []
    for i, (east, north) in enumerate(
        ((-500, -500), (-500, 500), (500, -500), (500, 500))
    ):
        cells.append(
            replace(
                source,
                source_model_id=f"cell-{i}",
                geometry=RectangularAreaGeometry(
                    GeodeticPosition(
                        math.degrees(north / RADIUS),
                        math.degrees((3000 + east) / RADIUS),
                        0,
                    ),
                    1000,
                    1000,
                ),
                amplitude=replace(source.amplitude, value=source.amplitude.value / 4),
            )
        )
    subdivided = solve_reference(tuple(cells), observer, 30, 60, medium, settings)
    delta = abs(whole.values[0] - subdivided.values[0])
    if (
        delta
        > settings.absolute_tolerance
        + settings.area_relative_tolerance * whole.values[0]
    ):
        raise ValueError("Fallada de conservació de la integració raster")
    sweeps = []
    for tolerance in (1e-4, 1e-6, 1e-8):
        controls = replace(
            settings,
            area_relative_tolerance=tolerance,
            los_relative_tolerance=min(1e-10, tolerance / 100),
        )
        sweeps.append(
            {
                "areaTolerance": tolerance,
                "result": solve_reference(
                    (source,), observer, 30, 60, medium, controls
                ).to_dict(),
            }
        )
    return {
        "source": source.to_dict(),
        "observer": asdict(observer),
        "direction": [30, 60],
        "optics": asdict(medium),
        "whole": whole.to_dict(),
        "rasterCells": [s.to_dict() for s in cells],
        "rasterSum": subdivided.to_dict(),
        "subdivisionRelativeDifference": delta / whole.values[0],
        "toleranceSweep": sweeps,
    }


def fine_reference(settings: ReferenceSettings) -> dict:
    library = load_spectral_library()
    spectrum = library.kelvin_spectrum(4000)
    source = replace(fixture_source(5000), spectrum=spectrum)
    waves = spectrum.wavelengths_nm
    scattering = tuple(1e-5 * (550 / w) ** 4 for w in waves)
    medium = ReferenceOptics(
        waves,
        tuple(b + 1e-5 for b in scattering),
        scattering,
        10000,
        ReferencePhase("hg", 0.6),
        "Fixture espectral λ^-4 + absorció constant definida; no calibració atmosfèrica",
    )
    result = solve_reference(
        (source,), GeodeticPosition(0, 0, 0), 90, 45, medium, settings
    )
    phases = []
    for n in (4097, 8193, 16385):
        mu = np.linspace(-1, 1, n)
        values = medium.phase.density(mu)
        table = ReferencePhase(
            "tabulated",
            cosines=tuple(float(x) for x in mu),
            relative_values=tuple(float(x) for x in values),
            evidence_reference=f"HG g=0.6 tabulada en {n} cosinus; normalització integral lineal",
        )
        comparison = solve_reference(
            (source,),
            GeodeticPosition(0, 0, 0),
            90,
            45,
            replace(medium, phase=table),
            settings,
        )
        relative = np.max(
            np.abs(np.array(comparison.values) / np.array(result.values) - 1)
        )
        phases.append(
            {
                "samples": n,
                "maxRelativeRadianceDifference": float(relative),
                "result": comparison.to_dict(),
            }
        )
    return {
        "source": source.to_dict(),
        "observer": [0, 0, 0],
        "direction": [90, 45],
        "optics": asdict(medium),
        "wavelengthCount": len(waves),
        "analyticPhase": result.to_dict(),
        "phaseResolutionSweep": phases,
    }


def f5_checks(settings: ReferenceSettings, criterion: dict) -> list[dict]:
    controls = criterion["multipleScattering"]
    source = fixture_source(15000, 20000)
    observer = GeodeticPosition(0, 0, 0)
    cases = []
    for phase in (
        ReferencePhase("isotropic"),
        ReferencePhase("rayleigh"),
        ReferencePhase("hg", 0.6),
    ):
        for tau in controls["opticalDepths"]:
            assert phase.kind != "tabulated"
            medium = optics(tau, phase)
            deterministic = solve_reference(
                (source,), observer, 0, 90, medium, settings
            )
            mc = estimate_multiple_scattering(
                source,
                observer,
                0,
                90,
                550,
                tau / 10000,
                controls["singleScatteringAlbedo"],
                10000,
                phase=phase.kind,
                asymmetry=phase.asymmetry,
                photons=controls["photonCount"],
                seed=controls["seed"],
                max_scatterings=controls["maxScatterings"],
            )
            difference = abs(deterministic.values[0] - mc.single_scattering)
            allowed = (
                6 * mc.single_standard_error + deterministic.numerical_error_estimate[0]
            )
            if (
                difference > allowed
                or mc.higher_orders <= 6 * mc.higher_orders_standard_error
            ):
                raise ValueError(f"Contrast F5 no resolt: {phase.kind}, τ={tau}")
            cases.append(
                {
                    "source": source.to_dict(),
                    "observer": asdict(observer),
                    "direction": [0, 90],
                    "optics": asdict(medium),
                    "opticalDepth": tau,
                    "deterministicSingle": deterministic.to_dict(),
                    "multiple": mc.to_dict(),
                    "firstOrderDifferenceInStandardErrors": difference
                    / mc.single_standard_error,
                    "prospectiveFirstOrderCheck": "PASS",
                    "higherOrderDetectionInStandardErrors": mc.higher_orders
                    / mc.higher_orders_standard_error,
                }
            )
            print(
                f"F5 {phase.kind} τ={tau}: biaix={1 - mc.single_scattering / mc.all_orders:.3%}",
                flush=True,
            )
    return cases


def conditional_checks(settings: ReferenceSettings, data_root: Path) -> list[dict]:
    root = data_root / "data/earth/light-pollution"
    granule = root / "vj146a2/2026/256/VJ146A2.A2026256.h18v04.002.2026264085938.h5"
    rsr_path = (
        root / "viirs-rsr/research/noaa-multisat/prepared/noaa-20-diagnostic-rsr.json"
    )
    policy = Vnp46Policy.from_profile(
        json.loads(
            (ROOT / "docs/skyglow/skyglow-v1-profile.json").read_text(encoding="utf-8")
        )
    )
    with Vnp46GranuleAdapter(
        granule,
        policy=noaa20_policy(policy),
        expected_sha256="2537a64667a440deb099cf08b47a39744c9127abb742419ce256d38b62d0b762",
    ) as reader:
        observation = reader.read_pixel(date(2026, 9, 13), 2067, 520)
    response = LocalViirsSpectralResponseRepository(rsr_path).resolve_reference(
        platform="NOAA-20", gain_stage="MGS"
    )
    observer = GeodeticPosition(
        observation.latitude_deg, observation.longitude_deg - 0.03, 0
    )
    library = load_spectral_library()
    medium = optics(phase=ReferencePhase("rayleigh"), waves=(450.0, 550.0, 650.0))
    cases = []
    for config in (
        SkyglowConfiguration(),
        SkyglowConfiguration(mode="kelvin", kelvin=3000),
        SkyglowConfiguration(mode="kelvin", kelvin=6500),
    ):
        print(f"C {config.mode}, {config.kelvin:g} K", flush=True)
        for scenario in build_conditional_scenarios(
            observation, response, library, config
        ):
            result = solve_reference(
                (scenario.source,), observer, 90, 60, medium, settings
            )
            context = scenario.to_dict()
            # El DTO de 7.5.1 continua expressant transport pendent del producte.
            # Aquest embolcall identifica inequívocament la propagació offline.
            cases.append(
                {
                    "conditionalContext": context,
                    "observer": asdict(observer),
                    "direction": [90, 60],
                    "optics": asdict(medium),
                    "referenceRadiance": result.to_dict(),
                    "calculationStatus": "offline_reference_complete",
                    "alternativeSemantics": "separate_not_summed",
                }
            )
    return cases


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="JSON de resultats; només s'escriu després dels contrasts",
    )
    parser.add_argument(
        "--with-real-black-marble",
        action="store_true",
        help="Incloure 18 alternatives C del grànul real instal·lat",
    )
    parser.add_argument("--data-root", type=Path, default=None)
    args = parser.parse_args()
    criterion_path = ROOT / "docs/evidencies/pas7.6/criteri-oracle-v1.json"
    raw = criterion_path.read_bytes()
    criterion = json.loads(raw)
    controls = criterion["deterministic"]
    settings = ReferenceSettings(
        los_relative_tolerance=controls["losRelativeTolerance"],
        absolute_tolerance=controls["losAbsoluteTolerance"],
        area_relative_tolerance=controls["areaRelativeTolerance"],
        area_orders=tuple(controls["areaOrders"]),
    )
    report = {
        "schemaVersion": 1,
        "criterionId": criterion["criterionId"],
        "criterionSha256": hashlib.sha256(raw).hexdigest(),
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
        "settings": asdict(settings),
        "analytic": analytical_check(settings),
        "spatial": spatial_check(settings),
        "fineSpectral": fine_reference(settings),
        "f5": f5_checks(settings, criterion),
        "conditional": conditional_checks(
            settings, args.data_root or resolve_data_root()
        )
        if args.with_real_black_marble
        else [],
        "runtimeGate": "not_evaluated_step_7.12",
        "empiricalValidation": "not_evaluated",
        "H": "not_homologated",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_name(args.output.name + ".tmp")
    temporary.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(args.output)
    print(f"Evidència SG-REF escrita: {args.output}")


if __name__ == "__main__":
    main()
