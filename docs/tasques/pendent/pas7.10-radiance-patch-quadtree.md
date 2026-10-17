# Pas 7.10 — Skyglow físic — RadiancePatch, quadtree adaptatiu i amplada angular

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
- [Pas 7.9](pas7.9-emission-region-watershed.md)

**En depenen:**
- [Pas 7.17](pas7.17-terrain-curvature.md)
- [Pas 7.21](pas7.21-dome-profile-pchip.md)

## Codi existent a reutilitzar

- `backend/src/terralab3d/domain/light_pollution/` i ports/adaptadors actuals.
- `backend/src/terralab3d/infrastructure/adapters/dem/adapter.py` quan hi hagi geometria/ràster.
- Contractes/bridge existents; no crear un segon canal paral·lel.

## Flux tècnic

EmissionRegion → quadtree intern → aproximació puntual candidata → contrast amb integració/submostreig d'àrea independent → refinament per error → patches → projecció topocèntrica i widths.

## Errors, cancel·lació i recursos

- Dades absents/corruptes tenen estat explícit i procedència.
- Resultats tardans es descarten; recursos grans no es dupliquen pel bridge.
- Risc: Explosió de patches propers.
- Risc: estimar `ε_patch` amb la mateixa aproximació puntual i no detectar el seu biaix.
- Rollback: integració d'àrea/subcel·les per patches que no compleixen el pressupost; mai fusió no controlada.

## Tasques

- [ ] Implementar contractes i transformacions d'aquest pas.
- [ ] Afegir unitats, versions i procedència.
- [ ] Afegir proves numèriques/fixtures.
- [ ] Executar benchmark indicat.
- [ ] Actualitzar evidències i inventari segons estat real.

## Criteri de sortida

regió allargada, wrap 359°/1°, outlier feble i oclusió parcial. Comparació explícita punt vs integració d'àrea en camp proper. B5 preliminar `ε_patch` vs patches/error sense usar la mateixa fórmula com a únic oracle. Cap capacitat posterior queda marcada com a implementada.

## Proves i evidències obligatòries

- [ ] regió allargada, wrap 359°/1°, outlier feble i oclusió parcial.
- [ ] B5 preliminar `ε_patch` vs patches/error.
- [ ] Evidència reproduïble sota `docs/evidencies/pas7.10/`.
- [ ] `tools/validate_docs.py` i regressions afectades en verd.

## Fora d'abast

Cache global i renderer.

## Instrucció per a Codex

EmissionRegion → quadtree intern → error `I/r²×T×V` → patches → projecció topocèntrica i widths. Mantén les decisions congelades del dossier i registra qualsevol desviació amb evidència.

## Treball pendent

- [ ] Completar tasques, proves i evidències abans de moure el pas a `completat/`.