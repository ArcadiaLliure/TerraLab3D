# Pas 23.71 — Skyglow físic — modes diagnòstics i observabilitat

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Connectar modes de depuració per fonts, LOS, tiles, fase, cache i incertesa.

## Descripció funcional

Fa inspeccionable cada component sense alterar la física.

## Fonts a consultar

- [`docs/skyglow/README.md`](../../skyglow/README.md).
- [`03-pipeline-python-typescript-threejs.md`](../../skyglow/03-pipeline-python-typescript-threejs.md), [`07-benchmark-b0-b7.md`](../../skyglow/07-benchmark-b0-b7.md) i [`08-validacio-cientifica.md`](../../skyglow/08-validacio-cientifica.md).
- [`docs/normes-arquitectura.md`](../../normes-arquitectura.md).

## Objectiu

Connectar modes de depuració per fonts, LOS, tiles, fase, cache i incertesa.

## Dependències

**Depèn de:**
- [Pas 23.70](pas23.70-three-renderer.md)

**En depenen:**
- [Pas 23.74](pas23.74-b7-homologacio-skyglow.md)

## Codi existent a reutilitzar

- `frontend/src/view/three/AtmosphereRenderer.ts` i `shaders/skyShader.ts` com a camí legacy a migrar, no com a física de referència.
- `frontend/src/bridge/`, `frontend/src/contracts/scene.ts` i recursos retinguts.
- Backend skyglow construït als passos anteriors.

## Flux tècnic

debug request → payload compacte → visualització fals color/overlay → telemetria.

## Errors, cancel·lació i recursos

- Resultats obsolets no arriben a escena; uploads i recursos tenen propietari/dispose.
- Comparacions científiques es fan abans de tone mapping.
- Risc: El debug altera timing o memòria.
- Rollback: Toggles desactivats.

## Tasques

- [ ] Implementar només l'abast d'aquest pas.
- [ ] Afegir revisions, observabilitat i lifecycle.
- [ ] Afegir proves de contracte i casos límit.
- [ ] Executar benchmark/validació indicats.
- [ ] Actualitzar README, inventari, MANUAL només si canvia comportament observable.

## Criteri de sortida

toggle cleanup, no leak, revisions obsoletes i debug OFF sense payload massiu. Overhead debug OFF i ON. El resultat queda documentat amb evidència reproduïble.

## Proves i evidències obligatòries

- [ ] toggle cleanup, no leak, revisions obsoletes i debug OFF sense payload massiu.
- [ ] Overhead debug OFF i ON.
- [ ] Evidència sota `docs/evidencies/pas23.71/`.
- [ ] `tools/validate_docs.py`, tests backend/frontend i regressions afectades en verd.

## Fora d'abast

Cap canvi de física o calibratge.

## Instrucció per a Codex

debug request → payload compacte → visualització fals color/overlay → telemetria. No eliminar el fallback legacy abans que el pas de tancament ho autoritzi amb evidència.

## Treball pendent

- [ ] Completar tasques, proves i evidències abans de moure el pas a `completat/`.