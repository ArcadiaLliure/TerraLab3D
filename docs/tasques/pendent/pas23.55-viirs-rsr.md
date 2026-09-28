# Pas 23.55 — Skyglow físic — RSR real NOAA-20/J1

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Incorporar loader/repository de RSR amb procedència i checksum sense assumir redistribució.

## Descripció funcional

Elimina aproximacions per centre, FWHM o rectangle.

## Fonts a consultar

- [`docs/skyglow/README.md`](../../skyglow/README.md).
- [`docs/normes-arquitectura.md`](../../normes-arquitectura.md) i [`docs/inventari-funcional.md`](../../inventari-funcional.md).
- [`04-justificacio-cientifica.md`](../../skyglow/04-justificacio-cientifica.md) i [`10-datasets-llicencies.md`](../../skyglow/10-datasets-llicencies.md).

## Objectiu

Incorporar loader/repository de RSR amb procedència i checksum sense assumir redistribució.

## Dependències

**Depèn de:**
- [Pas 23.54](pas23.54-spectral-bandset-b2a.md)

**En depenen:**
- [Pas 23.56](pas23.56-spectral-source-b2b.md)
- [Pas 23.57](pas23.57-viirs-adapter.md)

## Codi existent a reutilitzar

- `backend/src/terralab3d/domain/light_pollution/` i ports/adaptadors actuals.
- `backend/src/terralab3d/infrastructure/adapters/dem/adapter.py` quan hi hagi geometria/ràster.
- Contractes/bridge existents; no crear un segon canal paral·lel.

## Flux tècnic

recurs NOAA → validació λ/RSR → `ViirsSpectralResponse` → integració de normalització.

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

sanity checks dels paràmetres NOAA-20 i integral contra fixture. Mesurar cost de normalització offline; no entra al LOS. Cap capacitat posterior queda marcada com a implementada.

## Proves i evidències obligatòries

- [ ] sanity checks dels paràmetres NOAA-20 i integral contra fixture.
- [ ] Mesurar cost de normalització offline; no entra al LOS.
- [ ] Evidència reproduïble sota `docs/evidencies/pas23.55/`.
- [ ] `tools/validate_docs.py` i regressions afectades en verd.

## Fora d'abast

Detector-specific raw SDR si no és necessari a la primera vertical.

## Instrucció per a Codex

recurs NOAA → validació λ/RSR → `ViirsSpectralResponse` → integració de normalització. Mantén les decisions congelades del dossier i registra qualsevol desviació amb evidència.

## Treball pendent

- [ ] Completar tasques, proves i evidències abans de moure el pas a `completat/`.