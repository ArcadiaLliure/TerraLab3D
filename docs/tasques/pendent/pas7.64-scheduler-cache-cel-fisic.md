# Pas 7.64 — Scheduler latest-wins, invalidació i caches del cel físic

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Garantir interactivitat temporal sense publicar estats obsolets ni recalcular LUT/camps que no han canviat físicament.

## Descripció funcional

El scheduler és monotònic per revisió, coalescea scrubbing i té caches pròpies del cel astral. Comparteix política d'error amb skyglow, no les seves entrades de cache.

## Fonts a consultar

- [Dossier del cel físic](../../cel-fisic/README.md), especialment [decisions tancades](../../cel-fisic/05-decisions-tancades.md) i [contractes](../../cel-fisic/04-contractes-validacio.md).
- [Normes d'arquitectura](../../normes-arquitectura.md) i [inventari funcional](../../inventari-funcional.md).
- [Dossier skyglow](../../skyglow/README.md) només per contractes compartits; no fusionar integradors.

## Objectiu

Garantir interactivitat temporal sense publicar estats obsolets ni recalcular LUT/camps que no han canviat físicament.

## Dependències

**Depèn de:**
- [Pas 7.63](pas7.63-clouds-horizon-terminator.md)

**En depenen:**
- [Pas 7.65](pas7.65-reference-solver.md)

## Codi existent a reutilitzar

RenderLoopImpl, bridge revisions, lifecycle, LUT/cache keys dels passos 7.56–7.60 i `RadiativeErrorBudget`.

## Flux tècnic

UI/time → `currentRevision` → coalescing latest → invalidation matrix → GPU/job → publish només si `resultRevision == currentRevision`.

## Errors, cancel·lació i recursos

- Revisions temporals latest-wins; cap resultat obsolet es publica.
- Dades o drets no verificats → `unavailable`, no dades inventades.
- **Risc:** cues de temps, flicker per revisió antiga, cache hit físicament invàlid o stutter.
- **Rollback:** cache/reuse OFF i recomputació conservadora; mode simulated continua disponible.

## Tasques

- [ ] Implementar invariant `publishedRevision <= requestedRevision` i publicar només la revisió actual.
- [ ] Mantenir màxim una petició efectiva pendent; pointermove/scrub coalescea al latest sense debounce perceptible.
- [ ] Rellotge normal: objectiu d'actualització física 1 Hz; scrub: màxim una avaluació SkyView nova per frame.
- [ ] Separar claus: òptica, observador/altura, geometria solar/lunar, cloud revision, natural-sky revision i recursos GPU.
- [ ] Reutilitzar Transmittance/MultipleScattering quan només canvia geometria de font si la parametrizació ho permet; SkyView s'invalida per Sol/Lluna/altura.
- [ ] Un resultat antic només entra a cache si la clau completa segueix vàlida; mai es publica sobre un estat nou.
- [ ] `spectralBandCount` invalida caches científiques dependents, no la dimensió RGB de SkyView.

## Criteri de sortida

Scrubbing i 1 s/s no creen backlog; cap resultat stale es publica i cada cache hit és justificable per claus + error budget.

## Proves i evidències obligatòries

- [ ] 100+ revisions ràpides amb publicació exclusiva de l'última;
- [ ] teleport, canvi AOD/cloud, canvi d'altura, rotació de càmera i canvi de `spectralBandCount`;
- [ ] context loss/recovery i jobs tardans;
- [ ] queue depth efectiva <=1 i cap integral artificial disparada pel frame loop.
- [ ] Evidències reproduïbles sota `docs/evidencies/pas7.64/`.
- [ ] `tools/validate_docs.py` i regressions afectades en verd abans de completar.

## Fora d'abast

Scheduler del `PropagationKernel` artificial, que continua al Pas 7.18.

## Instrucció per a Codex

revision monotònica + latest-wins + invalidació física → compute/reuse → publish només current. Respectar `simulated|physical`, la separació 7.1–7.50 / 7.51+, les unitats i les llicències. No donar per implementat un contracte buit.

## Treball pendent

- [ ] Completar tasques, proves i evidències abans de moure aquest document a `completat/`.
