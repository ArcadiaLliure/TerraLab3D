# Pas 23.57 — Skyglow físic — adaptador de productes VIIRS/VNL/Black Marble

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Convertir productes reals a observacions de font amb semàntica, unitats i qualitat explícites.

## Descripció funcional

Diferencia DNB SDR, VNL i Black Marble abans del model de font.

## Fonts a consultar

- [`docs/skyglow/README.md`](../../skyglow/README.md).
- [`docs/normes-arquitectura.md`](../../normes-arquitectura.md) i [`docs/inventari-funcional.md`](../../inventari-funcional.md).
- [`04-justificacio-cientifica.md`](../../skyglow/04-justificacio-cientifica.md) i [`10-datasets-llicencies.md`](../../skyglow/10-datasets-llicencies.md).

## Objectiu

Convertir productes reals a observacions de font amb semàntica, unitats i qualitat explícites.

## Dependències

**Depèn de:**
- [Pas 23.55](pas23.55-viirs-rsr.md)

**En depenen:**
- [Pas 23.58](pas23.58-emission-region-watershed.md)

## Codi existent a reutilitzar

- `backend/src/terralab3d/domain/light_pollution/` i ports/adaptadors actuals.
- `backend/src/terralab3d/infrastructure/adapters/dem/adapter.py` quan hi hagi geometria/ràster.
- Contractes/bridge existents; no crear un segon canal paral·lel.

## Flux tècnic

raster/producte → quality/nodata/CRS/unitats → `ViirsSourceObservation` + provenance.

## Errors, cancel·lació i recursos

- Dades absents/corruptes tenen estat explícit i procedència.
- Resultats tardans es descarten; recursos grans no es dupliquen pel bridge.
- Risc: Confondre radiància TOA amb emissió de superfície.
- Rollback: Mantenir adapter legacy separat.

## Tasques

- [ ] Implementar contractes i transformacions d'aquest pas.
- [ ] Afegir unitats, versions i procedència.
- [ ] Afegir proves numèriques/fixtures.
- [ ] Executar benchmark indicat.
- [ ] Actualitzar evidències i inventari segons estat real.

## Criteri de sortida

fixtures de raster, unit conversion, nodata i mismatch de producte. Throughput d'ingestió separat del kernel. Cap capacitat posterior queda marcada com a implementada.

## Proves i evidències obligatòries

- [ ] fixtures de raster, unit conversion, nodata i mismatch de producte.
- [ ] Throughput d'ingestió separat del kernel.
- [ ] Evidència reproduïble sota `docs/evidencies/pas23.57/`.
- [ ] `tools/validate_docs.py` i regressions afectades en verd.

## Fora d'abast

Gestor de descàrregues complet del Pas 24.

## Instrucció per a Codex

raster/producte → quality/nodata/CRS/unitats → `ViirsSourceObservation` + provenance. Mantén les decisions congelades del dossier i registra qualsevol desviació amb evidència.

## Treball pendent

- [ ] Completar tasques, proves i evidències abans de moure el pas a `completat/`.