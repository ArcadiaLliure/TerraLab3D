"""Invoqueu esbuild per empaquetar el frontend TypeScript en un sol fitxer JS.

L'empaquetador és una utilitat de construcció: s'executa npx esbuild exactament
una vegada quan s'inicia ``python -m terralab3d``. La sortida s'escriu a
``frontend/dist/bundle.js`` i se serveix com a fitxer estàtic mitjançant aiohttp.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

_FRONTEND_DIR = Path(__file__).resolve().parents[4] / "frontend"
_DIST_DIR = _FRONTEND_DIR / "dist"
_ENTRY = _FRONTEND_DIR / "src" / "main.ts"


def _bundle_is_fresh(frontend_dir: Path, dist_dir: Path) -> bool:
    """Inclou totes les entrades que esbuild pot incorporar al JS o al CSS."""
    sources = [
        path for path in (frontend_dir / "src").rglob("*")
        if path.is_file() and path.suffix in {".ts", ".tsx", ".css"}
    ]
    outputs = [dist_dir / "bundle.js", dist_dir / "bundle.css"]
    if not sources or not all(path.exists() for path in outputs):
        return False
    return min(path.stat().st_mtime for path in outputs) >= max(path.stat().st_mtime for path in sources)


def _find_npx() -> str:
    """Localitza npx, comprovant les rutes habituals de Windows si no és al PATH."""
    npx = shutil.which("npx")
    if npx:
        return npx
    # Alternativa: ubicació d'instal·lació estàndard a Windows
    candidate = Path(r"C:\Program Files\nodejs\npx.cmd")
    if candidate.exists():
        return str(candidate)
    raise FileNotFoundError(
        "No s'ha trobat npx. Instal·leu Node.js o afegiu-lo al PATH."
    )


def bundle_frontend(*, force: bool = False) -> Path:
    """Empaqueta ``frontend/src/main.ts`` → ``frontend/dist/bundle.js``.

    Retorna la ruta al directori dist.
    """
    bundle_path = _DIST_DIR / "bundle.js"
    _DIST_DIR.mkdir(parents=True, exist_ok=True)

    # HTML i recursos públics també formen part del frontend. Sincronitzar-los
    # encara que el bundle TypeScript continuï vigent.
    index_src = _FRONTEND_DIR / "index.html"
    index_dst = _DIST_DIR / "index.html"
    if index_src.exists():
        shutil.copy2(index_src, index_dst)

    public_src = _FRONTEND_DIR / "public"
    if public_src.exists():
        shutil.copytree(public_src, _DIST_DIR, dirs_exist_ok=True)

    # Omet si ja s'ha compilat i el codi font no ha canviat (tret que es forci)
    if not force and _bundle_is_fresh(_FRONTEND_DIR, _DIST_DIR):
        return _DIST_DIR

    npx = _find_npx()
    cmd = [
        npx, "esbuild",
        str(_ENTRY),
        "--bundle",
        "--format=esm",
        f"--outfile={bundle_path}",
        "--sourcemap",
        "--target=es2022",
        "--platform=browser",
    ]

    print(f"[bundler] Construint el frontend: {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        cwd=str(_FRONTEND_DIR),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        raise RuntimeError(
            f"esbuild ha fallat (exit {result.returncode}):\n{result.stderr}"
        )

    if result.stderr:
        # esbuild escriu avisos a stderr fins i tot en èxit
        print(result.stderr, end="")

    size_kb = bundle_path.stat().st_size / 1024
    print(f"[bundler] OK -> {bundle_path}  ({size_kb:.0f} KB)")
    return _DIST_DIR


