# Pas 1 — Entorn 3D executable, càmera 360° i bridge Python ↔ Three.js

> Estat: **completat**
> Classificat mitjançant implementació, proves i validacions del repositori.

## Resultat funcional palpable

En executar `python -m terralab3d`, s’obre una aplicació real amb una escena Three.js 360°, una càmera navegable, un horitzó tècnic, punts cardinals i comunicació bidireccional amb Python.

## Fonts TerraLab a consultar

- `TerraLab/__main__.py` i bootstrap actual
- `TerraLab/runtime/supervisor.py`
- `TerraLab/runtime/render_service.py`
- `TerraLab/ui/astro_canvas.py`
- `TerraLab/ui/canvas_mixins/interaction.py`
- `TerraLab/scene/camera.py` i `TerraLab/scene/projection.py`
- `TerraLab/render/threejs/*` i contractes actuals del host

## Objectiu

Completar aquesta vertical funcional de punta a punta, mantenint la separació de responsabilitats i sense anticipar funcionalitats posteriors que no siguin imprescindibles.

## Tasques

- [x] Definir l’entrypoint oficial `python -m terralab3d` i una única seqüència d’arrencada.
- [x] Escollir i implementar un host d’escriptori concret per al frontend Three.js sense crear dues rutes permanents.
- [x] Arrencar el backend Python, el frontend i el bridge amb ports locals assignats de manera segura.
- [x] Implementar un handshake tipat amb `frontend_ready`, versió de protocol, capacitats i identificador de sessió.
- [x] Crear `ThreeSceneHost` amb `Scene`, `PerspectiveCamera`, `WebGLRenderer` i un únic canvas.
- [x] Definir la convenció de món: eix vertical, nord, est, azimut, altitud i sentit de rotació.
- [x] Mostrar un horitzó tècnic circular, punts N/E/S/O, zenit i una primitiva de diagnòstic.
- [x] Implementar pan/orbit, zoom per FOV, límits verticals, teclat i redimensionament.
- [x] Mantenir el moviment i el render de càmera completament locals a TypeScript.
- [x] Publicar `camera_changed` a Python només al final del gest o amb throttling/coalescing.
- [x] Permetre que Python enviï `set_camera_pose` i `focus_direction` amb transició visual.
- [x] Implementar `viewport_resized`, `bridge_error`, `shutdown_requested` i `shutdown_complete`.
- [x] Gestionar desconnexió, reconnexió controlada i missatge d’error visible en comptes d’una pantalla negra.
- [x] Alliberar listeners, timers, sockets, renderer, geometries i materials en tancar.
- [x] Afegir una pantalla de diagnòstic mínima amb estat del bridge, FPS i generació de sessió.

## Criteri de sortida

L’aplicació s’obre des de Python, la càmera es mou i fa zoom amb fluïdesa sense esperar el backend, Python pot reposicionar-la, el resize no deforma la projecció, la pèrdua del bridge es mostra de manera explícita i el tancament no deixa processos, ports ni contextos WebGL vius.

## Evidència obligatòria

- [x] Vídeo o captura de l’arrencada, navegació, focus des de Python, resize i tancament.
- [x] Prova d’integració del handshake i dels missatges de càmera.
- [x] Prova de lifecycle amb arrencada-tancament-arrencada.
- [x] Mètriques de frame P50/P95 en l’escena tècnica.
- [x] Comptador que demostri zero round-trips Python per frame de càmera.

## Fora d’abast del pas

No inclou encara coordenades astronòmiques, estrelles, cel físic, terreny real ni recursos binaris grans.
