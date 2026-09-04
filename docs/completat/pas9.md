# Pas 9 — Eclipsis, ocultacions, separacions i trajectòries

> Estat: **completat**
> Classificat mitjançant implementació, proves i validacions del repositori.

## Resultat funcional palpable

La simulació identifica i representa eclipsis solars/lunars, separacions angulars i trajectòries temporals dels cossos.

## Fonts TerraLab a consultar

- `TerraLab/astro/engine.py` — geometria d’eclipsi i separacions
- `TerraLab/runtime/offscreen_renderer.py` — fallback o composició actual
- `tests` d’eclipsis, fases i refracció

## Objectiu

Completar aquesta vertical funcional de punta a punta, mantenint la separació de responsabilitats i sense anticipar funcionalitats posteriors que no siguin imprescindibles.

## Tasques

- [ ] Crear un paquet científic específic d’eclipsis i ocultacions.
- [ ] Implementar separació angular i intersecció de discs aparents.
- [ ] Implementar magnitud, obscuració i fase instantània d’eclipsi.
- [ ] Implementar cerca de màxim i contactes dins d’un interval.
- [ ] Representar l’ombra, penombra o superposició amb geometria/materials adequats.
- [ ] Mostrar estat de l’esdeveniment i temps fins al contacte al HUD.
- [ ] Implementar trajectòries opcionals de Sol, Lluna, planetes i satèl·lits naturals seleccionats en un interval.
- [ ] Versionar la geometria de trajectòria i actualitzar-la només quan canvia l’interval.
- [ ] Gestionar esdeveniments no visibles des de la ubicació actual.
- [ ] Afegir toleràncies temporals i angulars explícites.
- [ ] Comparar esdeveniments coneguts amb TerraLab i una font astronòmica de referència.

## Criteri de sortida

Un cas d’eclipsi conegut es pot reproduir des de la UI temporal, els contactes i magnituds són coherents i les trajectòries no es recalculen per cada frame.

## Evidència obligatòria

- [ ] Fixtures d’eclipsi solar i lunar.
- [ ] Vídeo de l’esdeveniment a través de la timeline.
- [ ] Assertions de contactes, separacions i obscuració.
- [ ] Perfil de cost del càlcul i de la representació.

## Fora d’abast del pas

No inclou encara Via Làctia o NGC.

## Annex: Validació d’eclipsis, ocultacions i trajectòries

Data de validació: 2026-08-10

Base: `ebfc22844229cfb02288aeae7d6b245e794bbee1`

### Estat i autoritat científica

El Pas 9 està implementat sobre els kernels SPICE gestionats que ja usa el
sistema solar. No existeix una segona efemèride ni una segona càrrega de
kernels. `AstronomicalEventEphemerisPort` demana només els cossos necessaris i
comparteix `KernelManager`, lock, política d'aberració i lifecycle amb
`SpiceEphemerisAdapter`.

La convenció dels contactes és geomètrica i no refractada. C1–C4 es resolen
sobre limbe esfèric; LOLA només intervé en Perles de Baily i anell de diamant.

### Classificació solar i toleràncies

La classificació local és exactament:

```text
total:    d <= |Rm - Rs|  i  Rm >= Rs
annular:  d <= |Rm - Rs|  i  Rm < Rs
partial:  |Rm - Rs| < d < Rm + Rs
none:     d >= Rm + Rs
```

No hi ha èpsilon classificatori i `obscuration` no participa en la decisió.
Una prova construeix explícitament una parcial amb obscuració superior a
`0.999`.

Les toleràncies següents pertanyen exclusivament als algoritmes numèrics:

- contactes: `0.25 s` temporal i `1e-8°` residual angular;
- mínim temporal: cerca daurada fins a `0.25 s`;
- límit de banda: `1e-6°` en latitud i `1e-8°` en la funció de contacte intern;
- coarse scan de banda: `0.05°` per defecte, seguit de bracket i bisecció.

Cada `classify_observer()` crea el seu `ScientificObserver` i executa una
consulta topocèntrica Sol/Lluna independent. No comparteix ni interpola `d`.

### Fixtures 2026

El fixture offline és
`backend/tests/fixtures/eclipses_2026_reference.json`. Desa procedència,
observador, interval, contactes i toleràncies; NASA/JPL són validació, mentre
que el runtime continua sent SPICE/DE440.

#### Solar total — observador precís sol·licitat, 2026-08-12

Observador: `41.21240330896238°, 0.8072721734579367°`, elevació `330 m`.
La primera hora és UTC i la segona és hora local CEST (`UTC+2`):

```text
C1       17:35:28.007812Z  / 19:35:28.007812 CEST
C2       18:29:24.023438Z  / 20:29:24.023438 CEST
Greatest 18:29:59.095500Z  / 20:29:59.095500 CEST
C3       18:30:34.101562Z  / 20:30:34.101562 CEST
C4       19:21:15.820312Z  / 21:21:15.820312 CEST
magnitud màxima 1.0044504
```

A longitud `0.8072721734579367°`, al màxim:

```text
límit sud  40.7027481079°
límit nord 41.4648742676°
```

La prova obligatòria del límit nord usa `41.4498742676°` i
`41.4798742676°`: estan separats aproximadament `3.34 km`; el primer és
`total`, el segon `partial`, i el comptador confirma dues consultes SPICE
topocèntriques independents. També es valida el límit sud.

#### Lunar total — 2026-03-03

```text
P1       08:43:18.134766Z
U1       09:50:13.505859Z
U2       11:04:22.880859Z
Greatest 11:34:20.725903Z
U3       12:04:17.431641Z
U4       13:18:25.751953Z
P4       14:25:29.912109Z
magnitud umbral màxima 1.1580646
```

L'ombra usa Sol→Terra, eix antisolar, distàncies i radis físics. El factor
atmosfèric Danjon queda explícit com `1.02` i aproximat.

### Aparença i escena

- Durant un eclipsi solar, el shader lunar calcula per fragment la direcció
  visual cap al Sol. Només la intersecció Lluna–disc solar força alfa `1` i
  queda negra; la resta del costat nocturn conserva la transparència
  atmosfèrica establerta al Pas 8.
- El perfil visible LOLA publica `720` mostres de radi normalitzat. Una textura
  GPU persistent retalla el limbe ocultador i amplia la geometria només fins a
  l'envolupant màxima (`~1.0031` en la prova); les valls revelen el mateix disc
  solar subjacent, no un segon Sol ni un cercle negre substitutori.
- La Lluna té radi de presentació més proper i `renderOrder` superior al Sol:
  el Sol es pinta primer i la Lluna, com a foreground físic, l'oculta després.
- L'ombra lunar és espacial i per fragment sobre el material LRO existent;
  no és una multiplicació global d'opacitat.
- `LroLolaLimbProfileProvider` valida SHA-256 i deriva el limbe visible segons
  orientació, libració, observador i direcció topocèntrica.
- Les Perles de Baily agrupen valls LOLA realment exposades, amb posició,
  amplada, àrea, brillantor i limb darkening. Ingrés i egrés apareixen en
  costats diferents.
- La corona persistent és `magnetic_procedural_fallback`, qualitat
  `approximate`; distingeix polar plumes fines de helmet/equatorial/mid-latitude
  streamers i s'orienta amb el nord solar. La seva rampa visual depèn del gap
  geomètric al contacte intern, no d'un llindar ampli d'obscuració: és nul·la
  dos minuts abans de C2, emergeix amb les últimes perles, és visible amb
  l'anell de diamant i arriba a `1` en totalitat.
- Cromosfera i protuberàncies són `visual/approximate`. Durant Perles de Baily
  i anell de diamant la cromosfera queda limitada al sector topocèntric del
  contacte; la corona interna té estructura angular i no forma un donut blanc
  saturat que es pugui confondre amb una segona fotosfera.
- El cel de totalitat conserva un terra de llum dispersa de `0.06`; la paleta
  no torna a aplicar el mateix enfosquiment complet al shader. La supressió
  residual deixa un límit zenital aproximat de magnitud `1.42` en el màxim de
  la prova: Venus i només els astres més brillants poden emergir, sense
  convertir l'escena en una nit ordinària.
- Barra temporal i resultats de contacte mostren hora local del dispositiu i
  UTC simultàniament.
- Durant qualsevol eclipsi actiu, Sol i Lluna adopten atòmicament la generació
  científica de l'event i queden fora de la interpolació visual d'un segon.
  Això evita que corona, limbe LOLA i centres aparents barregin dues
  generacions i produeixin una rotació/tintineig entre snapshots.
- `EclipseSceneAppearance` s'aplica després dels factors científics, sense
  mutar magnitud, obscuració, efemèrides o Bortle.
- `CelestialOcclusionPolicy` ordena per `distanceKm` en capes compactes i
  recalcula escala per conservar el radi angular.
- `ApparentTrajectoryRenderer` és independent de `SatelliteOrbitRenderer` i
  manté buffers versionats persistents.

### Bridge i prova integrada

Missatges nous:

- `astronomical_event_snapshot`;
- `request_event_search` / `event_search_result`;
- `request_apparent_trajectory` / recurs binari `apparent_trajectory`.
- `request_angular_separation` / `angular_separation_result` per a una parella
  explícita, sense cap escaneig O(N²).

Prova real a `127.0.0.1:14398`, seguida de shutdown net:

```text
generació solar/event/sky/lighting 55
classificació total, obscuració 1.0
solarDiscTransmission 0.0 en event, sky i lighting
skyEclipseDimmingFactor 0.060; Bortle 4.0 intacte
eclipse snapshot 11687 bytes prop de C2 amb 720 mostres LOLA
cerca solar 136.25 ms, 300 consultes, C1/C2/C3/C4
trajectòria Lluna 64 mostres, 44.76 ms, 1088 bytes
event instant P50 0.447 ms; P95 0.740 ms
kernel pool net al tancament
```

La cerca i la trajectòria són `asyncio.to_thread`, cooperativament cancel·lables
i latest-wins; el tancament espera totes les tasques encara vives abans de
tancar l'adaptador SPICE.

### Regressions

```text
backend: 56 passed
frontend grid: 69 passed
frontend navigation: 18 passed
frontend solar system: 71 passed
frontend Step 8.6: 29 passed
frontend Step 8.7: 41 passed
frontend Step 9: 40 passed
frontend typecheck: passed
frontend build: passed
```

### Evidència visual pendent

La sessió no ha pogut capturar ni inspeccionar honestament imatges: el skill de
navegador no exposava cap browser i el fallback de Computer Use no trobava el
pipe nadiu (`os error 2`). El frontend WebGL sí que va arrencar i va publicar
mètriques, i la ruta de dades/renderers s'ha validat per tests i bridge, però
queden pendents les captures i vídeos subjectius enumerats al criteri
d'evidència del Pas 9. No es declaren observats.

### Fonts de validació

- NASA, [Total Solar Eclipse on August 12, 2026](https://science.nasa.gov/eclipses/future-eclipses/total-solar-eclipse-on-august-12-2026/)
- NASA GSFC, [2026 total eclipse path](https://eclipse.gsfc.nasa.gov/SEpath/SEpath2001/SE2026Aug12Tpath.html)
- NASA GSFC, [lunar eclipse contact convention](https://eclipse.gsfc.nasa.gov/OH/OHres/LEfigurekey.html)
- NAIF, [Geometry Finder Required Reading](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/req/gf.html)
- JPL, [Horizons manual](https://ssd.jpl.nasa.gov/horizons/manual.html)
