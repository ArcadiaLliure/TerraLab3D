# Pas 40 — Cel → Sistema Solar (navegació jeràrquica animada)

> Estat: **proposta nova — idea madura**
> Origen: pluja d'idees TerraLab3D, "Cielo → Sistema Solar".
> Depèn de: Pas 39 (esquelet del gestor de capes).

## Resultat funcional palpable

Dins de "Cel", la subsecció "Sistema Solar" mostra una animació amb el Sol al centre i els planetes orbitant, tots clicables; en seleccionar-ne un, la càmera hi fa zoom animat i es despleguen les targetes de recursos disponibles per a aquell cos (textura, DEM/model de forma, atmosfera...), amb un botó "Tornar".

## Context i decisions preses

- Sistema Solar **animat**, amb el Sol al centre; els planetes són **clicables**; en seleccionar-ne un, la vista fa **zoom animat** cap a aquell cos.
- Els satèl·lits es representen a les seves **òrbites reals**, usant els fitxers **SPICE** ja disponibles com a base orbital (aprofitant el catàleg de 461 satèl·lits ja integrat, Pas 8.6).
- Quan no es prem res (vista arrel del Sistema Solar), és on es col·loquen els **fitxers SPICE** com a recurs propi descarregable.
- Cada cos té una **targeta de recursos**: textura, DEM/model de forma, atmosfera, etc., segons el que apliqui a aquell cos concret.
- Botó **"Tornar"** per pujar un nivell (de satèl·lit a planeta, de planeta al Sistema Solar).
- Botó **"Descarregar tot"** (definit al Pas 39) a cada vista.
- La llista de cossos amb model d'elevació disponible i llicència d'ús comercial verificada (investigada durant la pluja d'idees) inclou, com a mínim: Terra, Lluna, Mart, Mercuri, Venus, Ceres, Vesta, Encèlad, Fobos, Deimos, i com a candidats afegits Titan, Plutó, Caront (LOLA i MOLA són domini públic; MESSENGER, Dawn i el DEM de Cassini per a Encèlad són d'ús lliure amb citació d'autors). La cobertura completa i la priorització final de cossos addicionals (Ío, Europa, Ganimedes, Cal·listo, Dione, Rea, Mimas, Tetis, Febe, i cossos menors com Eros, Steins, Itokawa, Bennu, Arrokoth) queda oberta i **no bloqueja aquest pas**: la UI i el pipeline de descàrrega han de ser genèrics per cos, no una llista tancada.
- Pendent (fora d'abast, marcat com a tal a la pluja d'idees): cinturó de Kuiper / núvol d'Oort, i sondes espacials (es podrien afegir trajectòries de sondes si n'hi ha recursos, sense bloquejar aquest pas).

## Objectiu

Construir la navegació visual jeràrquica Sol → planeta → satèl·lit dins la subsecció Sistema Solar del gestor de capes, amb targetes de recursos genèriques per cos.

## Tasques

- [ ] Renderitzar l'animació del Sistema Solar (Sol al centre, planetes orbitant) com a vista arrel de la subsecció.
- [ ] Fer clicables Sol i planetes; en seleccionar-ne un, zoom animat cap al cos.
- [ ] Representar satèl·lits en les seves òrbites reals a partir de les efemèrides SPICE ja integrades.
- [ ] Definir el model genèric de "targeta de recursos per cos" (textura, DEM/model de forma, atmosfera) que s'adapti al que existeixi realment per a cada cos, sense llista tancada.
- [ ] Botó "Tornar" per navegar un nivell amunt (satèl·lit → planeta → Sistema Solar).
- [ ] Botó "Descarregar tot" per vista, reutilitzant el patró del Pas 39.
- [ ] A la vista arrel (res seleccionat), exposar els fitxers SPICE com a recurs descarregable propi.
- [ ] Deixar preparada l'extensibilitat per afegir cossos nous (Kuiper/Oort, sondes) sense refactor.

## Criteri de sortida

Navegar Sol → Mart → Fobos i tornar funciona amb animació fluida i sense pèrdua d'estat; cada cos mostra només els recursos que realment té disponibles; "Descarregar tot" ofereix exactament els recursos rellevants per al context seleccionat.

## Evidència obligatòria

- [ ] Vídeo de navegació Sol → planeta → satèl·lit → Tornar.
- [ ] Captura de la targeta de recursos per a almenys tres cossos diferents amb contingut diferent (p. ex. Terra amb atmosfera, Fobos sense).
- [ ] Captura de l'assistent "Descarregar tot" per a un planeta.

## Fora d'abast del pas

Navegació lliure/física pel Sistema Solar amb nau en tercera persona (idea en maduració). Cinturó de Kuiper i núvol d'Oort. Trajectòries de sondes.

## Prompt per a Codex

```
Implementa el Pas 40 (Cel → Sistema Solar) descrit a
docs/novetats/idees-madures/pas40-cel-sistema-solar.md sobre main, després del Pas 39. Construeix la
vista animada del Sistema Solar (Sol al centre, planetes orbitant, clicables) com a subsecció de
"Cel" dins el gestor de capes. Reaprofita les efemèrides SPICE ja integrades (docs/completat/pas8.6.md)
per posicionar satèl·lits a les seves òrbites reals. Defineix un model GENÈRIC de targeta de recursos
per cos (textura/DEM/atmosfera segons disponibilitat real, sense llista tancada de cossos) i un botó
"Tornar" per pujar de nivell. Reutilitza el patró "Descarregar tot" del Pas 39. No implementis encara
navegació física/lliure amb nau (és una idea encara en maduració, fora d'abast d'aquest pas).
```
