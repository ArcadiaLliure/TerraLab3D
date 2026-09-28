# Pas 23.59 — Skyglow físic — RadiancePatch, quadtree adaptatiu i amplada angular

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Representar cada regió amb error controlat i calcular `W_physical/W_effective`.

## Descripció funcional

Permet fonts extenses i oclusió parcial sense un patch per píxel.

## Fonts a consultar

- [`docs/skyglow/README.md`](../../skyglow/README.md).
- [`docs/normes-arquitectura.md`](../../normes-arquitectura.md) i [`docs/inventari-funcional.md`](../../inventari-funcional.md).
- [`04-justificacio-cientifica.md`](../../skyglow/04-justificacio-cientifica.md) i [`10-datasets-llicencies.md`](../../skyglow/10-datasets-llicencies.md).

## Objectiu

Representar cada regió amb error controlat i calcular `W_physical/W_effective`.

## Dependències

**Depèn de:**
- [Pas 23.58](pas23.58-emission-region-watershed.md)

**En depenen:**
- [Pas 23.66](pas23.66-terrain-curvature.md)
- [Pas 23.69](pas23.69-dome-profile-pchip.md)

## Codi existent a reutilitzar

- `backend/src/terralab3d/domain/light_pollution/` i ports/adaptadors actuals.
- `backend/src/terralab3d/infrastructure/adapters/dem/adapter.py` quan hi hagi geometria/ràster.
- Contractes/bridge existents; no crear un segon canal paral·lel.

## Flux tècnic

EmissionRegion → quadtree intern → error `I/r²×T×V` → patches → projecció topocèntrica i widths.

## Errors, cancel·lació i recursos

- Dades absents/corruptes tenen estat explícit i procedència.
- Resultats tardans es descarten; recursos grans no es dupliquen pel bridge.
- Risc: Explosió de patches propers.
- Rollback: Refinament més conservador; mai fusió no controlada.

## Tasques

- [ ] Implementar contractes i transformacions d'aquest pas.
- [ ] Afegir unitats, versions i procedència.
- [ ] Afegir proves numèriques/fixtures.
- [ ] Executar benchmark indicat.
- [ ] Actualitzar evidències i inventari segons estat real.

## Criteri de sortida

regió allargada, wrap 359°/1°, outlier feble i oclusió parcial. B5 preliminar `ε_patch` vs patches/error. Cap capacitat posterior queda marcada com a implementada.

## Proves i evidències obligatòries

- [ ] regió allargada, wrap 359°/1°, outlier feble i oclusió parcial.
- [ ] B5 preliminar `ε_patch` vs patches/error.
- [ ] Evidència reproduïble sota `docs/evidencies/pas23.59/`.
- [ ] `tools/validate_docs.py` i regressions afectades en verd.

## Fora d'abast

Cache global i renderer.

## Instrucció per a Codex

EmissionRegion → quadtree intern → error `I/r²×T×V` → patches → projecció topocèntrica i widths. Mantén les decisions congelades del dossier i registra qualsevol desviació amb evidència.

## Treball pendent

- [ ] Completar tasques, proves i evidències abans de moure el pas a `completat/`.