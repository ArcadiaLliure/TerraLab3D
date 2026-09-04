"""Valida l’esquelet estructural sense requerir dependències d’execució."""
from __future__ import annotations
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    errors: list[str] = []
    for path in (ROOT / "backend/src").rglob("*.py"):
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            errors.append(f"Python invàlid: {path}: {exc}")
    for path in (ROOT / "contracts/schemas").rglob("*.json"):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"JSON invàlid: {path}: {exc}")
    for package in (ROOT / "backend/src/terralab3d/domain").iterdir():
        if package.name == "__pycache__":
            continue
        if package.is_dir() and not (package / "README.md").exists():
            errors.append(f"Falta README de domini: {package}")
        if package.is_dir() and not (package / "calculations.py").exists():
            errors.append(f"Falta espai de càlcul científic: {package}")
    if not (ROOT / "docs/normes_arquitectura.md").exists():
        errors.append("Falten les normes d’arquitectura")
    if not (ROOT / "docs/completat").is_dir():
        errors.append("Falta el directori de passos completats")
    if not (ROOT / "docs/pendent").is_dir():
        errors.append("Falta el directori de passos pendents")
    if errors:
        raise SystemExit("\n".join(errors))
    print("Esquelet TerraLab3D validat correctament")

if __name__ == "__main__":
    main()
