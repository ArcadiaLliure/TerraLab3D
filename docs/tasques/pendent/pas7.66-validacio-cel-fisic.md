# Pas 7.66 — Matriu de validació científica del cel físic

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Homologar radiometria, color, sensors, Luna, fons natural, núvols, altura i limbe contra els oracles del Pas 7.65 amb toleràncies explícites.

## Descripció funcional

Els errors numèrics del software es mesuren separats de la incertesa física de models i dades. La qualitat visual és una mètrica addicional, no una prova radiomètrica.

## Fonts a consultar

- [Dossier del cel físic](../../cel-fisic/README.md), especialment [decisions tancades](../../cel-fisic/05-decisions-tancades.md) i [contractes](../../cel-fisic/04-contractes-validacio.md).
- [Normes d'arquitectura](../../normes-arquitectura.md) i [inventari funcional](../../inventari-funcional.md).
- [Dossier skyglow](../../skyglow/README.md) només per contractes compartits; no fusionar integradors.

## Objectiu

Homologar radiometria, color, sensors, Luna, fons natural, núvols, altura i limbe contra els oracles del Pas 7.65 amb toleràncies explícites.

## Dependències

**Depèn de:**
- [Pas 7.65](pas7.65-reference-solver.md)

**En depenen:**
- [Pas 7.67](pas7.67-slo-rendiment-cel-fisic.md)

## Codi existent a reutilitzar

Fixtures/oracles de 7.65, `PhotometricProjectionService`, CIE/SQM/TESS, tests de limbe/DEM i modes simulated/physical.

## Flux tècnic

matriu d'escenaris → runtime + oracle → errors radiomètrics/instrumentals/geomètrics → uncertainty decomposition → pass/fail.

## Errors, cancel·lació i recursos

- Revisions temporals latest-wins; cap resultat obsolet es publica.
- Dades o drets no verificats → `unavailable`, no dades inventades.
- **Risc:** declarar precisió científica per aparença, amagar singularitats o barrejar error de model i implementació.
- **Rollback:** mantenir `physical` no homologat i documentar el domini fallit.

## Tasques

- [ ] Cobrir altura 0 m, muntanya, 10 km, 30 km, top-of-atmosphere i òrbita.
- [ ] Cobrir Sol +90/+30/+5/0/−6/−12/−18° i profundament ocult; vista zenit/horitzó/solar/90°/antisolar/limbe.
- [ ] Cobrir aerosols net/nominal/AOD alt; Luna plena, 30/60/90/>90°, perigeu/apogeu i eclipsi.
- [ ] Cobrir núvols clear i `τ≈0.1,1,5,20` quan el provider ho permet; fons natural baix/nominal/alt.
- [ ] Gates inicials: transmittance p95 <=2 %, radiància clear-sky p95 <=2 % fora singularitats, lunar software vs ROLO <=0.5 %, culling <=0.5 %, SQM/TESS solver <=1 % o tolerància instrumental més estricta.
- [ ] Separar aquests gates de les incerteses ROLO/aerosols/núvols/airglow/datasets.
- [ ] CIEDE2000 només com a regressió perceptual del resultat tone-mapped, mai com a criteri de pruning.

## Criteri de sortida

La matriu publica domini validat, errors de software, incerteses físiques i limitacions; cap resultat científic depèn del RGB de pantalla.

## Proves i evidències obligatòries

- [ ] goldens radiomètrics i instrumentals amb `L_floor`/error absolut prop de zero;
- [ ] continuïtat surface→space, simulated↔physical i frontera ROLO/extrapolació;
- [ ] geometria d'horitzó/limbe/ombra i eclipsis;
- [ ] cap benchmark de N bandes.
- [ ] Evidències reproduïbles sota `docs/evidencies/pas7.66/`.
- [ ] `tools/validate_docs.py` i regressions afectades en verd abans de completar.

## Fora d'abast

Prometre exactitud total del cel real igual als gates numèrics del software.

## Instrucció per a Codex

runtime + oracle independent → mètriques separades per radiància/sensor/geometria/visual → domini de validesa explícit. Respectar `simulated|physical`, la separació 7.1–7.50 / 7.51+, les unitats i les llicències. No donar per implementat un contracte buit.

## Treball pendent

- [ ] Completar tasques, proves i evidències abans de moure aquest document a `completat/`.
