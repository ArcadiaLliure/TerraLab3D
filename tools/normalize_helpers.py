"""Script per normalitzar tots els passos documentals a l'estàndard templates/pas.md."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

# Dependency maps
DEPENDS_ON = {
    "1": [],
    "2": ["1"],
    "3": ["2"],
    "3.5": ["1"],
    "4": ["1", "2", "3"],
    "5": ["1", "3"],
    "6": ["5"],
    "7": ["1", "3"],
    "8": ["1", "3"],
    "8.5": ["8"],
    "8.6": ["8", "8.5"],
    "8.7": ["7", "8.6"],
    "9": ["8", "8.6"],
    "10": ["5", "7"],
    "11": ["5", "10"],
    "12": ["5", "11"],
    "13": ["6", "12"],
    "14": ["3", "5"],
    "15": ["1", "2"],
    "16": ["15"],
    "17": ["16"],
    "19": ["5", "6", "13"],
    "21": ["1", "13"],
    "22": ["9", "15"],
    "22.5": [],
    "23": ["6", "13", "22", "22.5"],
    "24": ["8.6", "12"],
    "25": ["24"],
    "26": ["24", "25"],
    "27": ["10", "11", "24", "25"],
    "28": ["16", "24", "25"],
    "29": ["17", "24", "25"],
    "30": ["5", "11", "19"],
    "31": ["22", "23"],
    "32": ["9", "22"],
    "33": ["31", "32"],
    "34": ["32", "33"],
    "35": ["9", "33", "34"],
    "36": ["32", "33"],
    "37": ["19", "29"],
    "38": [
        "1", "2", "3", "3.5", "4", "5", "6", "7", "8", "8.5", "8.6", "8.7", "9",
        "10", "11", "12", "13", "14", "15", "16", "17", "19", "21", "22", "23",
        "24", "25", "26", "27", "28", "29", "30", "31", "32", "33", "34", "35",
        "36", "37"
    ],
}

# Calculate reverse dependencies
DEPENDED_BY: dict[str, list[str]] = {k: [] for k in DEPENDS_ON}
for source, targets in DEPENDS_ON.items():
    for target in targets:
        if target in DEPENDED_BY:
            DEPENDED_BY[target].append(source)

# Step titles and file basenames mapping
STEP_INFO = {
    "1": ("pas1.md", "Entorn 3D executable, càmera 360° i bridge Python ↔ Three.js", "completat"),
    "2": ("pas2.md", "Ubicació geogràfica de l'observador i orientació local", "completat"),
    "3": ("pas3.md", "Rellotge de simulació, temps sideral i moviment visible", "completat"),
    "3.5": ("pas3.5.md", "Càmera translacional, mode caminar i mode avió", "completat"),
    "4": ("pas4.md", "Grid celeste, brúixola, etiquetes i HUD", "completat"),
    "5": ("pas5.md", "Camp estel·lar Gaia real, fallback i buffers persistents", "completat"),
    "6": ("pas6.md", "Picking estel·lar precís", "completat"),
    "7": ("pas7.md", "Cel, atmosfera, contaminació lumínica i Bortle", "completat"),
    "8": ("pas8.md", "Sol, Lluna i planetes amb posicions i aparença reals", "completat"),
    "8.5": ("pas8.5.md", "Superfície lunar LRO/LOLA, orientació i libració", "completat"),
    "8.6": ("pas8.6.md", "Planetes, anells i satèl·lits naturals", "completat"),
    "8.7": ("pas8.7.md", "Il·luminació física de l'escena", "completat"),
    "9": ("pas9.md", "Eclipsis, ocultacions, separacions i trajectòries", "completat"),
    "10": ("pas10.md", "Via Làctia i pols galàctica Planck", "completat"),
    "11": ("pas11.md", "Cel profund NGC/IC", "completat"),
    "12": ("pas12.md", "Cerca astronòmica, focus i seguiment", "completat"),
    "13": ("pas13.md", "Picking real, hover, selecció i inspecció", "completat"),
    "14": ("pas14.md", "Traces circumpolars i exposició temporal", "completat"),
    "15": ("pas15.md", "Elevació real, perfil d'horitzó i oclusió", "completat"),
    "16": ("pas16.md", "Terreny 3D retingut, tiles, LOD i picking", "completat"),
    "17": ("pas17-superficie-progressiva.md", "Superfície categòrica, estils i refinament visual", "completat"),
    "19": ("pas19-modes-optics.md", "Modes d'observació: ull nu, càmera fotogràfica i telescopi/Scope", "completat"),
    "21": ("pas21-eines-mesura.md", "Eines de mesura esfèrica", "completat"),
    "22": ("pas22-trajectories-visibilitat.md", "Trajectòries i visibilitat sobre l'horitzó real", "completat"),
    "22.5": ("pas22.5-normalitzacio-documental.md", "Normalització de la documentació viva", "completat"),
    "23": ("pas23-constellacions.md", "Constel·lacions IAU, traçat de referència i documents d'usuari", "pendent"),
    "24": ("pas24-cataleg-recursos-descarregues.md", "Catàleg de recursos i descàrregues persistents", "pendent"),
    "25": ("pas25-gestor-capes.md", "Gestor de capes Cel/Terra", "pendent"),
    "26": ("pas26-recursos-sistema-solar.md", "Vista de recursos del Sistema Solar", "pendent"),
    "27": ("pas27-recursos-espai-profund.md", "Carta de recursos d'espai profund", "pendent"),
    "28": ("pas28-dem-multiproveidor.md", "Descobriment de DEM multiproveïdor", "pendent"),
    "29": ("pas29-superficie-semantica.md", "Superfície semàntica, TLST i refinament", "pendent"),
    "30": ("pas30-plate-solving.md", "Plate solving i comparador foto/simulació", "pendent"),
    "31": ("pas31-millor-nit-planificador.md", "“El millor d'aquesta nit” i planificador", "pendent"),
    "32": ("pas32-motor-efemerides.md", "Motor general d'efemèrides", "pendent"),
    "33": ("pas33-cercador-objectes-efemerides.md", "Cercador d'objectes i efemèrides", "pendent"),
    "34": ("pas34-previsualitzacions-efemerides.md", "Miniatures i animacions d'efemèrides", "pendent"),
    "35": ("pas35-pestanya-eclipsis.md", "Pestanya d'eclipsis", "pendent"),
    "36": ("pas36-esdeveniments-objectes.md", "Esdeveniments propis de planetes i Lluna", "pendent"),
    "37": ("pas37-geonames-empaquetat.md", "Nomenclàtor GeoNames empaquetat", "pendent"),
    "38": ("pas38-homologacio-final.md", "Homologació final, recuperació i rendiment", "pendent"),
}


def link_for_step(from_folder: str, target_id: str) -> str:
    fname, title, folder = STEP_INFO[target_id]
    if folder == from_folder:
        return f"[Pas {target_id} — {title}]({fname})"
    else:
        return f"[Pas {target_id} — {title}](../{folder}/{fname})"


def build_dependencies_block(step_id: str, current_folder: str) -> str:
    dep_on = DEPENDS_ON.get(step_id, [])
    dep_by = DEPENDED_BY.get(step_id, [])

    lines = ["## Dependències\n", "**Depèn de:**"]
    if not dep_on:
        lines.append("- Cap pas previ.")
    else:
        for sid in dep_on:
            lines.append(f"- {link_for_step(current_folder, sid)}")

    lines.append("\n**En depenen:**")
    if not dep_by:
        lines.append("- Cap pas posterior directe.")
    else:
        for sid in dep_by:
            lines.append(f"- {link_for_step(current_folder, sid)}")

    return "\n".join(lines)


print(f"Loaded step info for {len(STEP_INFO)} steps.")
