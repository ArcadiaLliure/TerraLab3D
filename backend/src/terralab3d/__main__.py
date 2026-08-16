"""Punt d'entrada de l'aplicació TerraLab3D.

Ús::

    python -m terralab3d

Seqüència:
  1. Compilar el frontend TypeScript (esbuild, una sola vegada).
  2. Iniciar el servidor aiohttp (HTTP estàtic + pont WebSocket).
  3. Obrir el navegador del sistema.
  4. Esperar el dóna-m'hi-l'anotació (handshake) del pont.
  5. Escoltar esdeveniments camera_changed, viewport_resized, etc.
  6. En Ctrl-C o tancament del navegador → demanar tancament del frontend → sortir netaient.
"""

from __future__ import annotations

import asyncio
import logging
import math
import os
import signal
import sys
import threading
import uuid
import webbrowser
from typing import Any
from datetime import datetime, timedelta, timezone

from terralab3d.domain.time.engine import AstronomicalEngine
from terralab3d.domain.time.models import ClockMode, SimulationInstant, ClockState
from terralab3d.domain.sky_background.sky_environment import SkyEnvironmentComposer
from terralab3d.domain.light_pollution.models import LightPollutionMode
from terralab3d.domain.solar_system.models import ScientificObserver, SolarSystemSnapshot
from terralab3d.domain.star_trails.models import (
    StarTrailPlaybackConfig,
    clamped_exposure_seconds,
)
from terralab3d.domain.lighting.environment import LightingEnvironmentComposer
from terralab3d.application.ephemeris_coordinator import EphemerisCoordinator
from terralab3d.application.orbit_sampler import OrbitSampler
from terralab3d.application.apparent_trajectory import (
    ApparentTrajectoryCoordinator,
    ApparentTrajectorySampler,
)
from terralab3d.application.astronomical_events import (
    AstronomicalEventSearcher,
    AstronomicalEventService,
    EventSearchCoordinator,
)
from terralab3d.application.search_coordinator import AstronomicalSearchCoordinator
from terralab3d.domain.eclipses.models import (
    AstronomicalEventEphemeris,
    EclipseKind,
    GeometryQuality,
)
from terralab3d.domain.eclipses.services import AstronomicalEventCalculator
from terralab3d.infrastructure.adapters.ephemeris.adapter import SkyfieldEphemerisAdapter
from terralab3d.infrastructure.adapters.ephemeris.spice_adapter import SpiceEphemerisAdapter
from terralab3d.domain.terrain.models import TerrainChunkIdentity

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("terralab3d")

SIMULATION_TICK_INTERVAL_SEC = 1.0  # 1 update per second for stable base ephemeris
VISUAL_STREAM_MIN_SPEED_MPS = 0.5

async def run() -> int:
    """Punt d'entrada asíncron principal."""
    from terralab3d.infrastructure.bundler import bundle_frontend
    from terralab3d.infrastructure.server import TerraLabServer
    from terralab3d.infrastructure.websocket_bridge import WebSocketBridge
    from terralab3d.infrastructure.adapters.file_assets.moon_surface import ManagedMoonSurfaceAssets
    from terralab3d.infrastructure.adapters.file_assets.solar_system import ManagedSolarSystemAssets
    from terralab3d.infrastructure.adapters.file_assets.lunar_limb import LroLolaLimbProfileProvider
    from terralab3d.infrastructure.adapters.file_assets.galactic import ManagedGalacticAssets
    from terralab3d.infrastructure.adapters.planck.adapter import PlanckDustAdapter
    from terralab3d.infrastructure.adapters.ngc_catalog.adapter import NgcCatalogPostProcessor, NgcCatalogAdapter
    from terralab3d.infrastructure.resources.catalog import ResourceCatalog
    from terralab3d.infrastructure.resources.installation_repository import ResourceInstallationRepository
    from terralab3d.infrastructure.resources.download_manager import DownloadJobManager
    from terralab3d.domain.identifiers import ResourceId, VariantId

    # ── 1. Compilar frontend i inicialitzar assets de dades ───────────
    try:
        dist_dir = bundle_frontend()
    except Exception as exc:
        log.error("La meva construcció del frontend ha fallat: %s", exc)
        return 1

    # ── 2. Crear pont i servidor ──────────────────────────────────────
    bridge = WebSocketBridge()
    moon_surface_assets = ManagedMoonSurfaceAssets()
    solar_system_assets = ManagedSolarSystemAssets()
    resource_catalog = ResourceCatalog()
    resource_repo = ResourceInstallationRepository()
    resource_repo.discover_existing_resources()
    galactic_assets = ManagedGalacticAssets(resource_repo)
    download_manager = DownloadJobManager(
        resource_catalog,
        resource_repo,
        bridge,
        post_processors={
            ResourceId("sky.planck_dust"): PlanckDustAdapter(),
            ResourceId("sky.ngc"): NgcCatalogPostProcessor(),
        },
    )
    server = TerraLabServer(
        dist_dir,
        bridge,
        moon_surface_assets,
        solar_system_assets,
        galactic_assets,
    )

    from terralab3d.application.deep_sky_coordinator import DeepSkyCoordinator
    deep_sky_adapter = NgcCatalogAdapter(resource_repo)
    deep_sky_coordinator = DeepSkyCoordinator(deep_sky_adapter)
    deep_sky_coordinator.set_publishers(bridge.send_binary_resource)

    loop = asyncio.get_running_loop()
    shutdown_requested = asyncio.Event()

    # Registrar manegadors de missatges del pont
    bridge.on("camera_changed", _on_camera_changed)
    bridge.on("viewport_resized", _on_viewport_resized)
    bridge.on("bridge_error", _on_bridge_error)

    # ── 2.5. Gestor Unificat de Recursos ──────────────────────────────
    def _handle_request_catalog_snapshot(data: dict[str, Any]) -> None:
        payload = {
            "descriptors": [d.to_dict() for d in resource_catalog.get_all_descriptors()],
            "installedStates": resource_repo.snapshot(),
        }
        asyncio.create_task(bridge.send_resource_catalog_snapshot(payload))

    def _handle_request_resource_download(data: dict[str, Any]) -> None:
        resource_id = data.get("resourceId")
        variant_id = data.get("variantId")
        if resource_id and variant_id:
            download_manager.start_download(ResourceId(resource_id), VariantId(variant_id))

    def _handle_pause_download(data: dict[str, Any]) -> None:
        resource_id = data.get("resourceId")
        variant_id = data.get("variantId")
        if resource_id and variant_id:
            download_manager.pause_download(ResourceId(resource_id), VariantId(variant_id))

    def _handle_cancel_download(data: dict[str, Any]) -> None:
        resource_id = data.get("resourceId")
        variant_id = data.get("variantId")
        if resource_id and variant_id:
            download_manager.cancel_download(ResourceId(resource_id), VariantId(variant_id))

    def _handle_delete_resource(data: dict[str, Any]) -> None:
        resource_id = data.get("resourceId")
        variant_id = data.get("variantId")
        if resource_id and variant_id:
            download_manager.delete_resource(ResourceId(resource_id), VariantId(variant_id))

    bridge.on("request_catalog_snapshot", _handle_request_catalog_snapshot)
    bridge.on("request_resource_download", _handle_request_resource_download)
    bridge.on("pause_download", _handle_pause_download)
    bridge.on("cancel_download", _handle_cancel_download)
    bridge.on("delete_resource", _handle_delete_resource)

    # ── 3. Lògica d'Ubicació (Fase 2) ─────────────────────────────────
    from terralab3d.domain.observer.models import GeoLocation, ObserverProfile
    from terralab3d.domain.identifiers import ObserverId
    from terralab3d.domain.horizon.models import (
        EARTH_RADIUS_M,
        OBSERVER_EYE_HEIGHT_M,
        HorizonProfileSettings,
        HorizonRangeMode,
        HorizonRequest,
    )
    from terralab3d.domain.horizon.calculations import resolve_visible_radius_m
    from terralab3d.application.elevation_coordinator import ElevationCoordinator
    from terralab3d.application.flight_terrain_refresh import (
        decide_flight_profile_refresh,
        decide_flight_stream_continuation,
        decide_visibility_window_refresh,
    )
    from terralab3d.application.horizon_coordinator import HorizonCoordinator, pack_terrain_mesh
    from terralab3d.application.land_cover_coordinator import LandCoverCoordinator
    from terralab3d.infrastructure.adapters.landcover.adapter import RasterLandCoverAdapter
    from terralab3d.domain.surface.models import SurfaceStyle
    from terralab3d.application.terrain_mesh_builder import TerrainMeshBuilder
    from terralab3d.infrastructure.adapters.dem import (
        PyprojAeqdProjector,
        RasterioElevationAdapter,
    )
    from terralab3d.infrastructure.adapters.dem.adapter import DemSamplingCancelled

    current_observer = ObserverProfile(
        observer_id=ObserverId("default"),
        location=GeoLocation(latitude_deg=41.21240330896238, longitude_deg=0.8072721734579367),
        height_offset_m=0.0
    )
    observer_generation = 1
    elevation_source = "no disponible — horitzó pla fallback"
    elevation_adapter = RasterioElevationAdapter.from_configured_library()
    elevation_coordinator = ElevationCoordinator(elevation_adapter)
    horizon_settings = HorizonProfileSettings()
    horizon_enabled = True
    horizon_request_generation = 0
    horizon_settings_generation = 1
    elevation_task: asyncio.Task[None] | None = None
    terrain_horizon_view: ObserverProfile | None = None
    navigation_hud_view: ObserverProfile | None = None
    terrain_horizon_generation = observer_generation
    camera_horizon_projector = PyprojAeqdProjector()
    # Global ENU origin of the wide resident mesh. Flight moves the camera in
    # this world; it does not silently redefine the terrain coordinate frame.
    terrain_world_observer = current_observer

    def observer_distance_m(first: ObserverProfile, second: ObserverProfile) -> float:
        latitude_delta_m = (first.location.latitude_deg - second.location.latitude_deg) * 111_320.0
        longitude_delta_m = (
            (first.location.longitude_deg - second.location.longitude_deg)
            * 111_320.0
            * math.cos(math.radians(first.location.latitude_deg))
        )
        return math.hypot(latitude_delta_m, longitude_delta_m)

    async def publish_horizon_profile(metadata: dict[str, object], payload: bytes) -> int:
        await bridge.send_binary_resource(
            str(metadata["resourceId"]),
            str(metadata["version"]),
            metadata,
            payload,
        )
        return len(payload)

    land_cover_adapter = RasterLandCoverAdapter()
    async def publish_surface_resource(metadata: dict[str, object], payload: bytes) -> int | None:
        if bridge.connected:
            await bridge.send_binary_resource(
                str(metadata.get("resourceId", "earth.terrain.surface")),
                str(metadata.get("version", metadata.get("generation", 0))),
                metadata,
                payload,
            )
            return len(payload)
        return 0

    land_cover_coordinator = LandCoverCoordinator(
        land_cover_port=land_cover_adapter,
        surface_publisher=publish_surface_resource,
        status_publisher=bridge.send_surface_status,
        legend_publisher=bridge.send_surface_legend,
    )

    horizon_coordinator = HorizonCoordinator(
        elevation_adapter,
        PyprojAeqdProjector(),
        publish_horizon_profile,
        bridge.send_horizon_status,
        land_cover_coordinator=land_cover_coordinator,
    )

    terrain_stream_builder = TerrainMeshBuilder(elevation_adapter, camera_horizon_projector)
    terrain_stream_task: asyncio.Task[None] | None = None
    terrain_stream_cancel: threading.Event | None = None
    terrain_stream_generation = 0
    terrain_stream_center_east_m = 0.0
    terrain_stream_center_north_m = 0.0
    terrain_stream_radius_m = 0.0
    terrain_stream_velocity_east_mps = 0.0
    terrain_stream_velocity_north_mps = 0.0
    navigation_pose_east_m = 0.0
    navigation_pose_north_m = 0.0
    navigation_velocity_east_mps = 0.0
    navigation_velocity_north_mps = 0.0
    navigation_speed_mps = 0.0
    terrain_regeneration_task: asyncio.Task[None] | None = None
    terrain_regeneration_generation = 0

    def new_horizon_request(
        *,
        force_recalculate: bool = False,
        build_terrain_mesh: bool = True,
        observer: ObserverProfile | None = None,
    ) -> HorizonRequest:
        nonlocal horizon_request_generation
        horizon_request_generation += 1
        profile_observer = (
            observer
            or (
                terrain_world_observer
                if build_terrain_mesh
                else terrain_horizon_view or navigation_hud_view or current_observer
            )
        )
        profile_generation = (
            observer_generation
            if build_terrain_mesh
            else terrain_horizon_generation
            if terrain_horizon_view is not None
            else observer_generation
        )
        return HorizonRequest(
            request_id=f"horizon-{horizon_request_generation}-{uuid.uuid4().hex[:8]}",
            generation=horizon_request_generation,
            observer_generation=profile_generation,
            settings_generation=horizon_settings_generation,
            latitude_deg=profile_observer.location.latitude_deg,
            longitude_deg=profile_observer.location.longitude_deg,
            terrain_elevation_m=profile_observer.location.elevation_m,
            height_offset_m=profile_observer.height_offset_m,
            settings=horizon_settings,
            force_recalculate=force_recalculate,
            build_terrain_mesh=build_terrain_mesh,
        )

    def cancel_visual_stream(*, reset_center: bool) -> None:
        """Invalidate a background detail build without disturbing the wide mesh."""

        nonlocal terrain_stream_cancel, terrain_stream_generation
        nonlocal terrain_stream_center_east_m, terrain_stream_center_north_m
        nonlocal terrain_stream_radius_m
        nonlocal terrain_stream_velocity_east_mps, terrain_stream_velocity_north_mps
        terrain_stream_generation += 1
        if terrain_stream_cancel is not None:
            terrain_stream_cancel.set()
        terrain_stream_cancel = None
        if reset_center:
            terrain_stream_center_east_m = 0.0
            terrain_stream_center_north_m = 0.0
            terrain_stream_radius_m = 0.0
            terrain_stream_velocity_east_mps = 0.0
            terrain_stream_velocity_north_mps = 0.0

    def visual_stream_lead_distance_m(speed_mps: float) -> float:
        """Lead distance from measured mesh preparation, bounded for stable swaps."""

        metrics = horizon_coordinator.metrics()
        prepare_seconds = max(
            float(metrics.get("terrainMeshBuildP95Ms", 0.0)),
            float(metrics.get("terrainMeshBuildP50Ms", 0.0)),
            1_000.0,
        ) / 1_000.0
        lead_seconds = min(35.0, max(8.0, prepare_seconds * 3.0))
        return min(10_000.0, max(1_500.0, speed_mps * lead_seconds))

    async def request_visual_stream_chunk(
        east_m: float,
        north_m: float,
        velocity_east_mps: float,
        velocity_north_mps: float,
        speed_mps: float,
        observer: ObserverProfile,
        *,
        force: bool = False,
    ) -> None:
        """Prepare the configured observer-centred range without clearing old meshes."""

        nonlocal terrain_stream_task, terrain_stream_cancel, terrain_stream_generation
        nonlocal terrain_stream_center_east_m, terrain_stream_center_north_m
        nonlocal terrain_stream_radius_m
        nonlocal terrain_stream_velocity_east_mps, terrain_stream_velocity_north_mps
        if not force and speed_mps < VISUAL_STREAM_MIN_SPEED_MPS:
            return
        profile = horizon_coordinator.active_profile
        if (
            profile is None
            or terrain_world_observer.location.elevation_m is None
            or profile.terrain_elevation_m is None
        ):
            return
        observer_eye_m = observer.effective_height_m + OBSERVER_EYE_HEIGHT_M
        requested_radius_m = resolve_visible_radius_m(horizon_settings, observer_eye_m)
        lead_distance_m = visual_stream_lead_distance_m(speed_mps)
        if terrain_stream_task is not None and not terrain_stream_task.done():
            # A normal sweep keeps useful in-flight work. Explicit regeneration
            # is the exception: it must replace a build made with stale UI settings.
            if force:
                decision_reason = "forced"
            else:
                continuation = decide_flight_stream_continuation(
                    active_velocity_east_mps=terrain_stream_velocity_east_mps,
                    active_velocity_north_mps=terrain_stream_velocity_north_mps,
                    current_velocity_east_mps=velocity_east_mps,
                    current_velocity_north_mps=velocity_north_mps,
                )
                if continuation.keep_active_build or terrain_stream_cancel is None:
                    return
                decision_reason = continuation.reason
            active_task = terrain_stream_task
            cancel_visual_stream(reset_center=False)
            log.info(
                "MGP: [__main__.py] [visual_stream] "
                "[cancel·lat chunk inservible reason=%s]",
                decision_reason,
            )
            try:
                await active_task
            except asyncio.CancelledError:
                pass

        distance_to_center_m = math.hypot(
            east_m - terrain_stream_center_east_m,
            north_m - terrain_stream_center_north_m,
        )
        if terrain_stream_radius_m <= 0.0:
            # The first completed wide mesh is centred at the world origin.
            terrain_stream_radius_m = profile.visible_radius_m
        window_decision = decide_visibility_window_refresh(
            distance_from_loaded_center_m=distance_to_center_m,
            loaded_radius_m=terrain_stream_radius_m,
            requested_radius_m=requested_radius_m,
            lead_distance_m=lead_distance_m,
            force=force,
        )
        if not window_decision.should_refresh:
            return

        terrain_stream_generation += 1
        generation = terrain_stream_generation
        cancel_event = threading.Event()
        terrain_stream_cancel = cancel_event
        terrain_stream_velocity_east_mps = velocity_east_mps
        terrain_stream_velocity_north_mps = velocity_north_mps
        # Prediction decides when to start. The scientific and visual centre
        # is always the observer position that caused this sweep.
        target_east_m = east_m
        target_north_m = north_m
        terrain_request = HorizonRequest(
            request_id=f"terrain-stream-{generation}-{uuid.uuid4().hex[:8]}",
            generation=generation,
            observer_generation=observer_generation,
            settings_generation=horizon_settings_generation,
            latitude_deg=terrain_world_observer.location.latitude_deg,
            longitude_deg=terrain_world_observer.location.longitude_deg,
            terrain_elevation_m=terrain_world_observer.location.elevation_m,
            height_offset_m=terrain_world_observer.height_offset_m,
            settings=horizon_settings,
            build_terrain_mesh=True,
        )

        async def build_and_publish() -> None:
            nonlocal terrain_stream_center_east_m, terrain_stream_center_north_m
            nonlocal terrain_stream_radius_m
            try:
                terrain = await asyncio.to_thread(
                    terrain_stream_builder.build,
                    terrain_request,
                    profile,
                    cancel_event,
                    None,
                    center_east_m=target_east_m,
                    center_north_m=target_north_m,
                    visual_radius_m=requested_radius_m,
                )
            except DemSamplingCancelled:
                return
            except Exception:
                log.exception(
                    "MGP: [__main__.py] [visual_stream] [No s'ha pogut preparar el bloc DEM]"
                )
                return
            if generation != terrain_stream_generation or cancel_event.is_set():
                return
            metadata, payload = pack_terrain_mesh(
                profile,
                terrain,
                role="terrain_stream_chunk",
                resource_id="earth.terrain.stream",
            )
            metadata.update({
                "version": generation,
                "contentKey": f"terrain-stream-{generation}",
                "visibleRadiusM": requested_radius_m,
                "latitudeDeg": observer.location.latitude_deg,
                "longitudeDeg": observer.location.longitude_deg,
                "settingsGeneration": terrain_request.settings_generation,
                "streamCenterEastM": target_east_m,
                "streamCenterNorthM": target_north_m,
                "streamLeadDistanceM": lead_distance_m,
            })
            await bridge.send_binary_resource(
                "earth.terrain.stream", str(generation), metadata, payload,
            )
            if generation != terrain_stream_generation or cancel_event.is_set():
                return
            terrain_stream_center_east_m = target_east_m
            terrain_stream_center_north_m = target_north_m
            terrain_stream_radius_m = requested_radius_m
            log.info(
                "MGP: [__main__.py] [visual_stream] "
                "[chunk=%d reason=%s radius_km=%.1f center_east_m=%.1f "
                "center_north_m=%.1f lead_m=%.1f vertices=%d]",
                generation,
                window_decision.reason,
                requested_radius_m / 1_000.0,
                target_east_m,
                target_north_m,
                lead_distance_m,
                terrain.vertex_count,
            )

        terrain_stream_task = asyncio.create_task(
            build_and_publish(), name=f"terrain-visual-stream-{generation}",
        )

    async def broadcast_location(
        observer: ObserverProfile | None = None,
        *,
        source: str | None = None,
        navigation: bool = False,
    ) -> None:
        visible_observer = observer or current_observer
        await bridge.send_observer_location_changed(
            lat=visible_observer.location.latitude_deg,
            lon=visible_observer.location.longitude_deg,
            elevation=visible_observer.location.elevation_m,
            effective_height=(
                visible_observer.effective_height_m + OBSERVER_EYE_HEIGHT_M
                if visible_observer.location.elevation_m is not None
                else None
            ),
            source=source or elevation_source,
            height_offset=visible_observer.height_offset_m,
            navigation=navigation,
        )

    async def resolve_current_elevation(expected: ObserverProfile) -> None:
        nonlocal current_observer, observer_generation, elevation_source
        nonlocal terrain_horizon_view, navigation_hud_view, terrain_horizon_generation
        nonlocal terrain_world_observer, terrain_stream_radius_m
        result = await elevation_coordinator.resolve(expected.location)
        if result is None or current_observer != expected:
            return
        sample = result.sample
        if not sample.available:
            elevation_source = "no disponible — horitzó pla fallback"
            await broadcast_location()
            return
        current_observer = ObserverProfile(
            observer_id=expected.observer_id,
            location=GeoLocation(
                expected.location.latitude_deg,
                expected.location.longitude_deg,
                sample.elevation_m,
            ),
            height_offset_m=expected.height_offset_m,
        )
        elevation_source = sample.source_id or "DEM"
        observer_generation += 1
        # This is the profile/mesh anchor. Camera motion updates HUD state, but
        # must never turn a stopped walking observer into a terrain request.
        terrain_world_observer = current_observer
        terrain_horizon_view = current_observer
        navigation_hud_view = None
        terrain_horizon_generation = observer_generation
        await horizon_coordinator.activate_observer_fallback(new_horizon_request())
        await broadcast_location()
        await broadcast_time(force_celestial_transform=True)
        if horizon_enabled:
            horizon_coordinator.request(new_horizon_request())
            terrain_stream_radius_m = resolve_visible_radius_m(
                horizon_settings,
                current_observer.effective_height_m + OBSERVER_EYE_HEIGHT_M,
            )
        log.info(
            "MGP: [__main__.py] [resolve_current_elevation] "
            "[Elevació DEM real elevation_m=%.2f source=%s observer_generation=%d duration_ms=%.2f]",
            sample.elevation_m,
            elevation_source,
            observer_generation,
            result.duration_ms,
        )

    async def _handle_set_location(data: dict[str, Any]) -> None:
        nonlocal current_observer, observer_generation, elevation_source, elevation_task
        nonlocal terrain_horizon_view, navigation_hud_view, terrain_horizon_generation, terrain_world_observer
        nonlocal terrain_regeneration_task, terrain_regeneration_generation
        try:
            lat = float(data.get("lat", 0.0))
            lon = float(data.get("lon", 0.0))
            height = float(data.get("extraHeight", 0.0))

            loc = GeoLocation(latitude_deg=lat, longitude_deg=lon)
            current_observer = ObserverProfile(
                observer_id=current_observer.observer_id,
                location=loc,
                height_offset_m=height
            )
            observer_generation += 1
            terrain_world_observer = current_observer
            terrain_horizon_view = None
            navigation_hud_view = None
            terrain_horizon_generation = observer_generation
            elevation_source = "consultant DEM…"
            elevation_coordinator.cancel()
            horizon_coordinator.cancel()
            cancel_visual_stream(reset_center=True)
            terrain_regeneration_generation += 1
            if terrain_regeneration_task is not None and not terrain_regeneration_task.done():
                terrain_regeneration_task.cancel()
            await horizon_coordinator.activate_observer_fallback(new_horizon_request())
            await broadcast_location()
            await broadcast_time()
            elevation_task = asyncio.create_task(
                resolve_current_elevation(current_observer),
                name="bare-elevation-latest-wins",
            )
            log.info(
                "Ubicació de l'observador actualitzada a: %.4f, %.4f (alt: %.1f)",
                current_observer.location.latitude_deg,
                current_observer.location.longitude_deg,
                height,
            )
        except Exception as e:
            await bridge.send_location_error(str(e))
            log.warning("Error a l'actualitzar la ubicació: %s", e)

    def request_horizon_for_live_observer(*, force_recalculate: bool) -> tuple[ObserverProfile, int, bool] | None:
        """Capture one immutable live centre for the next scientific sweep."""

        nonlocal terrain_horizon_view, terrain_horizon_generation
        nonlocal terrain_stream_radius_m
        live_observer = navigation_hud_view or terrain_horizon_view or current_observer
        if live_observer.location.elevation_m is None:
            return None
        retain_world_mesh = horizon_coordinator.has_active_terrain
        if retain_world_mesh:
            terrain_horizon_view = live_observer
            terrain_horizon_generation += 1
            horizon_coordinator.request(new_horizon_request(
                force_recalculate=force_recalculate,
                build_terrain_mesh=False,
                observer=live_observer,
            ))
            return live_observer, terrain_horizon_generation, True
        horizon_coordinator.request(new_horizon_request(
            force_recalculate=force_recalculate,
            build_terrain_mesh=True,
            observer=terrain_world_observer,
        ))
        terrain_stream_radius_m = resolve_visible_radius_m(
            horizon_settings,
            terrain_world_observer.effective_height_m + OBSERVER_EYE_HEIGHT_M,
        )
        return live_observer, observer_generation, False

    async def regenerate_live_visibility(
        generation: int,
        live_observer: ObserverProfile,
        profile_observer_generation: int,
        retain_world_mesh: bool,
        east_m: float,
        north_m: float,
        velocity_east_mps: float,
        velocity_north_mps: float,
        speed_mps: float,
    ) -> None:
        """Finish the forced live profile, then add its configured visual range."""

        try:
            await horizon_coordinator.wait_idle()
            if generation != terrain_regeneration_generation or not retain_world_mesh:
                return
            profile = horizon_coordinator.active_profile
            if profile is None or profile.observer_generation != profile_observer_generation:
                return
            await request_visual_stream_chunk(
                east_m,
                north_m,
                velocity_east_mps,
                velocity_north_mps,
                speed_mps,
                live_observer,
                force=True,
            )
        except asyncio.CancelledError:
            return

    # ── 3.1. Lògica d'Estrelles (Fase 5 i Pas 6) ─────────────────────
    async def _handle_set_horizon_settings(data: dict[str, Any]) -> None:
        nonlocal horizon_settings, horizon_settings_generation, horizon_enabled
        nonlocal terrain_regeneration_task, terrain_regeneration_generation
        try:
            horizon_enabled = bool(data.get("enabled", horizon_enabled))
            horizon_settings = HorizonProfileSettings(
                range_mode=HorizonRangeMode(str(data.get("rangeMode", horizon_settings.range_mode.value))),
                visible_radius_km=float(data.get("visibleRadiusKm", horizon_settings.visible_radius_km)),
                angular_step_deg=float(data.get("angularStepDeg", horizon_settings.angular_step_deg)),
                atmospheric_refraction_enabled=bool(
                    data.get("atmosphericRefractionEnabled", horizon_settings.atmospheric_refraction_enabled)
                ),
                effective_earth_radius_factor=float(
                    data.get("effectiveEarthRadiusFactor", horizon_settings.effective_earth_radius_factor)
                ),
                max_samples_per_ray=int(data.get("maxSamplesPerRay", horizon_settings.max_samples_per_ray)),
                memory_budget_bytes=int(data.get("memoryBudgetBytes", horizon_settings.memory_budget_bytes)),
            ).validated()
            horizon_settings_generation += 1
            terrain_regeneration_generation += 1
            if terrain_regeneration_task is not None and not terrain_regeneration_task.done():
                terrain_regeneration_task.cancel()
            if horizon_enabled and current_observer.location.elevation_m is not None:
                request_horizon_for_live_observer(force_recalculate=False)
            else:
                horizon_coordinator.cancel()
                await horizon_coordinator.activate_observer_fallback(new_horizon_request())
        except (TypeError, ValueError) as exc:
            await bridge.send_horizon_status({
                "type": "horizon_status",
                "phase": "error",
                "message": str(exc),
                "generation": horizon_request_generation,
                "observerGeneration": observer_generation,
                "settingsGeneration": horizon_settings_generation,
                "progress": None,
            })

    async def _handle_recalculate_horizon(data: dict[str, Any]) -> None:
        nonlocal terrain_regeneration_task, terrain_regeneration_generation
        if horizon_enabled and current_observer.location.elevation_m is not None:
            requested = request_horizon_for_live_observer(force_recalculate=True)
            if requested is None:
                return
            live_observer, profile_generation, retain_world_mesh = requested
            terrain_regeneration_generation += 1
            generation = terrain_regeneration_generation
            if terrain_regeneration_task is not None and not terrain_regeneration_task.done():
                terrain_regeneration_task.cancel()
            terrain_regeneration_task = asyncio.create_task(
                regenerate_live_visibility(
                    generation,
                    live_observer,
                    profile_generation,
                    retain_world_mesh,
                    navigation_pose_east_m,
                    navigation_pose_north_m,
                    navigation_velocity_east_mps,
                    navigation_velocity_north_mps,
                    navigation_speed_mps,
                ),
                name=f"terrain-live-regeneration-{generation}",
            )
        else:
            await horizon_coordinator.activate_observer_fallback(new_horizon_request())

    async def _handle_cancel_horizon(data: dict[str, Any]) -> None:
        nonlocal terrain_regeneration_task, terrain_regeneration_generation
        terrain_regeneration_generation += 1
        if terrain_regeneration_task is not None and not terrain_regeneration_task.done():
            terrain_regeneration_task.cancel()
        horizon_coordinator.cancel()

    async def _handle_camera_pose_changed(data: dict[str, Any]) -> None:
        """Refresh observer-centred visibility after meaningful navigation.

        The navigation camera remains local to the already uploaded world mesh.
        Movement nevertheless changes the eye point used by the horizon and
        celestial visibility calculations. New configured-radius chunks are
        added predictively; stopping by itself never starts a rebuild.
        """

        nonlocal terrain_horizon_view, navigation_hud_view, terrain_horizon_generation
        nonlocal navigation_pose_east_m, navigation_pose_north_m
        nonlocal navigation_velocity_east_mps, navigation_velocity_north_mps
        nonlocal navigation_speed_mps
        if current_observer.location.elevation_m is None:
            return
        try:
            mode = str(data.get("navigationMode", "walk"))
            east_m = float(data.get("positionEastM", 0.0))
            north_m = float(data.get("positionNorthM", 0.0))
            up_m = float(data.get("positionUpM", 0.0))
            requested_speed_mps = max(0.0, float(data.get("speedMps", 0.0)))
            velocity_east_mps = float(data.get("velocityEastMps", 0.0))
            velocity_north_mps = float(data.get("velocityNorthMps", 0.0))
        except (TypeError, ValueError):
            return
        if not all(math.isfinite(value) for value in (
            east_m, north_m, up_m, requested_speed_mps,
            velocity_east_mps, velocity_north_mps,
        )):
            return
        navigation_pose_east_m = east_m
        navigation_pose_north_m = north_m
        navigation_velocity_east_mps = velocity_east_mps
        navigation_velocity_north_mps = velocity_north_mps
        navigation_speed_mps = requested_speed_mps
        horizontal_m = math.hypot(east_m, north_m)
        base_ground_m = float(current_observer.location.elevation_m)
        azimuth_deg = math.degrees(math.atan2(east_m, north_m)) % 360.0
        latitude, longitude = camera_horizon_projector.project(
            current_observer.location.latitude_deg,
            current_observer.location.longitude_deg,
            azimuth_deg,
            horizontal_m,
        )
        flight_location = GeoLocation(float(latitude), float(longitude))
        # GPS position is cheap to derive from the local ENU pose. Publish it
        # immediately; the slower DEM elevation lookup below must not freeze
        # the observer coordinates shown in the HUD.
        await bridge.send_navigation_coordinates_changed(
            flight_location.latitude_deg,
            flight_location.longitude_deg,
        )
        sample = await asyncio.to_thread(elevation_adapter.elevation, flight_location)
        if not sample.available or sample.elevation_m is None:
            return
        effective_radius_m = EARTH_RADIUS_M * (
            horizon_settings.effective_earth_radius_factor
            if horizon_settings.atmospheric_refraction_enabled
            else 1.0
        )
        theta = min(horizontal_m / effective_radius_m, math.pi * 0.5)
        terrain_local_up_m = (
            (effective_radius_m + float(sample.elevation_m)) * math.cos(theta)
            - (effective_radius_m + base_ground_m)
        )
        camera_clearance_m = up_m - terrain_local_up_m
        height_offset_m = camera_clearance_m - OBSERVER_EYE_HEIGHT_M
        next_view = ObserverProfile(
            observer_id=current_observer.observer_id,
            location=GeoLocation(flight_location.latitude_deg, flight_location.longitude_deg, sample.elevation_m),
            height_offset_m=height_offset_m,
        )

        previous_hud = navigation_hud_view
        if previous_hud is None or observer_distance_m(next_view, previous_hud) >= 10.0 or (
            abs(next_view.effective_height_m - previous_hud.effective_height_m) >= 2.0
        ):
            navigation_hud_view = next_view
            await broadcast_location(
                next_view,
                source=sample.source_id or elevation_source,
                navigation=True,
            )

        # The first request owns the base world mesh. A predictive
        # profile-only navigation request is allowed only after that mesh is
        # resident; otherwise it can supersede the initial build and leave a
        # real horizon profile with no visible DEM mesh.
        if not horizon_coordinator.has_active_terrain:
            return

        previous = terrain_horizon_view
        if previous is None:
            # An initial full terrain request owns the first profile. Do not
            # cancel it just because the camera has started moving.
            return
        await request_visual_stream_chunk(
            east_m,
            north_m,
            velocity_east_mps,
            velocity_north_mps,
            requested_speed_mps,
            next_view,
        )
        coordinator_metrics = horizon_coordinator.metrics()
        measured_prepare_ms = max(
            float(coordinator_metrics.get("horizonBakeP50Ms", 0.0)),
            float(coordinator_metrics.get("terrainMeshBuildP50Ms", 0.0)),
        )
        decision = decide_flight_profile_refresh(
            distance_since_profile_m=observer_distance_m(next_view, previous),
            eye_delta_m=abs(next_view.effective_height_m - previous.effective_height_m),
            speed_mps=requested_speed_mps,
            measured_prepare_ms=measured_prepare_ms,
        )
        if not decision.should_refresh:
            return
        # While a scientific navigation profile is baking, retain it. Sending a
        # second request here would make HorizonCoordinator cancel and restart
        # the same work whenever the aircraft reaches the lead boundary.
        if horizon_coordinator.is_busy:
            return
        terrain_horizon_view = next_view
        terrain_horizon_generation += 1
        if horizon_enabled:
            horizon_coordinator.request(new_horizon_request(build_terrain_mesh=False))
        log.info(
            "MGP: [__main__.py] [navigation_horizon] "
            "[perfil predictiu mode=%s reason=%s lead_m=%.1f east_m=%.1f "
            "north_m=%.1f eye_m=%.1f radius_km=%.1f]",
            mode,
            decision.reason,
            decision.lead_distance_m,
            east_m,
            north_m,
            next_view.effective_height_m + OBSERVER_EYE_HEIGHT_M,
            resolve_visible_radius_m(
                horizon_settings,
                next_view.effective_height_m + OBSERVER_EYE_HEIGHT_M,
            ) / 1_000.0,
        )

    bridge.on("set_horizon_settings", _handle_set_horizon_settings)
    bridge.on("recalculate_horizon", _handle_recalculate_horizon)
    bridge.on("cancel_horizon", _handle_cancel_horizon)
    bridge.on("camera_pose_changed", _handle_camera_pose_changed)

    async def _handle_request_surface_catalog(data: dict[str, Any]) -> None:
        log.info("MGP: Backend (__main__.py:%d: _handle_request_surface_catalog -> Sol·licitud catàleg superfície)", sys._getframe().f_lineno)
        catalog = land_cover_adapter.metadata()
        if bridge.connected:
            await bridge.send_surface_catalog({
                "sources": [
                    {
                        "id": d.id,
                        "name": d.name,
                        "sourceType": d.source_type.value,
                        "resolutionM": d.resolution_m,
                        "priority": d.priority,
                        "attribution": getattr(d, "attribution", ""),
                        "enabled": True
                    } for d in catalog
                ]
            })

    async def _handle_set_surface_source(data: dict[str, Any]) -> None:
        source_id = data.get("sourceId")
        log.info("MGP: Backend (__main__.py:%d: _handle_set_surface_source -> Seleccionar font de cobertura: %s)", sys._getframe().f_lineno, source_id)
        land_cover_coordinator.set_selected_source(source_id)
        horizon_coordinator.request(new_horizon_request())

    async def _handle_set_surface_style(data: dict[str, Any]) -> None:
        mode = data.get("style", data.get("mode"))
        log.info("MGP: Backend (__main__.py:%d: _handle_set_surface_style -> Mode superfície: %s)", sys._getframe().f_lineno, mode)
        if mode == "categorical_original":
            land_cover_coordinator.set_style(SurfaceStyle.CATEGORICAL_ORIGINAL)
        else:
            land_cover_coordinator.set_style(SurfaceStyle.BASE)
        
        # Enviar confirmació immediata del canvi de mode al frontend
        status = land_cover_coordinator.status()
        if bridge.connected:
            await bridge.send_surface_status(status)
        
        horizon_coordinator.request(new_horizon_request())

    bridge.on("request_surface_catalog", _handle_request_surface_catalog)
    bridge.on("set_surface_source", _handle_set_surface_source)
    bridge.on("set_surface_mode", _handle_set_surface_style)

    from terralab3d.application.star_coordinator import StarCoordinator
    from terralab3d.application.star_pick_resolver import StarPickResolver
    from terralab3d.domain.stars.star_pick_models import StarPickRequest
    
    star_pick_resolver = StarPickResolver()
    star_coordinator = StarCoordinator()
    star_coordinator.set_pick_resolver(star_pick_resolver)
    star_coordinator.set_publishers(
        resource_publisher=bridge.send_binary_resource,
        status_publisher=bridge.send_star_catalog_status,
        transform_publisher=bridge.send_celestial_frame_transform,
    )

    async def _handle_resolve_star_pick(data: dict[str, Any]) -> None:
        try:
            req = StarPickRequest(
                request_id=data["requestId"],
                generation=int(data["generation"]),
                resource_id=data["resourceId"],
                resource_version=data["resourceVersion"],
                catalog_index=int(data["catalogIndex"]),
                purpose=data["purpose"],
            )
            resp = star_pick_resolver.resolve(req)
            star_dict = None
            if resp.resolved:
                star_dict = {
                    "kind": "star",
                    "resourceId": resp.resolved.resource_id,
                    "resourceVersion": resp.resolved.version,
                    "catalogIndex": resp.resolved.catalog_index,
                    "sourceId": str(resp.resolved.source_id),
                    "raDeg": resp.resolved.ra_deg,
                    "decDeg": resp.resolved.dec_deg,
                    "magnitude": resp.resolved.magnitude,
                    "bpRp": resp.resolved.bp_rp,
                    "sourceRole": resp.resolved.source_role,
                }
            await bridge.send_star_pick_resolved(
                request_id=resp.request_id,
                generation=resp.generation,
                status=resp.status,
                star_data=star_dict,
            )
        except Exception as e:
            log.error("MGP: [__main__] [Error resolvent pick: %s]", e)

    async def _on_frontend_ready(data: dict[str, Any]) -> None:
        nonlocal elevation_task
        # Quan el frontend es connecta, enviem la ubicació inicial, iniciem estrelles, etc.
        if horizon_coordinator.active_profile is None:
            await horizon_coordinator.activate_observer_fallback(new_horizon_request())
        else:
            await horizon_coordinator.publish_active()
        await broadcast_location()
        await bridge.send_moon_surface_resource(moon_surface_assets.descriptor)
        await bridge.send_planet_texture_manifest(solar_system_assets.descriptor)
        await bridge.send_satellite_catalog_manifest(solar_system_assets.descriptor)
        await broadcast_time(force_celestial_transform=True)
        if current_observer.location.elevation_m is None and (
            elevation_task is None or elevation_task.done()
        ):
            elevation_task = asyncio.create_task(
                resolve_current_elevation(current_observer),
                name="bare-elevation-initial",
            )
        # Iniciar la càrrega d'estrelles o re-enviar les existents si ja estan carregades (re-connexió F5)
        if not star_coordinator._started:
            asyncio.create_task(star_coordinator.start())
        else:
            asyncio.create_task(star_coordinator.publish_current_state())

        asyncio.create_task(deep_sky_coordinator.publish_current_state())

        if star_trails_session["sessionId"]:
            await broadcast_star_trails_snapshot()

    bridge.on("set_observer_location", _handle_set_location)
    bridge.on("frontend_ready", _on_frontend_ready)
    bridge.on("resolve_star_pick", _handle_resolve_star_pick)

    # ── 3.2. Lògica de Temps (Fase 3) i Cel (Fase 7) ─────────────────
    engine = AstronomicalEngine()
    sky_composer = SkyEnvironmentComposer()
    lighting_composer = LightingEnvironmentComposer()
    sim_time_utc = datetime.now(timezone.utc)
    is_realtime = True
    is_time_playing = True
    time_rate = 1.0
    time_drag_active = False
    latest_solar_system: SolarSystemSnapshot | None = None
    latest_event = None
    event_service: AstronomicalEventService | None = None
    event_search_coordinator: EventSearchCoordinator | None = None
    trajectory_coordinator: ApparentTrajectoryCoordinator | None = None
    lunar_limb_provider: LroLolaLimbProfileProvider | None = None

    # Capacitat Star Trails (Traces Circumpolars)
    star_trails_session: dict[str, Any] = {
        "sessionId": "",
        "sessionVersion": 0,
        "state": "idle",
        "startUtcIso": "",
        "accumulatedExposureSeconds": 0.0,
        "durationSeconds": 86400.0,
        "sampleIntervalSeconds": 60.0,
        "magnitudeLimit": 6.0,
        "playbackRate": 1.0,
        "starCount": 0,
        "segmentCount": 0,
        "gpuBytes": 0,
    }

    async def broadcast_star_trails_snapshot() -> None:
        if not bridge.connected:
            return
        await bridge.send({
            "type": "star_trails_snapshot",
            "sessionId": star_trails_session["sessionId"],
            "sessionVersion": star_trails_session["sessionVersion"],
            "state": star_trails_session["state"],
            "startUtcIso": star_trails_session["startUtcIso"],
            "accumulatedExposureSeconds": star_trails_session["accumulatedExposureSeconds"],
            "durationSeconds": star_trails_session["durationSeconds"],
            "playbackRate": star_trails_session["playbackRate"],
            "magnitudeLimit": star_trails_session["magnitudeLimit"],
            "starCount": star_trails_session["starCount"],
            "segmentCount": star_trails_session["segmentCount"],
            "gpuBytes": star_trails_session["gpuBytes"],
        })
    
    # Pas 12: Cerca astronòmica
    search_coordinator = AstronomicalSearchCoordinator(bridge.send_astronomical_search_result)

    async def publish_solar_system(snapshot: SolarSystemSnapshot) -> int:
        """Publish one coherent science state to bodies, sky and local lighting."""
        nonlocal latest_solar_system, latest_event
        latest_solar_system = snapshot
        observer = snapshot.scientific_observer
        if event_service is not None and observer is not None:
            event = await asyncio.to_thread(
                event_service.snapshot,
                snapshot.timestamp_utc,
                observer,
                observer_generation=snapshot.observer_generation,
                source_solar_system_generation=snapshot.generation,
            )
        else:
            fallback_observer = observer or scientific_observer()
            event = AstronomicalEventCalculator().calculate(
                AstronomicalEventEphemeris(
                    timestamp_utc=snapshot.timestamp_utc,
                    observer_latitude_deg=fallback_observer.latitude_deg,
                    observer_longitude_deg=fallback_observer.longitude_deg,
                    observer_elevation_m=fallback_observer.elevation_m,
                    kernel_generation=snapshot.kernel_generation or "unavailable",
                    source="event geometry unavailable",
                    quality=GeometryQuality.UNAVAILABLE,
                    bodies=(),
                ),
                observer_generation=snapshot.observer_generation,
                source_solar_system_generation=snapshot.generation,
            )
        latest_event = event
        byte_count = await bridge.send_solar_system_snapshot(snapshot)
        await bridge.send_astronomical_event_snapshot(event)
        sky = sky_composer.compose(
            snapshot.sun,
            snapshot.generation,
            solar_disc_transmission=event.solar.solar_disc_transmission,
            sky_eclipse_dimming_factor=event.sky_eclipse_dimming_factor,
        )
        await bridge.send_sky_environment_snapshot(sky)
        await bridge.send_lighting_environment_snapshot(
            lighting_composer.compose(
                sky,
                snapshot,
                direct_solar_visibility_factor=event.solar.solar_disc_transmission,
                lunar_direct_visibility_factor=event.lunar.mean_lunar_light_transmission,
            )
        )
        return byte_count

    if (
        solar_system_assets.kernel_manifest_path is not None
        and solar_system_assets.satellite_catalog is not None
    ):
        try:
            ephemeris_adapter = SpiceEphemerisAdapter(
                solar_system_assets.kernel_manifest_path,
                solar_system_assets.satellite_catalog,
            )
        except Exception as exc:
            log.exception(
                "MGP: [__main__.py] [ephemeris] "
                "[SPICE unavailable; es conserva el fallback validat DE421: %s]",
                exc,
            )
            ephemeris_adapter = SkyfieldEphemerisAdapter()
    else:
        ephemeris_adapter = SkyfieldEphemerisAdapter()
    ephemeris_coordinator = EphemerisCoordinator(
        ephemeris_adapter,
        publish_solar_system,
        horizon_profile=lambda: horizon_coordinator.active_profile,
    )
    orbit_sampler = (
        OrbitSampler(ephemeris_adapter)
        if isinstance(ephemeris_adapter, SpiceEphemerisAdapter)
        else None
    )
    if isinstance(ephemeris_adapter, SpiceEphemerisAdapter):
        lunar_limb_provider = LroLolaLimbProfileProvider()
        event_service = AstronomicalEventService(
            ephemeris_adapter,
            lunar_limb_provider,
        )
        event_search_coordinator = EventSearchCoordinator(
            AstronomicalEventSearcher(ephemeris_adapter),
            bridge.send_event_search_result,
        )
        trajectory_coordinator = ApparentTrajectoryCoordinator(
            ApparentTrajectorySampler(ephemeris_adapter),
            bridge.send_apparent_trajectory,
        )
    metadata = ephemeris_adapter.metadata
    log.info(
        "Efemèride: provider=%s kernel=%s generation=%s sha256=%s",
        metadata.provider,
        metadata.kernel_name or "fallback",
        metadata.kernel_generation or metadata.skyfield_version or "unavailable",
        metadata.kernel_sha256 or "unavailable",
    )

    async def _handle_set_satellite_systems(data: dict[str, Any]) -> None:
        if not isinstance(ephemeris_adapter, SpiceEphemerisAdapter):
            await bridge.send({
                "type": "bridge_error",
                "code": "SPICE_UNAVAILABLE",
                "message": "Els kernels de satèl·lits no estan disponibles",
            })
            return
        try:
            systems = data.get("systems", ())
            if not isinstance(systems, list):
                raise ValueError("systems must be a list")
            ephemeris_adapter.set_satellite_systems(str(item) for item in systems)
            ephemeris_coordinator.request(
                sim_time_utc, scientific_observer(), observer_generation
            )
        except (TypeError, ValueError) as exc:
            await bridge.send({
                "type": "bridge_error",
                "code": "INVALID_SATELLITE_SYSTEMS",
                "message": str(exc),
            })

    async def _handle_request_satellite_orbit(data: dict[str, Any]) -> None:
        if orbit_sampler is None or not isinstance(ephemeris_adapter, SpiceEphemerisAdapter):
            return
        body_id = str(data.get("bodyId", ""))
        definition = next(
            (
                item
                for item in ephemeris_adapter.satellite_catalog.satellites
                if item.body_id == body_id
            ),
            None,
        )
        if definition is None:
            return
        interval_days = max(0.01, min(3650.0, float(data.get("intervalDays", 30.0))))
        sample_count = max(16, min(2048, int(data.get("sampleCount", 256))))
        center_et = ephemeris_adapter.utc_to_et(sim_time_utc)
        half_interval = interval_days * 43_200.0
        start_et = max(
            center_et - half_interval,
            definition.coverage_start_et or center_et - half_interval,
        )
        end_et = min(
            center_et + half_interval,
            definition.coverage_end_et or center_et + half_interval,
        )
        geometry = await asyncio.to_thread(
            orbit_sampler.sample,
            definition,
            start_et,
            end_et,
            sample_count,
            metadata.kernel_generation or "unknown",
        )
        log.info(
            "MGP: [OrbitSampler] [sample] [body=%s samples=%d duration_ms=%.3f cache_hits=%d]",
            body_id,
            sample_count,
            orbit_sampler.last_sampling_duration_ms,
            orbit_sampler.cache_hit_count,
        )
        await bridge.send_orbit_geometry(orbit_sampler.encode(geometry))

    async def _handle_request_event_search(data: dict[str, Any]) -> None:
        if event_search_coordinator is None:
            await bridge.send({
                "type": "bridge_error",
                "code": "EVENT_SEARCH_UNAVAILABLE",
                "message": "La cerca precisa requereix SPICE/DE440",
            })
            return
        try:
            request_id = str(data["requestId"])
            event_type = EclipseKind(str(data.get("eventType", "solar")))
            if event_type not in {EclipseKind.SOLAR, EclipseKind.LUNAR}:
                raise ValueError("eventType must be solar or lunar")
            start_utc = datetime.fromisoformat(str(data["startUtc"]).replace("Z", "+00:00"))
            end_utc = datetime.fromisoformat(str(data["endUtc"]).replace("Z", "+00:00"))
            event_search_coordinator.request(
                request_id=request_id,
                event_type=event_type,
                observer=scientific_observer(),
                observer_generation=observer_generation,
                start_utc=start_utc,
                end_utc=end_utc,
            )
        except (KeyError, TypeError, ValueError) as exc:
            await bridge.send({
                "type": "bridge_error",
                "code": "INVALID_EVENT_SEARCH",
                "message": str(exc),
            })

    async def _handle_request_apparent_trajectory(data: dict[str, Any]) -> None:
        if trajectory_coordinator is None:
            await bridge.send({
                "type": "bridge_error",
                "code": "TRAJECTORY_UNAVAILABLE",
                "message": "Les trajectòries precises requereixen SPICE/DE440",
            })
            return
        try:
            trajectory_coordinator.request(
                request_id=str(data["requestId"]),
                body_id=str(data["bodyId"]),
                observer=scientific_observer(),
                observer_generation=observer_generation,
                start_utc=datetime.fromisoformat(
                    str(data["startUtc"]).replace("Z", "+00:00")
                ),
                end_utc=datetime.fromisoformat(
                    str(data["endUtc"]).replace("Z", "+00:00")
                ),
                sample_count=max(2, min(4096, int(data.get("sampleCount", 256)))),
            )
        except (KeyError, TypeError, ValueError) as exc:
            await bridge.send({
                "type": "bridge_error",
                "code": "INVALID_APPARENT_TRAJECTORY",
                "message": str(exc),
            })

    async def _handle_request_angular_separation(data: dict[str, Any]) -> None:
        if event_service is None:
            await bridge.send({
                "type": "bridge_error",
                "code": "ANGULAR_SEPARATION_UNAVAILABLE",
                "message": "La separació precisa requereix SPICE/DE440",
            })
            return
        try:
            instant = datetime.fromisoformat(
                str(data.get("utc", sim_time_utc.isoformat())).replace("Z", "+00:00")
            )
            result = await asyncio.to_thread(
                event_service.measure_pair,
                str(data["requestId"]),
                instant,
                scientific_observer(),
                str(data["bodyA"]),
                str(data["bodyB"]),
            )
            await bridge.send_angular_separation_result(result)
        except (KeyError, TypeError, ValueError, RuntimeError) as exc:
            await bridge.send({
                "type": "bridge_error",
                "code": "INVALID_ANGULAR_SEPARATION",
                "message": str(exc),
            })

    bridge.on("set_satellite_systems", _handle_set_satellite_systems)
    bridge.on("request_satellite_orbit", _handle_request_satellite_orbit)
    bridge.on("request_event_search", _handle_request_event_search)
    bridge.on("request_apparent_trajectory", _handle_request_apparent_trajectory)
    bridge.on("request_angular_separation", _handle_request_angular_separation)

    async def _handle_astronomical_search_request(data: dict[str, Any]) -> None:
        try:
            req_id = data["requestId"]
            gen = data["generation"]
            query = data["query"]
            limit = data.get("limit", 20)
            
            # Poblar index dinàmicament just abans de la primera cerca
            if latest_solar_system and not search_coordinator.is_index_built:
                planets_data = []
                indexed_ids = set()
                
                # 1. Carregar tots els satèl·lits del catàleg complet (460+)
                sat_catalog = solar_system_assets.satellite_catalog
                if sat_catalog:
                    for defn in sat_catalog.satellites:
                        aliases = [defn.name]
                        if defn.provisional_designation:
                            aliases.append(defn.provisional_designation)
                        planets_data.append({
                            "body_id": defn.body_id,
                            "canon_name": defn.name,
                            "aliases": aliases,
                        })
                        indexed_ids.add(defn.body_id)

                # 2. Afegir cossos principals del sistema solar (Sol, Lluna, Planetes, etc.)
                all_bodies = [latest_solar_system.sun, latest_solar_system.moon]
                if latest_solar_system.planets:
                    all_bodies.extend(latest_solar_system.planets)
                if latest_solar_system.satellites:
                    all_bodies.extend(latest_solar_system.satellites)
                    
                for b in all_bodies:
                    name = b.display_name if b.display_name else b.body_id.capitalize()
                    aliases = [name]
                    if b.body_id == "sun": aliases.extend(["Sol", "Sun"])
                    elif b.body_id == "moon": aliases.extend(["Lluna", "Luna", "Moon"])
                    elif b.body_id == "earth": aliases.extend(["Terra", "Tierra", "Earth"])
                    elif b.body_id == "mercury": aliases.extend(["Mercuri", "Mercurio", "Mercury"])
                    elif b.body_id == "venus": aliases.extend(["Venus"])
                    elif b.body_id == "mars": aliases.extend(["Mart", "Marte", "Mars"])
                    elif b.body_id == "jupiter": aliases.extend(["Júpiter", "Jupiter"])
                    elif b.body_id == "saturn": aliases.extend(["Saturn", "Saturno"])
                    elif b.body_id == "uranus": aliases.extend(["Urà", "Urano", "Uranus"])
                    elif b.body_id == "neptune": aliases.extend(["Neptú", "Neptuno", "Neptune"])
                    elif b.body_id == "pluto": aliases.extend(["Plutó", "Plutón", "Pluto"])

                    if b.body_id in indexed_ids:
                        for pd in planets_data:
                            if pd["body_id"] == b.body_id:
                                pd["coordinate_snapshot"] = b.equatorial
                                break
                    else:
                        planets_data.append({
                            "body_id": b.body_id,
                            "canon_name": name,
                            "aliases": aliases,
                            "coordinate_snapshot": b.equatorial
                        })
                        indexed_ids.add(b.body_id)

                # 3. Objectes NGC / Cel Profund
                ngc_objects = deep_sky_adapter.load_search_objects()

                # 4. Estrelles importants / Gaia (Named stars)
                named_stars = [
                    {"name": "Sirius", "source_id": "Gaia-1", "ra": 101.28715, "dec": -16.7161},
                    {"name": "Canopus", "source_id": "Gaia-2", "ra": 95.98787, "dec": -52.6957},
                    {"name": "Rigil Kentaurus", "source_id": "Gaia-3", "ra": 219.9021, "dec": -60.833},
                    {"name": "Arcturus", "source_id": "Gaia-4", "ra": 213.9153, "dec": 19.1824},
                    {"name": "Vega", "source_id": "Gaia-5", "ra": 279.23473, "dec": 38.78369},
                    {"name": "Capella", "source_id": "Gaia-6", "ra": 79.1723, "dec": 45.998},
                    {"name": "Rigel", "source_id": "Gaia-7", "ra": 78.63446, "dec": -8.20164},
                    {"name": "Procyon", "source_id": "Gaia-8", "ra": 114.8255, "dec": 5.225},
                    {"name": "Achernar", "source_id": "Gaia-9", "ra": 24.4285, "dec": -57.2367},
                    {"name": "Betelgeuse", "source_id": "Gaia-10", "ra": 88.7929, "dec": 7.40706},
                    {"name": "Hadar", "source_id": "Gaia-11", "ra": 210.9559, "dec": -60.373},
                    {"name": "Altair", "source_id": "Gaia-12", "ra": 297.6958, "dec": 8.8683},
                    {"name": "Aldebaran", "source_id": "Gaia-13", "ra": 68.98016, "dec": 16.5093},
                    {"name": "Spica", "source_id": "Gaia-14", "ra": 201.2983, "dec": -11.1613},
                    {"name": "Antares", "source_id": "Gaia-15", "ra": 247.3519, "dec": -26.432},
                    {"name": "Pollux", "source_id": "Gaia-16", "ra": 116.3289, "dec": 28.0262},
                    {"name": "Fomalhaut", "source_id": "Gaia-17", "ra": 344.4127, "dec": -29.6222},
                    {"name": "Deneb", "source_id": "Gaia-18", "ra": 310.3579, "dec": 45.2803},
                    {"name": "Regulus", "source_id": "Gaia-19", "ra": 152.0929, "dec": 11.9672},
                    {"name": "Adhara", "source_id": "Gaia-20", "ra": 104.6565, "dec": -28.9721},
                    {"name": "Castor", "source_id": "Gaia-21", "ra": 113.6494, "dec": 31.8883},
                    {"name": "Shaula", "source_id": "Gaia-22", "ra": 263.4022, "dec": -37.0984},
                    {"name": "Bellatrix", "source_id": "Gaia-23", "ra": 81.2827, "dec": 6.3497},
                    {"name": "Elnath", "source_id": "Gaia-24", "ra": 81.573, "dec": 28.6075},
                    {"name": "Miaplacidus", "source_id": "Gaia-25", "ra": 139.7554, "dec": -69.7172},
                    {"name": "Alnilam", "source_id": "Gaia-26", "ra": 84.0534, "dec": -1.2019},
                    {"name": "Alnitak", "source_id": "Gaia-27", "ra": 85.1897, "dec": -1.9426},
                    {"name": "Alioth", "source_id": "Gaia-28", "ra": 193.5073, "dec": 55.9598},
                    {"name": "Dubhe", "source_id": "Gaia-29", "ra": 165.932, "dec": 61.751},
                    {"name": "Mirfak", "source_id": "Gaia-30", "ra": 51.0807, "dec": 49.8612},
                    {"name": "Alkaid", "source_id": "Gaia-31", "ra": 206.8852, "dec": 49.3133},
                    {"name": "Polaris", "source_id": "Gaia-32", "ra": 37.9546, "dec": 89.2641},
                    {"name": "Mizar", "source_id": "Gaia-33", "ra": 200.9814, "dec": 54.9254},
                    {"name": "Algol", "source_id": "Gaia-34", "ra": 47.0422, "dec": 40.9556},
                    {"name": "Kochab", "source_id": "Gaia-35", "ra": 222.6764, "dec": 74.1555},
                    {"name": "Denebola", "source_id": "Gaia-36", "ra": 177.2649, "dec": 14.5721},
                ]

                search_coordinator.build_index(
                    named_stars=named_stars,
                    ngc_objects=ngc_objects,
                    planets=planets_data
                )
            
            await search_coordinator.search(req_id, gen, query, limit)
        except Exception as e:
            log.error("MGP: [__main__] Error executant cerca: %s", e)
            req_id = data.get("requestId", "")
            gen = data.get("generation", 0)
            if req_id:
                try:
                    await bridge.send_astronomical_search_result(req_id, gen, "error", [])
                except Exception:
                    pass
            
    bridge.on("astronomical_search_request", _handle_astronomical_search_request)

    def scientific_observer() -> ScientificObserver:
        return ScientificObserver(
            latitude_deg=current_observer.location.latitude_deg,
            longitude_deg=current_observer.location.longitude_deg,
            elevation_m=current_observer.effective_height_m,
        )

    async def broadcast_sky_environment() -> None:
        if bridge.connected and latest_solar_system is not None:
            solar_transmission = (
                latest_event.solar.solar_disc_transmission
                if latest_event is not None
                else 1.0
            )
            sky_dimming = (
                latest_event.sky_eclipse_dimming_factor
                if latest_event is not None
                else 1.0
            )
            lunar_transmission = (
                latest_event.lunar.mean_lunar_light_transmission
                if latest_event is not None
                else 1.0
            )
            sky = sky_composer.compose(
                latest_solar_system.sun,
                latest_solar_system.generation,
                solar_disc_transmission=solar_transmission,
                sky_eclipse_dimming_factor=sky_dimming,
            )
            await bridge.send_sky_environment_snapshot(sky)
            await bridge.send_lighting_environment_snapshot(
                lighting_composer.compose(
                    sky,
                    latest_solar_system,
                    direct_solar_visibility_factor=solar_transmission,
                    lunar_direct_visibility_factor=lunar_transmission,
                )
            )

    async def broadcast_time(*, force_celestial_transform: bool = False) -> None:
        if not bridge.connected:
            return
        # Calculate Astro parameters
        jd = engine.julian_day(sim_time_utc)
        lst_deg = engine.local_sidereal_angle_deg(sim_time_utc, current_observer.location.longitude_deg)
        sun_alts = engine.generate_sun_altitude_samples(
            sim_time_utc,
            current_observer.location.latitude_deg,
            current_observer.location.longitude_deg,
            steps=96
        )
        
        await bridge.send_simulation_time_snapshot(
            current_time_iso=sim_time_utc.isoformat(),
            julian_day=jd,
            lst_deg=lst_deg,
            sun_altitudes=sun_alts,
            is_realtime=is_realtime
        )
        
        # Generar i enviar l'estat del cel (Pas 7)
        # Enviar actualització de transformació d'estrelles (LST o latitud han pogut canviar)
        await star_coordinator.update_celestial_transform(
            latitude_deg=current_observer.location.latitude_deg,
            lst_deg=lst_deg,
            force_publish=force_celestial_transform,
        )
        ephemeris_coordinator.request(
            sim_time_utc,
            scientific_observer(),
            observer_generation,
        )

    async def _handle_set_simulation_time(data: dict[str, Any]) -> None:
        nonlocal sim_time_utc, is_realtime
        try:
            iso_str = data.get("currentTimeIso")
            if iso_str:
                sim_time_utc = datetime.fromisoformat(iso_str)
                if sim_time_utc.tzinfo is None:
                    sim_time_utc = sim_time_utc.replace(tzinfo=timezone.utc)
                else:
                    sim_time_utc = sim_time_utc.astimezone(timezone.utc)
                is_realtime = False
                await broadcast_time()
                if star_trails_session["state"] == "running" and star_trails_session["startUtcIso"]:
                    try:
                        start_dt = datetime.fromisoformat(star_trails_session["startUtcIso"])
                        elapsed = clamped_exposure_seconds(
                            start_dt,
                            sim_time_utc,
                            float(star_trails_session["durationSeconds"]),
                        )
                        star_trails_session["accumulatedExposureSeconds"] = elapsed
                        await broadcast_star_trails_snapshot()
                    except Exception:
                        pass
        except ValueError as e:
            log.warning("Invalid time format: %s", e)

    async def _handle_set_realtime_mode(data: dict[str, Any]) -> None:
        nonlocal is_realtime, sim_time_utc
        enabled = bool(data.get("enabled", False))
        is_realtime = enabled
        if is_realtime:
            sim_time_utc = datetime.now(timezone.utc)
        await broadcast_time()

    async def _handle_timeline_drag_started(data: dict[str, Any]) -> None:
        nonlocal time_drag_active, is_realtime
        time_drag_active = True
        is_realtime = False

    async def _handle_timeline_drag_finished(data: dict[str, Any]) -> None:
        nonlocal time_drag_active
        time_drag_active = False
        # Sync final state
        if "currentTimeIso" in data:
            await _handle_set_simulation_time(data)

    async def _handle_request_offset_day(data: dict[str, Any]) -> None:
        nonlocal sim_time_utc, is_realtime
        offset = int(data.get("offsetDays", 0))
        if offset != 0:
            sim_time_utc += timedelta(days=offset)
            is_realtime = False
            await broadcast_time()

    async def _handle_set_time_playing(data: dict[str, Any]) -> None:
        nonlocal is_time_playing
        is_time_playing = bool(data.get("enabled", True))

    async def _handle_set_time_rate(data: dict[str, Any]) -> None:
        nonlocal time_rate
        time_rate = float(data.get("rate", 1.0))
        
    bridge.on("set_simulation_time", _handle_set_simulation_time)
    bridge.on("set_realtime_mode", _handle_set_realtime_mode)
    bridge.on("timeline_drag_started", _handle_timeline_drag_started)
    bridge.on("timeline_drag_finished", _handle_timeline_drag_finished)
    bridge.on("request_offset_day", _handle_request_offset_day)
    bridge.on("set_time_playing", _handle_set_time_playing)
    bridge.on("set_time_rate", _handle_set_time_rate)

    # ── 3.3. Handlers de UI per a Cel i Atmosfera (Fase 7) ───────────
    async def _handle_set_atmosphere_enabled(data: dict[str, Any]) -> None:
        sky_composer.atmosphere_enabled = bool(data.get("enabled", True))
        await broadcast_sky_environment()

    async def _handle_set_light_pollution_enabled(data: dict[str, Any]) -> None:
        sky_composer.light_pollution_enabled = bool(data.get("enabled", True))
        await broadcast_sky_environment()

    async def _handle_set_light_pollution_mode(data: dict[str, Any]) -> None:
        mode_str = data.get("mode", "bortle")
        try:
            sky_composer.light_pollution_mode = LightPollutionMode(mode_str)
        except ValueError:
            pass
        await broadcast_sky_environment()

    async def _handle_set_bortle_class(data: dict[str, Any]) -> None:
        sky_composer.bortle_value = float(data.get("bortleClass", 4.0))
        await broadcast_sky_environment()

    async def _handle_set_manual_magnitude_limit(data: dict[str, Any]) -> None:
        sky_composer.magnitude_limit = float(data.get("magnitudeLimit", 6.0))
        await broadcast_sky_environment()

    bridge.on("set_atmosphere_enabled", _handle_set_atmosphere_enabled)
    bridge.on("set_light_pollution_enabled", _handle_set_light_pollution_enabled)
    bridge.on("set_light_pollution_mode", _handle_set_light_pollution_mode)
    bridge.on("set_bortle_class", _handle_set_bortle_class)
    bridge.on("set_manual_magnitude_limit", _handle_set_manual_magnitude_limit)

    # ── 3.4. Handlers de Traces Circumpolars (Star Trails) ───────────
    async def _handle_start_star_trails(data: dict[str, Any]) -> None:
        nonlocal star_trails_session, is_time_playing, is_realtime, time_rate
        sess_id = uuid.uuid4().hex[:12]
        config = StarTrailPlaybackConfig.normalized(
            duration_seconds=float(data.get("durationSeconds", 86_400.0)),
            sample_interval_seconds=float(
                data.get("sampleIntervalSeconds", 60.0)
            ),
            magnitude_limit=float(data.get("magnitudeLimit", 6.0)),
            playback_rate=float(data.get("playbackRate", 1.0)),
        )
        is_realtime = False
        is_time_playing = True
        time_rate = config.playback_rate
        star_trails_session = {
            "sessionId": sess_id,
            "sessionVersion": 1,
            "state": "running",
            "startUtcIso": sim_time_utc.isoformat(),
            "accumulatedExposureSeconds": 0.0,
            "durationSeconds": config.duration_seconds,
            "sampleIntervalSeconds": config.sample_interval_seconds,
            "magnitudeLimit": config.magnitude_limit,
            "playbackRate": config.playback_rate,
            # Renderer-owned diagnostics are overlaid from the actual filtered
            # catalog and resident WebGL resources in the frontend.
            "starCount": 0,
            "segmentCount": 0,
            "gpuBytes": 0,
        }
        log.info(
            "Star trails iniciat: %s (mag<=%.1f, rate=%.1fx)",
            sess_id,
            config.magnitude_limit,
            config.playback_rate,
        )
        await broadcast_star_trails_snapshot()

    async def _handle_pause_star_trails(data: dict[str, Any]) -> None:
        nonlocal is_time_playing
        if star_trails_session["state"] == "running":
            star_trails_session["state"] = "paused"
            star_trails_session["sessionVersion"] += 1
            is_time_playing = False
            await broadcast_star_trails_snapshot()

    async def _handle_resume_star_trails(data: dict[str, Any]) -> None:
        nonlocal is_time_playing
        if star_trails_session["state"] == "paused":
            star_trails_session["state"] = "running"
            star_trails_session["sessionVersion"] += 1
            is_time_playing = True
            await broadcast_star_trails_snapshot()

    async def _handle_stop_star_trails(data: dict[str, Any]) -> None:
        nonlocal is_time_playing
        if star_trails_session["state"] in ("running", "paused"):
            star_trails_session["state"] = "stopped"
            star_trails_session["sessionVersion"] += 1
            is_time_playing = False
            await broadcast_star_trails_snapshot()

    async def _handle_clear_star_trails(data: dict[str, Any]) -> None:
        nonlocal star_trails_session
        star_trails_session = {
            "sessionId": "",
            "sessionVersion": 0,
            "state": "idle",
            "startUtcIso": "",
            "accumulatedExposureSeconds": 0.0,
            "durationSeconds": 86400.0,
            "sampleIntervalSeconds": 60.0,
            "magnitudeLimit": 6.0,
            "playbackRate": 1.0,
            "starCount": 0,
            "segmentCount": 0,
            "gpuBytes": 0,
        }
        await broadcast_star_trails_snapshot()

    bridge.on("start_star_trails", _handle_start_star_trails)
    bridge.on("pause_star_trails", _handle_pause_star_trails)
    bridge.on("resume_star_trails", _handle_resume_star_trails)
    bridge.on("stop_star_trails", _handle_stop_star_trails)
    bridge.on("clear_star_trails", _handle_clear_star_trails)

    async def clock_ticker() -> None:
        """S'encarrega d'avançar el temps si està en temps real i publicar l'estat."""
        nonlocal sim_time_utc
        tick_interval = SIMULATION_TICK_INTERVAL_SEC
        while not shutdown_requested.is_set():
            await asyncio.sleep(tick_interval)
            if not time_drag_active:
                if is_realtime:
                    sim_time_utc = datetime.now(timezone.utc)
                    await broadcast_time()
                elif is_time_playing:
                    sim_time_utc += timedelta(seconds=tick_interval * time_rate)
                    await broadcast_time()
                if star_trails_session["state"] == "running" and star_trails_session["startUtcIso"]:
                    try:
                        start_dt = datetime.fromisoformat(star_trails_session["startUtcIso"])
                        elapsed = clamped_exposure_seconds(
                            start_dt,
                            sim_time_utc,
                            float(star_trails_session["durationSeconds"]),
                        )
                        star_trails_session["accumulatedExposureSeconds"] = elapsed
                        if elapsed >= star_trails_session["durationSeconds"]:
                            star_trails_session["state"] = "completed"
                            star_trails_session["sessionVersion"] += 1
                        await broadcast_star_trails_snapshot()
                    except Exception:
                        pass

    clock_task = asyncio.create_task(clock_ticker())

    # ── 4. Iniciar servidor ───────────────────────────────────────────
    url = await server.start()
    log.info("TerraLab3D a punt a %s", url)

    # ── 5. Obrir navegador ────────────────────────────────────────────
    if os.getenv("TERRALAB3D_NO_BROWSER") != "1":
        asyncio.create_task(asyncio.to_thread(webbrowser.open, url))

    # ── 6. Esperar tancament ──────────────────────────────────────────
    # Configurar el manegador de Ctrl-C
    def handle_signal() -> None:
        log.info("Senyal rebut — aturant l'aplicació")
        shutdown_requested.set()

    # Registrar manegadors de senyals
    try:
        loop.add_signal_handler(signal.SIGINT, handle_signal)
        loop.add_signal_handler(signal.SIGTERM, handle_signal)
    except NotImplementedError:
        # Windows no admet add_signal_handler per a tots els senyals
        # Utilitzem signal.signal com a alternativa per a SIGINT
        signal.signal(signal.SIGINT, lambda *_: handle_signal())

    # Programar una ordre de demostració de càmera després de 3 segons (demostra bidireccionalitat)
    async def demo_camera_command() -> None:
        """Espera la connexió inicial i envia una posició de càmera de prova per
        verificar que la comunicació Python → Frontend funciona."""
        while not bridge.connected:
            await asyncio.sleep(0.1)
        log.info("Pont connectat — sessió %s", bridge.session_id)
        await asyncio.sleep(3)
        if bridge.connected:
            log.info("Enviant set_camera_pose per verificar el pont bidireccional")
            await bridge.send_set_camera_pose(
                az=180.0, alt=30.0, fov=60.0, transition_ms=1200,
            )

    demo_task = asyncio.create_task(demo_camera_command())

    # Esperar tant Ctrl-C com la desconnexió del navegador
    done, _ = await asyncio.wait(
        [
            asyncio.create_task(shutdown_requested.wait()),
            asyncio.create_task(bridge.shutdown_event.wait()),
        ],
        return_when=asyncio.FIRST_COMPLETED,
    )

    # ── 6. Tancament net ──────────────────────────────────────────────
    log.info("Iniciant tancament...")

    # Cancel·lar les tasques
    demo_task.cancel()
    clock_task.cancel()
    try:
        await demo_task
        await clock_task
    except asyncio.CancelledError:
        pass

    # Demanar al frontend que netegi (si encara està connectat)
    if event_search_coordinator is not None:
        await event_search_coordinator.close()
    if trajectory_coordinator is not None:
        await trajectory_coordinator.close()
    if lunar_limb_provider is not None:
        lunar_limb_provider.close()
    if terrain_regeneration_task is not None and not terrain_regeneration_task.done():
        terrain_regeneration_task.cancel()
        try:
            await terrain_regeneration_task
        except asyncio.CancelledError:
            pass
    cancel_visual_stream(reset_center=False)
    if terrain_stream_task is not None:
        try:
            await terrain_stream_task
        except asyncio.CancelledError:
            pass
    await horizon_coordinator.close()
    if elevation_task is not None:
        try:
            await elevation_task
        except asyncio.CancelledError:
            pass
    elevation_adapter.close()
    log.debug("MGP: [__main__.py] [shutdown] [Mètriques elevació: %s]", elevation_coordinator.metrics())
    log.debug("MGP: [__main__.py] [shutdown] [Mètriques horitzó: %s]", horizon_coordinator.metrics())
    await ephemeris_coordinator.close()
    log.debug("Mètriques d'efemèrides: %s", ephemeris_coordinator.metrics())
    if event_service is not None:
        log.debug("Mètriques Pas 9 instantànies: %s", event_service.metrics())
    if event_search_coordinator is not None:
        log.debug("Mètriques Pas 9 cerques: %s", event_search_coordinator.metrics())
    if trajectory_coordinator is not None:
        log.debug("Mètriques Pas 9 trajectòries: %s", trajectory_coordinator.metrics())
        
    await deep_sky_coordinator.shutdown()

    if bridge.connected:
        await bridge.request_shutdown()
        try:
            await asyncio.wait_for(bridge.shutdown_event.wait(), timeout=3.0)
        except asyncio.TimeoutError:
            log.warning("El frontend no ha confirmat el tancament en 3 segons")

    await server.stop()
    log.info("TerraLab3D s'ha aturat netament")
    return 0


# ─── Manegadors de missatges del pont ───────────────────────────────

async def _on_camera_changed(data: dict[str, Any]) -> None:
    """Rep actualitzacions de la posició de la càmera des del frontend (filtrat)."""
    log.debug(
        "Càmera: az=%.1f° alt=%.1f° fov=%.1f°",
        data.get("azimuthDeg", 0),
        data.get("altitudeDeg", 0),
        data.get("horizontalFovDeg", 0),
    )


async def _on_viewport_resized(data: dict[str, Any]) -> None:
    log.info(
        "Mida de la finestra canviada: %dx%d @%.1fx",
        data.get("widthPx", 0),
        data.get("heightPx", 0),
        data.get("devicePixelRatio", 1),
    )
    
async def _on_bridge_error(data: dict[str, Any]) -> None:
    log.error(
        "Error de pont des del frontend: [%s] %s",
        data.get("code", "?"),
        data.get("message", "?"),
    )


def main() -> int:
    """Punt d'entrada sincrònic per a ``python -m terralab3d``."""
    try:
        return asyncio.run(run())
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())

