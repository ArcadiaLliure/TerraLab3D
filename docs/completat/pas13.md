# Pas 13 — Picking real, hover, selecció i inspecció d’objectes

> Estat: **completat**
> Classificat mitjançant implementació, proves i validacions del repositori.

## Resultat funcional palpable

L’usuari pot passar el cursor i clicar estrelles, cossos, NGC i elements compatibles, veure’n informació i centrar-los.

## Fonts TerraLab a consultar

- `TerraLab/core/rendering_contracts/contracts.py` — `PickResult`
- `TerraLab/ui/astro_canvas.py` — gestió de resultats
- `TerraLab/runtime/offscreen_renderer.py` — picking actual
- `TerraLab/render/threejs/*` — picking existent o provisional

## Objectiu

Completar aquesta vertical funcional de punta a punta, mantenint la separació de responsabilitats i sense anticipar funcionalitats posteriors que no siguin imprescindibles.

## Tasques

- [ ] Definir `PickRequest` i `PickResult` amb ID de petició i generació d’escena.
- [ ] Implementar picking real de Three.js; prohibir resultats sintètics o count-only.
- [ ] Implementar estratègia eficient per punts estel·lars i instàncies.
- [ ] Implementar hover amb throttling i prioritat entre capes.
- [ ] Rebutjar resultats de generacions obsoletes.
- [ ] Mantenir l’estat de selecció autoritatiu a l’aplicació.
- [ ] Mostrar ressaltat, pols o contorn sense recrear l’objecte.
- [ ] Crear un panell d’inspecció amb dades científiques disponibles.
- [ ] Afegir accions de focus, seguiment i neteja de selecció.
- [ ] Gestionar objectes ocults o recursos descarregats durant una selecció.
- [ ] Preparar extensió per terreny, mesures i constel·lacions.
- [ ] Comparar radi de selecció i comportament amb TerraLab.

## Criteri de sortida

Cada objecte visible important es pot seleccionar mitjançant geometria real; els resultats stale no alteren l’estat; la informació i el focus funcionen de punta a punta.

## Evidència obligatòria

- [ ] Proves d’ID/generació i descart stale.
- [ ] Vídeo de hover i selecció de cada tipus.
- [ ] Mesura de latència de picking P50/P95.
- [ ] Prova amb objectes superposats.

## Fora d’abast del pas

El picking de terreny i overlays s’afegirà amb les seves verticals.
