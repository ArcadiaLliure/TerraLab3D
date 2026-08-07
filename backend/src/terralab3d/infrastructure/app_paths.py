"""Helpers de rutes en temps d'execució per a TerraLab3D.

Llegeix la configuració de la llibreria de dades de l'usuari des de:
1. Variable d'entorn `TERRALAB_DATA_ROOT`
2. Fitxer apuntador `%APPDATA%/TerraLab/config/data_location.json`
3. Directori local o ruta fallback

Estructura de la llibreria de dades (layout TerraLab):
- root / "data" / "sky" / "gaia"
- root / "data" / "sky" / "ngc"
- root / "data" / "sky" / "milky-way"
- root / "data" / "sky" / "solar-system"
- root / "data" / "earth" / "elevation"
- root / "data" / "earth" / "surface"
- root / "data" / "earth" / "light-pollution"
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

log = logging.getLogger("terralab3d.app_paths")

POINTER_NAME = "data_location.json"
DATA_ROOT_ENV = "TERRALAB_DATA_ROOT"


def platform_state_base() -> Path:
    """Retorna el directori d'estat de la plataforma (APPDATA en Windows)."""
    appdata = os.getenv("APPDATA")
    if appdata:
        return Path(appdata)
    if sys.platform.startswith("darwin"):
        return Path.home() / "Library" / "Application Support"
    return Path.home() / ".local" / "share"


def application_state_root() -> Path:
    """Retorna el directori d'estat de TerraLab (%APPDATA%/TerraLab)."""
    return platform_state_base() / "TerraLab"


def data_location_pointer_path() -> Path:
    """Retorna la ruta del fitxer apuntador a la llibreria de dades."""
    return application_state_root() / "config" / POINTER_NAME


def resolve_data_root() -> Path:
    """Resol l'arrel de la llibreria de dades seleccionada per l'usuari.

    1. En primer lloc comprova TERRALAB_DATA_ROOT
    2. En segon lloc llegeix %APPDATA%/TerraLab/config/data_location.json
    3. Si no existeix cap dels dos, utilitza %APPDATA%/TerraLab
    """
    env_root = os.getenv(DATA_ROOT_ENV, "").strip()
    if env_root:
        path = Path(env_root).expanduser().resolve(strict=False)
        log.info("MGP: [app_paths] [resolve_data_root] [Des d'entorn: %s]", path)
        return path

    pointer = data_location_pointer_path()
    if pointer.exists():
        try:
            with pointer.open("r", encoding="utf-8") as h:
                payload = json.load(h)
            raw_root = str(payload.get("data_root", "") or "").strip()
            if raw_root:
                path = Path(raw_root).expanduser().resolve(strict=False)
                log.info("MGP: [app_paths] [resolve_data_root] [Des d'apuntador %s: %s]", pointer, path)
                return path
        except Exception as exc:
            log.warning("MGP: [app_paths] [resolve_data_root] [Error llegint %s: %s]", pointer, exc)

    fallback = application_state_root()
    log.info("MGP: [app_paths] [resolve_data_root] [Utilitzant fallback: %s]", fallback)
    return fallback


def resolve_gaia_data_dir() -> Path:
    """Retorna el directori de dades Gaia (data/sky/gaia sota l'arrel de la llibreria)."""
    root = resolve_data_root()
    gaia_dir = root / "data" / "sky" / "gaia"
    gaia_dir.mkdir(parents=True, exist_ok=True)
    return gaia_dir
