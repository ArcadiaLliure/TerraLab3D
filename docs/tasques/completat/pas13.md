# Pas 13 — Picking real, hover, selecció i inspecció

> **Estat:** completat. **Estat funcional:** observable. **Origen:** planificat. **Abast vigent:** picking real, hover, selecció i inspecció implementat, verificat i observable en el repositori.

## Descripció funcional

L’usuari pot passar el cursor i clicar estrelles, cossos, NGC i elements compatibles, veure’n informació i centrar-los.

## Fonts a consultar

- `TerraLab/core/rendering_contracts/contracts.py` — `PickResult`
- `TerraLab/ui/astro_canvas.py` — gestió de resultats
- `TerraLab/runtime/offscreen_renderer.py` — picking actual
- `TerraLab/render/threejs/*` — picking existent o provisional

## Objectiu

Completar aquesta vertical funcional de punta a punta, mantenint la separació de responsabilitats i sense anticipar funcionalitats posteriors que no siguin imprescindibles.

## Dependències

**Depèn de:**
- [Pas 6 — Picking estel·lar precís](pas6.md)
- [Pas 12 — Cerca astronòmica, focus i seguiment](pas12.md)

**En depenen:**
- [Pas 19 — Modes d'observació: ull nu, càmera fotogràfica i telescopi/Scope](pas19-modes-optics.md)
- [Pas 21 — Eines de mesura esfèrica](pas21-eines-mesura.md)
- [Pas 23 — Constel·lacions IAU, traçat de referència i documents d'usuari](../pendent/pas23-constellacions.md)
- [Pas 38 — Homologació final, recuperació i rendiment](../pendent/pas38-homologacio-final.md)

## Codi existent a reutilitzar

- **Repositori actual:** Models, coordinadors i renderers Three.js del repositori.
- **Projectes de referència autoritzats:** TerraLab (commit `1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d`).

## Flux tècnic

Integració domini Python → bridge de missatges/binari → escena Three.js persistent.

## Errors, cancel·lació i recursos

Gestió de recursos amb `dispose()`, cancel·lació cooperativa i degradació controlada en cas d'absència de dades.

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

## Proves i evidències obligatòries

- [ ] Proves d’ID/generació i descart stale.
- [ ] Vídeo de hover i selecció de cada tipus.
- [ ] Mesura de latència de picking P50/P95.
- [ ] Prova amb objectes superposats.

## Fora d'abast

El picking de terreny i overlays s’afegirà amb les seves verticals.

## Instrucció per a Codex

Pas 13 completat amb èxit. Consultar el següent pas assenyalat a `docs/README.md`.

## Treball pendent

Cap després del criteri de sortida.
