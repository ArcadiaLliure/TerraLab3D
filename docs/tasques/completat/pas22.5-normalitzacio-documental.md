# Pas 22.5 — Normalització de la documentació viva

> **Estat:** completat. **Estat funcional:** observable. **Origen:** planificat. **Abast vigent:** normalitzar l'estructura, les plantilles, els enllaços, l'inventari i els validadors documentals sense alterar funcionalitat de TerraLab3D ni reescriure editorialment passos aliens.

## Descripció funcional

Aquest pas no afegeix cap funció visible al producte. Deixa el pla viu en un estat mecànicament verificable perquè un agent pugui identificar el punt de represa, executar un únic pas, marcar-ne el progrés i distingir especificació, implementació i evidència.

## Fonts a consultar

- `C:/Users/Manel/.agents/skills/plan/SKILL.md` i `templates/pas.md`: estàndard `/plan`; consultats el 2026-09-17. La ruta és local a l'entorn de desenvolupament i no forma part del producte distribuït.
- [`AGENTS.md`](../../../AGENTS.md): instrucció persistent de manteniment documental; consultada el 2026-09-17.
- [`README.md`](../../README.md), [`inventari-funcional.md`](../../inventari-funcional.md) i les dues variants actuals de les normes: estat documental auditat el 2026-09-17.
- [`tools/validate_skeleton.py`](../../../tools/validate_skeleton.py): validador existent adaptat a la nova estructura canònica; consultat el 2026-09-17.

## Objectiu

Adoptar l'estructura obligatòria `docs/tasques/{pendent,completat,idees-per-madurar}`, fer que tots els passos compleixin `templates/pas.md`, reparar enllaços i inventari, i deixar una validació reproduïble amb zero incidències. El canvi ha de preservar contingut, identificadors històrics, evidències i treball local.

## Dependències

**Depèn de:**
- Cap pas previ.

**En depenen:**
- [Pas 23 — Constel·lacions IAU, traçat de referència i documents d'usuari](pas23-constellacions.md)

## Codi existent a reutilitzar

- **Repositori actual:** [`tools/validate_skeleton.py`](../../../tools/validate_skeleton.py), [`tools/validate_docs.py`](../../../tools/validate_docs.py), l'arbre `docs/` existent i l'historial de Git per verificar moviments i preservació.
- **Projectes de referència autoritzats:** skill local `plan`, especialment `templates/pas.md` i `scripts/validate_docs.py`; adaptat i integrat a `tools/validate_docs.py`.

## Flux tècnic

Estat Git i inventari documental → mapa de moviments preservant identificadors → estructura canònica `docs/tasques/` → normalització mecànica de seccions i checkboxes → reparació d'enllaços i dependències bidireccionals → inventari i README coherents → validadors estructural i semàntic → evidències de sortida → moviment d'aquest pas a `tasques/completat/` i activació del Pas 23.

La variant canònica de les normes és `docs/normes-arquitectura.md`. S'ha comprovat que ambdues còpies eren idèntiques, s'han actualitzat totes les referències i s'ha eliminat `docs/normes_arquitectura.md`.

## Errors, cancel·lació i recursos

- No modificar ni esborrar `docs/MANUAL.md`, captures, exemples o eines no versionades que ja siguin treball local aliè a aquest pas.
- Fer moviments explícits i revisables; no recrear documents perdent-ne la traçabilitat.
- Si dues còpies aparentment duplicades han divergit, conservar-les i aturar només la fusió afectada fins a integrar-ne el contingut sense pèrdua.
- Una incidència del validador no es resol debilitant la regla: s'ha de corregir el document o justificar-hi explícitament «No aplicable».
- No executar formatadors massius ni canvis cosmètics sobre codi o documentació no afectada.

## Tasques

- [x] Inventariar `git status`, documents, evidències, enllaços, identificadors i modificacions locals que s'han de preservar.
- [x] Crear `docs/tasques/pendent/`, `docs/tasques/completat/` i `docs/tasques/idees-per-madurar/`, i moure-hi els documents actuals mantenint noms i historial.
- [x] Normalitzar tots els fitxers de pas amb totes les seccions de `templates/pas.md`, afegint només estructura, estat i checkboxes quan el contingut ja existeixi i sense reinterpretar-ne l'abast.
- [x] Consolidar `docs/normes-arquitectura.md` com a nom únic i reparar totes les referències a la variant amb guió baix.
- [x] Reparar la duplicació i les files malformades de `docs/inventari-funcional.md` sense promocionar cap capacitat no verificada.
- [x] Actualitzar `docs/README.md`, el punt de represa, les taules i totes les dependències entrants i sortints després dels moviments.
- [x] Incorporar `tools/validate_docs.py`, adaptar `tools/validate_skeleton.py` a les rutes canòniques i incloure totes dues comprovacions al flux `npm run validate`.
- [x] Validar enllaços Markdown, recursos referenciats, identificadors únics, seccions obligatòries, checkboxes, dependències bidireccionals i absència de cicles nous.
- [x] Revisar `git diff -- docs/ tools/ package.json`, distingir canvis previs dels propis i desar els resultats reproduïbles a `docs/evidencies/pas22.5/`.
- [x] Quan totes les comprovacions siguin verdes, marcar el pas completat, moure'l a `docs/tasques/completat/` i deixar el Pas 23 com a següent pas executable.

## Criteri de sortida

`docs/` compleix l'estructura de la skill, cada pas és un prompt executable amb totes les seccions i checkboxes, els enllaços i dependències són vàlids, l'inventari no està duplicat, els validadors acaben sense incidències i `docs/README.md` assenyala el Pas 23. Cap funcionalitat del producte ni evidència històrica ha canviat.

## Proves i evidències obligatòries

- [x] Executar `python tools/validate_docs.py`; resultat esperat: zero incidències. Desar la sortida a `../../evidencies/pas22.5/validacio-documental.txt` després del moviment canònic.
- [x] Executar `python tools/validate_skeleton.py`; resultat esperat: esquelet vàlid amb les rutes documentals noves. Afegir-ne el resultat a `../../evidencies/pas22.5/validacio-documental.txt`.
- [x] Executar `npm run validate`; resultat esperat: validadors documentals, esquelet i typecheck correctes.
- [x] Fer una comprovació automàtica d'enllaços i recursos locals; resultat esperat: cap destí inexistent. Desar-ne el resum a `../../evidencies/pas22.5/auditoria-enllacos.txt`.
- [x] Inspeccionar `git diff -- docs/ tools/ package.json` i `git status --short`; resultat esperat: moviments traçables, cap pèrdua de contingut i modificacions locals prèvies preservades.

**Resultats verificats:** Validació documental, d'esquelet i typecheck superades amb 0 incidències; evidències arxivades a `docs/evidencies/pas22.5/`.

## Fora d'abast

- Implementar constel·lacions o qualsevol altra funció del producte.
- Reescriure editorialment la història dels passos, renumerar identificadors o alterar criteris funcionals no relacionats.
- Regenerar captures, exemples o el manual quan el comportament observable no ha canviat.
- Fer commits, pushes o netejar treball local aliè.

## Instrucció per a Codex

Pas 22.5 completat amb èxit. El següent pas executable és el **Pas 23 — Constel·lacions IAU, traçat de referència i documents d'usuari**. Revisa `docs/README.md` i `docs/normes-arquitectura.md` abans de començar.

## Treball pendent

Cap després del criteri de sortida.
