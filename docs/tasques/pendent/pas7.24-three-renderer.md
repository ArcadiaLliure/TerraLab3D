# Pas 7.24 — Skyglow físic — renderer Three.js lineal i doble buffer

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Visualitzar DomeProfile sense fer ciència al shader ni bloquejar el render thread.

## Descripció funcional

Substitueix el glow Bortle com a font física del skyglow artificial, sense eliminar el mode global de cel simulat que es conserva permanentment.

## Fonts a consultar

- [`docs/skyglow/README.md`](../../skyglow/README.md).
- [`03-pipeline-python-typescript-threejs.md`](../../skyglow/03-pipeline-python-typescript-threejs.md), [`07-benchmark-b0-b7.md`](../../skyglow/07-benchmark-b0-b7.md) i [`08-validacio-cientifica.md`](../../skyglow/08-validacio-cientifica.md).
- [`docs/normes-arquitectura.md`](../../normes-arquitectura.md).

## Objectiu

Visualitzar DomeProfile sense fer ciència al shader ni bloquejar el render thread.

## Dependències

**Depèn de:**
- [Pas 7.21](pas7.21-dome-profile-pchip.md)

**En depenen:**
- [Pas 7.25](pas7.25-debug-modes.md)

## Codi existent a reutilitzar

- `frontend/src/view/three/AtmosphereRenderer.ts` i `shaders/skyShader.ts` com a camí legacy a migrar, no com a física de referència.
- `frontend/src/bridge/`, `frontend/src/contracts/scene.ts` i recursos retinguts.
- Backend skyglow construït als passos anteriors.

## Flux tècnic

DomeProfile DTO → validació/revision → buffer inactiu → upload → swap → suma lineal → tone mapping.

## Errors, cancel·lació i recursos

- Resultats obsolets no arriben a escena; uploads i recursos tenen propietari/dispose.
- Comparacions científiques es fan abans de tone mapping.
- Risc: Banding, precisió GPU o stutter d'upload.
- Rollback: Conservar últim buffer vàlid o tornar explícitament al mode simulat; mai substituir silenciosament el mode físic.

## Tasques

- [ ] Implementar només l'abast d'aquest pas.
- [ ] Afegir revisions, observabilitat i lifecycle.
- [ ] Afegir proves de contracte i casos límit.
- [ ] Executar benchmark/validació indicats.
- [ ] Actualitzar README, inventari, MANUAL només si canvia comportament observable.

## Criteri de sortida

resultats tardans descartats, suma lineal i zero upload per frame. GPU upload, frame p95/p99 i stutter. El resultat queda documentat amb evidència reproduïble.

## Proves i evidències obligatòries

- [ ] resultats tardans descartats, suma lineal i zero upload per frame.
- [ ] GPU upload, frame p95/p99 i stutter.
- [ ] Evidència sota `docs/evidencies/pas7.24/`.
- [ ] `tools/validate_docs.py`, tests backend/frontend i regressions afectades en verd.

## Fora d'abast

Retirada del mode simulat: prohibida; el selector simulat/real és una funcionalitat permanent de la vertical 7.51+.

## Instrucció per a Codex

DomeProfile DTO → validació/revision → buffer inactiu → upload → swap → suma lineal → tone mapping. No eliminar el fallback legacy abans que el pas de tancament ho autoritzi amb evidència.

## Treball pendent

- [ ] Completar tasques, proves i evidències abans de moure el pas a `completat/`.