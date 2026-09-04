# Pas 16 — Terreny tridimensional retingut, tiles, LOD i picking de superfície

> Estat: **completat**
> Classificat mitjançant implementació, proves i validacions del repositori.

## Resultat funcional palpable

L’escena conté muntanyes, valls i relleu 3D navegable al voltant de l’observador, amb tiles persistents, LOD, llum i picking.

## Fonts TerraLab a consultar

- `TerraLab/terrain/overlay.py`
- `TerraLab/terrain/overlay_mixins/*`
- `TerraLab/terrain/render/*`
- `TerraLab/terrain/raycast.py` i geometria
- `TerraLab/terrain/worker.py`
- `TerraLab/ui/widget_controls_builder.py` — relleu 3D, capes i profunditat

## Objectiu

Completar aquesta vertical funcional de punta a punta, mantenint la separació de responsabilitats i sense anticipar funcionalitats posteriors que no siguin imprescindibles.

## Tasques

- [ ] Definir tiles, bounds, malles, normals, índexs i versions renderer-neutral.
- [ ] Extreure triangulació i càlcul de normals dels camins QPainter.
- [ ] Definir LOD per error de pantalla, distància i pressupost.
- [ ] Dividir el terreny en recursos persistents substituïbles.
- [ ] Transferir buffers binaris sense Base64.
- [ ] Implementar registre, referències i dispose de tiles GPU.
- [ ] Carregar i descarregar tiles segons visibilitat sense reconstruir tota la malla.
- [ ] Implementar frustum culling i límits de memòria.
- [ ] Implementar il·luminació solar/lunar i boira per distància com a materials/uniforms.
- [ ] Implementar mode relleu 3D i compatibilitat amb silueta per distància.
- [ ] Implementar picking de superfície i coordenada del punt impactat.
- [ ] Gestionar canvi de profunditat, qualitat i precisió amb cancel·lació.
- [ ] Mostrar progrés i estat del terreny.
- [ ] Comparar geometria i visibilitat amb TerraLab.

## Criteri de sortida

La càmera pot navegar sobre un terreny real sense reconstrucció global per frame; tiles, LOD, llum, boira i picking funcionen; la memòria es manté dins pressupost.

## Evidència obligatòria

- [ ] Vídeo de navegació amb càrrega/descàrrega de tiles.
- [ ] Captures de diferents profunditats i LOD.
- [ ] Mètriques de triangles, draw calls, memòria i temps de tile.
- [ ] Prova de cancel·lació en canviar d’ubicació.

## Fora d’abast del pas

Els materials d’ortofoto i cobertura arriben al pas següent.

## Annex de paritat DEM

TerraLab s’utilitza només com a oracle de comportament. La implementació de
TerraLab3D disposa d’un perfil d’horitzó obtingut del DEM real, una malla DEM
resident i un fallback visual transparent quan no hi ha autoritat DEM.

### Capacitats verificades

- L’arrel de dades és configurable i el DEM es resol a `data/earth/elevation`.
- `RasterioElevationAdapter` agrupa fonts per resolució, aplica memòria cau LRU,
  interpolació bilineal i fallback entre bandes sense convertir `nodata` en relleu.
- La curvatura usa `R = 6.371.000 m` i la refracció opcional `R_eff = 7R/6`.
- El radi manual d’1 a 530 km es conserva sense degradació científica silenciosa.
- El perfil binari versionat governa l’oclusió de cossos, estrelles i cel profund.
- `TerrainMeshBuilder` publica el pegat ENU i la malla polar com a buffers binaris
  amb la convenció `X=E, Y=Up, Z=-N`.
- La navegació, la col·lisió, el límit de cobertura i el Goto consulten la mateixa
  malla DEM resident; aturar-se no inicia nous càlculs.
- Els chunks detallats es preparen en segon pla, es retenen incrementalment i
  respecten una memòria cau GPU LRU acotada.
- La geometria DEM no es barreja amb ortofoto o cobertura categòrica; aquestes
  responsabilitats corresponen al Pas 17.

### Mesura de referència

Per a l’escena `41.21240330896238, 0.8072721734579367`, radi 150 km i pas 0,5°:

| Mètrica | Resultat |
| --- | ---: |
| Cobertura del perfil DEM | 100 % |
| Rajos científics | 720 |
| Cocció de l’horitzó | 20,436 s |
| Temps total amb malla | 33,243 s |
| Vèrtexs de malla | 268.209 |
| Índexs / triangles | 1.604.184 / 534.728 |
| Transferència de malla | 14.999.424 B |
| Pic RSS del procés | 379.854.848 B |

### Millores pendents relacionades

Aquestes millores no invaliden la vertical funcional del Pas 16, però continuen
obertes per als passos de superfície i homologació:

- refinament adaptatiu complet i objectiu automàtic de 8.849 m;
- reducció modal LOD i picking semàntic de categories;
- estil vibrant, atmosfera mètrica, ombres de cresta i proves visuals GPU;
- recuperació després de perdre el context WebGL i comparatives finals.
