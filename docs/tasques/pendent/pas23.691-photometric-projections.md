# Pas 23.691 — Skyglow físic — projeccions fotomètriques, SQM/TESS i BortleEquivalent

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Projectar radiància física a luminància i sensors sense alterar ni recalibrar el PropagationKernel.

## Descripció funcional

Afegeix adaptadors post-kernel per luminància fotòpica, SQM, TESS-W i sensors futurs, amb resposta espectral/FOV/calibratge versionats. Defineix `BortleEquivalent` com a diagnòstic, no com a magnitud física.

## Fonts a consultar

- [`01-especificacio-algorismes.md`](../../skyglow/01-especificacio-algorismes.md), [`04-justificacio-cientifica.md`](../../skyglow/04-justificacio-cientifica.md), [`06-contractes-dades.md`](../../skyglow/06-contractes-dades.md) i [`08-validacio-cientifica.md`](../../skyglow/08-validacio-cientifica.md).
- [ADR-017](../../skyglow/adrs/ADR-017-zenith-photometric-projections.md).

## Objectiu

Produir projeccions auditables a partir de `PropagationResult`/`DomeProfile`, sense cap nova integral LOS ni conversió directa VIIRS→SQM.

## Dependències

**Depèn de:**
- [Pas 23.681](pas23.681-zenith-absolute-gate.md)
- [Pas 23.69](pas23.69-dome-profile-pchip.md)

**En depenen:**
- [Pas 23.692](pas23.692-sky-radiance-composition.md)
- [Pas 23.72](pas23.72-ground-truth-validation.md)

## Codi existent a reutilitzar

- Bandes/espectre i `PropagationResult` dels passos previs.
- RSR/FOV/calibratge de sensors com a recursos versionats.
- Bridge existent només per DTO compactes; cap física al shader.

## Flux tècnic

radiància espectral/de bandes → pesos CIE o sensor precomputats → integració espectral/FOV → `PhotometricProjection` → diagnòstics; política versionada opcional → `BortleEquivalent`.

## Errors, cancel·lació i recursos

- Resposta espectral, FOV o zero point absent implica projecció `unavailable`, no fallback numèric silenciós.
- Els pesos per band set/sensor es precomputen i cachegen; la projecció no reinvoca el kernel.
- Bortle no s'usa per calibrar la radiància.

## Tasques

- [ ] Implementar contracte `PhotometricProjection`.
- [ ] Implementar luminància fotòpica amb funció CIE versionada.
- [ ] Implementar models SQM/TESS amb resposta espectral, FOV i calibratge identificables.
- [ ] Definir `bortlePolicyId` i semàntica `BortleEquivalent`.
- [ ] Vectoritzar/cachejar pesos de projecció per evitar cost per LOS.

## Criteri de sortida

Les projeccions coincideixen amb integració espectral fina dins tolerància, SQM/TESS respecten el model de sensor, cap factor universal substitueix la resposta real i el cost és post-processament petit respecte del kernel.

## Proves i evidències obligatòries

- [ ] golden fotòpic contra espectre fi.
- [ ] sensor-response/FOV/zero-point fixtures.
- [ ] mateix `PropagationResult` produeix projeccions diferents quan canvia el sensor sense recompute.
- [ ] `BortleEquivalent` no es presenta com a ground truth.
- [ ] Evidència sota `docs/evidencies/pas23.691/`.

## Fora d'abast

Model natural/lunar complet i calibratge regional de la política Bortle.

## Instrucció per a Codex

Mantén totes les projeccions després del kernel; qualsevol dada insuficient es declara. No ajustis la radiància física per fer quadrar una lectura SQM.

## Treball pendent

- [ ] Completar tasques, proves i evidències abans de moure aquest document a `completat/`.
