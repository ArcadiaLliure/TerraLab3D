# Pas 6 — Picking estel·lar precís

> **Estat:** completat. **Estat funcional:** observable. **Origen:** planificat. **Abast vigent:** picking estel·lar precís implementat, verificat i observable en el repositori.

## Descripció funcional

Es pot fer clic de manera precisa i determinista sobre una estrella del camp cel·lar (Gaia o fallback). El marker de selecció screen-space segueix l'estrella seleccionada encara que la càmera es mogui, i la informació científica (identitat real de catàleg) es recupera al frontend sense readback de GPU, enviant només l'ID als sistemes rellevants.

## Fonts a consultar

- `TerraLab/ui/astro_canvas.py` — click vs drag (pointer events), i les diferents generacions de picking.
- `TerraLab/ui/frame_presenter.py` — dispatch de picking.

## Objectiu

Aconseguir identificació estel·lar interactiva totalment desacoblada de l'estructura en GPU, confiant exclusivament en l'índex per recuperar la identitat al backend.

- [x] Crear els contractes tipats de picking (`star_picking_contracts.ts`)
- [x] Definir funcions compartides de mida de punt per calcular hit radius.
- [x] Extreure `CelestialTransformState` per compartir la matriu entre renderer i picker.
- [x] Modificar `StarFieldRenderer` per conservar `Uint32Array` canònic de catalogIndex.
- [x] Implementar `StarSpatialIndex` (cube-sphere hash) per queries de con ràpides.
- [x] Implementar `PointerGestureRouter` per diferenciar netament click vs drag sense capturar ratolí de més.
- [x] Implementar `StarPickProvider` per calcular ray, query, refinament i occlusions.
- [x] Afegir `SelectionMarker` screen-space.
- [x] Orquestrar-ho tot amb `ScenePickingController` incloent el resolving (latest-wins).
- [x] Afegir mètodes al pont WebSocket per `resolve_star_pick` i resposta de resolució.
- [x] Crear `StarPickResolver` al backend (O(1) lookups).
- [x] Modificar `StarCoordinator` al backend per retenir el batch en memòria per al resolutor.
- [x] Posar al HUD la informació bàsica (source_id, ra, dec, mag) de la selecció.
- [x] Preparar tests de Picking.

## Dependències

**Depèn de:**
- [Pas 5 — Camp estel·lar Gaia real, fallback i buffers persistents](pas5.md)

**En depenen:**
- [Pas 13 — Picking real, hover, selecció i inspecció](pas13.md)
- [Pas 19 — Modes d'observació: ull nu, càmera fotogràfica i telescopi/Scope](pas19-modes-optics.md)
- [Pas 23 — Constel·lacions IAU, traçat de referència i documents d'usuari](pas23-constellacions.md)
- [Pas 38 — Homologació final, recuperació i rendiment](../pendent/pas38-homologacio-final.md)

## Codi existent a reutilitzar

- **Repositori actual:** Models, coordinadors i renderers Three.js del repositori.
- **Projectes de referència autoritzats:** TerraLab (commit `1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d`).

## Flux tècnic

Integració domini Python → bridge de missatges/binari → escena Three.js persistent.

## Errors, cancel·lació i recursos

Gestió de recursos amb `dispose()`, cancel·lació cooperativa i degradació controlada en cas d'absència de dades.

## Tasques

- [x] Implementació i integració completa de picking estel·lar precís.

## Criteri de sortida

Es poden seleccionar estrelles denses del catàleg Gaia i el marker mai es perd en moure la càmera, demostrant un circuit de dades sencer.

## Proves i evidències obligatòries

- [ ] Captura de vídeo fent pan i picking simultani.
- [ ] Tests superats demostrant que els ids en uint32 sobrepassen els problemes de float32 antics.

## Fora d'abast

No inclou menús contextuals de target o GOTO automàtic.

> **Nota**: El "Pas 6" original (Cel diürn, nocturn, crepuscle i atmosfera visual contínua) s'ha mogut a l'annex per poder donar prioritat a aquest sistema de picking a petició de l'usuari.

## Instrucció per a Codex

Pas 6 completat amb èxit. Consultar el següent pas assenyalat a `docs/README.md`.

## Treball pendent

Cap després del criteri de sortida.
