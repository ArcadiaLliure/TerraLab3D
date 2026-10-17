# Pas 7.6 — Skyglow físic — model de mesura DNB, RSR real i BAND_INTEGRATED

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Incorporar el model de mesura DNB amb RSR versionada, `BAND_INTEGRATED`, procedència i resolució compatible amb release/data sense assumir redistribució.

## Descripció funcional

Interpreta VNP46 mitjançant la semàntica DNB sense aproximar la RSR per centre/FWHM/rectangle.

## Fonts a consultar

- [`docs/skyglow/README.md`](../../skyglow/README.md).
- [`docs/normes-arquitectura.md`](../../normes-arquitectura.md) i [`docs/inventari-funcional.md`](../../inventari-funcional.md).
- [`04-justificacio-cientifica.md`](../../skyglow/04-justificacio-cientifica.md) i [`10-datasets-llicencies.md`](../../skyglow/10-datasets-llicencies.md).

## Objectiu

Incorporar loader/repository de RSR i l'operador `BAND_INTEGRATED`, amb procedència/checksum i resolució per release + data d'adquisició. La unitat exacta DNB queda pendent de verificació directa contra l'ATBD.

## Dependències

**Depèn de:**
- [Pas 7.5](pas7.5-spectral-bandset-b2a.md)

**En depenen:**
- [Pas 7.7](pas7.7-spectral-source-b2b.md)
- [Pas 7.8](pas7.8-vnp46-adapter.md)

## Codi existent a reutilitzar

- `backend/src/terralab3d/domain/light_pollution/` i ports/adaptadors actuals.
- `backend/src/terralab3d/infrastructure/adapters/dem/adapter.py` quan hi hagi geometria/ràster.
- Contractes/bridge existents; no crear un segon canal paral·lel.

## Flux tècnic

observació VNP46(producte/release/data) + recurs RSR → resolució RSR compatible → `ViirsSpectralResponse` + `measurementOperatorId=BAND_INTEGRATED` → normalització `A=L/∫S·R dλ`.

## Errors, cancel·lació i recursos

- Dades absents/corruptes tenen estat explícit i procedència.
- Resultats tardans es descarten; recursos grans no es dupliquen pel bridge.
- Risc: Drets de redistribució del ZIP.
- Rollback: Descàrrega externa obligatòria.

## Tasques

- [ ] Implementar contractes i transformacions d'aquest pas.
- [ ] Afegir unitats, versions i procedència.
- [ ] Afegir proves numèriques/fixtures.
- [ ] Executar benchmark indicat.
- [ ] Actualitzar evidències i inventari segons estat real.

## Criteri de sortida

fixture RSR/release/data, invariant de l'operador `BAND_INTEGRATED` i integral contra referència. No es dona per verificat cap unitat de l'ATBD encara pendent. Mesurar cost de normalització offline; no entra al LOS. Cap capacitat posterior queda marcada com a implementada.

## Proves i evidències obligatòries

- [ ] sanity checks dels paràmetres NOAA-20 i integral contra fixture.
- [ ] Mesurar cost de normalització offline; no entra al LOS.
- [ ] Evidència reproduïble sota `docs/evidencies/pas7.6/`.
- [ ] `tools/validate_docs.py` i regressions afectades en verd.

## Fora d'abast

Detector-specific raw SDR si no és necessari a la primera vertical.

## Instrucció per a Codex

RSR + release/data → `ViirsSpectralResponse` → `BAND_INTEGRATED` → normalització. No normalitzis la RSR per la seva integral per defecte i no codifiquis una unitat DNB no verificada. Mantén les decisions congelades del dossier i registra qualsevol desviació amb evidència.

## Treball pendent

- [ ] Completar tasques, proves i evidències abans de moure el pas a `completat/`.