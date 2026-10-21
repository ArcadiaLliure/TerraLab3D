"""Projecta CIE2019 amb aire/buit explícit, sense repetir el transport arxivat."""

import argparse
import json
import time
from dataclasses import asdict
from pathlib import Path

from photometry_coordinates_step7_14_v2 import cie_standard_air, digest, write
from project_skyglow_photometry import spectral_payload
from terralab3d.application.coordinate_photometry import project_coordinate_band


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--case", required=True)
    parser.add_argument(
        "--input-radiance-basis",
        required=True,
        choices=["vacuum_nm"],
        help="Declaració de la coordenada de les densitats; no transforma la SPD d’entrada",
    )
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("La sortida ja existeix; conservar les evidències")
    data = json.loads(args.input.read_text("utf8"))
    selected = [r for r in data if r["name"] == args.case]
    if len(selected) != 1:
        parser.error("Cal un cas existent i únic")
    result = spectral_payload(selected[0]["captured"])
    response = cie_standard_air()
    start = time.perf_counter()
    rows = []
    for sample in result.spectral_samples:
        projection = project_coordinate_band(
            sample,
            response,
            input_radiance_basis=args.input_radiance_basis,
            domain_nm=(sample.knots_nm[0], sample.knots_nm[-1]),
        )
        rows.append(
            dict(
                sourceId=sample.source_id,
                directionId=sample.direction_id,
                band=asdict(projection),
                cieSignal=683 * projection.signal.value,
                cieUnit="cd m^-2"
                if projection.signal.absolute
                else "relative (683 V-weighted)",
                qualification="Model CIE amb resposta en aire estàndard450ppm i entrada explícita en buit; cap calibratge SQM/TESS o observacional",
            )
        )
    write(
        args.output,
        dict(
            case=args.case,
            inputSha256=digest(args.input),
            responseBasis=response.basis,
            physicalTransportEvaluations=0,
            postProjectionWallSeconds=time.perf_counter() - start,
            rows=rows,
            scope="La SPD original no canvia; la seva correspondència amb un catàleg físic en aire s’ha de declarar separadament.",
        ),
    )
    print(f"CIE2019 escrit a {args.output}; transport físic addicional:0")


if __name__ == "__main__":
    main()
