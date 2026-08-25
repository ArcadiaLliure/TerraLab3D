"""Servidor HTTP + WebSocket per a TerraLab3D.

Serveix el frontend compilat com a fitxers estàtics i exposa un punt final ``/ws``
per al pont bidireccional Python ↔ Three.js.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from pathlib import Path
from typing import Any
from datetime import datetime

import aiohttp.web

from .websocket_bridge import WebSocketBridge
from terralab3d.application.ports.moon_surface_assets import MoonSurfaceAssetPort
from terralab3d.application.ports.solar_system_assets import SolarSystemAssetPort
from terralab3d.infrastructure.adapters.file_assets.galactic import ManagedGalacticAssets
from terralab3d.application.raster_imports import RasterImportError, RasterImportService
from terralab3d.infrastructure.adapters.raster import RasterDatasetError

log = logging.getLogger("terralab3d.server")


class TerraLabServer:
    """Servidor HTTP/WebSocket basat en asyncio per a TerraLab3D."""

    def __init__(
        self,
        dist_dir: Path,
        bridge: WebSocketBridge,
        moon_surface_assets: MoonSurfaceAssetPort | None = None,
        solar_system_assets: SolarSystemAssetPort | None = None,
        galactic_assets: ManagedGalacticAssets | None = None,
        raster_imports: RasterImportService | None = None,
        *,
        host: str = "127.0.0.1",
        port: int = 14398,
    ) -> None:
        self._dist_dir = dist_dir
        self._bridge = bridge
        self._moon_surface_assets = moon_surface_assets
        self._solar_system_assets = solar_system_assets
        self._galactic_assets = galactic_assets
        self._raster_imports = raster_imports
        self._host = host
        self._port = port
        self._actual_port = 0
        self._app: aiohttp.web.Application | None = None
        self._runner: aiohttp.web.AppRunner | None = None
        self._site: aiohttp.web.TCPSite | None = None

    @property
    def url(self) -> str:
        return f"http://{self._host}:{self._actual_port}"

    @property
    def actual_port(self) -> int:
        return self._actual_port

    def set_raster_import_service(self, service: RasterImportService) -> None:
        if self._app is not None:
            raise RuntimeError("Raster import routes must be configured before server start")
        self._raster_imports = service

    @aiohttp.web.middleware
    async def _remove_csp_middleware(self, request: aiohttp.web.Request, handler: Any) -> aiohttp.web.StreamResponse:
        try:
            response = await handler(request)
            if "Content-Security-Policy" in response.headers:
                del response.headers["Content-Security-Policy"]
            return response
        except aiohttp.web.HTTPException as ex:
            if "Content-Security-Policy" in ex.headers:
                del ex.headers["Content-Security-Policy"]
            raise

    async def _remove_csp_on_prepare(self, request: aiohttp.web.Request, response: aiohttp.web.StreamResponse) -> None:
        if "Content-Security-Policy" in response.headers:
            del response.headers["Content-Security-Policy"]
        if request.path in {
            "/",
            "/index.html",
            "/bundle.js",
            "/bundle.js.map",
            "/bundle.css",
        }:
            # The executable rebuilds these files in place. Revalidation is not
            # enough for an application tab surviving a backend restart: the UI
            # shell must never be restored from an old browser cache.
            response.headers["Cache-Control"] = "no-store, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"

    async def start(self) -> str:
        """Inicia el servidor i retorna l'URL base."""
        self._app = aiohttp.web.Application(middlewares=[self._remove_csp_middleware])
        self._app.on_response_prepare.append(self._remove_csp_on_prepare)
        self._app.router.add_get("/ws", self._bridge.handle_websocket)
        if self._moon_surface_assets is not None:
            self._app.router.add_get("/moon-assets/{asset_name}", self._serve_moon_asset)
        if self._solar_system_assets is not None:
            self._app.router.add_get("/planet-assets/{asset_name}", self._serve_planet_asset)
        if self._galactic_assets is not None:
            self._app.router.add_get(
                "/managed-galactic-assets/{resource_id}",
                self._serve_galactic_asset,
            )
        if self._raster_imports is not None:
            self._app.router.add_get(
                "/api/classification-schemes",
                self._classification_schemes,
            )
            self._app.router.add_post("/api/raster-imports", self._create_raster_import)
            self._app.router.add_put(
                "/api/raster-imports/{import_id}/files/{ordinal}",
                self._upload_raster_import_file,
            )
            self._app.router.add_post(
                "/api/raster-imports/{import_id}/inspect",
                self._inspect_raster_import,
            )
            self._app.router.add_post(
                "/api/raster-imports/{import_id}/commit",
                self._commit_raster_import,
            )
            self._app.router.add_delete(
                "/api/raster-imports/{import_id}",
                self._cancel_raster_import,
            )
        self._app.router.add_get("/", self._serve_index)
        self._app.router.add_static(
            "/", self._dist_dir, show_index=False,
        )

        self._runner = aiohttp.web.AppRunner(
            self._app,
            access_log=None,  # suprimeix els registres d'accés sorollosos
        )
        await self._runner.setup()

        try:
            self._site = aiohttp.web.TCPSite(
                self._runner, self._host, self._port, reuse_address=False,
            )
            await self._site.start()
        except OSError:
            # Si el port està ocupat, recaure en port dinàmic del SO (port=0)
            self._site = aiohttp.web.TCPSite(
                self._runner, self._host, 0, reuse_address=False,
            )
            await self._site.start()

        # Resol el port real (quan port=0, el SO n'assigna un)
        for sock in self._site._server.sockets:  # type: ignore[union-attr]
            addr = sock.getsockname()
            self._actual_port = addr[1]
            break

        log.debug("Servidor escoltant a %s", self.url)
        return self.url

    async def stop(self) -> None:
        """Atura el servidor de manera ordenada."""
        if self._site:
            await self._site.stop()
        if self._runner:
            await self._runner.cleanup()
        log.debug("Servidor aturat")

    async def _serve_index(
        self, request: aiohttp.web.Request,
    ) -> aiohttp.web.FileResponse:
        """Serveix index.html per a la ruta arrel."""
        return aiohttp.web.FileResponse(self._dist_dir / "index.html")

    async def _serve_moon_asset(
        self, request: aiohttp.web.Request,
    ) -> aiohttp.web.StreamResponse:
        """Serve only names accepted by the validated managed-layer manifest."""

        if self._moon_surface_assets is None:
            raise aiohttp.web.HTTPNotFound()
        path = self._moon_surface_assets.resolve_asset(request.match_info["asset_name"])
        if path is None:
            raise aiohttp.web.HTTPNotFound()
        response = aiohttp.web.FileResponse(path)
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        return response

    async def _serve_planet_asset(
        self, request: aiohttp.web.Request,
    ) -> aiohttp.web.StreamResponse:
        """Serve validated external textures without copying them into Git."""

        if self._solar_system_assets is None:
            raise aiohttp.web.HTTPNotFound()
        path = self._solar_system_assets.resolve_texture(request.match_info["asset_name"])
        if path is None:
            raise aiohttp.web.HTTPNotFound()
        response = aiohttp.web.FileResponse(path)
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        return response

    async def _serve_galactic_asset(
        self, request: aiohttp.web.Request,
    ) -> aiohttp.web.StreamResponse:
        """Serveix només l'asset READY resolt des del catàleg local."""

        if self._galactic_assets is None:
            raise aiohttp.web.HTTPNotFound()
        path = self._galactic_assets.resolve_asset(request.match_info["resource_id"])
        if path is None:
            raise aiohttp.web.HTTPNotFound()
        response = aiohttp.web.FileResponse(path)
        response.headers["Cache-Control"] = "private, no-cache"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        return response

    async def _create_raster_import(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        service = self._require_raster_imports()
        try:
            payload = await request.json()
            session = service.create(
                ownership=str(payload.get("ownership", "managed")),
                name=str(payload.get("name", "")),
                external_path=payload.get("externalPath"),
                file_count=int(payload.get("fileCount", 1)),
                semantic_kind=str(payload.get("semanticKind", "elevation")),
            )
            return aiohttp.web.json_response(_raster_session_json(session), status=201)
        except (RasterImportError, ValueError, TypeError, json.JSONDecodeError) as exc:
            raise aiohttp.web.HTTPBadRequest(text=str(exc)) from exc

    async def _upload_raster_import_file(
        self,
        request: aiohttp.web.Request,
    ) -> aiohttp.web.Response:
        service = self._require_raster_imports()
        import_id = request.match_info["import_id"]
        try:
            ordinal = int(request.match_info["ordinal"])
            relative_path = request.headers.get("X-TerraLab-Relative-Path", "")
            destination = service.upload_destination(import_id, ordinal, relative_path)
            temporary = destination.with_suffix(destination.suffix + ".upload")
            digest = hashlib.sha256()
            byte_size = 0
            with temporary.open("wb") as handle:
                async for chunk in request.content.iter_chunked(1024 * 1024):
                    await asyncio.to_thread(handle.write, chunk)
                    digest.update(chunk)
                    byte_size += len(chunk)
                await asyncio.to_thread(handle.flush)
            temporary.replace(destination)
            session = service.finish_upload(
                import_id,
                ordinal,
                relative_path,
                byte_size,
                digest.hexdigest(),
            )
            return aiohttp.web.json_response(_raster_session_json(session))
        except (RasterImportError, ValueError, OSError) as exc:
            raise aiohttp.web.HTTPBadRequest(text=str(exc)) from exc

    async def _inspect_raster_import(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        service = self._require_raster_imports()
        try:
            payload = await request.json()
            result = await asyncio.to_thread(
                service.inspect,
                request.match_info["import_id"],
                payload,
            )
            return aiohttp.web.json_response(result)
        except (RasterImportError, RasterDatasetError, ValueError, TypeError) as exc:
            raise aiohttp.web.HTTPBadRequest(text=str(exc)) from exc

    async def _commit_raster_import(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        service = self._require_raster_imports()
        try:
            payload = await request.json()
            result = await asyncio.to_thread(
                service.commit,
                request.match_info["import_id"],
                payload,
            )
            return aiohttp.web.json_response(result)
        except (RasterImportError, RasterDatasetError, ValueError, TypeError, OSError) as exc:
            raise aiohttp.web.HTTPBadRequest(text=str(exc)) from exc

    async def _cancel_raster_import(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        service = self._require_raster_imports()
        try:
            await asyncio.to_thread(service.cancel, request.match_info["import_id"])
            return aiohttp.web.json_response({"cancelled": True})
        except RasterImportError as exc:
            raise aiohttp.web.HTTPNotFound(text=str(exc)) from exc

    async def _classification_schemes(
        self,
        request: aiohttp.web.Request,
    ) -> aiohttp.web.Response:
        service = self._require_raster_imports()
        try:
            return aiohttp.web.json_response(service.classification_scheme_catalog())
        except RasterImportError as exc:
            raise aiohttp.web.HTTPNotFound(text=str(exc)) from exc

    def _require_raster_imports(self) -> RasterImportService:
        if self._raster_imports is None:
            raise aiohttp.web.HTTPNotFound()
        return self._raster_imports


def _raster_session_json(session: Any) -> dict[str, Any]:
    return {
        "importId": session.import_id,
        "ownership": session.ownership,
        "name": session.name,
        "externalPath": session.external_path,
        "fileCount": session.file_count,
        "state": session.state,
        "files": list(session.files),
        "inspection": session.inspection,
        "semanticKind": session.semantic_kind,
    }
