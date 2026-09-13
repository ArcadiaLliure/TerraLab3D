# Pas 29 — Constel·lacions com a objectes (oficials i creades per l'usuari)

> Estat: **proposta nova — idea madura**
> Origen: pluja d'idees TerraLab3D, bloc "Constelaciones".
> Depèn de: Pas 28 (`ObservableObject`).

## Resultat funcional palpable

L'usuari pot cercar una constel·lació com si fos un objecte més: TerraLab3D en calcula el centre/envolupant, la selecciona, en dibuixa les línies i li aplica trajectòria i visibilitat, igual que a qualsevol altre objecte observable.

## Context i decisions preses

- Cercar i seleccionar una constel·lació com un objecte: en calcular el centre/envolupant, s'hi pot aplicar la mateixa trajectòria que a qualsevol altre `ObservableObject` (Pas 28).
- Mostrar les línies de la constel·lació.
- Admetre constel·lacions **oficials** i **creades per l'usuari** (TerraLab, l'aplicació d'escriptori de referència, ja té un mode de creació de constel·lacions del qual es reaprofita el codi).
- Mode per mostrar-les totes simultàniament (canvia només el render, no el model).

## Objectiu

Tractar la constel·lació com una especialització d'`ObservableObject` amb centre calculat, línies pròpies i suport per a conjunts oficials i personalitzats.

## Tasques

- [ ] Definir el model de constel·lació: llista d'estrelles, segments que la formen, catàleg oficial (IAU) vs. definicions d'usuari.
- [ ] Calcular el centre/envolupant de cada constel·lació per poder-hi aplicar trajectòria (Pas 28).
- [ ] Renderitzar les línies de la constel·lació sobre l'escena.
- [ ] Integrar la cerca de constel·lacions al cercador (es connectarà amb el Pas 33, cercador multipestanya).
- [ ] Mode "mostrar totes les constel·lacions" (canvi de render, no de model).
- [ ] Reaprofitar/adaptar el motor de creació de constel·lacions ja existent a TerraLab (aplicació d'escriptori) per a la creació d'usuari en TerraLab3D: nom, selecció d'estrelles, unió per segments, edició/eliminació.
- [ ] Persistència de constel·lacions creades per l'usuari.

## Criteri de sortida

Cercar una constel·lació la selecciona com un objecte complet (centre, línies, trajectòria); el mode "mostrar totes" funciona sense duplicar lògica; l'usuari pot crear, editar i eliminar constel·lacions pròpies.

## Evidència obligatòria

- [ ] Captura d'una constel·lació oficial seleccionada amb trajectòria activa.
- [ ] Captura del mode "mostrar totes".
- [ ] Captura del flux de creació d'una constel·lació d'usuari.

## Fora d'abast del pas

Integració amb el cercador multipestanya (Pas 33) més enllà de l'exposició de l'API de cerca.

## Prompt per a Codex

```
Implementa el Pas 29 (Constel·lacions com a objectes) descrit a
docs/novetats/idees-madures/pas29-constellacions.md sobre main, després del Pas 28. Modela la
constel·lació com una especialització d'ObservableObject amb centre/envolupant calculat i línies
pròpies. Admet catàleg oficial (IAU) i constel·lacions creades per l'usuari, reaprofitant si és
possible la lògica del mode de creació de constel·lacions de l'aplicació TerraLab de referència
(consulta docs/normes_arquitectura.md per l'estil d'integració). Afegeix el mode "mostrar totes"
com un canvi de render, sense duplicar el model de dades.
```
