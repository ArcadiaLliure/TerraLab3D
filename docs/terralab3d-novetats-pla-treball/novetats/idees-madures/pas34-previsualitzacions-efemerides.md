# Pas 34 — Previsualitzacions i animacions d'efemèrides

> Estat: **proposta nova — idea madura**
> Origen: pluja d'idees TerraLab3D, bloc "Previsualizaciones de efemérides".
> Depèn de: Pas 32 (Motor d'efemèrides), Pas 33 (Cercador multipestanya).

## Resultat funcional palpable

Cada efemèride del cercador porta una miniatura **generada pel propi renderer de TerraLab3D** (no una il·lustració externa) mostrant l'instant de màxima aproximació, i es pot obrir una petita animació temporal del fenomen amb accions directes «Anar a la data» i «Afegir al pla».

## Context i decisions preses

- **Nivell 1 — miniatura estàtica:** en cada efemèride, una petita captura generada per TerraLab3D (no imatge externa):
  - conjunció: els dos o tres objectes en el seu màxim acostament;
  - ocultació: l'instant més representatiu, just abans o durant;
  - acostament a la Lluna: la Lluna i l'objecte tal com es veuran al cel.
- **Nivell 2 — animació curta o scrub temporal:** en obrir la fitxa de l'efemèride, una mini animació que comença una mica abans, reprodueix l'acostament, mostra l'instant clau i acaba una mica després. **No obligatòria a la llista** (recarregaria la UI i cost computacional); disponible com a botó «Previsualitzar» o en entrar a la fitxa.
- La miniatura és **el cel real calculat per TerraLab3D**: escala correcta, horitzó real si aplica, camp visual adequat, instant exacte de l'esdeveniment — no una il·lustració decorativa.
- Format de targeta d'efemèride:
  ```
  [miniatura del cel]
  Venus · Lluna
  Màxim acostament: 05:42
  Separació: 0,8°
  Visible des de la teva ubicació: sí
  [ Veure ] [ Anar a la data ] [ Afegir al pla ]
  ```

## Objectiu

Generar miniatures i animacions renderitzades pel motor de TerraLab3D per a cada efemèride detectada, integrades a les targetes del cercador (Pas 33).

## Tasques

- [ ] Implementar la captura d'escena "headless"/offscreen de TerraLab3D per a un moment i camp de visió donats (reaprofitar mecanismes de captura ja existents al projecte si n'hi ha).
- [ ] Generar la miniatura de l'instant de màxima aproximació per a cada efemèride de la llista.
- [ ] Calcular el camp de visió i l'encaix (2 o 3 objectes) automàticament segons la separació angular de l'esdeveniment.
- [ ] Implementar l'animació/scrub temporal (des d'una mica abans fins una mica després de l'instant clau).
- [ ] Botó «Previsualitzar» a la fitxa de l'efemèride, sense forçar l'animació a totes les targetes de la llista.
- [ ] Afegir «Visible des de la teva ubicació» reutilitzant el càlcul de visibilitat del Pas 28.
- [ ] Accions «Anar a la data» i «Afegir al pla» (reutilitzant Pas 31) des de la targeta.
- [ ] Cache de miniatures generades per evitar recalcular-les en cada obertura del cercador.

## Criteri de sortida

Cada efemèride de la llista mostra una miniatura fidel al càlcul real de TerraLab3D (no una il·lustració genèrica); l'animació de la fitxa és fluida i reprodueix correctament l'aproximació al llarg del temps; el rendiment de la llista no es degrada per generar moltes miniatures alhora.

## Evidència obligatòria

- [ ] Miniatures d'exemple per a una conjunció de dos cossos i una ocultació.
- [ ] Vídeo curt de l'animació/scrub d'una efemèride.
- [ ] Mesura de temps de generació de la llista amb miniatures vs. sense (pressupost de rendiment).

## Fora d'abast del pas

La pestanya d'Eclipsis pròpia (Pas 35) i els esdeveniments propis de fitxa d'objecte (Pas 36) reutilitzaran aquest mateix mecanisme de miniatura, però es documenten com a passos separats.

## Prompt per a Codex

```
Implementa el Pas 34 (Previsualitzacions i animacions d'efemèrides) descrit a
docs/novetats/idees-madures/pas34-previsualitzacions-efemerides.md sobre main, després dels Pas 32
i Pas 33. Genera miniatures offscreen amb el renderer real de TerraLab3D per a l'instant de màxima
aproximació de cada efemèride (no il·lustracions externes), amb càmera i FOV calculats automàticament
segons la separació angular de l'esdeveniment. Afegeix una animació/scrub temporal accessible des de
la fitxa (botó "Previsualitzar", no obligatòria a la llista) i un sistema de cache de miniatures per
no degradar el rendiment de la llista del cercador.
```
