# Pas 7.65 — Solver espectral de referència i oracles científics

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Construir un camí offline/dev de referència que permeti verificar el runtime físic sense convertir-se en dependència de producció ni benchmark per escollir N.

## Descripció funcional

La qualitat científica no es valida perquè «s'assembla a Unreal». Es manté una jerarquia d'oracles independents per clear-sky, geometria/multiple scattering, Luna, fons natural, nubes i sensors.

## Fonts a consultar

- [Dossier del cel físic](../../cel-fisic/README.md), especialment [decisions tancades](../../cel-fisic/05-decisions-tancades.md) i [contractes](../../cel-fisic/04-contractes-validacio.md).
- [Normes d'arquitectura](../../normes-arquitectura.md) i [inventari funcional](../../inventari-funcional.md).
- [Dossier skyglow](../../skyglow/README.md) només per contractes compartits; no fusionar integradors.

## Objectiu

Construir un camí offline/dev de referència que permeti verificar el runtime físic sense convertir-se en dependència de producció ni benchmark per escollir N.

## Dependències

**Depèn de:**
- [Pas 7.64](pas7.64-scheduler-cache-cel-fisic.md)

**En depenen:**
- [Pas 7.66](pas7.66-validacio-cel-fisic.md)

## Codi existent a reutilitzar

Bruneton BSD-3, path tracer Hillaire MIT, ROLO/USGS, harness de tests científics i adapters offline.

## Flux tècnic

escenari congelat → oracle(s) independent(s) → fixture/resultat versionat → comparador unitats/radiància/color/sensor → informe.

## Errors, cancel·lació i recursos

- Revisions temporals latest-wins; cap resultat obsolet es publica.
- Dades o drets no verificats → `unavailable`, no dades inventades.
- **Risc:** validar un model contra si mateix, vendoritzar copyleft o confondre reference solver amb runtime.
- **Rollback:** oracle extern/manual amb fixtures reproduïbles; runtime no es promociona sense comparació.

## Tasques

- [ ] Bruneton CPU/espectral com a referència clear-sky de transmittance/scattering/colorimetria.
- [ ] Path tracer Hillaire com a segona referència per geometria planetària i multiple scattering.
- [ ] ROLO/USGS per irradiància lunar; LIME només com a contrast extern mentre no es vendoritzi.
- [ ] GAMBONS/ESO/SkyCalc com a referència externa del fons natural; no incorporar codi GPL ni datasets sense drets.
- [ ] ecRad/discrete ordinates o equivalent per fixtures de nubes; fixar versió/llicència quan s'utilitzi.
- [ ] Solucions analítiques per esfera, tangència, depressió d'horitzó i casos zero.
- [ ] Registrar unitats, versions, hashes i incertesa de cada oracle/fixture.
- [ ] Executar la configuració `spectralBandCount` activa; **no** fer sweep de N per seleccionar-la.

## Criteri de sortida

Cada família física té almenys un oracle independent o una solució analítica reproduïble, amb llicència/procedència i unitats registrades.

## Proves i evidències obligatòries

- [ ] mateix escenari reproduïble entre runs i plataformes de referència;
- [ ] comparació d'unitats i convencions abans de comparar nombres;
- [ ] detecció intencionada de regressions de signe, escala, geometria i gamma;
- [ ] cap dependència runtime GPL/LGPL introduïda pels oracles.
- [ ] Evidències reproduïbles sota `docs/evidencies/pas7.65/`.
- [ ] `tools/validate_docs.py` i regressions afectades en verd abans de completar.

## Fora d'abast

Fer córrer Bruneton/path tracing de referència a 60 FPS.

## Instrucció per a Codex

oracles independents offline/dev → fixtures versionats → comparador; mai usar el renderer runtime com a única referència. Respectar `simulated|physical`, la separació 7.1–7.50 / 7.51+, les unitats i les llicències. No donar per implementat un contracte buit.

## Treball pendent

- [ ] Completar tasques, proves i evidències abans de moure aquest document a `completat/`.
