# Pas 7.52 — Selector permanent de cel simulat/real

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Afegir el flag tipat skyRenderingMode=simulated|physical, sense alterar lightPollutionMode ni les efemèrides; simulated conserva el resultat actual.

## Descripció funcional

Afegir el flag tipat skyRenderingMode=simulated|physical, sense alterar lightPollutionMode ni les efemèrides; simulated conserva el resultat actual.

## Fonts a consultar

- [Dossier del cel físic](../../cel-fisic/README.md) i els seus documents d'arquitectura, física, llicències i validació.
- [Normes d'arquitectura](../../normes-arquitectura.md), [inventari](../../inventari-funcional.md) i codi real del repositori.
- [Dossier skyglow artificial](../../skyglow/README.md) només per compartir estat òptic i composició; no duplicar-ne el kernel.

## Objectiu

Afegir el flag tipat skyRenderingMode=simulated|physical, sense alterar lightPollutionMode ni les efemèrides; simulated conserva el resultat actual.

## Dependències

**Depèn de:**
- [Pas 7.51](pas7.51-llicencies-i-recursos.md)

**En depenen:**
- [Pas 7.53](pas7.53-optica-observador-altura.md)

## Codi existent a reutilitzar

SkyEnvironmentSnapshot, frontend/contracts, frontend/application, AtmosphereRenderer.ts, ThreeSceneHostImpl.

## Flux tècnic

preferència UI → frontend/application → bridge/DTO i revisió → selector d'estratègia de render → simulat existent o estat physical unavailable.

## Errors, cancel·lació i recursos

- Revisions temporals latest-wins; resultats obsolets descartats i recursos GPU amb propietari i dispose.
- Les dades o llicències no verificades es publiquen com a unavailable, mai com a resultats científics inventats.
- **Risc:** Barrejar mode visual amb autoritat radiomètrica o duplicar recursos.
- **Rollback:** Seleccionar explícitament simulated; el flag no s'elimina.

## Tasques

- [ ] Crear el selector persistent amb valors simulated i physical i etiquetes Simulat / Real (físic).
- [ ] Preservar sky_palette.py, AtmosphereRenderer.ts i skyShader.ts com a camí simulat sense modificar-ne la física.
- [ ] Separar les estratègies de dibuix darrere d'una façana integrada al ThreeSceneHostImpl, sense segon rellotge, bridge ni escena.
- [ ] Exposar initializing/unavailable/available amb causa; prohibir fallback silenciós physical→simulated.
- [ ] Garantir que SQM/TESS i skyglow científic no depenen del selector visual.

## Criteri de sortida

El selector és observable i reversible, simulated funciona igual que abans i physical informa disponibilitat real.

## Proves i evidències obligatòries

- [ ] Commutació repetida i persistència del flag, render històric simulat inalterat.
- [ ] physical no disponible comunica error sense fingir cel real; canvi manual de tornada a simulat.
- [ ] El canvi no reinicia catàlegs, efemèrides ni modes Bortle/magnitud.
- [ ] Evidències reproduïbles sota docs/evidencies/pas7.52/ quan s'implementi.
- [ ] Executar tools/validate_docs.py i les regressions afectades abans de completar.

## Fora d'abast

Implementació del transport Hillaire, que correspon al Pas 7.56.

## Instrucció per a Codex

preferència UI → frontend/application → bridge/DTO i revisió → selector d'estratègia de render → simulat existent o estat physical unavailable. Respectar els límits de la vertical 7.51+, les llicències comercials i el mode simulat permanent. No donar per implementat un contracte buit.

## Treball pendent

- [ ] Completar tasques, proves i evidències abans de moure aquest document a completat/.
