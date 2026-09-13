# Pas 26 — Simulador fotogràfic (exposició, ISO, traces i exportació)

> Estat: **proposta nova — idea madura**
> Origen: pluja d'idees TerraLab3D, bloc "Simulador fotogràfic".
> Depèn de: Pas 25 (Modes òptics).

## Resultat funcional palpable

Amb el mode telescopi/objectiu actiu, l'usuari configura focal, obertura, ISO, temps d'exposició i (quan es conegui) el format del sensor, i TerraLab3D li mostra què capturaria realment: estrelles puntuals o traces, límit de magnitud i el temps màxim abans que apareguin traces.

## Context i decisions preses

- No és un mode nou: reutilitza el marc del mode telescopi del Pas 25 (circular o rectangular, com un sensor).
- Paràmetres: focal, obertura, exposició, ISO i format de sensor quan es conegui.
- Estimació del temps màxim d'exposició sense traces mitjançant regles tipus **500** i **NPF**.
- Botó **"Fer foto"**.
- Simulació visual de traces estel·lars **reutilitzant la lògica ja existent de circumpolars** (Pas 14, ja completat).
- Estimació de la magnitud límit capturable i, per tant, quines estrelles de Gaia apareixerien aproximadament.
- Possibilitat d'exportar la imatge simulada.
- Ampliació de comoditat (no duplicació): un selector opcional de model de càmera/sensor que calculi automàticament la mida del marc al cel, estrelles estimades dins i si cal seguiment — depèn d'una base de dades de sensors (vegeu la idea pendent corresponent).

## Objectiu

Convertir el mode telescopi en una eina fotogràfica plausible: calcular què es capturaria i oferir-ne una simulació visual exportable.

## Tasques

- [ ] Afegir panell de paràmetres de càmera (focal ja ve del Pas 25; afegir obertura, ISO, temps d'exposició).
- [ ] Implementar el càlcul de temps màxim sense traces (regla 500 i regla NPF), mostrant-lo com a referència al costat del control d'exposició.
- [ ] Reutilitzar el motor de traces circumpolars (Pas 14) per dibuixar les estrelles com a traces quan l'exposició superi el llindar calculat.
- [ ] Calcular la magnitud límit efectiva segons ISO/obertura/exposició i filtrar el catàleg Gaia visible en conseqüència dins el marc.
- [ ] Botó "Fer foto": generar una captura de l'escena tal com es veuria amb aquests paràmetres (estrelles puntuals o traces segons correspongui).
- [ ] Exportació de la imatge simulada (PNG/JPEG) amb metadades bàsiques dels paràmetres utilitzats.
- [ ] (Opcional, si hi ha temps) selector de model de càmera/sensor amb valors preestablerts manuals mentre no hi hagi base de dades comercial.

## Criteri de sortida

Els paràmetres fotogràfics afecten visualment la simulació (puntual vs. traça) i el recompte d'estrelles mostrat; el botó "Fer foto" genera una exportació reproduïble amb els mateixos paràmetres.

## Evidència obligatòria

- [ ] Captures comparant la mateixa escena amb exposicions curta i llarga (estrelles puntuals vs. traces).
- [ ] Verificació manual del càlcul 500/NPF contra un exemple de referència conegut.
- [ ] Fitxer exportat de mostra.

## Fora d'abast del pas

Base de dades comercial de sensors/càmeres (idea pendent d'investigació). Comparador foto real vs. simulació (depèn del Pas 27, plate solving).

## Prompt per a Codex

```
Implementa el Pas 26 (Simulador fotogràfic) descrit a docs/novetats/idees-madures/pas26-simulador-fotografic.md,
sobre la branca main de TerraLab3D, després del Pas 25. Afegeix un panell de paràmetres de càmera al mode
telescopi (focal ja existent, més obertura/ISO/exposició), calcula el temps màxim sense traces amb les
regles 500 i NPF, i reutilitza el motor de traces circumpolars ja existent a docs/completat/pas14.md per
dibuixar les estrelles com a punts o traces segons correspongui. Afegeix exportació d'imatge i el botó
"Fer foto". No creïs un mode d'escena nou: opera sobre l'estat del mode telescopi del Pas 25.
```
