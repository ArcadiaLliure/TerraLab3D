# Pas 7.28 — Skyglow físic — B7 FULL, SLO i tancament de skyglow artificial

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Executar la configuració candidata completa i fixar SLO basats en evidència.

## Descripció funcional

Tanca la vertical sense declarar rendiment o precisió per intuïció.

## Fonts a consultar

- [`docs/skyglow/README.md`](../../skyglow/README.md).
- [`03-pipeline-python-typescript-threejs.md`](../../skyglow/03-pipeline-python-typescript-threejs.md), [`07-benchmark-b0-b7.md`](../../skyglow/07-benchmark-b0-b7.md) i [`08-validacio-cientifica.md`](../../skyglow/08-validacio-cientifica.md).
- [`docs/normes-arquitectura.md`](../../normes-arquitectura.md).

## Objectiu

Executar la configuració candidata completa i fixar SLO basats en evidència.

## Dependències

**Depèn de:**
- [Pas 7.13](pas7.13-legendre-b3.md)
- [Pas 7.25](pas7.25-debug-modes.md)
- [Pas 7.26](pas7.26-ground-truth-validation.md)
- [Pas 7.27](pas7.27-clouds-b6.md)
- [Pas 7.23](pas7.23-sky-radiance-composition.md)

**En depenen:**
- [Pas 38 — Homologació final](pas38-homologacio-final.md)

## Codi existent a reutilitzar

- `frontend/src/view/three/AtmosphereRenderer.ts` i `shaders/skyShader.ts` com a camí legacy a migrar, no com a física de referència.
- `frontend/src/bridge/`, `frontend/src/contracts/scene.ts` i recursos retinguts.
- Backend skyglow construït als passos anteriors.

## Flux tècnic

VNP46/producte/release + configuració espectral activa + `SourceModel` + gate zenital + projeccions/composició + B7 + ground truth + comparació directe↔accelerat si aplica → frontera error↔cost → SLO → decisió shadow/default.

## Errors, cancel·lació i recursos

- Resultats obsolets no arriben a escena; uploads i recursos tenen propietari/dispose.
- Comparacions científiques es fan abans de tone mapping.
- Risc: Cap configuració compleix tots els SLO.
- Risc: una decisió bloquejant (F1/F5/V1/V3/S1/LOW-RAD/DNB-2017) queda amagada darrere un fallback o una constant.
- Rollback: Mantenir shadow/legacy i obrir un pas específic de millora.

## Tasques

- [ ] Implementar només l'abast d'aquest pas.
- [ ] Afegir revisions, observabilitat i lifecycle.
- [ ] Afegir proves de contracte i casos límit.
- [ ] Executar benchmark/validació indicats.
- [ ] Actualitzar README, inventari, MANUAL només si canvia comportament observable.

## Criteri de sortida

regressió completa, coherència matemàtica/unitats/contractes i **cap decisió bloquejant necessària per al domini homologat sense tancar**. Si F5 adopta l'opció B, l'homologació depèn explícitament del Pas 7.65. B7 AD OFF/ON, uncertainty OFF/ON, cache cold/warm/movement/prefetch/teleport i SLO multidimensional. Gate zenital mantingut, `BortleEquivalent` només reference, composició lineal correcta i `kernelIntegralsPerRenderFrame=0`. El resultat queda documentat amb evidència reproduïble.

## Proves i evidències obligatòries

- [ ] regressió completa, coherència matemàtica/unitats/contractes i cap pendent bloquejant ocult.
- [ ] B7 AD OFF/ON, uncertainty OFF/ON, cache cold/warm i SLO multidimensional.
- [ ] Si hi ha backend LUT/FFT/precomputat: comparar-lo contra la ruta directa i registrar domini/error/fallback.
- [ ] Auditar DATA-VNP46, F1, F5, V1, V3, S1, DNB-2017 i LOW-RAD abans de declarar homologació.
- [ ] Evidència sota `docs/evidencies/pas7.28/`.
- [ ] `tools/validate_docs.py`, tests backend/frontend i regressions afectades en verd.

## Fora d'abast

Multiple scattering general si no és requisit del producte.

## Instrucció per a Codex

No homologuis una acceleració perquè sigui ràpida ni una emissió perquè runtime i oracle coincideixin. Tanca només el domini que tingui producte VNP46, SourceModel, oracle, ground truth i criteris preregistrats traçables. No eliminar el fallback legacy abans que el pas de tancament ho autoritzi amb evidència.

## Treball pendent

- [ ] Completar tasques, proves i evidències abans de moure el pas a `completat/`.