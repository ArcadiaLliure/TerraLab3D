"""Projecta espectres arxivats amb els perfils de referència7.14, sense transport."""

import argparse
import json
import time
from dataclasses import asdict
from pathlib import Path

from photometry_fixtures_step7_14 import profiles
from terralab3d.application.photometric_projections import project_retained
from terralab3d.domain.light_pollution.propagation_kernel import (
    GeometricRayResult,
    KernelCounters,
    PropagationResult,
)
from terralab3d.domain.light_pollution.spectral_transport import SpectralRaySamples
from terralab3d.domain.photometric_projection import project_band, sensor_magnitude


def spectral_payload(data) -> PropagationResult:
    """Llegeix espectres i resums; no publica un nou resultat de transport.

    Les traces geomètriques/diagnòstics crus continuen a l’entrada original i
    no són dades necessàries per a aquesta projecció.
    """
    samples = tuple(
        SpectralRaySamples(
            s["source_id"],
            s["direction_id"],
            tuple(s["knots_nm"]),
            tuple(s["radiance_per_nm"]),
            tuple(s["los_error_per_nm"]),
            s["unit"],
            s["scale_id"],
            s["band_set_id"],
        )
        for s in data["spectral_samples"]
    )
    rays = tuple(
        GeometricRayResult(
            r["source_id"],
            r["direction_id"],
            r["azimuth_deg"],
            r["elevation_deg"],
            r["path_length_m"],
            r["integral"],
            r["estimated_error"],
            tuple(tuple(v) for v in r["geometric_cells"]),
            KernelCounters(**r["counters"]),
        )
        for r in data["rays"]
    )
    return PropagationResult(
        data["revision"],
        data["input_signature"],
        data["integrand_id"],
        data["integral_unit"],
        rays,
        KernelCounters(**data["counters"]),
        model_version=data["model_version"],
        spectral_samples=samples,
        spectral_metadata=data.get("spectral_metadata"),
        terrain_metadata=data.get("terrain_metadata"),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Resultat amb spectral_samples o campanya arxivada",
    )
    parser.add_argument("--case", help="Nom exacte del cas d’una campanya")
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Fitxer nou; no sobreescriu evidències",
    )
    parser.add_argument(
        "--reference-bands",
        action="store_true",
        help="Afegeix bandes condicionades; no són lectures SQM/TESS natives",
    )
    args = parser.parse_args()
    if args.output.exists():
        parser.error("La sortida ja existeix; trieu un fitxer nou")
    try:
        source = json.loads(args.input.read_text("utf8"))
        if isinstance(source, list):
            selected = [r for r in source if r.get("name") == args.case]
            if len(selected) != 1:
                raise ValueError("Cal un nom de cas existent i únic")
            source = selected[0]["captured"]
        elif "captured" in source:
            source = source["captured"]
        retained = spectral_payload(source)
        responses = profiles()
        start = time.perf_counter()
        result = project_retained(
            retained, responses, expected_revision=retained.revision
        )
        if args.reference_bands:
            rows = []
            for s in retained.spectral_samples:
                for p in responses[1:]:
                    lo = max(s.knots_nm[0], p.curve.wavelengths_nm[0])
                    hi = min(s.knots_nm[-1], p.curve.wavelengths_nm[-1])
                    signal = project_band(s, p, domain_nm=(lo, hi))
                    rows.append(
                        dict(
                            sourceId=s.source_id,
                            signal=asdict(signal),
                            directionalReferenceOnly=sensor_magnitude(
                                signal, p, allow_reference=True
                            ),
                        )
                    )
            result["conditionalReferenceBands"] = rows
        result["postProjectionWallSeconds"] = time.perf_counter() - start
        result["scope"] = (
            "Perfils de referència7.14; unavailable no és zero. No calibratge natiu ni Bortle."
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(
                result, ensure_ascii=False, indent=2, default=asdict, allow_nan=False
            )
            + "\n",
            encoding="utf8",
            newline="\n",
        )
        print(f"Projeccions escrites a {args.output}; avaluacions del kernel: 0")
    except (ValueError, KeyError, TypeError, OSError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
