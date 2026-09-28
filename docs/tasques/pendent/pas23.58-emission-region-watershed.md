# Pas 23.58 — Skyglow físic — EmissionRegion i watershed radiomètric

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Segmentar fonts per estructura radiomètrica, no per municipis.

## Descripció funcional

Implementa log-radiance, denoise, threshold, maxima/prominence, watershed i merge.

## Fonts a consultar

- [`docs/skyglow/README.md`](../../skyglow/README.md).
- [`docs/normes-arquitectura.md`](../../normes-arquitectura.md) i [`docs/inventari-funcional.md`](../../inventari-funcional.md).
- [`04-justificacio-cientifica.md`](../../skyglow/04-justificacio-cientifica.md) i [`10-datasets-llicencies.md`](../../skyglow/10-datasets-llicencies.md).

## Objectiu

Segmentar fonts per estructura radiomètrica, no per municipis.

## Dependències

**Depèn de:**
- [Pas 23.57](pas23.57-viirs-adapter.md)

**En depenen:**
- [Pas 23.59](pas23.59-radiance-patch-quadtree.md)

## Codi existent a reutilitzar

- `backend/src/terralab3d/domain/light_pollution/` i ports/adaptadors actuals.
- `backend/src/terralab3d/infrastructure/adapters/dem/adapter.py` quan hi hagi geometria/ràster.
- Contractes/bridge existents; no crear un segon canal paral·lel.

## Flux tècnic

raster validat → log-radiance → watershed → merge → `EmissionRegion[]` amb geometria i moments.

## Errors, cancel·lació i recursos

- Dades absents/corruptes tenen estat explícit i procedència.
- Resultats tardans es descarten; recursos grans no es dupliquen pel bridge.
- Risc: Sobre/infra-segmentació.
- Rollback: Paràmetres versionats i reproduïbles.

## Tasques

- [ ] Implementar contractes i transformacions d'aquest pas.
- [ ] Afegir unitats, versions i procedència.
- [ ] Afegir proves numèriques/fixtures.
- [ ] Executar benchmark indicat.
- [ ] Actualitzar evidències i inventari segons estat real.

## Criteri de sortida

dues conques unides per pont feble, font allargada, soroll i conservació radiomètrica. Cost de preprocessament per raster/tile. Cap capacitat posterior queda marcada com a implementada.

## Proves i evidències obligatòries

- [ ] dues conques unides per pont feble, font allargada, soroll i conservació radiomètrica.
- [ ] Cost de preprocessament per raster/tile.
- [ ] Evidència reproduïble sota `docs/evidencies/pas23.58/`.
- [ ] `tools/validate_docs.py` i regressions afectades en verd.

## Fora d'abast

Quadtree intern i oclusió parcial.

## Instrucció per a Codex

raster validat → log-radiance → watershed → merge → `EmissionRegion[]` amb geometria i moments. Mantén les decisions congelades del dossier i registra qualsevol desviació amb evidència.

## Treball pendent

- [ ] Completar tasques, proves i evidències abans de moure el pas a `completat/`.