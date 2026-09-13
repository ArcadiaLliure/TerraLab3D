# Pas 46 — TLST com a ontologia/traductor de classes

> Estat: **proposta nova — idea madura**
> Origen: pluja d'idees TerraLab3D, "TLST como ontología/traductor".
> Forma un sol nucli conceptual amb el Pas 45: *Adapter → TLST → classe canònica → arbre → intèrpret*.

## Resultat funcional palpable

Un mateix concepte (p. ex. "oliverar") es representa sempre amb un únic codi canònic intern de TerraLab3D, sigui quin sigui el proveïdor d'origen (codi 17 a la font catalana, codi 58 a Copernicus, etc.), de manera que la resta del motor mai treballa amb codis de proveïdor.

## Context i decisions preses

- Fórmula acordada: **`font + codi font → classe canònica TerraLab`**.
- A partir d'aquí, **tota la resta del motor (arbre de refinament, intèrprets) treballa exclusivament amb codis interns comuns**, mai amb codis de proveïdor.
- La taula d'equivalències s'ha de mantenir **sempre indexada per font i versió**, per no barrejar semàntiques entre revisions d'un mateix proveïdor.
- TLST ja existeix parcialment com a base de dades pròpia al projecte (la graella de 14.201 teseles ja documentada a `docs/completat` i a la memòria del projecte); aquest pas en formalitza el paper com a **capa de traducció obligatòria abans** que qualsevol ràster entri a l'arbre de refinament (Pas 45), no com un component solt.
- Nucli arquitectònic acordat literalment a la pluja d'idees: **Adapter → LST/TLST → classe canònica → arbre → intèrpret**.

## Objectiu

Formalitzar TLST com la capa de traducció obligatòria font+codi→classe canònica, prèvia a qualsevol consulta del motor de refinament.

## Tasques

- [ ] Documentar l'esquema de la taula d'equivalències (font, versió, codi font → classe canònica), indexada per font i versió.
- [ ] Implementar l'"Adapter" per cada font de dades suportada (Copernicus, font catalana, altres) que resol codi font → classe canònica via TLST abans que el ràster entri al pipeline.
- [ ] Assegurar que cap component posterior (arbre de refinament, intèrprets) accedeix mai a codis de proveïdor en brut.
- [ ] Migrar les fonts ja integrades al projecte (Copernicus, CropTypes, etc.) a aquest esquema de traducció si encara no hi passen.
- [ ] Documentar el procediment per afegir una font nova: registrar-ne els codis a TLST abans de connectar-la al pipeline.

## Criteri de sortida

Afegir una font de dades nova només requereix ampliar la taula TLST amb els seus codis; cap canvi al motor de refinament ni als intèrprets és necessari per suportar-la.

## Evidència obligatòria

- [ ] Exemple documentat: el mateix concepte (oliverar) traduït des de dues fonts diferents amb codis diferents, resolent-se a la mateixa classe canònica.
- [ ] Prova que el motor de refinament (Pas 45) mai rep un codi de proveïdor sense traduir.

## Fora d'abast del pas

L'arbre de refinament pròpiament dit (Pas 45), que consumeix les classes canòniques que aquest pas produeix.

## Prompt per a Codex

```
Implementa el Pas 46 (TLST com a ontologia/traductor) descrit a
docs/novetats/idees-madures/pas46-tlst-ontologia.md sobre main. Formalitza la capa de traducció
"font + codi font → classe canònica TerraLab", indexada per font i versió, com a pas obligatori
ABANS que qualsevol ràster entri a l'arbre de refinament del Pas 45. Reaprofita el sistema TLST
existent (graella de 14.201 teseles, vegeu la documentació de mosaic ja completada) i migra-hi les
fonts ja integrades (Copernicus, CropTypes). El motor de refinament i els intèrprets posteriors mai
han d'accedir a un codi de proveïdor sense traduir; segueix l'arquitectura Adapter → TLST → classe
canònica → arbre → intèrpret.
```
