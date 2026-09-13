# Pas 42 — Nou sistema de descàrregues (pausa/reprèn/cancel·la, persistència)

> Estat: **proposta nova — idea madura**
> Origen: pluja d'idees TerraLab3D, "Nuevo sistema de descargas".
> Depèn de: Pas 39 (esquelet del gestor de capes). Requisit base per als Pas 40, 41, 43, 44.

## Resultat funcional palpable

Cada targeta de recurs té una barra de progrés amb pausa/reprèn/cancel·la; si es tanca TerraLab3D amb descàrregues actives i es torna a obrir, apareix un únic missatge («Tens N descàrregues pendents, vols reprendre-les?») que reprèn automàticament el que es pugui i reinicia en silenci el que no sigui reprenible.

## Context i decisions preses

- Barra de progrés **per targeta**, amb botons **pausa/reprèn** i **cancel·la**, sense floritures addicionals.
- **Persistència a disc**: cada targeta guarda el seu estat no només com a percentatge, sinó també identificador del recurs, bytes descarregats i estat. Suport per descàrregues per rangs i validació amb checksum o mida remota abans de continuar (per no barrejar versions).
- Si el proveïdor no suporta reprendre, es comunica clarament a l'usuari.
- En obrir TerraLab3D amb descàrregues pendents: **un únic missatge centralitzat** — «Tens N descàrregues pendents, vols reprendre-les?» — no un missatge per targeta.
- El que es pot reprendre, es reprèn; **el que no es pot reprendre, es reinicia en silenci**, sense generar drama a l'usuari; la targeta reflecteix l'estat resultant ("Reprès" / "Reiniciat").
- Tot centralitzat en un **únic gestor de descàrregues**, no repartit per targeta (la lògica viu fora de la vista, seguint el patró d'altres mòduls del projecte).
- **Molt important per a l'usuari (explícitament remarcat a la pluja d'idees): les barres de progrés han de funcionar bé sempre.** Quan no es pot calcular percentatge/temps restant, mostrar igualment activitat: barra indeterminada + "X MB descarregats", actualitzant-se com a mínim cada segon, perquè mai sembli que l'aplicació s'ha penjat.
- Si l'usuari s'interessa per una capa concreta, que la pugui mirar sense que això bloquegi la resta de descàrregues en curs.

## Objectiu

Construir un gestor de descàrregues centralitzat, persistent i reprenible, amb feedback visual fiable en tot moment, reutilitzable per totes les seccions del gestor de capes.

## Tasques

- [ ] Dissenyar el model de persistència d'estat de descàrrega (identificador de recurs, bytes descarregats, estat, checksum/mida remota).
- [ ] Implementar pausa/reprèn/cancel·la per descàrrega individual.
- [ ] Implementar descàrrega per rangs (range requests) quan el proveïdor ho permeti; detectar i comunicar quan no ho permet.
- [ ] Implementar el gestor centralitzat (no lògica repartida per targeta).
- [ ] A l'inici de TerraLab3D, detectar descàrregues pendents i mostrar el missatge únic de represa.
- [ ] Reprendre automàticament el reprenible; reiniciar en silenci el no reprenible, reflectint l'estat a la targeta.
- [ ] Implementar la barra indeterminada amb "X MB descarregats" actualitzada com a mínim cada segon quan no hi ha percentatge calculable.
- [ ] Provar el tancament abrupte de l'aplicació amb descàrregues actives i la seva represa correcta en reobrir.

## Criteri de sortida

Tancar TerraLab3D amb diverses descàrregues actives i tornar-lo a obrir reprodueix l'estat correctament (reprès/reiniciat segons correspongui) amb un únic missatge; cap descàrrega mostra mai una barra "morta" sense feedback d'activitat.

## Evidència obligatòria

- [ ] Vídeo de tancament i reobertura amb descàrregues pendents, mostrant el missatge únic i la represa.
- [ ] Captura d'una descàrrega sense percentatge calculable mostrant MB descarregats actualitzant-se.
- [ ] Prova de cancel·lació i de pausa/reprèn manual.

## Fora d'abast del pas

El contingut concret que es descarrega a cada secció (Pas 40, 41, 43, 44) — aquest pas només construeix el mecanisme genèric de descàrrega.

## Prompt per a Codex

```
Implementa el Pas 42 (Nou sistema de descàrregues) descrit a
docs/novetats/idees-madures/pas42-nou-sistema-descarregues.md sobre main, després del Pas 39.
Construeix un gestor de descàrregues CENTRALITZAT (no lògica per targeta) amb persistència a disc de
l'estat (identificador, bytes descarregats, estat, checksum/mida remota), suport de range requests
quan sigui possible, pausa/reprèn/cancel·la per descàrrega, i un únic missatge en obrir l'aplicació
("Tens N descàrregues pendents, vols reprendre-les?") que reprèn el reprenible i reinicia en silenci
la resta. És CRÍTIC que la barra de progrés mai sembli penjada: quan no hi ha percentatge calculable,
mostra una barra indeterminada amb "X MB descarregats" actualitzada com a mínim cada segon. Aquest és
un requisit que l'usuari ha remarcat explícitament com a molt important.
```
