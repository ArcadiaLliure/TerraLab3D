# Pas 19 — Modes d'observació: ull nu, càmera i telescopi

> Estat: **completat**. L'antic Pas 20 queda absorbit en aquesta vertical; el
> número es conserva només com a traça històrica.

## Resultat funcional verificat

- [x] Selector `eye | camera | telescope` de 36 × 36 px al costat de caminar/volar, amb SVG inline, `aria-label`, `title` i activació per teclat.
- [x] Una sola càmera visual: `CameraRig` conserva pose, pointing i FOV visual en tots els canvis de mode.
- [x] Rectangle de càmera i Scope circular com a overlays GPU retinguts; el clipping no força zoom.
- [x] UI de càmera amb APS-C, Full Frame, perfils personals, sensor, focal, número f, ISO, exposició, transmissió i tracking.
- [x] UI de telescopi amb paràmetres, HUD, moviment fi/ràpid, GoTo de selecció i RA/Dec manual.
- [x] Snapshot científic autoritatiu després de l'arrencada i de cada mutació vàlida; els borradors locals no alteren geometria ni resultats abans de l'acceptació.
- [x] Perfils personals i selecció persistents en JSON atòmic; l'arrencada sempre torna a `eye`.
- [x] `PhotographicLimitingMagnitudeModelV1` reproduïble i separat de qualsevol futura magnitud visual telescòpica.
- [x] Gaia profunda out-of-core amb interval `(8, photometricLimit]`, deduplicació, top-N global incremental, cancel·lació i recurs estable.
- [x] Ownership de traces `explicitSession > cameraPreview > none`, amb recuperació automàtica de la preview.

## Autoritat i contractes

`CameraRig` és l'única autoritat de pose i FOV visual. El backend ho és dels
perfils, paràmetres instrumentals, geometria òptica, fotometria i estat Gaia.
`ObservationSnapshot` no transporta estat de càmera visual.

Les revisions són independents:

- `observationRevision`: snapshot instrumental i mutacions validades;
- `deepQueryRevision`: consulta Gaia, cancel·lació i `latest-wins`;
- `gotoRevision`: resolució i navegació locals del frontend.

El contracte interoperable és
[`observation-state.schema.json`](../../contracts/schemas/observation-state.schema.json),
amb `schemaVersion: 1`. Els tipus de frontend són a
[`observation_contracts.ts`](../../frontend/src/contracts/observation_contracts.ts)
i els models autoritatius a
[`models.py`](../../backend/src/terralab3d/domain/optics/models.py).

## Càlcul científic

Totes les dimensions requerides són finites i estrictament positives; `null`
només s'admet als camps opcionals declarats.

### Camp i angle sòlid

Per cada dimensió del sensor:

```text
FOV = 2·atan(sensorDimension / (2·focal))
```

Per un rectangle, amb `a=FOVh/2` i `b=FOVv/2`:

```text
Ω = 4·atan((tan(a)·tan(b)) / sqrt(1 + tan²(a) + tan²(b)))  [sr]
```

Per un camp telescòpic circular, `r=trueFOV/2`:

```text
Ω = 2π·(1-cos(r))  [sr]
```

El telescopi inicial 400/80 mm amb ocular 20 mm i AFOV 50° produeix exactament
20×, pupil·la de sortida de 4 mm i camp real de 2,5°.

| Perfil, focal | FOV horitzontal | FOV vertical | Diagonal | Ω |
|---|---:|---:|---:|---:|
| APS-C 23,6 × 15,7 mm, 250 mm | 5,4047° | 3,5970° | 6,4893° | 0,0059188 sr |
| Full Frame 36 × 24 mm, 250 mm | 8,2364° | 5,4962° | 9,8913° | 0,0137725 sr |

### Escala de píxel

Amb dimensions i resolució es deriven `pitchX/Y` i governa `FOV/resolució`.
Sense resolució, un pitch conegut usa `206,265·pitch/focal` arcsec/px. La
coherència amb píxels quadrats es valida al 2 % inclusiu; els píxels no
quadrats exigeixen pitch X/Y o derivación completa de dimensions i resolució.

### PhotographicLimitingMagnitudeModelV1

Domini: estimació empírica de detecció puntual, no radiometria absoluta ni
simulació RAW. Unitats: focal i diàmetre en mm, exposició en segons, ISO
adimensional i pèrdues en magnituds.

```text
D = focalMm/fNumber
T_atmosphere = 10^(-0.4·atmosphericLossMag)
T_total = T_optics·T_atmosphere
capturedPhotonIndex = D²·t·T_total
s = log2(ISO/100)

G_iso = 1.25·log10(ISO)                                      si ISO≤100
G_iso = 2.5 + 1.25·log10(2)·(min(s,3)+0.25·max(0,s-3))      si ISO>100
P_short = 0                                                   si t≥5
P_short = 1.6·log10(5/t)                                     si t<5
L_sky = max(0, 7.6-eyeLimitMagnitude)

m_raw = 3.4 + 2.5·log10(D²) + 1.25·log10(t) + G_iso
        + 2.5·log10(T_total) - P_short
estimatedLimit = clamp(m_raw-L_sky, -12, 22)
```

La UI etiqueta el resultat com **«Magnitud límit estimada»**. L'atmosfera
només entra a `T_total`; ISO no modifica `capturedPhotonIndex`.

| Focal / f / ISO / t | Magnitud estimada | Índex de fotons |
|---|---:|---:|
| 250 / 4 / 800 / 2 s | 14,0478 | 6.498,15 |
| 250 / 4 / 800 / 10 s | 15,5583 | 32.490,77 |
| 250 / 2,8 / 800 / 2 s | 14,8224 | 13.261,54 |
| 400 / 4 / 800 / 2 s | 15,0684 | 16.635,28 |

## Render i coordinació

La projecció de càmera usa:

```text
x = tan(FOV_instr_h/2) / tan(FOV_visual_h/2)
y = tan(FOV_instr_v/2) / tan(FOV_visual_v/2)
```

El Scope calcula un únic radi angular i el shader compensa l'aspect ratio en
espai de píxel. Els renderers creen una geometria i un material retinguts,
només actualitzen uniforms en canvis explícits, restauren els recursos propis
després de `webglcontextrestored` i els alliberen en `dispose`.

La clau Gaia conté únicament azimut/elevació, diagonal instrumental i
profunditat fotomètrica. Zoom visual, resize, DPR i ticks de transformació no
la modifiquen. El debounce és de 300 ms. El backend recalcula autoritativament
radi (semidiagonal + 10 %) i límit, itera tiles, filtra, deduplica i manté fins
a 250.000 estrelles abans de substituir `stars:deep:camera`.

## Persistència i degradació

- [x] Presets integrats immutables.
- [x] IDs personals `camera:user:<uuid>`.
- [x] `selectedCameraProfileId` persisteix; mode i paràmetres de presa no.
- [x] Eliminar el perfil actiu selecciona APS-C.
- [x] Un JSON corrupte es conserva intacte, produeix avís recuperable i no bloqueja `eye`.
- [x] Sense Gaia es conserva el catàleg resident i s'informa de degradació.
- [x] La profunditat fotogràfica només filtra estrelles, mai DSO estesos.

## Proves i evidències

### Automatització

- [x] `pytest`: 140 proves de backend, incloses 12 del Pas 19.
- [x] `npm test`: totes les suites frontend, inclosa `observation_step19.test.ts`.
- [x] `npm run typecheck` i `npm run build`.
- [x] `python tools/validate_skeleton.py`.
- [x] `python tools/check_doc_links.py`.
- [x] Esquema JSON parsejat i `git diff --check` net.

La cobertura específica inclou números òptics, angle sòlid, pitches quadrats i
no quadrats, frontera del 2 %, nul·labilitat, vectors dorats del model V1,
invariància ISO/fotons, persistència/corrupció, interval Gaia, deduplicació,
top-N global, cancel·lació, overlays, clipping, cercle en píxels, clau
científica i precedència de traces.

### Recorrregut real i captures

El script reproduïble
[`capture_step19.mjs`](../../frontend/tools/capture_step19.mjs) va recórrer
`eye → camera → telescope → eye` a 1440 × 900 contra l'entrypoint real.

- [x] [Ull nu](../evidencies/pas19/eye.png)
- [x] [Càmera APS-C](../evidencies/pas19/camera.png)
- [x] [Telescopi](../evidencies/pas19/telescope.png)
- [x] Botó mesurat a 36 × 36 px, amb `aria-label` i `title` vigents.
- [x] HUD càmera: `5,40° × 3,60°`, magnitud estimada `14,05`.
- [x] HUD telescopi: `20,0×`, pupil·la `4,0 mm`, camp `2,50°`.
- [x] 120 frames: P50 `6,8 ms`, P95 `9,0 ms`; zero errors de navegador.
- [x] Gaia real: 46.295 estrelles seleccionades, 1.481.440 bytes, 327,8 ms en la consulta de major volum observada; recurs únic i acotat.

El smoke prolongat va detectar que una primera versió incloïa la generació de
transformació celeste a la clau Gaia. Es va retirar i es va afegir una prova de
regressió: cap tick temporal, zoom, resize o DPR torna a consultar Gaia.

## Criteri de sortida

- [x] Els tres modes són observables i l'ull nu conserva el comportament anterior.
- [x] Càmera i telescopi projecten camps físicament derivats sense segon zoom.
- [x] Perfils, previsualització, Scope, HUD, moviment i GoTo estan connectats punta a punta.
- [x] Gaia és cancel·lable, `latest-wins`, estable i acotada.
- [x] No hi ha round-trip científic per frame ni assignacions GPU per frame.
- [x] Tots els recursos i listeners nous tenen propietari, restauració i `dispose`.
- [x] Proves, captures, fórmules i mètriques són reproduïbles.

## Fora d'abast conservat

Mode prismàtics, segon motor de zoom, catàleg comercial de càmeres/objectius,
ASCOM/Alpaca/INDI, plate solving, RAW, HDR/autoexposure físic i calibratge
fotomètric absolut.
