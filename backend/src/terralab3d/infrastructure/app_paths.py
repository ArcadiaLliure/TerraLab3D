"""Helpers de rutes en temps d'execució per a TerraLab3D.

Llegeix la configuració de la llibreria de dades de l'usuari des de:
1. Variable d'entorn `TERRALAB_DATA_ROOT`
2. Fitxer apuntador `%APPDATA%/TerraLab3D/config/data_location.json`
3. Directori local o ruta fallback

Estructura de la llibreria de dades (layout TerraLab3D):
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
    """Retorna el directori d'estat de TerraLab3D (%APPDATA%/TerraLab3D)."""
    return platform_state_base() / "TerraLab3D"


def data_location_pointer_path() -> Path:
    """Retorna la ruta del fitxer apuntador a la llibreria de dades."""
    return application_state_root() / "config" / POINTER_NAME


def resolve_data_root() -> Path:
    """Resol l'arrel de la llibreria de dades seleccionada per l'usuari.

    1. En primer lloc comprova TERRALAB_DATA_ROOT
    2. En segon lloc llegeix %APPDATA%/TerraLab3D/config/data_location.json
    3. Si no existeix cap dels dos, utilitza %APPDATA%/TerraLab3D
    """
    env_root = os.getenv(DATA_ROOT_ENV, "").strip()
    if env_root:
        path = Path(env_root).expanduser().resolve(strict=False)
        log.debug("MGP: [app_paths] [resolve_data_root] [Des d'entorn: %s]", path)
        return path

    pointer = data_location_pointer_path()
    if pointer.exists():
        try:
            with pointer.open("r", encoding="utf-8") as h:
                payload = json.load(h)
            raw_root = str(payload.get("data_root", "") or "").strip()
            if raw_root:
                path = Path(raw_root).expanduser().resolve(strict=False)
                log.debug("MGP: [app_paths] [resolve_data_root] [Des d'apuntador %s: %s]", pointer, path)
                return path
        except Exception as exc:
            log.warning("MGP: [app_paths] [resolve_data_root] [Error llegint %s: %s]", pointer, exc)

    fallback = application_state_root()
    log.debug("MGP: [app_paths] [resolve_data_root] [Utilitzant fallback: %s]", fallback)
    return fallback


def resolve_gaia_data_dir() -> Path:
    """Retorna el directori de dades Gaia (data/sky/gaia sota l'arrel de la llibreria)."""
    root = resolve_data_root()
    gaia_dir = root / "data" / "sky" / "gaia"
    gaia_dir.mkdir(parents=True, exist_ok=True)
    return gaia_dir


def resolve_elevation_data_dir() -> Path:
    """Resolve configured Earth elevation data without creating fake coverage."""

    return resolve_data_root() / "data" / "earth" / "elevation"


def resolve_solar_system_planets_dir() -> Path:
    """Retorna el directori de dades dels planetes (data/sky/solar-system/planets sota l'arrel de la llibreria)."""
    root = resolve_data_root()
    planets_dir = root / "data" / "sky" / "solar-system" / "planets"
    planets_dir.mkdir(parents=True, exist_ok=True)
    return planets_dir


def resolve_resource_state_dir() -> Path:
    """Retorna el directori on es guarda l'estat local dels recursos i capes (state/resources)."""
    root = resolve_data_root()
    state_dir = root / "state" / "resources"
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir


def resolve_download_temp_dir() -> Path:
    """Retorna el directori on es guarden les descàrregues parcials (state/downloads)."""
    root = resolve_data_root()
    temp_dir = root / "state" / "downloads"
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir


def resolve_resource_install_dir(resource_id: str) -> Path:
    """Retorna el directori on s'ha d'instal·lar un recurs basant-se en l'estructura oficial."""
    root = resolve_data_root()
    
    # Domini TERRA
    if resource_id.startswith("earth.elevation"):
        d = root / "data" / "earth" / "elevation" / resource_id.split(".")[-1]
    elif resource_id.startswith("earth.land_cover"):
        d = root / "data" / "earth" / "land-cover" / resource_id.split(".")[-1]
    elif resource_id.startswith("earth.light_pollution"):
        d = root / "data" / "earth" / "light-pollution" / resource_id.split(".")[-1]
        
    # Domini CEL
    elif resource_id.startswith("sky.milky_way") or resource_id.startswith("sky.planck_dust"):
        d = root / "data" / "sky" / "milky-way"
    elif resource_id.startswith("sky.ngc"):
        d = root / "data" / "sky" / "ngc"
    elif resource_id.startswith("sky.stars") or resource_id.startswith("celestial.gaia"):
        d = root / "data" / "sky" / "gaia"
    elif resource_id.startswith("solar.saturn"):
        d = root / "data" / "sky" / "solar-system" / "planets"
    elif resource_id.startswith("solar."):
        d = root / "data" / "sky" / "solar-system" / "kernels"
    else:
        # Fallback conservador basat en el domini
        if resource_id.startswith("earth."):
            d = root / "data" / "earth" / "managed"
        else:
            d = root / "data" / "sky" / "managed"
            
    d.mkdir(parents=True, exist_ok=True)
    return d


def resolve_derived_resource_dir(resource_id: str) -> Path:
    """Retorna la cache derivada d'un recurs sense exposar rutes arbitràries."""
    safe_name = resource_id.replace(".", "-").replace("/", "-").replace("\\", "-")
    derived_dir = resolve_data_root() / "cache" / "resources" / safe_name
    derived_dir.mkdir(parents=True, exist_ok=True)
    return derived_dir
