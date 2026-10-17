# Pas 7.8 — Skyglow físic — adaptador VNP46 i qualitat de baixa radiància

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Convertir el producte VNP46 seleccionat a `ViirsSourceObservation` preservant producte/release/data, unitat, qualitat i baixa radiància sense confondre observació i emissió.

## Descripció funcional

VNP46 és la família operativa. DNB SDR/VNL resten com a documentació/fixtures del model de mesura, no com a entrada primària de la v1.

## Fonts a consultar

- [`docs/skyglow/README.md`](../../skyglow/README.md).
- [`docs/normes-arquitectura.md`](../../normes-arquitectura.md) i [`docs/inventari-funcional.md`](../../inventari-funcional.md).
- [`04-justificacio-cientifica.md`](../../skyglow/04-justificacio-cientifica.md) i [`10-datasets-llicencies.md`](../../skyglow/10-datasets-llicencies.md).

## Objectiu

Convertir el producte/release VNP46 que es decideixi a una observació mínima i traçable, sense `max(0,·)`, registrant la restricció de baixa radiància pre/post-2017 i sense duplicar correccions ja aplicades pel producte.

## Dependències

**Depèn de:**
- [Pas 7.6](pas7.6-viirs-rsr.md)
- [Pas 7.7](pas7.7-spectral-source-b2b.md)

**En depenen:**
- [Pas 7.9](pas7.9-emission-region-watershed.md)
- [Pas 7.20](pas7.20-zenith-absolute-gate.md)

## Codi existent a reutilitzar

- `backend/src/terralab3d/domain/light_pollution/` i ports/adaptadors actuals.
- `backend/src/terralab3d/infrastructure/adapters/dem/adapter.py` quan hi hagi geometria/ràster.
- Contractes/bridge existents; no crear un segon canal paral·lel.

## Flux tècnic

VNP46 producte/release/data → quality/nodata/CRS/unitat declarada → `ViirsSourceObservation` → model DNB/RSR → `SourceModel`. Stray light: a confirmar segons producte; no corregir dues vegades.

## Errors, cancel·lació i recursos

- Dades absents/corruptes tenen estat explícit i procedència.
- Resultats tardans es descarten; recursos grans no es dupliquen pel bridge.
- Risc: Confondre radiància observada amb emissió de superfície o aplicar dues vegades una correcció del producte.
- Risc: clippar valors negatius/prop de zero i crear un biaix sistemàtic de fonts febles.
- Rollback: observació `unavailable`/no usable; no fabricar emissió.

## Tasques

- [ ] Implementar contractes i transformacions d'aquest pas.
- [ ] Afegir unitats, versions i procedència.
- [ ] Afegir proves numèriques/fixtures.
- [ ] Executar benchmark indicat.
- [ ] Actualitzar evidències i inventari segons estat real.

## Criteri de sortida

fixtures VNP46 de producte/release/data, unitat, nodata/quality, valors negatius/prop de zero i restricció temporal 2017. Cap `max(0,·)` silenciós. La unitat DNB no es hardcodeja des de l'ATBD pendent. Cap capacitat posterior queda marcada com a implementada.

## Proves i evidències obligatòries

- [ ] fixtures de raster, unit conversion, nodata i mismatch de producte.
- [ ] Throughput d'ingestió separat del kernel.
- [ ] Evidència reproduïble sota `docs/evidencies/pas7.8/`.
- [ ] `tools/validate_docs.py` i regressions afectades en verd.

## Fora d'abast

Gestor de descàrregues complet del Pas 24.

## Instrucció per a Codex

VNP46 → observació immutable → model DNB/RSR → SourceModel. No assumeixis Lambert, no clipis baixa radiància i no apliquis stray light si el producte/release ja la incorpora. Mantén les decisions congelades del dossier i registra qualsevol desviació amb evidència.

## Treball pendent

- [ ] Completar tasques, proves i evidències abans de moure el pas a `completat/`.