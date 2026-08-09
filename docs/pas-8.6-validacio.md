# Pas 8.6 — validació científica, recursos i rendiment

Data de preparació: 2026-08-09. Snapshot de catàleg: 2026-07-09.

## Resultat implementat

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

## Recursos i provenance

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

## Cobertura del catàleg

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

## Evidència numèrica

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

## Validacions executades

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

## Evidència visual pendent d’entorn

La sessió d’implementació no exposava cap backend de navegador, per tant no es
van poder produir captures ni vídeos ni mesurar P50/P95 del frame/GPU sobre una
escena WebGL real. La compilació, els tests de geometria/material/lifecycle i la
prova HTTP/WebSocket sí que es van completar. No afecta la ciència ni la
integració, però les captures, vídeos i mètriques de frame/GPU continuen sent
evidència visual pendent.
