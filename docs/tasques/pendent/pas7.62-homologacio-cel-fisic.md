# Pas 7.62 — Homologació del cel real/simulat i tancament documental

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Tancar la vertical amb compatibilitat comercial, persistència del selector, geometria del limbe i separació científica verificades.

## Descripció funcional

Tancar la vertical amb compatibilitat comercial, persistència del selector, geometria del limbe i separació científica verificades.

## Fonts a consultar

- [Dossier del cel físic](../../cel-fisic/README.md) i els seus documents d'arquitectura, física, llicències i validació.
- [Normes d'arquitectura](../../normes-arquitectura.md), [inventari](../../inventari-funcional.md) i codi real del repositori.
- [Dossier skyglow artificial](../../skyglow/README.md) només per compartir estat òptic i composició; no duplicar-ne el kernel.

## Objectiu

Tancar la vertical amb compatibilitat comercial, persistència del selector, geometria del limbe i separació científica verificades.

## Dependències

**Depèn de:**
- [Pas 7.61](pas7.61-validacio-cel-fisic.md)

**En depenen:**
- [Pas 38 — Homologació final](pas38-homologacio-final.md)

## Codi existent a reutilitzar

Passos 7.51–7.61, docs/README, docs/inventari-funcional i docs/MANUAL.

## Flux tècnic

gate de llicències + proves científiques + SLO runtime + regressió simulat + manual i inventari → decisió de disponibilitat de physical.

## Errors, cancel·lació i recursos

- Revisions temporals latest-wins; resultats obsolets descartats i recursos GPU amb propietari i dispose.
- Les dades o llicències no verificades es publiquen com a unavailable, mai com a resultats científics inventats.
- **Risc:** Confondre especificació amb funcionalitat implementada o ocultar una restricció de llicència.
- **Rollback:** No promoure physical; mantenir simulated i registrar incidències.

## Tasques

- [ ] Revisar licències, avisos, datasets i procedència dels recursos efectivament incorporats.
- [ ] Homologar canvi de mode, temps continu, Sol/Lluna, altura, curvatura, halo del limbe, eclipsis i il·luminació.
- [ ] Confirmar que els resultats SQM/TESS són independents del mode visual i que el skyglow artificial continua separat.
- [ ] Registrar limitacions físiques, errors, versions i SLO reals sense seleccionar N per benchmarks.
- [ ] Actualitzar docs/README, inventari, MANUAL i THIRD-PARTY només amb evidència d'implementació.

## Criteri de sortida

La vertical està implementada i homologada amb llicències compatibles, dues estratègies permanents i resultats científics traçables.

## Proves i evidències obligatòries

- [ ] Matriz de regressió simulated/physical i cap fallback silenciós.
- [ ] Llicències comercials verificades i avisos complets.
- [ ] Tests físics, sensors, altitude/limbe i performance amb evidències.
- [ ] Evidències reproduïbles sota docs/evidencies/pas7.62/ quan s'implementi.
- [ ] Executar tools/validate_docs.py i les regressions afectades abans de completar.

## Fora d'abast

Eliminar el mode simulat o publicar dades sense drets verificats.

## Instrucció per a Codex

gate de llicències + proves científiques + SLO runtime + regressió simulat + manual i inventari → decisió de disponibilitat de physical. Respectar els límits de la vertical 7.51+, les llicències comercials i el mode simulat permanent. No donar per implementat un contracte buit.

## Treball pendent

- [ ] Completar tasques, proves i evidències abans de moure aquest document a completat/.
