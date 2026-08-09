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
import os
import signal
import sys
import webbrowser
from typing import Any
from datetime import datetime, timedelta, timezone

from terralab3d.domain.time.engine import AstronomicalEngine
from terralab3d.domain.time.models import ClockMode, SimulationInstant, ClockState
from terralab3d.domain.sky_background.sky_environment import SkyEnvironmentComposer
from terralab3d.domain.light_pollution.models import LightPollutionMode
from terralab3d.domain.solar_system.models import ScientificObserver, SolarSystemSnapshot
from terralab3d.domain.lighting.environment import LightingEnvironmentComposer
from terralab3d.application.ephemeris_coordinator import EphemerisCoordinator
from terralab3d.application.orbit_sampler import OrbitSampler
from terralab3d.infrastructure.adapters.ephemeris.adapter import SkyfieldEphemerisAdapter
from terralab3d.infrastructure.adapters.ephemeris.spice_adapter import SpiceEphemerisAdapter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("terralab3d")


async def run() -> int:
    """Punt d'entrada asíncron principal."""
    from terralab3d.infrastructure.bundler import bundle_frontend
    from terralab3d.infrastructure.server import TerraLabServer
    from terralab3d.infrastructure.websocket_bridge import WebSocketBridge
    from terralab3d.infrastructure.adapters.file_assets.moon_surface import ManagedMoonSurfaceAssets
    from terralab3d.infrastructure.adapters.file_assets.solar_system import ManagedSolarSystemAssets

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
    server = TerraLabServer(dist_dir, bridge, moon_surface_assets, solar_system_assets)

    loop = asyncio.get_running_loop()
    shutdown_requested = asyncio.Event()

    # Registrar manegadors de missatges del pont
    bridge.on("camera_changed", _on_camera_changed)
    bridge.on("viewport_resized", _on_viewport_resized)
    bridge.on("bridge_error", _on_bridge_error)
    bridge.on("frontend_performance_metrics", _on_frontend_performance_metrics)

    # ── 3. Lògica d'Ubicació (Fase 2) ─────────────────────────────────
    from terralab3d.domain.observer.models import GeoLocation, ObserverProfile
    from terralab3d.domain.identifiers import ObserverId

    current_observer = ObserverProfile(
        observer_id=ObserverId("default"),
        location=GeoLocation(latitude_deg=41.189795, longitude_deg=1.210058),
        height_offset_m=0.0
    )
    observer_generation = 1

    async def broadcast_location() -> None:
        await bridge.send_observer_location_changed(
            lat=current_observer.location.latitude_deg,
            lon=current_observer.location.longitude_deg,
            elevation=current_observer.location.elevation_m or 0.0,
            effective_height=current_observer.effective_height_m,
            source="Pendent (sense DEM)"
        )

    async def _handle_set_location(data: dict[str, Any]) -> None:
        nonlocal current_observer, observer_generation
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
            await broadcast_location()
            await broadcast_time()
            log.info(
                "Ubicació de l'observador actualitzada a: %.4f, %.4f (alt: %.1f)",
                current_observer.location.latitude_deg,
                current_observer.location.longitude_deg,
                height,
            )
        except Exception as e:
            await bridge.send_location_error(str(e))
            log.warning("Error a l'actualitzar la ubicació: %s", e)

    # ── 3.1. Lògica d'Estrelles (Fase 5 i Pas 6) ─────────────────────
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
        # Quan el frontend es connecta, enviem la ubicació inicial, iniciem estrelles, etc.
        await broadcast_location()
        await bridge.send_moon_surface_resource(moon_surface_assets.descriptor)
        await bridge.send_planet_texture_manifest(solar_system_assets.descriptor)
        await bridge.send_satellite_catalog_manifest(solar_system_assets.descriptor)
        await broadcast_time()
        # Iniciar la càrrega d'estrelles o re-enviar les existents si ja estan carregades (re-connexió F5)
        if not star_coordinator._started:
            asyncio.create_task(star_coordinator.start())
        else:
            asyncio.create_task(star_coordinator.publish_current_state())

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

    async def publish_solar_system(snapshot: SolarSystemSnapshot) -> int:
        """Publish one coherent science state to bodies, sky and local lighting."""
        nonlocal latest_solar_system
        latest_solar_system = snapshot
        byte_count = await bridge.send_solar_system_snapshot(snapshot)
        sky = sky_composer.compose(snapshot.sun, snapshot.generation)
        await bridge.send_sky_environment_snapshot(sky)
        await bridge.send_lighting_environment_snapshot(
            lighting_composer.compose(sky, snapshot)
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
    ephemeris_coordinator = EphemerisCoordinator(ephemeris_adapter, publish_solar_system)
    orbit_sampler = (
        OrbitSampler(ephemeris_adapter)
        if isinstance(ephemeris_adapter, SpiceEphemerisAdapter)
        else None
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

    bridge.on("set_satellite_systems", _handle_set_satellite_systems)
    bridge.on("request_satellite_orbit", _handle_request_satellite_orbit)

    def scientific_observer() -> ScientificObserver:
        return ScientificObserver(
            latitude_deg=current_observer.location.latitude_deg,
            longitude_deg=current_observer.location.longitude_deg,
            elevation_m=current_observer.effective_height_m,
        )

    async def broadcast_sky_environment() -> None:
        if bridge.connected and latest_solar_system is not None:
            sky = sky_composer.compose(
                latest_solar_system.sun,
                latest_solar_system.generation,
            )
            await bridge.send_sky_environment_snapshot(sky)
            await bridge.send_lighting_environment_snapshot(
                lighting_composer.compose(sky, latest_solar_system)
            )

    async def broadcast_time() -> None:
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

    async def clock_ticker() -> None:
        """S'encarrega d'avançar el temps si està en temps real i publicar l'estat."""
        nonlocal sim_time_utc
        tick_interval = 1.0  # 1-second refresh rate
        while not shutdown_requested.is_set():
            await asyncio.sleep(tick_interval)
            if not time_drag_active:
                if is_realtime:
                    sim_time_utc = datetime.now(timezone.utc)
                    await broadcast_time()
                elif is_time_playing:
                    sim_time_utc += timedelta(seconds=tick_interval * time_rate)
                    await broadcast_time()

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
    await ephemeris_coordinator.close()
    log.info("Mètriques d'efemèrides: %s", ephemeris_coordinator.metrics())

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


async def _on_frontend_performance_metrics(data: dict[str, Any]) -> None:
    log.info(
        "Frontend metrics: frame_ms_p50=%.2f frame_ms_p95=%.2f samples=%d "
        "entities=%d geometries=%d materials=%d snapshots=%d stale=%d bridge_bytes=%d",
        data.get("frameMsP50", 0.0),
        data.get("frameMsP95", 0.0),
        data.get("frameSampleCount", 0),
        data.get("solarSystemEntityBuildCount", 0),
        data.get("solarBodyGeometryBuildCount", 0),
        data.get(
            "solarBodyMaterialBuildCount",
            data.get("solarSystemMaterialBuildCount", 0),
        ),
        data.get("solarSystemSnapshotApplyCount", 0),
        data.get("solarSystemStaleSnapshotCount", 0),
        data.get("solarSystemBridgeBytes", 0),
    )
    log.info(
        "Solar 8.6 metrics: planet_texture_loads=%d texture_upload_bytes=%d "
        "catalog=%d states=%d ring_geometry=%d ring_material=%d "
        "orbit_geometry=%d orbit_bridge_bytes=%d gpu_estimate_bytes=%d",
        data.get("planetTextureLoadCount", 0),
        data.get("planetTextureUploadBytes", 0),
        data.get("satelliteCatalogCount", 0),
        data.get("satelliteStateCountPerTick", 0),
        data.get("ringGeometryBuildCount", 0),
        data.get("ringMaterialBuildCount", 0),
        data.get("orbitGeometryBuildCount", 0),
        data.get("orbitBridgeBytes", 0),
        data.get("gpuMemoryEstimateBytes", 0),
    )
    log.info(
        "Moon metrics: geometry=%d material=%d albedo_loads=%d normal_loads=%d "
        "texture_upload_bytes=%d bridge_texture_bytes=%d",
        data.get("moonGeometryBuildCount", 0),
        data.get("moonMaterialBuildCount", 0),
        data.get("moonAlbedoTextureLoadCount", 0),
        data.get("moonNormalTextureLoadCount", 0),
        data.get("moonTextureUploadBytes", 0),
        data.get("moonBridgeTextureBytes", 0),
    )
    log.info(
        "Lighting 8.7 metrics: sun_build=%d moon_build=%d diffuse_build=%d "
        "pbr_materials=%d snapshots=%d stale=%d bridge_bytes=%d "
        "sun_shadow_updates=%d moon_shadow_updates=%d shadow_bytes=%d "
        "renderer_calls=%d renderer_geometries=%d renderer_textures=%d",
        data.get("sunLightBuildCount", 0),
        data.get("moonLightBuildCount", 0),
        data.get("diffuseLightBuildCount", 0),
        data.get("pbrMaterialBuildCount", 0),
        data.get("lightingSnapshotCount", 0),
        data.get("lightingStaleCount", 0),
        data.get("lightingBridgeBytes", 0),
        data.get("sunShadowUpdateCount", 0),
        data.get("moonShadowUpdateCount", 0),
        data.get("shadowMapEstimateBytes", 0),
        data.get("rendererRenderCalls", 0),
        data.get("rendererMemoryGeometries", 0),
        data.get("rendererMemoryTextures", 0),
    )
    log.info(
        "Shadow timings: off_p50=%.2f off_p95=%.2f "
        "medium_p50=%.2f medium_p95=%.2f high_p50=%.2f high_p95=%.2f",
        data.get("shadowOffFrameMsP50", 0.0),
        data.get("shadowOffFrameMsP95", 0.0),
        data.get("shadowMediumFrameMsP50", 0.0),
        data.get("shadowMediumFrameMsP95", 0.0),
        data.get("shadowHighFrameMsP50", 0.0),
        data.get("shadowHighFrameMsP95", 0.0),
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
