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
import signal
import sys
import webbrowser
from typing import Any
from datetime import datetime, timedelta, timezone

from terralab3d.domain.time.engine import AstronomicalEngine
from terralab3d.domain.time.models import ClockMode, SimulationInstant, ClockState

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

    # ── 1. Compilar frontend ──────────────────────────────────────────
    try:
        dist_dir = bundle_frontend()
    except Exception as exc:
        log.error("La meva construcció del frontend ha fallat: %s", exc)
        return 1

    # ── 2. Crear pont i servidor ──────────────────────────────────────
    bridge = WebSocketBridge()
    server = TerraLabServer(dist_dir, bridge)

    loop = asyncio.get_running_loop()
    shutdown_requested = asyncio.Event()

    # Registrar manegadors de missatges del pont
    bridge.on("camera_changed", _on_camera_changed)
    bridge.on("viewport_resized", _on_viewport_resized)
    bridge.on("bridge_error", _on_bridge_error)

    # ── 3. Lògica d'Ubicació (Fase 2) ─────────────────────────────────
    from terralab3d.domain.observer.models import GeoLocation, ObserverProfile
    from terralab3d.domain.identifiers import ObserverId

    current_observer = ObserverProfile(
        observer_id=ObserverId("default"),
        location=GeoLocation(latitude_deg=41.189795, longitude_deg=1.210058),
        height_offset_m=0.0
    )

    async def broadcast_location() -> None:
        await bridge.send_observer_location_changed(
            lat=current_observer.location.latitude_deg,
            lon=current_observer.location.longitude_deg,
            elevation=current_observer.location.elevation_m or 0.0,
            effective_height=current_observer.effective_height_m,
            source="Pendent (sense DEM)"
        )

    async def _handle_set_location(data: dict[str, Any]) -> None:
        nonlocal current_observer
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
            
            await broadcast_location()
            log.info(
                "Ubicació de l'observador actualitzada a: %.4f, %.4f (alt: %.1f)",
                current_observer.location.latitude_deg,
                current_observer.location.longitude_deg,
                height,
            )
        except Exception as e:
            await bridge.send_location_error(str(e))
            log.warning("Error a l'actualitzar la ubicació: %s", e)

    async def _on_frontend_ready(data: dict[str, Any]) -> None:
        # Quan el frontend es connecta, enviem la ubicació inicial.
        await broadcast_location()
        await broadcast_time()

    bridge.on("set_observer_location", _handle_set_location)
    bridge.on("frontend_ready", _on_frontend_ready)

    # ── 3.1. Lògica de Temps (Fase 3) ────────────────────────────────
    engine = AstronomicalEngine()
    
    sim_time_utc = datetime.now(timezone.utc)
    is_realtime = True
    time_drag_active = False

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

    async def _handle_set_simulation_time(data: dict[str, Any]) -> None:
        nonlocal sim_time_utc, is_realtime
        try:
            iso_str = data.get("currentTimeIso")
            if iso_str:
                sim_time_utc = datetime.fromisoformat(iso_str)
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

    bridge.on("set_simulation_time", _handle_set_simulation_time)
    bridge.on("set_realtime_mode", _handle_set_realtime_mode)
    bridge.on("timeline_drag_started", _handle_timeline_drag_started)
    bridge.on("timeline_drag_finished", _handle_timeline_drag_finished)
    bridge.on("request_offset_day", _handle_request_offset_day)

    async def clock_ticker() -> None:
        """S'encarrega d'avançar el temps si està en temps real i publicar l'estat."""
        nonlocal sim_time_utc
        while not shutdown_requested.is_set():
            await asyncio.sleep(1.0)
            if is_realtime and not time_drag_active:
                sim_time_utc = datetime.now(timezone.utc)
                await broadcast_time()

    clock_task = asyncio.create_task(clock_ticker())

    # ── 4. Iniciar servidor ───────────────────────────────────────────
    url = await server.start()
    log.info("TerraLab3D a punt a %s", url)

    # ── 5. Obrir navegador ────────────────────────────────────────────
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



