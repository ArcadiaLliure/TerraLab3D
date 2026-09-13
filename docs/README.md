# Pla de millores de TerraLab3D

Aquest és el punt d'entrada i la font de veritat del progrés. L'estat es basa en comportament observable, proves i evidències del repositori; l'existència d'un paquet, contracte o renderer buit no equival a una funcionalitat implementada.

Consulta també les [normes d'arquitectura i execució](normes_arquitectura.md) i l'[inventari funcional verificat](inventari-funcional.md).

## Punt de represa

> **Següent pas executable: [Pas 17 — superfície progressiva](pendent/pas17-superficie-progressiva.md).**

La instrucció **«continua amb el pla de millores»** és suficient: Codex ha de començar en aquest README, seguir el punter anterior i executar només el primer pas que encara no compleixi el seu criteri de sortida.

## Protocol perquè Codex continuï el pla

1. Llegir aquest README i les [normes d'arquitectura](normes_arquitectura.md).
2. Obrir el document assenyalat a **Punt de represa** i verificar de nou l'estat del codi; el repositori actual preval sobre la descripció.
3. Implementar la vertical funcional completa en l'ordre de les caselles de “Treball pendent”, ampliant el codi existent indicat i respectant dependències i fora d'abast.
4. Executar les proves del pas i les regressions afectades; recollir les evidències exigides i escriure al document els resultats reproduïbles.
5. Actualitzar caselles i estat. `parcial` només és vàlid si hi ha una part observable connectada; un esquelet continua `pendent`.
6. Quan totes les caselles i el criteri de sortida estiguin verificats, canviar l'estat a `completat`, moure el mateix document de `pendent/` a `completat/`, actualitzar les dues taules i avançar **Punt de represa** al número següent.
7. No començar un pas posterior per esquivar un criteri de sortida ni incorporar una [idea per madurar](idees-per-madurar/README.md) a la seqüència sense tancar abans les seves decisions obertes.

Estats admesos:

- `completat`: vertical executable amb criteri de sortida i evidències verificats.
- `parcial`: hi ha comportament observable reutilitzable, però falta part del resultat funcional.
- `pendent`: només hi ha especificació, contractes, esquelets o cap implementació útil.
- `per madurar`: la idea encara té decisions funcionals o tècniques obertes i queda fora de l'ordre executable.

## Passos completats

| Pas | Capacitat | Estat |
|---:|---|---|
| 1 | [Entorn 3D executable, càmera 360° i bridge Python ↔ Three.js](completat/pas1.md) | `completat` |
| 2 | [Ubicació geogràfica de l'observador i orientació local](completat/pas2.md) | `completat` |
| 3 | [Rellotge de simulació, temps sideral i moviment visible](completat/pas3.md) | `completat` |
| 3.5 | [Càmera translacional, mode caminar i mode avió](completat/pas3.5.md) | `completat` |
| 4 | [Grid celeste, brúixola, etiquetes i HUD](completat/pas4.md) | `completat` |
| 5 | [Camp estel·lar Gaia real, fallback i buffers persistents](completat/pas5.md) | `completat` |
| 6 | [Picking estel·lar precís](completat/pas6.md) | `completat` |
| 7 | [Cel, atmosfera, contaminació lumínica i Bortle](completat/pas7.md) | `completat` |
| 8 | [Sol, Lluna i planetes amb posicions i aparença reals](completat/pas8.md) | `completat` |
| 8.5 | [Superfície lunar LRO/LOLA, orientació i libració](completat/pas8.5.md) | `completat` |
| 8.6 | [Planetes, anells i satèl·lits naturals](completat/pas8.6.md) | `completat` |
| 8.7 | [Il·luminació física de l'escena](completat/pas8.7.md) | `completat` |
| 9 | [Eclipsis, ocultacions, separacions i trajectòries](completat/pas9.md) | `completat` |
| 10 | [Via Làctia i pols galàctica Planck](completat/pas10.md) | `completat` |
| 11 | [Cel profund NGC/IC](completat/pas11.md) | `completat` |
| 12 | [Cerca astronòmica, focus i seguiment](completat/pas12.md) | `completat` |
| 13 | [Picking real, hover, selecció i inspecció](completat/pas13.md) | `completat` |
| 14 | [Traces circumpolars i exposició temporal](completat/pas14.md) | `completat` |
| 15 | [Elevació real, perfil d'horitzó i oclusió](completat/pas15.md) | `completat` |
| 16 | [Terreny 3D retingut, tiles, LOD i picking](completat/pas16.md) | `completat` |

La numeració decimal és històrica; els passos 1–16 i els seus subpassos no es renumeren.

## Passos pendents

| Pas | Capacitat | Estat | Dependències |
|---:|---|---|---|
| 17 | [Superfície, ortofoto, cobertura, estils i refinament visual](pendent/pas17-superficie-progressiva.md) | `parcial` | 16 |
| 18 | [Meteorologia real, fallback i efectes atmosfèrics](pendent/pas18-meteorologia.md) | `pendent` | 7 |
| 19 | [Modes ull, prismàtics i telescopi/càmera](pendent/pas19-modes-optics.md) | `pendent` | 5, 13 |
| 20 | [Simulació fotogràfica](pendent/pas20-simulador-fotografic.md) | `pendent` | 14, 19 |
| 21 | [Eines de mesura esfèrica](pendent/pas21-eines-mesura.md) | `pendent` | 6, 13, 19 |
| 22 | [Trajectòries i visibilitat sobre l'horitzó real](pendent/pas22-trajectories-visibilitat.md) | `parcial` | 9, 15 |
| 23 | [Constel·lacions oficials i d'usuari](pendent/pas23-constellacions.md) | `pendent` | 6, 13, 22 |
| 24 | [Catàleg de recursos i descàrregues persistents](pendent/pas24-cataleg-recursos-descarregues.md) | `parcial` | 8.6, 12 |
| 25 | [Gestor de capes Cel/Terra](pendent/pas25-gestor-capes.md) | `pendent` | 24 |
| 26 | [Vista de recursos del Sistema Solar](pendent/pas26-recursos-sistema-solar.md) | `parcial` | 24, 25 |
| 27 | [Carta de recursos d'espai profund](pendent/pas27-recursos-espai-profund.md) | `parcial` | 10, 11, 24, 25 |
| 28 | [Descobriment de DEM multiproveïdor](pendent/pas28-dem-multiproveidor.md) | `parcial` | 16, 24, 25 |
| 29 | [Superfície semàntica, TLST i refinament](pendent/pas29-superficie-semantica.md) | `parcial` | 17, 24, 25 |
| 30 | [Plate solving i comparador foto/simulació](pendent/pas30-plate-solving.md) | `pendent` | 5, 11, 20 |
| 31 | [“El millor d'aquesta nit” i planificador](pendent/pas31-millor-nit-planificador.md) | `pendent` | 22, 23 |
| 32 | [Motor general d'efemèrides](pendent/pas32-motor-efemerides.md) | `parcial` | 9, 22 |
| 33 | [Cercador d'objectes i efemèrides](pendent/pas33-cercador-objectes-efemerides.md) | `parcial` | 31, 32 |
| 34 | [Miniatures i animacions d'efemèrides](pendent/pas34-previsualitzacions-efemerides.md) | `pendent` | 32, 33 |
| 35 | [Pestanya d'eclipsis](pendent/pas35-pestanya-eclipsis.md) | `parcial` | 9, 33, 34 opcional |
| 36 | [Esdeveniments propis de planetes i Lluna](pendent/pas36-esdeveniments-objectes.md) | `parcial` | 32, 33 |
| 37 | [Nomenclàtor GeoNames empaquetat](pendent/pas37-geonames-empaquetat.md) | `pendent` | 19, 29 |
| 38 | [Homologació final, recuperació i rendiment](pendent/pas38-homologacio-final.md) | `pendent` | 1–37 |

## Idees per madurar

Els dotze dossiers exclosos de la seqüència executable, la seva decisió pendent, condició de maduresa i relació amb el backlog són a l'[índex d'idees per madurar](idees-per-madurar/README.md). El seu estat és `per madurar`.

## Mapa històric de la consolidació

La taula registra una sola destinació per a cadascun dels vuit pendents històrics i els vint-i-cinc dossiers madurs del brainstorming. Els números de “pendent” i “novetat” són els identificadors anteriors a la fusió; ja no són ordre executable.

| Pas final | Fonts absorbides | Decisió de fusió |
|---:|---|---|
| 17 | pendent 17 + novetat 37 | Superfície i refinament visual sobre els tiles ja completats. |
| 18 | pendent 18 (còpia local provisional 30) | Meteorologia conserva tot el contingut i recupera el número correcte. |
| 19 | pendent 19 + novetat 25 | Enquadrament, geometria òptica, HUD, Gaia i persistència. |
| 20 | pendent 20 + novetat 26 | Fotometria, soroll, exposició, tracking i exportació. |
| 21 | pendent 21 | Mesures esfèriques editables. |
| 22 | novetat 28 | Trajectòries comunes i visibilitat contra l'horitzó real. |
| 23 | pendent 22 + novetat 29 | Constel·lacions oficials, observables, editables i persistents. |
| 24 | part de pendent 23 + novetat 42 | Catàleg i treballs de descàrrega. |
| 25 | resta de pendent 23 + novetat 39 | Capes, AOI, disponibilitat, visibilitat i preferències. |
| 26 | novetat 40 | Recursos del Sistema Solar. |
| 27 | novetat 41 | Recursos d'espai profund. |
| 28 | novetat 43 | DEM multiproveïdor. |
| 29 | novetats 44 + 45 + 46 | Superfície semàntica, TLST i refinament. |
| 30 | novetat 27 | Plate solving. |
| 31 | novetats 30 + 31 | Recomanacions i planificador com una experiència única. |
| 32 | novetat 32 | Motor general d'efemèrides. |
| 33 | novetat 33 | Cercador multipestanya. |
| 34 | novetat 34 | Previsualitzacions generades pel renderer. |
| 35 | novetat 35 | Pestanya d'eclipsis. |
| 36 | novetat 36 | Esdeveniments propis per cos. |
| 37 | novetats 47 + 48 + 49 | Assentaments, cims i dades base empaquetades. |
| 38 | pendent 24 + novetat 38 | Homologació i transicions llargues interactives; el vol físic queda immadur. |

## Procedència i criteri del brainstorming

La pluja d'idees va aportar 25 propostes prou tancades per fusionar amb el pla i 12 dossiers amb preguntes obertes. Aquesta consolidació conserva decisions funcionals, elimina repeticions i instruccions de “crear des de zero”, i les vincula al codi real disponible. TerraLab és només oracle de comportament al [commit auditat `1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d`](https://github.com/ArcadiaLliure/TerraLab/tree/1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d); TerraLab3D no en depèn en execució.

## Evidències i dades de referència

- [`manifests/`](manifests/) conté manifests reproduïbles de recursos científics.
- [`reference-scenarios/`](reference-scenarios/) conté escenaris i captures de comparació visual.
