# Idea pendent de madurar — Transició terreny local → planeta esfèric

> Origen: pluja d'idees TerraLab3D, bloc "Transición Tierra local → planeta completo".

## Què s'ha decidit ja

- Requisit explícit: en guanyar molta altitud, la Terra **no pot convertir-se en un disc pla**; ha d'aparèixer la curvatura planetària.
- Cal una transició entre representació local del terreny (l'actual, plana localment) i representació global esfèrica/el·lipsoidal amb textura planetària.
- És un **requisit tècnic imprescindible** perquè la navegació espacial i el "Go In" siguin coherents (sense aquesta peça, cap de les dues altres idees pendents pot funcionar de manera creïble).
- Combinació apuntada: representació local de precisió (l'actual) + representació planetària esfèrica/el·lipsoidal amb textura global, transicionant de manera contínua (canvi de coordenades locals planes a coordenades geocèntriques).

## Per què encara no és una fase concreta

- No hi ha cap decisió sobre l'algorisme concret de transició (a quina altitud comença, com s'interpolen les dues representacions, com es gestiona el nivell de detall durant la transició).
- No s'ha decidit si es reutilitza el pipeline de tiles/LOD del Pas 37 per a la representació esfèrica llunyana o si cal un sistema nou.

## Preguntes obertes

1. A quina altitud (o criteri visual) comença la transició de pla a esfèric?
2. Com es gestiona el canvi de sistema de coordenades (local planes → geocèntriques) sense salts perceptibles?
3. Es reutilitza el terreny tridimensional retingut ja existent (Pas 16) per a la vista propera, i una textura planetària nova per a la vista llunyana?

## Relació amb altres idees pendents

Bloquejant per a: navegació lliure pel Sistema Solar, Go In / superfícies planetàries.
