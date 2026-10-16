# Pas 7.68 — Homologació final del cel físic real/simulat

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Tancar la vertical 7.51–7.68 només quan llicències, ciència, scheduler, SLO, lifecycle i regressió del mode simulat tinguin evidència reproduïble.

## Descripció funcional

La homologació integra els gates anteriors sense convertir-se en un calaix de noves features. `simulated` continua sent una estratègia permanent i `physical` només es promociona quan és traçable.

## Fonts a consultar

- [Dossier del cel físic](../../cel-fisic/README.md), especialment [decisions tancades](../../cel-fisic/05-decisions-tancades.md) i [contractes](../../cel-fisic/04-contractes-validacio.md).
- [Normes d'arquitectura](../../normes-arquitectura.md) i [inventari funcional](../../inventari-funcional.md).
- [Dossier skyglow](../../skyglow/README.md) només per contractes compartits; no fusionar integradors.

## Objectiu

Tancar la vertical 7.51–7.68 només quan llicències, ciència, scheduler, SLO, lifecycle i regressió del mode simulat tinguin evidència reproduïble.

## Dependències

**Depèn de:**
- [Pas 7.67](pas7.67-slo-rendiment-cel-fisic.md)

**En depenen:**
- [Pas 38 — Homologació final del producte](pas38-homologacio-final.md)

## Codi existent a reutilitzar

Passos 7.51–7.67, docs/README, inventari, MANUAL, THIRD-PARTY, lifecycle i suites backend/frontend.

## Flux tècnic

gate legal + matriu científica + error budget + SLO + recovery + regressió simulated/physical → decisió de disponibilitat de `physical`.

## Errors, cancel·lació i recursos

- Revisions temporals latest-wins; cap resultat obsolet es publica.
- Dades o drets no verificats → `unavailable`, no dades inventades.
- **Risc:** confondre especificació amb implementació, ocultar una llicència o degradar científicament per complir performance.
- **Rollback:** no promocionar `physical`; conservar `simulated` i incidències obertes.

## Tasques

- [ ] Auditar llicències/avisos/datasets realment incorporats i `THIRD-PARTY.md`.
- [ ] Homologar Sol/Lluna/ROLO, fons natural, nubes, altura, limbe/terminador, eclipsis i il·luminació de terreny.
- [ ] Confirmar error budget conservador i absència de falsos pruning en corpus advers.
- [ ] Confirmar SQM/TESS/CIE independents del mode visual i del RGB SkyView.
- [ ] Homologar latest-wins, context loss, reconnect/resync, dispose i restore.
- [ ] Publicar SLO reals del perfil hardware i limitacions; no seleccionar N per benchmark.
- [ ] Actualitzar README, inventari, MANUAL i manifests només segons estat observable.

## Criteri de sortida

La vertical està implementada, legalment distribuïble, científicament traçable i interactiva dins del perfil homologat; `simulated` i `physical` romanen separats i reversibles.

## Proves i evidències obligatòries

- [ ] matriu completa simulated/physical sense fallback silenciós;
- [ ] gates científics 7.66 i SLO 7.67 en verd;
- [ ] llicències i avisos complets;
- [ ] recovery/context loss i teardown sense recursos filtrats.
- [ ] Evidències reproduïbles sota `docs/evidencies/pas7.68/`.
- [ ] `tools/validate_docs.py` i regressions afectades en verd abans de completar.

## Fora d'abast

Eliminar el mode simulat, relaxar gates sense ADR/evidència o publicar recursos de drets incerts.

## Instrucció per a Codex

executa tots els gates 7.51–7.67 i només llavors promociona `physical`; qualsevol fallada manté la vertical pendent/parcial. Respectar `simulated|physical`, la separació 7.1–7.50 / 7.51+, les unitats i les llicències. No donar per implementat un contracte buit.

## Treball pendent

- [ ] Completar tasques, proves i evidències abans de moure aquest document a `completat/`.
