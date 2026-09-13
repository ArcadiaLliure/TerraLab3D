# Pas 25 — Modes òptics (ull, prismàtics, telescopi/càmera) amb HUD unificat

> Estat: **proposta nova — idea madura, llesta per especificar tasca a tasca**
> Origen: pluja d'idees TerraLab3D (converses del 2 al 11 de setembre de 2026), bloc "Modes òptics".
> Branca de partida: `main`.

## Resultat funcional palpable

L'usuari pot alternar entre quatre maneres de mirar el cel —ull, prismàtics, objectiu i telescopi— amb un únic botó d'intercanvi. Cada mode reutilitza el mateix nucli d'escena i només canvia el camp de visió, l'overlay i el comportament del ratolí, en lloc de ser quatre lògiques independents.

## Context i decisions preses a la pluja d'idees

- **Ull:** FOV humà normal, comportament actual de l'aplicació sense canvis.
- **Prismàtics:** el FOV global es manté humà; apareix una **mira circular** al voltant del cursor que amplia només aquella zona (no el camp global).
  - `Scroll` → augment òptic dins la mira.
  - `Ctrl + scroll` → mida física del cercle de la mira (no altera el FOV òptic).
  - El ratolí ha de quedar amagat sota la mira; la mira substitueix visualment el cursor.
  - HUD amb distància, azimut i elevació del que s'apunta.
- **Objectiu/Telescopi:** camp **circular o rectangular** (rectangular = sensor de càmera), focal configurable en mm, relació focal, ocular, tipus d'instrument.
  - Mateixos controls: `scroll` = zoom òptic (focal), `Ctrl + scroll` = mida de la mira/marc quan aplica.
  - HUD igual que TerraLab clàssic: àrea en graus que abasta la vista, nombre d'estrelles dins del camp.
  - Ha de mostrar FOV horitzontal/vertical, diagonal, superfície angular i nombre d'estrelles contingudes.
- Els quatre modes **comparteixen botó** (fan *swap* de la icona) però són eines diferents amb comportament propi, no un únic mode amb flags.
- Aquesta funcionalitat és la base tècnica del "Simulador fotogràfic" (Pas 26): si el mode telescopi ja permet focal + marc circular/rectangular, el simulador fotogràfic no n'és un mode nou, sinó una capa de comoditat (preset de càmera/sensor) sobre aquest mateix mode.

## Objectiu

Implementar la infraestructura compartida "modes òptics" com a vista intercanviable d'un mateix estat d'escena, amb la mira/marc, els controls de scroll/Ctrl+scroll i el HUD associat a cada mode.

## Tasques

- [ ] Definir el model `OpticalMode` (`eye | binoculars | scope`) compartint estat de la càmera principal.
- [ ] Implementar la mira circular de prismàtics: render sobre el cursor, radi configurable, zoom intern independent del FOV global.
- [ ] Implementar el marc de telescopi/objectiu: circular o rectangular (aspecte segons sensor), amb focal configurable.
- [ ] Cablejar `scroll` → zoom òptic segons el mode actiu (global en "ull", intern en prismàtics/telescopi).
- [ ] Cablejar `Ctrl + scroll` → mida de la mira/marc, sense tocar el zoom òptic.
- [ ] Amagar el cursor natiu quan la mira/marc és visible.
- [ ] Construir el HUD per mode: distància/azimut/elevació (prismàtics); FOV H/V, diagonal, superfície angular i recompte d'estrelles Gaia dins el camp (telescopi).
- [ ] Botó d'intercanvi de mode a la UI amb icona pròpia per mode (ull / prismàtics / objectiu).
- [ ] Persistir l'últim mode i paràmetres (focal, mida de mira) entre sessions.
- [ ] Proves manuals: transicions entre modes sense salts de càmera, recompte d'estrelles coherent amb el catàleg Gaia ja integrat.

## Criteri de sortida

Els quatre modes funcionen sobre el mateix nucli d'escena, sense duplicar lògica de càmera; el canvi de mode és instantani i no reinicia la vista; el HUD de cada mode mostra dades correctes i actualitzades en temps real.

## Evidència obligatòria

- [ ] Captures dels quatre modes amb el HUD visible.
- [ ] Vídeo curt mostrant scroll i Ctrl+scroll en prismàtics i telescopi.
- [ ] Verificació que el recompte d'estrelles del HUD coincideix amb una consulta manual al catàleg Gaia pel mateix camp.

## Fora d'abast del pas

Els paràmetres de càmera (ISO, exposició, sensor) i la simulació fotogràfica pertanyen al Pas 26. El "plate solving" (importar foto real) pertany al Pas 27.

## Prompt per a Codex

```
Implementa el Pas 25 (Modes òptics) descrit a docs/novetats/idees-madures/pas25-modes-optics.md,
a partir de la branca main de TerraLab3D. Crea/adapta un únic component d'escena amb un enum
OpticalMode (eye | binoculars | scope) que comparteixi la mateixa càmera Three.js i només canviï:
(1) el comportament de scroll/Ctrl+scroll, (2) l'overlay de mira/marc, (3) el contingut del HUD.
No dupliquis la lògica de posicionament de càmera entre modes. Segueix les normes d'arquitectura
a docs/normes_arquitectura.md. Afegeix tests per a: canvi de mode sense salt de càmera, zoom intern
de la mira vs zoom global, recompte d'estrelles del HUD contra el catàleg Gaia ja carregat.
```
