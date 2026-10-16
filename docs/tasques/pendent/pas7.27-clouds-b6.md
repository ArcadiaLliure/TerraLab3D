# Pas 7.27 — Skyglow físic — CloudOptics single-scattering i benchmark B6

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Afegir núvols com a dispersors/absorbidors i derivar `A_skyglow`.

## Descripció funcional

Els núvols no són un multiplicador arbitrari d'entrada.

## Fonts a consultar

- [`docs/skyglow/README.md`](../../skyglow/README.md).
- [`03-pipeline-python-typescript-threejs.md`](../../skyglow/03-pipeline-python-typescript-threejs.md), [`07-benchmark-b0-b7.md`](../../skyglow/07-benchmark-b0-b7.md) i [`08-validacio-cientifica.md`](../../skyglow/08-validacio-cientifica.md).
- [`docs/normes-arquitectura.md`](../../normes-arquitectura.md).
- [`docs/cel-fisic/02-fisica-altura-limbe.md`](../../cel-fisic/02-fisica-altura-limbe.md) i [`04-contractes-validacio.md`](../../cel-fisic/04-contractes-validacio.md) per al contracte neutral `CloudOpticalState`.

## Objectiu

Afegir núvols com a dispersors/absorbidors i derivar `A_skyglow`.

## Dependències

**Depèn de:**
- [Pas 7.16](pas7.16-atmos-provider-era5-cams.md)
- [Pas 7.12](pas7.12-phase-aerosol-library.md)
- [Pas 7.14](pas7.14-gas-b4.md)

**En depenen:**
- [Pas 7.28](pas7.28-b7-homologacio-skyglow.md)
- [Pas 7.63 — Núvols del cel astral](pas7.63-clouds-horizon-terminator.md)

## Codi existent a reutilitzar

- `frontend/src/view/three/AtmosphereRenderer.ts` i `shaders/skyShader.ts` com a camí legacy a migrar, no com a física de referència.
- `frontend/src/bridge/`, `frontend/src/contracts/scene.ts` i recursos retinguts.
- Backend skyglow construït als passos anteriors.

## Flux tècnic

cloud microphysics/state → `CloudOpticalState(τ,ω0,g,cover,base,top,bandSetId)` → mateix Γ del kernel artificial → cloudy/clear diagnostic. Aquest pas **no** calcula dispersió solar/lunar.

## Errors, cancel·lació i recursos

- Resultats obsolets no arriben a escena; uploads i recursos tenen propietari/dispose.
- Comparacions científiques es fan abans de tone mapping.
- Risc: Subestimació sota overcast.
- Rollback: Clouds OFF/clear-sky explícit.

## Tasques

- [ ] Implementar només l'abast d'aquest pas.
- [ ] Definir/publicar `CloudOpticalState` com a contracte neutral reutilitzable, amb unitats, bandes, revisió i procedència; l'integrador artificial només en consumeix la part necessària.
- [ ] Mantenir separats `CloudDataProvider`, `CloudOpticsModel` i l'efecte radiatiu del `PropagationKernel`.
- [ ] Prohibir que aquest pas implementi Hillaire, Sol, Lluna, limbe o terminador; això és 7.63.
- [ ] Afegir revisions, observabilitat i lifecycle.
- [ ] Afegir proves de contracte i casos límit.
- [ ] Executar benchmark/validació indicats.
- [ ] Actualitzar README, inventari, MANUAL només si canvia comportament observable.

## Criteri de sortida

clear limit, A<1 o A>1 possible i cap amplificació hardcoded. B6 incremental amb capa òpticament prima/moderada. El resultat queda documentat amb evidència reproduïble.

## Proves i evidències obligatòries

- [ ] clear limit, A<1 o A>1 possible i cap amplificació hardcoded.
- [ ] B6 incremental amb capa òpticament prima/moderada.
- [ ] Evidència sota `docs/evidencies/pas7.27/`.
- [ ] `tools/validate_docs.py`, tests backend/frontend i regressions afectades en verd.

## Fora d'abast

Transport solar/lunar de núvols i multiple scattering astral; correspon al Pas 7.63.

## Instrucció per a Codex

cloud data → `CloudOpticalState` compartit → Γ del kernel **artificial** → cloudy/clear diagnostic. No implementar aquí Sol/Lluna. No eliminar el fallback legacy abans que el pas de tancament ho autoritzi amb evidència.

## Treball pendent

- [ ] Completar tasques, proves i evidències abans de moure el pas a `completat/`.