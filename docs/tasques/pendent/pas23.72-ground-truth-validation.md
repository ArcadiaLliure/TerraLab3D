# Pas 23.72 — Skyglow físic — validació TESS/SQM/all-sky

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Comparar prediccions amb mesures reals separant calibratge i validació.

## Descripció funcional

Simula resposta espectral/FOV i aplica leave-one-site-out.

## Fonts a consultar

- [`docs/skyglow/README.md`](../../skyglow/README.md).
- [`03-pipeline-python-typescript-threejs.md`](../../skyglow/03-pipeline-python-typescript-threejs.md), [`07-benchmark-b0-b7.md`](../../skyglow/07-benchmark-b0-b7.md) i [`08-validacio-cientifica.md`](../../skyglow/08-validacio-cientifica.md).
- [`docs/normes-arquitectura.md`](../../normes-arquitectura.md).

## Objectiu

Comparar prediccions amb mesures reals separant calibratge i validació.

## Dependències

**Depèn de:**
- [Pas 23.69](pas23.69-dome-profile-pchip.md)
- [Pas 23.65](pas23.65-atmos-provider-era5-cams.md)
- [Pas 23.68](pas23.68-uncertainty-registry.md)

**En depenen:**
- [Pas 23.74](pas23.74-b7-homologacio-skyglow.md)

## Codi existent a reutilitzar

- `frontend/src/view/three/AtmosphereRenderer.ts` i `shaders/skyShader.ts` com a camí legacy a migrar, no com a física de referència.
- `frontend/src/bridge/`, `frontend/src/contracts/scene.ts` i recursos retinguts.
- Backend skyglow construït als passos anteriors.

## Flux tècnic

observacions calibrades + metadata → simulació sensor → join temporal/geogràfic → mètriques/intervals.

## Errors, cancel·lació i recursos

- Resultats obsolets no arriben a escena; uploads i recursos tenen propietari/dispose.
- Comparacions científiques es fan abans de tone mapping.
- Risc: Ground truth heterogeni o meteorologia desconeguda.
- Rollback: Campanya exploratòria sense promoure paràmetres.

## Tasques

- [ ] Implementar només l'abast d'aquest pas.
- [ ] Afegir revisions, observabilitat i lifecycle.
- [ ] Afegir proves de contracte i casos límit.
- [ ] Executar benchmark/validació indicats.
- [ ] Actualitzar README, inventari, MANUAL només si canvia comportament observable.

## Criteri de sortida

data leakage checks i sensor-response golden. Informe científic; no benchmark runtime. El resultat queda documentat amb evidència reproduïble.

## Proves i evidències obligatòries

- [ ] data leakage checks i sensor-response golden.
- [ ] Informe científic; no benchmark runtime.
- [ ] Evidència sota `docs/evidencies/pas23.72/`.
- [ ] `tools/validate_docs.py`, tests backend/frontend i regressions afectades en verd.

## Fora d'abast

Reajustar el model sobre el conjunt de test.

## Instrucció per a Codex

observacions calibrades + metadata → simulació sensor → join temporal/geogràfic → mètriques/intervals. No eliminar el fallback legacy abans que el pas de tancament ho autoritzi amb evidència.

## Treball pendent

- [ ] Completar tasques, proves i evidències abans de moure el pas a `completat/`.