# Pas 7.63 — Núvols físics, horitzó, ombra planetària i terminador

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Aplicar `CloudOpticalState` compartit al transport solar/lunar/natural i tancar la geometria d'il·luminació del terminador sense barrejar el kernel artificial.

## Descripció funcional

Les núvols es representen per propietats òptiques auditables, no textures alpha. La visibilitat Sol→mostra i mostra→observador, Terra/DEM i trajectes tangents decideixen crepuscle, ombra i limbe.

## Fonts a consultar

- [Dossier del cel físic](../../cel-fisic/README.md), especialment [decisions tancades](../../cel-fisic/05-decisions-tancades.md) i [contractes](../../cel-fisic/04-contractes-validacio.md).
- [Normes d'arquitectura](../../normes-arquitectura.md) i [inventari funcional](../../inventari-funcional.md).
- [Dossier skyglow](../../skyglow/README.md) només per contractes compartits; no fusionar integradors.

## Objectiu

Aplicar `CloudOpticalState` compartit al transport solar/lunar/natural i tancar la geometria d'il·luminació del terminador sense barrejar el kernel artificial.

## Dependències

**Depèn de:**
- [Pas 7.62](pas7.62-radiative-error-budget.md)
- [Pas 7.23 — CloudOpticalState artificial](pas7.23-clouds-b6.md)

**En depenen:**
- [Pas 7.64](pas7.64-scheduler-cache-cel-fisic.md)

## Codi existent a reutilitzar

`CloudOpticalState` de 7.23, providers ERA5/CAMS de 7.16, optical state, Hillaire de 7.56, DEM/horitzó i limbe de 7.58.

## Flux tècnic

CloudDataProvider → CloudOpticsModel → `CloudOpticalState(τ,ω0,g,cover,base,top)` → transport astral delta-Eddington/Beer-Lambert + visibilitat Terra/DEM.

## Errors, cancel·lació i recursos

- Revisions temporals latest-wins; cap resultat obsolet es publica.
- Dades o drets no verificats → `unavailable`, no dades inventades.
- **Risc:** subestimar núvols gruixudes, doble comptar scattering o usar cloud cover com a simple multiplicador.
- **Rollback:** clear-sky explícit o cloud component `unavailable`; mai textura artística en `physical`.

## Tasques

- [ ] Consumir el mateix `CloudOpticalState` neutral de 7.23, sense reutilitzar el seu integrador artificial.
- [ ] Baseline: transmissió Beer-Lambert + fase direccional; compensar multiple scattering de capa amb delta-Eddington i declarar-ne límits.
- [ ] Separar `CloudDataProvider` de la conversió microfísica→òptica; ERA5/CAMS és un provider, no el model radiatiu.
- [ ] Avaluar visibilitat Sol/Lluna→mostra i mostra→observador amb Terra/DEM; un Sol sota l'horitzó de l'observador pot il·luminar capes altes.
- [ ] Fer coherent terminador, ombra planetària i limbe amb el mateix estat de núvols/atmosfera.
- [ ] Propagar envelopes de `τ/ω0/g` al `RadiativeErrorBudget`; sense envelope segur, pruning OFF.

## Criteri de sortida

Clear-sky, capa fina/moderada i casos de núvol gruixut degradat explícitament tenen estat físic traçable; terminador/limbe no depenen de hacks visuals.

## Proves i evidències obligatòries

- [ ] clear, `τ≈0.1,1,5,20`, líquid/gel quan el provider ho permet;
- [ ] comparació de transmissió/fluxos amb ecRad/discrete ordinates o fixtures equivalents;
- [ ] Sol sota horitzó, terminador i costat dia/nit del limbe;
- [ ] cap amplificació hardcoded ni doble scattering entre integradors.
- [ ] Evidències reproduïbles sota `docs/evidencies/pas7.63/`.
- [ ] `tools/validate_docs.py` i regressions afectades en verd abans de completar.

## Fora d'abast

Volumetria meteorològica 3D completa o Monte Carlo cloud en runtime.

## Instrucció per a Codex

`CloudOpticalState` compartit → integrador astral propi + geometria Terra/DEM → radiància; el Pas 7.23 continua exclusivament artificial. Respectar `simulated|physical`, la separació 7.1–7.50 / 7.51+, les unitats i les llicències. No donar per implementat un contracte buit.

## Treball pendent

- [ ] Completar tasques, proves i evidències abans de moure aquest document a `completat/`.
