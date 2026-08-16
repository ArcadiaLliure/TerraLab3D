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

    # Omet si ja s'ha compilat i el codi font no ha canviat (tret que es forci)
    if not force and bundle_path.exists():
        src_mtime = max(
            f.stat().st_mtime
            for f in (_FRONTEND_DIR / "src").rglob("*.ts")
        )
        if bundle_path.stat().st_mtime >= src_mtime:
            return _DIST_DIR

    _DIST_DIR.mkdir(parents=True, exist_ok=True)

    # Copia index.html i recursos públics a dist
    index_src = _FRONTEND_DIR / "index.html"
    index_dst = _DIST_DIR / "index.html"
    if index_src.exists():
        shutil.copy2(index_src, index_dst)

    public_src = _FRONTEND_DIR / "public"
    if public_src.exists():
        shutil.copytree(public_src, _DIST_DIR, dirs_exist_ok=True)

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

    import os
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"

    result = subprocess.run(
        cmd,
        cwd=str(_FRONTEND_DIR),
        capture_output=True,
        text=False,
    )
    
    safe_stderr = result.stderr.decode("utf-8", errors="replace") if result.stderr else ""

    if result.returncode != 0:
        print(safe_stderr, file=sys.stderr)
        raise RuntimeError(
            f"esbuild ha fallat (exit {result.returncode}):\n{result.stderr}"
        )

    if result.stderr:
        # esbuild escriu avisos a stderr fins i tot en èxit
        print(result.stderr, end="")

    size_kb = bundle_path.stat().st_size / 1024
    print(f"[bundler] OK -> {bundle_path}  ({size_kb:.0f} KB)")
    return _DIST_DIR


