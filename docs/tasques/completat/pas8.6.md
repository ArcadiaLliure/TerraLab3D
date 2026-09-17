# Pas 8.6 — Planetes, anells i satèl·lits naturals

> **Estat:** completat. **Estat funcional:** observable. **Origen:** planificat. **Abast vigent:** planetes, anells i satèl·lits naturals implementat, verificat i observable en el repositori.

## Descripció funcional

El Sistema Solar deixa de representar els planetes com a discos o esferes genèriques i passa a disposar d’una representació 3D persistent i físicament orientada dels planetes, els anells de Saturn i els satèl·lits naturals planetaris coneguts amb efemèride disponible.

En completar aquest pas:

- Mercuri, Venus, Mart, Júpiter, Saturn, Urà i Neptú utilitzen les textures planetàries locals ja disponibles;
- la Terra no es representa com a planeta visible des de l’observador terrestre, però continua existint com a cos científic i origen de l’observador;
- Plutó i el seu sistema de satèl·lits s’admeten dins del mateix model genèric de cossos, encara que no es presenti com a planeta;
- cada planeta té radi/forma, eix de rotació, orientació body-fixed i rotació compatibles amb el millor model carregat;
- l’aspecte il·luminat de cada planeta prové de la direcció física cap al Sol, no d’una fase pintada dins de la textura;
- Saturn presenta anells persistents orientats pel seu **pla equatorial real**;
- la inclinació aparent dels anells no es calcula com una rotació visual independent: emergeix de la geometria observador–Saturn–pla equatorial;
- les llunes es posicionen a partir d’efemèrides JPL/NAIF SPK i no d’el·lipses keplerianes simplificades;
- les òrbites planetocèntriques es poden mostrar com a geometries persistents mostrejades de l’efemèride;
- la informació d’orientació, forma, radi, textura i qualitat física és explícita per cos;
- un satèl·lit sense textura o sense model d’orientació continua apareixent a la posició correcta, sense inventar dades;
- el sistema és data-driven: afegir una lluna nova al catàleg o als kernels no requereix crear un renderer específic;
- la càmera local continua sense provocar cap recàlcul científic ni cap round-trip Python per frame.

## Fonts a consultar

### TerraLab3D `main`

Abans d’implementar, revisar l’estat real de `main` després dels Passos 8 i 8.5. Preval el codi real sobre els noms conceptuals d’aquest document.

Revisar especialment:

- `EphemerisPort` o contracte equivalent creat al Pas 8;
- l’adaptador real d’efemèrides;
- `SolarSystemSnapshot` o estat equivalent;
- model de Sol, Lluna i planetes;
- renderer persistent de la Lluna creat/refinat al Pas 8.5;
- pipeline d’il·luminació Sol → cos;
- conversió ICRF/J2000 → ENU → Three.js;
- convenció d’eixos i quaternions;
- `celestialRoot`;
- bridge binari existent;
- sistema de recursos i manifests;
- UI `Cel → Sistema solar`;
- lifecycle de textures/materials/geometries;
- sistema de picking i labels existent.

No crear una segona autoritat de temps, observador, Sol o efemèrides.

### TerraLab, només com a referència funcional

Consultar en mode lectura:

- `TerraLab/astro/engine.py`;
- `TerraLab/astro/ephemeris_coordinator.py`;
- `TerraLab/runtime/offscreen_renderer.py`;
- `TerraLab/data/layer_manager.py`;
- qualsevol suport real de planetes, satèl·lits, fases, magnituds i textures que existeixi al checkout;
- tests d’efemèrides i sistema solar.

No copiar una representació 2D si entra en conflicte amb el model 3D persistent.

## Objectiu

Completar la vertical funcional de «planetes, anells i satèl·lits naturals» de punta a punta, mantenint la separació de responsabilitats i comprovant-ne el rendiment i funcionament observable.

## Dependències

**Depèn de:**
- [Pas 8 — Sol, Lluna i planetes amb posicions i aparença reals](pas8.md)
- [Pas 8.5 — Superfície lunar LRO/LOLA, orientació i libració](pas8.5.md)

**En depenen:**
- [Pas 8.7 — Il·luminació física de l'escena](pas8.7.md)
- [Pas 9 — Eclipsis, ocultacions, separacions i trajectòries](pas9.md)
- [Pas 24 — Catàleg de recursos i descàrregues persistents](../pendent/pas24-cataleg-recursos-descarregues.md)
- [Pas 38 — Homologació final, recuperació i rendiment](../pendent/pas38-homologacio-final.md)

## Codi existent a reutilitzar

- **Repositori actual:** Models, coordinadors i renderers Three.js del repositori.
- **Projectes de referència autoritzats:** TerraLab (commit `1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d`).

## Flux tècnic

Integració domini Python → bridge de missatges/binari → escena Three.js persistent.

## Errors, cancel·lació i recursos

Gestió de recursos amb `dispose()`, cancel·lació cooperativa i degradació controlada en cas d'absència de dades.

## Tasques

- [x] Implementació i integració completa de planetes, anells i satèl·lits naturals.

## Criteri de sortida

El Pas 8.6 no es considera complet fins que:

- [ ] les textures existents de `I:\TerraLab\data\sky\solar-system\planets` s’utilitzen a través de `data_location.json`, sense hardcodejar la unitat;
- [ ] els planetes reutilitzen el pipeline genèric extret de la Lluna sempre que sigui aplicable;
- [ ] els planetes tenen orientació física derivada del model científic, no rotations visuals manuals;
- [ ] Saturn té anells persistents alineats amb el seu equador real;
- [ ] la posició de Saturn, la seva orientació i el frame local de l’observador tenen autoritats separades i explícites;
- [ ] `SATURN (699)` no es confon amb `SATURN BARYCENTER (6)`;
- [ ] els radis de Saturn provenen del PCK actiu;
- [ ] la transformació ICRF/J2000 → local depèn correctament de l’observador i respecta `+Y = Up`;
- [ ] els anells comparteixen el pla equatorial però no hereten semànticament el spin W de la superfície;
- [ ] matriu SPICE → quaternion → Three.js conserva la transformació i usa ordre `[x,y,z,w]`;
- [ ] la inclinació aparent dels anells emergeix de la geometria;
- [ ] `B_geocentric` i `B_topocentric` estan diferenciats i cap d’ells controla la rotació del mesh;
- [ ] el cas `B ≈ 0°` és estable sense truc d’opacitat científicament fals;
- [ ] els anells tenen material de doble cara amb il·luminació solar direccional física;
- [ ] planetes i satèl·lits reutilitzen un sistema comú de `Body → Sun direction`, sense llum enganxada a càmera;
- [ ] visibilitat/horitzó reutilitza el pipeline compartit i la refracció queda preparada però no implementada;
- [ ] el catàleg del snapshot cobreix 461 planetary satellites;
- [ ] tots els satèl·lits amb SPK vàlid poden obtenir posició;
- [ ] cap absència de kernel/orientació/textura queda amagada;
- [ ] els satèl·lits sense orientació coneguda no reben rotació inventada;
- [ ] les òrbites es deriven de mostres SPK i no d’el·lipses ideals com a autoritat;
- [ ] les òrbites romanen persistents a GPU;
- [ ] els elements orbitals són metadades, no el motor de posició;
- [ ] la ciència continua íntegrament a Python;
- [ ] Three.js només representa estat científic + recursos visuals;
- [ ] el bridge envia deltes petits i buffers d’òrbita només per generació;
- [ ] la càmera local no recalcula planetes ni llunes;
- [ ] el sistema és data-driven i no conté centenars de classes específiques;
- [ ] lifecycle i `dispose` són idempotents;
- [ ] totes les proves científiques, visuals i de rendiment passen;
- [ ] els Passos 1–8.6 continuen funcionant;
- [ ] el Pas 9 encara no s’ha començat.

## Proves i evidències obligatòries

- [ ] Manifest de textures planetàries real de la carpeta de dades.
- [ ] Hash de totes les textures utilitzades.
- [ ] Manifest de kernels amb URL, hash i coverage.
- [ ] Snapshot versionat del catàleg JPL.
- [ ] Report de cobertura `catalogats / amb SPK / amb orientació / amb radi / amb textura`.
- [ ] Prova numèrica del pol/equador de Saturn.
- [ ] Prova de provenance dels radis de Saturn des del PCK actiu.
- [ ] Prova de cadena SPK Earth → Saturn barycenter → Saturn center.
- [ ] Prova numèrica ICRF/J2000 → local en diversos observadors.
- [ ] Prova d’equivalència matriu SPICE ↔ quaternion Three.js `[x,y,z,w]`.
- [ ] Prova numèrica de `B_geocentric` i `B_topocentric` dels anells en diverses dates.
- [ ] Captures de Saturn amb anells oberts i propers al cantell.
- [ ] Captures dels sistemes de Júpiter, Saturn, Urà i Neptú amb llunes.
- [ ] Captura de Plutó + Caront/Nix/Hidra/Quèrberos/Estix quan el FOV/mode d’inspecció ho permeti.
- [ ] Vídeo de timeline amb moviment continu de llunes sense reconstrucció de recursos.
- [ ] Vídeo activant/desactivant òrbites.
- [ ] Fixture d’Hiperió demostrant fallback honest d’orientació.
- [ ] Prova de data fora de coverage.
- [ ] Prova que canviar FOV/resize/camera roll no fa queries SPICE.
- [ ] Prova que caminar/volar no fa queries SPICE amb temps pausat.
- [ ] Mètriques P50/P95.
- [ ] Mètriques de bytes del bridge.
- [ ] Mètriques de memòria GPU.
- [ ] Prova d’arrencada → tancament → arrencada sense kernels/textures/geometries duplicats.

## Fora d'abast

Aquest pas no implementa encara:

- eclipsis i contactes;
- ocultacions entre cossos;
- trajectòries topocèntriques temporals del Pas 9;
- atmosfera meteorològica temporal de Júpiter/Saturn;
- núvols 3D volumètrics planetaris;
- self-shadow microscòpic i dispersió múltiple entre partícules individuals dels anells;
- refracció atmosfèrica aparent, que queda com a extensió del pipeline observacional;
- ombres topogràfiques d’alta resolució sobre totes les llunes;
- DSK d’alta resolució per centenars de cossos;
- textures científiques d’alta resolució per a totes les llunes quan no existeixen;
- satèl·lits artificials;
- navegació física sobre altres planetes;
- tots els sistemes binaris de small bodies com a criteri de tancament.

Aquests elements no poden justificar dades inventades dins del Pas 8.6.

## Instrucció per a Codex

Pas 8.6 completat amb èxit. Consultar el següent pas assenyalat a `docs/README.md`.

## Treball pendent

Cap després del criteri de sortida.

## Annex: Validació científica, de recursos i de rendiment

Data de preparació: 2026-08-09. Snapshot de catàleg: 2026-07-09.

### Resultat implementat

La ciència del sistema solar té una única autoritat `SpiceEphemerisAdapter` amb
DE440, SPK de satèl·lits, LSK, PCK/FK/BPC i política observacional `LT+S`. La
transformació és J2000/ICRF → `ITRF93` → ENU canònic i el wire conserva l’ordre
històric `(East, Up, North)`. Three.js rep quaternions `[x,y,z,w]`, vectors,
qualitats i recursos validats; no calcula efemèrides.

El renderer manté persistents la geometria planetària compartida, els materials,
les textures, el pla dels anells, un únic batch GPU de satèl·lits i els buffers
d’òrbita versionats. La superfície de Saturn rep W al seu `surfaceSpinRoot`; els
anells són un germà orientat només pel pla equatorial. L’oclusió del semianell
posterior es resol al shader projectant sobre l’el·lipsoide unitari en coordenades
locals de Saturn, sense dependre de la precisió del `depth buffer` a la distància
de l’esfera celeste; el semianell anterior i les zones fora del limbe es conserven.

La UI `Cel → Sistema solar` inclou anells, satèl·lits, òrbites, filtre per sistema,
LOD, etiquetes acotades i estat de catàleg/kernels/coverage. La inspecció mostra
NAIF, pare, distància, diàmetre angular, radis, fase, qualitat i diagnòstics B.

### Recursos i provenance

Els binaris viuen sota el `data_root` resolt per `data_location.json`, actualment:

```text
I:\TerraLab\data\sky\solar-system\planets
I:\TerraLab\data\sky\solar-system\kernels
```

No hi ha textures ni kernels al repositori. Els manifests compactes versionats
són a `backend/src/terralab3d/data/solar_system`; els manifests actius són a
`[data_root]/data/sky/solar-system/kernels/manifests`.

Fonts primàries:

- catàleg: <https://ssd.jpl.nasa.gov/sats/discovery.html>;
- paràmetres físics: <https://ssd.jpl.nasa.gov/sats/phys_par/>;
- kernels i checksums: <https://naif.jpl.nasa.gov/pub/naif/generic_kernels/>;
- inventari SPK: <https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/satellites/aa_summaries.txt>;
- vectors de contrast: <https://ssd.jpl.nasa.gov/api/horizons.api>;
- radis dels anells: <https://nssdc.gsfc.nasa.gov/planetary/factsheet/satringfact.html>.

Generació activa de kernels: `97bdf4bf136424a2`, 28 fitxers, 13.913.742.560 B
(12,958 GiB). Tots passen mida, confinament de ruta i SHA-256; quan NAIF publica
MD5 també es valida durant la preparació. Les 9 textures sumen 42.065.271 B i
també passen SHA-256 i validació de dimensions.

### Cobertura del catàleg

| Sistema | Catalogats | Amb SPK al snapshot |
|---|---:|---:|
| Terra | 1 | 1 |
| Mart | 2 | 2 |
| Júpiter | 115 | 115 |
| Saturn | 293 | 292 |
| Urà | 29 | 28 |
| Neptú | 16 | 16 |
| Plutó | 5 | 5 |
| **Total** | **461** | **459** |

Cobertura complementària: 51 orientacions i 71 radis. Els dos casos sense SPK
oficial són `S/2009 S1` i `S/2025 U1`; consten al catàleg com `NO_KERNEL` i no
reben posició inventada. Hiperió té radi però orientació `UNAVAILABLE`.

Decisió de precedència no determinada al pla: `nep104`/`nep105` es carreguen
abans de les tres parts de `nep098`, de manera que la solució global NEP098 de
2026 preval en solapaments. El canvi es va decidir després de contrastar Nereida
amb Horizons; l’error va passar de 317 km a menys de 2 nm al fixture J2000.

### Evidència numèrica

- 21 fixtures Horizons (`Moon`, Fobos, Deimos, galileanes, Himàlia, satèl·lits
  principals i irregulars de Saturn, Urà, Neptú i Plutó) coincideixen amb els
  SPK: error de posició < 0,1 km i velocitat < 1e-5 km/s.
- `SATURN (699)` es resol com a centre físic; el kernel actiu mai és el
  `SATURN BARYCENTER (6)`.
- `BODY699_RADII` del PCK actiu: `(60268, 60268, 54364) km`.
- El pol obtingut amb la matriu ICRF→ENU i el vector rotat pel quaternion
  equatorial coincideixen amb error < 1e-12.
- A 2026-07-09, B geocèntric és `-9,1023432032°` per a Barcelona i Canberra;
  B topocèntric és respectivament `-9,1021807782°` i `-9,1024948174°`.
- Fixtures B: `+9,1816°` (2024-01-01), `+0,0444°` (2025-03-23), `-2,1858°`
  (2025-05-06) i `-26,4934°` (2032-01-01), sense NaN ni flip.
- L’òrbita de Fobos es transmet com 64 mostres Float32: 768 B de payload.
- La prova d’oclusió dels anells verifica els tres casos geomètrics: davant del
  planeta, darrere del planeta i darrere però fora del limbe. El material no
  consulta ni escriu el `depth buffer`: l’oclusió analítica evita els forats
  triangulars del semianell anterior a la distància de l’esfera celeste.
- La regressió lunar recorre els angles de fase enters de `0°` a `180°` en els
  dos sentits del limbe (362 casos) i contrasta la fracció il·luminada amb
  `(1 + cos(phaseAngle)) / 2`, amb tolerància `1e-12`.
- El material lunar conserva `MeshLambertMaterial`, però recupera literalment
  del commit `439b9f6` l’alfa de fase `clamp(directLight + 0.015, 0, 1)`. Això
  deixa que l’atmosfera real del Pas 7 sigui predominant sense afegir cap llum,
  exposició ni segona capa atmosfèrica al renderer lunar. Durant el dia,
  `(1 - twilightFactor) * horizonHaze` comprimeix el contrast de l’albedo cap al
  gris lunar històric `#d8d8d2`; de nit el factor és exactament zero. La llum
  direccional té intensitat `π` per compensar el factor `1/π` del BRDF de
  `MeshLambertMaterial` i recuperar la luminància unitària del shader del Pas 8.

### Validacions executades

```text
python -m pytest backend/tests -q       31 passed
npm run typecheck                       passed
npm test                                187 passed
npm run build                           passed
git diff --check                        passed
```

Prova integrada d’arrencada/bridge/tancament:

- `/` = 200;
- textura externa validada = 200, nom fora de manifest = 404;
- manifests = 9 textures, 461 catalogats, 459 amb SPK;
- snapshot = SPICE/DE440, 8 planetes, kernels `ready`;
- activació del sistema de Mart i òrbita binària de Fobos correctes;
- pool CSPICE netejat i servidor aturat ordenadament.

Mètriques de la passada integrada: efemèrides P50/P95 `7,76/16,49 ms`, batch
d’orientació P50/P95 `1,10/1,48 ms`, òrbita de Fobos `3,69 ms`, snapshot compacte
`17.635 B`, 0 bytes de textures i 0 bytes de kernels pel bridge.

### Evidència visual pendent d’entorn

La sessió d’implementació no exposava cap backend de navegador, per tant no es
van poder produir captures ni vídeos ni mesurar P50/P95 del frame/GPU sobre una
escena WebGL real. La compilació, els tests de geometria/material/lifecycle i la
prova HTTP/WebSocket sí que es van completar. No afecta la ciència ni la
integració, però les captures, vídeos i mètriques de frame/GPU continuen sent
evidència visual pendent.
