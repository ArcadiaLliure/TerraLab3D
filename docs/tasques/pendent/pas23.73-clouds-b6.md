# Pas 23.73 — Skyglow físic — CloudOptics single-scattering i benchmark B6

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Afegir núvols com a dispersors/absorbidors i derivar `A_skyglow`.

## Descripció funcional

Els núvols no són un multiplicador arbitrari d'entrada.

## Fonts a consultar

- [`docs/skyglow/README.md`](../../skyglow/README.md).
- [`03-pipeline-python-typescript-threejs.md`](../../skyglow/03-pipeline-python-typescript-threejs.md), [`07-benchmark-b0-b7.md`](../../skyglow/07-benchmark-b0-b7.md) i [`08-validacio-cientifica.md`](../../skyglow/08-validacio-cientifica.md).
- [`docs/normes-arquitectura.md`](../../normes-arquitectura.md).

## Objectiu

Afegir núvols com a dispersors/absorbidors i derivar `A_skyglow`.

## Dependències

**Depèn de:**
- [Pas 23.65](pas23.65-atmos-provider-era5-cams.md)
- [Pas 23.61](pas23.61-phase-aerosol-library.md)
- [Pas 23.63](pas23.63-gas-b4.md)

**En depenen:**
- [Pas 23.74](pas23.74-b7-homologacio-skyglow.md)

## Codi existent a reutilitzar

- `frontend/src/view/three/AtmosphereRenderer.ts` i `shaders/skyShader.ts` com a camí legacy a migrar, no com a física de referència.
- `frontend/src/bridge/`, `frontend/src/contracts/scene.ts` i recursos retinguts.
- Backend skyglow construït als passos anteriors.

## Flux tècnic

cloud microphysics/state → β_ext,ω0,P → mateix Γ del kernel → cloudy/clear diagnostic.

## Errors, cancel·lació i recursos

- Resultats obsolets no arriben a escena; uploads i recursos tenen propietari/dispose.
- Comparacions científiques es fan abans de tone mapping.
- Risc: Subestimació sota overcast.
- Rollback: Clouds OFF/clear-sky explícit.

## Tasques

- [ ] Implementar només l'abast d'aquest pas.
- [ ] Afegir revisions, observabilitat i lifecycle.
- [ ] Afegir proves de contracte i casos límit.
- [ ] Executar benchmark/validació indicats.
- [ ] Actualitzar README, inventari, MANUAL només si canvia comportament observable.

## Criteri de sortida

clear limit, A<1 o A>1 possible i cap amplificació hardcoded. B6 incremental amb capa òpticament prima/moderada. El resultat queda documentat amb evidència reproduïble.

## Proves i evidències obligatòries

- [ ] clear limit, A<1 o A>1 possible i cap amplificació hardcoded.
- [ ] B6 incremental amb capa òpticament prima/moderada.
- [ ] Evidència sota `docs/evidencies/pas23.73/`.
- [ ] `tools/validate_docs.py`, tests backend/frontend i regressions afectades en verd.

## Fora d'abast

Multiple scattering de núvol gruixut.

## Instrucció per a Codex

cloud microphysics/state → β_ext,ω0,P → mateix Γ del kernel → cloudy/clear diagnostic. No eliminar el fallback legacy abans que el pas de tancament ho autoritzi amb evidència.

## Treball pendent

- [ ] Completar tasques, proves i evidències abans de moure el pas a `completat/`.