# Idea pendent de madurar — Navegació lliure pel Sistema Solar

> Origen: pluja d'idees TerraLab3D, bloc "Navegación libre por el Sistema Solar".

## Què s'ha decidit ja

- Permetre desplaçament real de l'observador entre cossos, no només una cinemàtica fixa Terra→Lluna.
- Durant el viatge: la posició de l'observador canvia contínuament, es recalcula la geometria aparent del cel, la Terra s'allunya, el destí creix angularment, i el rellotge astronòmic segueix funcionant.
- El viatge està vinculat al **rellotge global** (×1, ×10, ×100, ×10.000...): a ×1 pot durar el temps físic real (mesos/anys si es deixa executant); amb acceleració temporal es comprimeix.
- Si es pausa a mig trajecte, l'observador roman en aquell punt de l'espai.
- **Navegació lliure/sandbox**: a més del viatge dirigit a un destí, permetre abandonar la trajectòria i moure's lliurement per l'espai. L'espai pot ser computacionalment més senzill que la superfície terrestre perquè hi desapareix el terreny, la vegetació, el land cover i el refinament ràster; es manté fonamentalment el sistema astronòmic.
- Cinturó de Kuiper i núvol d'Oort: es vol que es notin si s'hi viatja amb la nau, però **s'ha deixat explícitament pendent** ("ja veurem", "ho deixem en pausa") sense cap decisió de disseny.

## Per què encara no és una fase concreta

- Depèn de la transició terreny local → planeta esfèric (idea pendent separada) per no generar salts visuals en guanyar altitud.
- No hi ha decisió sobre el motor de renderitzat per a "espai buit" (quin nivell de detall es manté, quins catàlegs es continuen mostrant durant el viatge).
- Kuiper/Oort no tenen cap disseny, ni tan sols conceptual.

## Preguntes obertes

1. Com es gestiona el rendiment durant trajectes molt llargs a velocitat ×1 (dies/mesos reals)?
2. Quins elements astronòmics romanen visibles/actius durant el viatge lliure (catàleg Gaia sencer? NGC?)?
3. Com es representa Kuiper/Oort perquè "es notin" sense dades concretes encara triades?
4. Com s'articula amb la nau 3D en tercera persona (idea pendent separada)?

## Relació amb altres idees pendents

Nau 3D en tercera persona, transició terreny local → planeta esfèric, Go In / superfícies planetàries, representació del Sol.
