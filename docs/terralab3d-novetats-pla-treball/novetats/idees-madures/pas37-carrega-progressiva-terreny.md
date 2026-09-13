# Pas 37 — Càrrega progressiva de terreny (tiles/LOD/streaming)

> Estat: **proposta nova — idea madura, requisit transversal**
> Origen: pluja d'idees TerraLab3D, "Requisits transversals d'experiència d'usuari".

## Resultat funcional palpable

El terreny ja no espera a tenir el 100% del ràster carregat abans de mostrar-se: apareix progressivament amb una representació basta inicial que es va refinant fins a la qualitat màxima disponible, generalitzable a qualsevol cos (Terra i, més endavant, superfícies planetàries).

## Context i decisions preses

- **No esperar al 100% del ràster** per mostrar el terreny.
- Aparició progressiva:
  1. representació inicial basta;
  2. zones prioritàries;
  3. refinament;
  4. màxima resolució disponible.
- Implica tiles/streaming/LOD i s'ha de generalitzar a capes pesades, no només al DEM base.
- Aplicable no només a la Terra, sinó també a futures superfícies planetàries (Lluna, Mart...).

## Objectiu

Introduir un pipeline de càrrega per tiles amb nivells de detall progressius per al terreny, reemplaçant l'espera al ràster complet.

## Tasques

- [ ] Definir l'esquema de tiles i nivells de detall (LOD) per al terreny base.
- [ ] Implementar la càrrega asíncrona per tiles amb prioritat (zona propera a l'observador primer).
- [ ] Renderitzar una representació basta immediata mentre es descarreguen/processen tiles de major resolució.
- [ ] Substituir progressivament les tiles basses per les refinades sense salts visuals bruscos (transició suau).
- [ ] Generalitzar el mecanisme perquè sigui reutilitzable per altres capes pesades (superfície, land cover).
- [ ] Provar amb connexió lenta simulada per validar la percepció de fluïdesa.

## Criteri de sortida

En obrir TerraLab3D o desplaçar-se a una nova zona, l'usuari veu terreny des dels primers segons, que es va refinant sense bloquejar la interacció; el patró és reutilitzable per altres capes.

## Evidència obligatòria

- [ ] Vídeo mostrant l'evolució de basta a refinada en obrir una ubicació nova.
- [ ] Mesura de temps fins a la primera representació visible (P50/P95) abans i després del canvi.

## Fora d'abast del pas

L'aplicació d'aquest mateix mecanisme a superfícies planetàries fora de la Terra (dependrà del Pas de "Go In", encara en maduració).

## Prompt per a Codex

```
Implementa el Pas 37 (Càrrega progressiva de terreny) descrit a
docs/novetats/idees-madures/pas37-carrega-progressiva-terreny.md sobre main. Introdueix un esquema
de tiles amb LOD progressiu per al terreny base: mostra una representació basta immediata i
refina'l progressivament sense esperar el 100% del ràster. Fes-ho generalitzable a altres capes
pesades (superfície, land cover), seguint les normes d'arquitectura a docs/normes_arquitectura.md.
Mesura i documenta el temps fins a la primera representació visible (P50/P95) abans i després del
canvi.
```
