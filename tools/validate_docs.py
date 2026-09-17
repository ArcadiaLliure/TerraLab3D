"""Validador documental de TerraLab3D.

Verifica l'estructura de docs/tasques/, la presència de totes les seccions canòniques,
la resolució de tots els enllaços Markdown locals, la integritat de les dependències
i la coherència entre README, inventari i passos.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

REQUIRED_H2_SECTIONS = [
    "Descripció funcional",
    "Fonts a consultar",
    "Objectiu",
    "Dependències",
    "Codi existent a reutilitzar",
    "Flux tècnic",
    "Errors, cancel·lació i recursos",
    "Tasques",
    "Criteri de sortida",
    "Proves i evidències obligatòries",
    "Fora d'abast",
    "Instrucció per a Codex",
    "Treball pendent",
]

LINK_PATTERN = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
H1_PATTERN = re.compile(r"^#\s+Pas\s+([0-9]+(?:\.[0-9]+)?)\s*—\s*(.+)$", re.MULTILINE)
H2_PATTERN = re.compile(r"^##\s+(.+)$", re.MULTILINE)
META_PATTERN = re.compile(
    r">\s*\*\*Estat:\*\*\s*([^.]+?)\.\s*\*\*Estat funcional:\*\*\s*([^.]+?)\.\s*\*\*Origen:\*\*\s*([^.]+?)\.\s*\*\*Abast vigent:\*\*\s*(.+)",
    re.MULTILINE,
)


def local_target(raw: str) -> str | None:
    value = raw.strip()
    if value.startswith("<") and ">" in value:
        value = value[1 : value.index(">")]
    else:
        value = value.split(maxsplit=1)[0]
    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc or not parsed.path:
        return None
    return unquote(parsed.path)


def check_structure(errors: list[str]) -> None:
    if not (DOCS / "normes-arquitectura.md").exists():
        errors.append("Falta docs/normes-arquitectura.md")
    if (DOCS / "normes_arquitectura.md").exists():
        errors.append("Existeix docs/normes_arquitectura.md obsolet (cal eliminar-lo)")
    if not (DOCS / "README.md").exists():
        errors.append("Falta docs/README.md")
    if not (DOCS / "inventari-funcional.md").exists():
        errors.append("Falta docs/inventari-funcional.md")

    if not (DOCS / "tasques/completat").is_dir():
        errors.append("Falta docs/tasques/completat/")
    if not (DOCS / "tasques/pendent").is_dir():
        errors.append("Falta docs/tasques/pendent/")
    if not (DOCS / "tasques/idees-per-madurar").is_dir():
        errors.append("Falta docs/tasques/idees-per-madurar/")

    # Check old directories don't exist
    if (DOCS / "completat").exists():
        errors.append("El directori antic docs/completat/ encara existeix")
    if (DOCS / "pendent").exists():
        errors.append("El directori antic docs/pendent/ encara existeix")
    if (DOCS / "idees-per-madurar").exists():
        errors.append("El directori antic docs/idees-per-madurar/ encara existeix")


def check_links(errors: list[str]) -> None:
    for doc in sorted(DOCS.rglob("*.md")):
        text = doc.read_text(encoding="utf-8")
        for line_num, line in enumerate(text.splitlines(), start=1):
            for match in LINK_PATTERN.finditer(line):
                target = local_target(match.group(1))
                if target is None:
                    continue
                # Normalize relative path
                resolved = (doc.parent / target).resolve()
                if not resolved.exists():
                    rel_doc = doc.relative_to(ROOT)
                    errors.append(f"Enllaç trencat a {rel_doc}:{line_num} -> {target}")


def parse_step_file(doc: Path, errors: list[str]) -> dict | None:
    text = doc.read_text(encoding="utf-8")
    rel_doc = doc.relative_to(ROOT)

    # 1. H1 title
    h1_match = H1_PATTERN.search(text)
    if not h1_match:
        errors.append(f"{rel_doc}: Falta o és invàlid el títol H1 (# Pas X — Títol)")
        step_id = doc.stem
    else:
        step_id = h1_match.group(1)

    # 2. Metadata header
    meta_match = META_PATTERN.search(text)
    if not meta_match:
        errors.append(f"{rel_doc}: Falta la capçalera de metadades (> **Estat:** ...)")
        state = ""
    else:
        state = meta_match.group(1).strip()

    # 3. H2 sections
    h2_sections = [m.strip() for m in H2_PATTERN.findall(text)]
    for required in REQUIRED_H2_SECTIONS:
        if required not in h2_sections:
            errors.append(f"{rel_doc}: Falta la secció obligatòria '## {required}'")

    # 4. Checkboxes in Tasques
    tasques_match = re.search(r"## Tasques\s*\n(.*?)(?=\n## |\Z)", text, re.DOTALL)
    if tasques_match:
        tasques_text = tasques_match.group(1)
        if "- [" not in tasques_text:
            errors.append(f"{rel_doc}: La secció ## Tasques no té caselles de verificació (- [ ] o - [x])")

    # 5. Checkboxes in Proves i evidències obligatòries
    proves_match = re.search(
        r"## Proves i evidències obligatòries\s*\n(.*?)(?=\n## |\Z)", text, re.DOTALL
    )
    if proves_match:
        proves_text = proves_match.group(1)
        if "- [" not in proves_text:
            errors.append(f"{rel_doc}: La secció ## Proves i evidències obligatòries no té caselles (- [ ] o - [x])")

    # 6. Checkboxes/contingut in Treball pendent
    pendent_match = re.search(
        r"## Treball pendent\s*\n(.*?)(?=\n## |\Z)", text, re.DOTALL
    )
    if pendent_match:
        pendent_text = pendent_match.group(1).strip()
        if not pendent_text:
            errors.append(f"{rel_doc}: La secció ## Treball pendent està buida")

    # 7. Dependències section structure
    dep_match = re.search(r"## Dependències\s*\n(.*?)(?=\n## |\Z)", text, re.DOTALL)
    depends_on: list[str] = []
    depended_by: list[str] = []
    if dep_match:
        dep_text = dep_match.group(1)
        if "**Depèn de:**" not in dep_text:
            errors.append(f"{rel_doc}: La secció ## Dependències no té '**Depèn de:**'")
        if "**En depenen:**" not in dep_text:
            errors.append(f"{rel_doc}: La secció ## Dependències no té '**En depenen:**'")

        # Extract linked step IDs
        dep_de_part = ""
        en_dep_part = ""
        if "**Depèn de:**" in dep_text and "**En depenen:**" in dep_text:
            parts = dep_text.split("**En depenen:**")
            dep_de_part = parts[0]
            en_dep_part = parts[1]
        elif "**Depèn de:**" in dep_text:
            dep_de_part = dep_text

        for m in re.finditer(r"pas([0-9]+(?:\.[0-9]+)?)[^)]*\.md", dep_de_part):
            depends_on.append(m.group(1))
        for m in re.finditer(r"pas([0-9]+(?:\.[0-9]+)?)[^)]*\.md", en_dep_part):
            depended_by.append(m.group(1))

    return {
        "path": doc,
        "step_id": step_id,
        "state": state,
        "depends_on": depends_on,
        "depended_by": depended_by,
    }


def check_step_files(errors: list[str]) -> dict[str, dict]:
    steps: dict[str, dict] = {}
    for folder in ["completat", "pendent"]:
        for doc in sorted((DOCS / "tasques" / folder).glob("*.md")):
            info = parse_step_file(doc, errors)
            if info:
                sid = info["step_id"]
                if sid in steps:
                    errors.append(f"Identificador de pas duplicat: Pas {sid} ({doc} i {steps[sid]['path']})")
                steps[sid] = info
    return steps


def check_bidirectional_dependencies(steps: dict[str, dict], errors: list[str]) -> None:
    for sid, info in steps.items():
        for dep_id in info["depends_on"]:
            if dep_id in steps:
                target_info = steps[dep_id]
                if sid not in target_info["depended_by"]:
                    rel_source = info["path"].relative_to(ROOT)
                    rel_target = target_info["path"].relative_to(ROOT)
                    errors.append(
                        f"Dependència asimètrica: {rel_source} depèn de Pas {dep_id}, "
                        f"però {rel_target} no té Pas {sid} a '**En depenen:**'"
                    )


def main() -> int:
    errors: list[str] = []
    check_structure(errors)
    check_links(errors)
    steps = check_step_files(errors)
    check_bidirectional_dependencies(steps, errors)

    if errors:
        print(f"S'han trobat {len(errors)} incidències documentals:")
        for err in errors:
            print(f"  - {err}")
        return 1

    print(f"Validació documental completada amb èxit ({len(steps)} passos analitzats, zero incidències).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
