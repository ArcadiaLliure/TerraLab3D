# Pas 15 — Validació d’elevació, horitzó i oclusió

Data de validació: 2026-08-14.

## Resultat funcional

La vertical implementada és:

```text
data_root configurat
  → adaptador DEM windowed + bare elevation
  → kernel radial vectoritzat + HorizonProfile 360°
  → recurs binari versionat
  → HorizonOcclusionState CPU/GPU
  → cortina angular Three.js
  → Gaia / NGC / Sistema Solar / labels / picking
```

El càlcul és automàtic: comença quan arriba l’elevació DEM inicial i es torna a
generar després d’un canvi d’observador o dels paràmetres topogràfics. El botó
`Regenerar ara` força un bake nou i no reutilitza la memòria cau. La pàgina
`Topografia` concentra els controls i l’estat; el HUD no conté controls de terreny.

La refracció atmosfèrica topogràfica conserva internament la paritat de TerraLab
amb `R_eff = 7/6 R`. No s’exposa com un control críptic a la pàgina principal.

## Configuració, DEM i CRS

La ruta no està codificada al programa. Es resol com:

```text
resolve_data_root() / data / earth / elevation
```

En aquesta màquina, `data_location.json` resol actualment `data_root` a
`I:\TerraLab`, i per tant el directori efectiu és
`I:\TerraLab\data\earth\elevation`. Canviar la configuració canvia la font sense
modificar el codi.

La cadena trobada conté 681 NPY, 215 ASC i el mosaic europeu
`eudem_dem_4258_europe.tifa` d’uns 20 GB. L’adaptador obre datasets de manera
mandrosa, fa lectures per finestra, conserva una memòria cau LRU acotada i tanca
els handles de manera idempotent. `nodata` es manté separat de 0 m.

El CRS mètric de treball és AEQD local centrat en l’observador; el CRS d’entrada,
el nadiu de cada raster i el de treball són explícits. La convenció radial és
0° nord, 90° est, 180° sud i 270° oest.

## Mostra real configurada

Observador de validació:

```text
latitud:  41.21240330896238°
longitud: 0.8072721734579367°
elevació bare DEM: 376.3800048828125 m
font: dem:Y_(4560000.0_4570000.0)X_(308000.0_318000.0)
```

El perfil per defecte té 150 km de radi, pas de 0,5°, 720 raigs, qualitat `REAL`,
cobertura resolta 100% i payload binari de 9.360 bytes.

## Kernel, cobertura i lifecycle

- Distàncies adaptatives amb passos 1×/2×/4×/8× segons distància i resolució.
- Càlcul angular i reducció del màxim vectoritzats amb NumPy.
- Un forat curt de `nodata` no talla un raig; vuit misses consecutius delimiten
  el final de cobertura.
- Un únic refinament acotat per costat conserva el pressupost.
- Worker `asyncio.to_thread`, cancel·lació entre batches, latest-wins i descart
  de resultats stale.
- Memòria cau de perfils acotada i clau basada en observador, elevació, offset,
  fingerprint DEM, settings i versió del kernel.
- `Regenerar ara` usa `force_recalculate` i salta aquesta memòria cau.
- Sense elevació real es publica immediatament un `FLAT_FALLBACK` de 0° i
  `resolvedFraction=0`, mai una elevació DEM fictícia.

La curvatura conserva la fórmula de paritat de TerraLab. Diferència de la
formulació exacta respecte de la paritat, en metres:

| Distància | Diferència |
|---:|---:|
| 1 km | -9,24e-10 m |
| 25 km | -0,000189 m |
| 150 km | -0,244778 m |
| 530 km | -38,273427 m |

## Payload i GPU

Cada perfil publica metadata immutable i quatre blocs contigus:

```text
Float32[N] horizonElevationDeg
Float32[N] occluderDistanceM
Float32[N] occluderHeightM
Uint8[N]   validMask
```

La mida és `13 × N` bytes: 9.360 bytes a 0,5° i 936.000 bytes a 0,005°.
La precisió de 0,005° conserva els 72.000 raigs en una `DataTexture` 2D de
4096 × 18; no redueix el perfil.

La silueta és una cortina angular persistent d’un sol `Mesh`, una sola
`BufferGeometry` i un sol material amb depth write. Els canvis de visibilitat no
reconstrueixen la geometria. El mateix estat decideix render, labels i picking de
Gaia i NGC, i enriqueix el Sistema Solar després de l’efemèride. La visibilitat
lògica dels discs usa radi angular; la cortina de profunditat en fa el clipping
parcial.

## Rendiment mesurat

Tres bakes reals independents amb els settings per defecte:

| Mètrica | Resultat |
|---|---:|
| horizon bake P50 | 13.236,86 ms |
| horizon bake P95 | 13.301,40 ms |
| raigs | 720 |
| mostres DEM | 2.949.120 |
| mostres/s | ~223.502 |
| batch màxim | 262.016 |
| peak RSS | 392.974.336 bytes |
| payload | 9.360 bytes |
| bytes raster lògics/run | ~7.889.374.000 |

Set consultes d’elevació bare van donar P50 0,423 ms i P95 202,387 ms, amb una
entrada servida des de memòria cau. La cancel·lació d’un bake de 72.000 raigs va
tenir 15,51 ms de latència observada (15,20 ms a la mètrica interna), no va
publicar cap perfil parcial i el worker va continuar reutilitzable.

Mètriques del test frontend:

```text
horizonUploadBytes:          13.824
horizonTextureBuildCount:    8
activeTextureCount:          1
horizonGeometryBuildCount:   6
horizonGeometryUploadBytes:  103.824
activeMeshCount:             1
horizonLookupCpuP50/P95:     ~0,0001 ms
```

## Comparació amb TerraLab

Amb el mateix DEM, observador, radi, pas angular i `7/6 R`, la comparació del
kernel nou contra la fórmula de TerraLab va donar:

```text
error angular mitjà: 7,235e-8°
P95:                  2,042e-7°
màxim:                4,624e-7°
```

Mostres cardinals/intercardinals del perfil real:

| Azimut | Angle | Distància oclusor | Alçada oclusor |
|---:|---:|---:|---:|
| 0° | 5,342365° | 7.212,5 m | 1.054,342 m |
| 45° | 4,081268° | 1.455,0 m | 480,340 m |
| 90° | 5,944355° | 2.777,5 m | 666,099 m |
| 135° | 8,013867° | 950,0 m | 510,189 m |
| 180° | 4,129484° | 5,0 m | 376,741 m |
| 225° | 0,629158° | 52.680,0 m | 1.141,560 m |
| 270° | 2,271088° | 5.755,0 m | 606,844 m |
| 315° | 4,211881° | 4.610,0 m | 717,308 m |

El pic local principal és a 133,5°: 8,251425°, 955 m i 514,934 m.

## Proves i evidència

- Backend complet: `97 passed`.
- Fixtures específiques Pas 15: `22 passed`.
- Frontend complet: totes les suites passen; Pas 15 `30 passed`.
- TypeScript `tsc --noEmit`: correcte.
- Bundle de producció: correcte.
- `compileall` backend: correcte.
- Tests coberts: flat/mountain/nodata, CRS geogràfic/projectat, curvatura i
  refracció, 5°/0,5°/0,05°/0,005°, cache/force-recalculate, cancel·lació,
  latest-wins, seam 359°/0°, Gaia/NGC/picking, discs parcials, lifecycle GPU i
  persistència de selecció.

Validació manual feta a l’aplicació:

1. l’observador configurat mostra elevació 376,4 m i source DEM real;
2. la cortina 360° mostra el perfil muntanyós i acaba en `REAL 100%`;
3. una ubicació 0°,0° mostra elevació no disponible i fallback pla explícit;
4. tornar a l’observador recupera el perfil real coherent;
5. un bake a 0,005° es pot cancel·lar i acaba en estat `cancelled`;
6. la convenció visual 0° nord/90° est es va contrastar amb l’azimut de Sol;
7. consola frontend i log backend sense errors en la sessió final.

La sortida/entrada exacta del Sol o la Lluna darrere d’una carena, i l’ocultació
manual d’una estrella i un NGC concrets, queden cobertes per proves automatitzades
però no es van aconseguir reproduir manualment amb una efemèride convenient durant
la sessió. Per tant, aquesta evidència visual concreta continua sent una limitació
de validació manual, no una limitació coneguda de la implementació.

Una revisió posterior amb captura real va detectar que l’atmosfera i la cortina
DEM compartien `renderOrder=-1000`: la passada atmosfèrica, amb depth test
desactivat, podia tapar completament la silueta. L’atmosfera es dibuixa ara com a
fons a `-2000`; la cortina DEM es dibuixa després, escriu profunditat i queda per
davant del cel. Una prova d’integració fixa aquest ordre.
