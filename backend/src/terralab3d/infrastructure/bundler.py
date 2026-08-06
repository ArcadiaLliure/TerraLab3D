"""Invoke esbuild to bundle the TypeScript frontend into a single JS file.

The bundler is a build-time utility: it runs npx esbuild exactly once when
``python -m terralab3d`` starts.  The output is written to
``frontend/dist/bundle.js`` and served as a static file by aiohttp.
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
    """Locate npx, checking common Windows paths if it isn't on PATH."""
    npx = shutil.which("npx")
    if npx:
        return npx
    # Fallback: standard Windows install location
    candidate = Path(r"C:\Program Files\nodejs\npx.cmd")
    if candidate.exists():
        return str(candidate)
    raise FileNotFoundError(
        "npx not found.  Install Node.js or add it to PATH."
    )


def bundle_frontend(*, force: bool = False) -> Path:
    """Bundle ``frontend/src/main.ts`` → ``frontend/dist/bundle.js``.

    Returns the path to the dist directory.
    """
    bundle_path = _DIST_DIR / "bundle.js"

    # Skip if already built and source hasn't changed (unless forced)
    if not force and bundle_path.exists():
        src_mtime = max(
            f.stat().st_mtime
            for f in (_FRONTEND_DIR / "src").rglob("*.ts")
        )
        if bundle_path.stat().st_mtime >= src_mtime:
            return _DIST_DIR

    _DIST_DIR.mkdir(parents=True, exist_ok=True)

    # Copy index.html to dist
    index_src = _FRONTEND_DIR / "index.html"
    index_dst = _DIST_DIR / "index.html"
    if index_src.exists():
        shutil.copy2(index_src, index_dst)

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

    print(f"[bundler] Building frontend: {' '.join(cmd)}")
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
            f"esbuild failed (exit {result.returncode}):\n{result.stderr}"
        )

    if result.stderr:
        # esbuild writes warnings to stderr even on success
        print(result.stderr, end="")

    size_kb = bundle_path.stat().st_size / 1024
    print(f"[bundler] OK -> {bundle_path}  ({size_kb:.0f} KB)")
    return _DIST_DIR
