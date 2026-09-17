# Pas 1 — Entorn 3D executable, càmera 360° i bridge Python ↔ Three.js

> **Estat:** completat. **Estat funcional:** observable. **Origen:** planificat. **Abast vigent:** entorn 3d executable, càmera 360° i bridge python ↔ three.js implementat, verificat i observable en el repositori.

## Descripció funcional

En executar `python -m terralab3d`, s’obre una aplicació real amb una escena Three.js 360°, una càmera navegable, un horitzó tècnic, punts cardinals i comunicació bidireccional amb Python.

## Fonts a consultar

- `TerraLab/__main__.py` i bootstrap actual
- `TerraLab/runtime/supervisor.py`
- `TerraLab/runtime/render_service.py`
- `TerraLab/ui/astro_canvas.py`
- `TerraLab/ui/canvas_mixins/interaction.py`
- `TerraLab/scene/camera.py` i `TerraLab/scene/projection.py`
- `TerraLab/render/threejs/*` i contractes actuals del host

## Objectiu

Completar aquesta vertical funcional de punta a punta, mantenint la separació de responsabilitats i sense anticipar funcionalitats posteriors que no siguin imprescindibles.

## Dependències

**Depèn de:**
- Cap pas previ.

**En depenen:**
- [Pas 2 — Ubicació geogràfica de l'observador i orientació local](pas2.md)
- [Pas 3.5 — Càmera translacional, mode caminar i mode avió](pas3.5.md)
- [Pas 4 — Grid celeste, brúixola, etiquetes i HUD](pas4.md)
- [Pas 5 — Camp estel·lar Gaia real, fallback i buffers persistents](pas5.md)
- [Pas 7 — Cel, atmosfera, contaminació lumínica i Bortle](pas7.md)
- [Pas 8 — Sol, Lluna i planetes amb posicions i aparença reals](pas8.md)
- [Pas 15 — Elevació real, perfil d'horitzó i oclusió](pas15.md)
- [Pas 21 — Eines de mesura esfèrica](pas21-eines-mesura.md)
- [Pas 38 — Homologació final, recuperació i rendiment](../pendent/pas38-homologacio-final.md)

## Codi existent a reutilitzar

- **Repositori actual:** Models, coordinadors i renderers Three.js del repositori.
- **Projectes de referència autoritzats:** TerraLab (commit `1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d`).

## Flux tècnic

Integració domini Python → bridge de missatges/binari → escena Three.js persistent.

## Errors, cancel·lació i recursos

Gestió de recursos amb `dispose()`, cancel·lació cooperativa i degradació controlada en cas d'absència de dades.

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

## Proves i evidències obligatòries

- [x] Vídeo o captura de l’arrencada, navegació, focus des de Python, resize i tancament.
- [x] Prova d’integració del handshake i dels missatges de càmera.
- [x] Prova de lifecycle amb arrencada-tancament-arrencada.
- [x] Mètriques de frame P50/P95 en l’escena tècnica.
- [x] Comptador que demostri zero round-trips Python per frame de càmera.

## Fora d'abast

No inclou encara coordenades astronòmiques, estrelles, cel físic, terreny real ni recursos binaris grans.

## Instrucció per a Codex

Pas 1 completat amb èxit. Consultar el següent pas assenyalat a `docs/README.md`.

## Treball pendent

Cap després del criteri de sortida.
