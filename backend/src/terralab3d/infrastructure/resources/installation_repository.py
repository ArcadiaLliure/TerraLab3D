"""Repositori de l'estat local d'instal·lació de recursos."""

import json
import logging
from pathlib import Path
from typing import Any, Dict

from terralab3d.domain.identifiers import ResourceId, VariantId
from terralab3d.domain.resources.models import ResourceInstallState
from terralab3d.infrastructure.app_paths import resolve_resource_state_dir, resolve_data_root

log = logging.getLogger("terralab3d.resources.repository")


class ResourceInstallationRepository:
    """Gestiona l'estat local dels recursos (què està instal·lat, quina variant, on es troba)."""

    def __init__(self) -> None:
        self._state_file = resolve_resource_state_dir() / "local_installation_state.json"
        self._state: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        if not self._state_file.exists():
            self._state = {"resources": {}}
            self.save()
            return

        try:
            with open(self._state_file, "r", encoding="utf-8") as f:
                self._state = json.load(f)
        except Exception as exc:
            log.warning("MGP: [ResourceInstallationRepository] [Error llegint estat local, inicialitzant buit: %s]", exc)
            self._state = {"resources": {}}
            self.save()

    def save(self) -> None:
        try:
            # Atomic write pattern recommended, but simple write for now
            temp_file = self._state_file.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(self._state, f, indent=2)
            temp_file.replace(self._state_file)
        except Exception as exc:
            log.error("MGP: [ResourceInstallationRepository] [Error desant estat local: %s]", exc)

    def get_resource_state(self, resource_id: ResourceId) -> Dict[str, Any] | None:
        return self._state.get("resources", {}).get(resource_id)

    def snapshot(self) -> dict[str, dict[str, Any]]:
        """Retorna una còpia serialitzable de l'estat publicable."""
        resources = self._state.get("resources", {})
        snapshot: dict[str, dict[str, Any]] = {}
        for resource_id, state in resources.items():
            if not isinstance(state, dict):
                continue
            manifest = state.get("manifestData")
            public_manifest = {
                key: value
                for key, value in manifest.items()
                if key not in ("sourcePath", "renderPath")
            } if isinstance(manifest, dict) else None
            snapshot[str(resource_id)] = {
                "status": state.get("status", ResourceInstallState.NOT_INSTALLED.value),
                "variantId": state.get("variantId"),
                "downloadedBytes": state.get("downloadedBytes", 0),
                "verifiedAt": state.get("verifiedAt"),
                "error": state.get("error"),
                "manifestData": public_manifest,
            }
        return snapshot

    def set_resource_state(
        self,
        resource_id: ResourceId,
        state: ResourceInstallState,
        variant_id: VariantId | None = None,
        resolved_path: str | None = None,
        downloaded_bytes: int = 0,
        verified_at: str | None = None,
        error_message: str | None = None,
        manifest_data: Dict[str, Any] | None = None,
    ) -> None:
        resources = self._state.setdefault("resources", {})
        
        current = resources.get(resource_id, {})
        current.update({
            "status": state.value,
            "variantId": variant_id,
            "resolvedPath": resolved_path,
            "downloadedBytes": downloaded_bytes,
            "verifiedAt": verified_at,
            "error": error_message,
        })
        if manifest_data is not None:
            current["manifestData"] = manifest_data
            
        resources[resource_id] = current
        self.save()

    def clear_resource_state(
        self,
        resource_id: ResourceId,
        variant_id: VariantId | None = None,
    ) -> None:
        self._state.setdefault("resources", {})[resource_id] = {
            "status": ResourceInstallState.NOT_INSTALLED.value,
            "variantId": variant_id,
            "resolvedPath": None,
            "downloadedBytes": 0,
            "verifiedAt": None,
            "error": None,
        }
        self.save()

    def resolve_render_asset(self, resource_id: ResourceId) -> Path | None:
        """Resol l'asset READY destinat al renderer, mai una ruta aportada per UI."""
        state = self.get_resource_state(resource_id)
        if not state or state.get("status") != ResourceInstallState.READY.value:
            return None
        manifest = state.get("manifestData")
        candidate = manifest.get("renderPath") if isinstance(manifest, dict) else None
        if not candidate:
            candidate = state.get("resolvedPath")
        if not candidate:
            return None

        root = resolve_data_root().resolve(strict=False)
        resolved = Path(str(candidate)).resolve(strict=False)
        if not resolved.is_relative_to(root) or not resolved.is_file():
            return None
        return resolved

    def discover_existing_resources(self) -> None:
        """Explora el directori de dades actual per registrar els recursos ja presents (migració)."""
        data_root = resolve_data_root()
        resources = self._state.setdefault("resources", {})
        changed = False

        # Discovery de Sistema Solar (Kernels)
        kernels_dir = data_root / "data" / "sky" / "solar-system" / "kernels"
        if kernels_dir.exists():
            # Bundle base
            lsk_file = kernels_dir / "lsk" / "naif0012.tls"
            if lsk_file.exists() and "solar.core" not in resources:
                self.set_resource_state(
                    ResourceId("solar.core"),
                    ResourceInstallState.READY,
                    resolved_path=str(kernels_dir),
                    downloaded_bytes=0,  # Could calculate total
                )
                changed = True
            
            # Saturn rings
            planets_dir = data_root / "data" / "sky" / "solar-system" / "planets"
            saturn_rings = planets_dir / "saturn_rings.png"
            if saturn_rings.exists() and "solar.saturn.rings" not in resources:
                self.set_resource_state(
                    ResourceId("solar.saturn.rings"),
                    ResourceInstallState.READY,
                    VariantId("2k_saturn_ring_alpha"),
                    resolved_path=str(saturn_rings)
                )
                changed = True
        
        # Discovery de Gaia
        gaia_dir = data_root / "data" / "sky" / "gaia"
        if gaia_dir.exists():
            tile_all = gaia_dir / "tile_all.npz"
            manifest = gaia_dir / "tile_manifest.json"
            if (tile_all.exists() or manifest.exists()) and "sky.stars.full" not in resources:
                self.set_resource_state(
                    ResourceId("sky.stars.full"),
                    ResourceInstallState.READY,
                    resolved_path=str(gaia_dir)
                )
                changed = True
                
        # Discovery de Milky Way i Planck
        milky_dir = data_root / "data" / "sky" / "milky-way"
        if milky_dir.exists():
            # Busquem milkyway_2020_*.exr o planck_*.exr
            for file in milky_dir.glob("*.exr"):
                name = file.name.lower()
                if name.startswith("milkyway_2020_") and "sky.milky_way" not in resources:
                    variant_str = name.split("_")[-1].split(".")[0] # ex: 8k
                    self.set_resource_state(
                        ResourceId("sky.milky_way"),
                        ResourceInstallState.READY,
                        VariantId(variant_str),
                        resolved_path=str(file)
                    )
                    changed = True
                elif name.startswith("planck_dust_") and "sky.planck_dust" not in resources:
                    variant_str = name.split("_")[-1].split(".")[0]
                    self.set_resource_state(
                        ResourceId("sky.planck_dust"),
                        ResourceInstallState.READY,
                        VariantId(variant_str),
                        resolved_path=str(file)
                    )
                    changed = True

        if changed:
            log.debug("MGP: [ResourceInstallationRepository] [Descobriment inicial ha completat noves deteccions]")
            self.save()
