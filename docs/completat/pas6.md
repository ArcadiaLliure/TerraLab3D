# Pas 6 — Sistema de picking estel·lar precís

> Estat: **completat**
> Classificat mitjançant implementació, proves i validacions del repositori.

## Resultat funcional palpable

Es pot fer clic de manera precisa i determinista sobre una estrella del camp cel·lar (Gaia o fallback). El marker de selecció screen-space segueix l'estrella seleccionada encara que la càmera es mogui, i la informació científica (identitat real de catàleg) es recupera al frontend sense readback de GPU, enviant només l'ID als sistemes rellevants.

## Fonts TerraLab a consultar

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

## Criteri de sortida

Es poden seleccionar estrelles denses del catàleg Gaia i el marker mai es perd en moure la càmera, demostrant un circuit de dades sencer.

## Evidència obligatòria

- [ ] Captura de vídeo fent pan i picking simultani.
- [ ] Tests superats demostrant que els ids en uint32 sobrepassen els problemes de float32 antics.

## Fora d’abast del pas

No inclou menús contextuals de target o GOTO automàtic.

> **Nota**: El "Pas 6" original (Cel diürn, nocturn, crepuscle i atmosfera visual contínua) s'ha mogut a l'annex per poder donar prioritat a aquest sistema de picking a petició de l'usuari.
