# Pas 7.7 — Skyglow físic — SourceModel espectral/angular, bases SPD i B2b

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Implementar la inferència de font separant SPD, escala DNB, model angular i incertesa, sense inferir un SPD ni una emissió hemisfèrica únics a partir de VNP46.

## Descripció funcional

Separa observació VNP46, model de mesura DNB, composició espectral i emissió angular.

## Fonts a consultar

- [`docs/skyglow/README.md`](../../skyglow/README.md).
- [`docs/normes-arquitectura.md`](../../normes-arquitectura.md) i [`docs/inventari-funcional.md`](../../inventari-funcional.md).
- [`04-justificacio-cientifica.md`](../../skyglow/04-justificacio-cientifica.md) i [`10-datasets-llicencies.md`](../../skyglow/10-datasets-llicencies.md).

## Objectiu

Implementar bases normalitzades, priors/ensemble i el contracte de model angular. F1 continua oberta: el pas no imposa Lambert ni calibra l'hemisferi amb VNP46 quasi-nadir.

## Dependències

**Depèn de:**
- [Pas 7.6](pas7.6-viirs-rsr.md)

**En depenen:**
- [Pas 7.8](pas7.8-vnp46-adapter.md)
- [Pas 7.19](pas7.19-uncertainty-registry.md)

## Codi existent a reutilitzar

- `backend/src/terralab3d/domain/light_pollution/` i ports/adaptadors actuals.
- `backend/src/terralab3d/infrastructure/adapters/dem/adapter.py` quan hi hagi geometria/ràster.
- Contractes/bridge existents; no crear un segon canal paral·lel.

## Flux tècnic

`ViirsSourceObservation` sintètica + RSR/BAND_INTEGRATED + `Φ_f`/pesos → escala/espectre per bandes + `UpwardEmissionModel` explícit → `SpectralSourceEstimate`; F1 no es tanca.

## Errors, cancel·lació i recursos

- Dades absents/corruptes tenen estat explícit i procedència.
- Resultats tardans es descarten; recursos grans no es dupliquen pel bridge.
- Risc: SPD sense llicència o prior massa rígid.
- Rollback: Base sintètica mínima amb confiança baixa.

## Tasques

- [ ] Implementar contractes i transformacions d'aquest pas.
- [ ] Afegir unitats, versions i procedència.
- [ ] Afegir proves numèriques/fixtures.
- [ ] Executar benchmark indicat.
- [ ] Actualitzar evidències i inventari segons estat real.

## Criteri de sortida

normalització DNB coherent, suma de pesos i absència de doble comptatge. B2b amb diverses bases només per cost/robustesa de l'ensemble, no per convertir-lo en un SPD únic. Fixtures angulars demostren que el model no assumeix Lambert implícitament. Cap capacitat posterior queda marcada com a implementada.

## Proves i evidències obligatòries

- [ ] conservació d'energia, suma de pesos i absència de doble comptatge.
- [ ] B2b amb 1/2/3/5 bases.
- [ ] Evidència reproduïble sota `docs/evidencies/pas7.7/`.
- [ ] `tools/validate_docs.py` i regressions afectades en verd.

## Fora d'abast

Biblioteca SPD definitiva o calibratge regional.

## Instrucció per a Codex

Separa SPD i emissió angular. VNP46 restringeix la mesura DNB però no autoritza una funció hemisfèrica única. Mantén F1 oberta i propaga la seva incertesa. Mantén les decisions congelades del dossier i registra qualsevol desviació amb evidència.

## Treball pendent

- [ ] Completar tasques, proves i evidències abans de moure el pas a `completat/`.