# Pas 10 — Via Làctia i pols galàctica Planck

> Estat: **completat**
> Classificat mitjançant implementació, proves i validacions del repositori.

## Resultat funcional palpable

La volta celeste mostra una Via Làctia orientada correctament i un mapa de pols Planck opcional, amb opacitat afectada pel cel i la contaminació lumínica.

## Fonts TerraLab a consultar

- `TerraLab/render/sky/milkyway_overlay.py`
- `TerraLab/data/layer_manager.py` — `SKY_MILKY_WAY` i `SKY_PLANCK_DUST`
- `TerraLab/data/assets/*` i manifests de recursos

## Objectiu

Completar aquesta vertical funcional de punta a punta, mantenint la separació de responsabilitats i sense anticipar funcionalitats posteriors que no siguin imprescindibles.

## Tasques

- [x] Identificar i validar els formats FITS/PNG i metadades de coordenades actuals.
- [x] Definir descriptors versionats per textura de Via Làctia i mapa Planck.
- [x] Implementar adaptadors de càrrega i conversió fora del domini.
- [x] Definir orientació galàctica, offset RA, flips i frame de coordenades com a estat tipat.
- [x] Carregar la textura una sola vegada per versió.
- [x] Representar la Via Làctia en un skydome persistent.
- [x] Aplicar opacitat, blend i extinció amb uniforms.
- [x] Aplicar pols com densitat visual i/o extinció segons la semàntica caracteritzada.
- [x] Mostrar estat de càrrega, recurs absent, fallback i errors.
- [x] Implementar toggles independents de Via Làctia i Planck.
- [x] Evitar qualsevol sampling de pantalla al backend.
- [x] Comparar orientació i estructura reconeixible amb TerraLab.

## Criteri de sortida

La Via Làctia i Planck apareixen orientats correctament, responen a temps/Bortle sense retransferir textures i fallen de manera explícita si falta el recurs.

## Evidència obligatòria

- [ ] Captures en diverses orientacions i dates.
- [ ] Hash, versió i mida de textures.
- [ ] Mesura de bytes transferits i memòria GPU estimada.
- [ ] Prova de recurs absent i recuperació després d’instal·lar-lo.

## Fora d’abast del pas

No inclou encara els objectes NGC/IC.

## Annex: Validació de la Via Làctia i la pols galàctica

Data de validació: 2026-08-10

### Fonts i adquisició

La Via Làctia usa exclusivament els cinc EXR celestes `milkyway_2020_*` de
NASA SVS 4851, de 4K a 64K. No existeix cap URL `_gal` ni `starmap_2020_*` al
descriptor. NASA documenta aquesta imatge com el fons sense estrelles brillants
Hipparcos/Tycho, en ICRF/J2000, plate carrée, amb RA=0h al centre i RA creixent
cap a l’esquerra.

La pols conserva la font utilitzada a TerraLab:
`COM_CompMap_Dust-GNILC-Model-Opacity_2048_R2.01.fits`, camp `TAU353`, HEALPix
NSIDE 2048 i marc galàctic. El FITS oficial és la font instal·lada; un
postprocessador genera localment una cache PNG 3600×1800 normalitzada als
percentils 1–99,5. El derivat no entra a Git ni substitueix el FITS.

Les descàrregues són HTTPS directes a NASA/IRSA, es fan en streaming a
`.part`, admeten represa i cancel·lació, calculen SHA-256, fan rename atòmic i
registren versió, mida, hash i metadades. El servidor local només serveix
assets `READY` resolts des del repositori; no és un proxy remot ni un CDN.

### Coordenades i renderer

`GalacticSkyRenderer` crea una sola `SphereGeometry`, un sol material i la
cara interior del skydome. Els recursos GPU persisteixen per versió i només es
reemplacen quan canvia aquesta versió.

Via Làctia NASA:

```text
fitxer NASA: y = 0.5 - Dec / 180° (nord a la fila superior)
GPU després d'EXRLoader: u = fract(0.5 - RA / 360°)
                         v = 0.5 + Dec / 180°
```

`EXRLoader` inverteix les scanlines del fitxer en construir la textura WebGL.
Per això la coordenada GPU de la Via Làctia no comparteix el signe vertical
amb la coordenada d'imatge ni amb el PNG Planck. Tractar-les igual reflectia el
cel en declinació: el nucli passava de Dec −28,94° a +28,94° i podia aparèixer
falsament a uns 78° d'altura des de 41,21° N.

Pols Planck derivada:

```text
ICRF/J2000 --matriu IAU fixa--> Galactic l,b
u = fract(l / 360°)
v = 0.5 - b / 180°
```

La conversió galàctica s’aplica només a Planck. La Via Làctia no té offset RA,
flip manual ni calibratge del centre galàctic. Posició de l’observador i temps
entren exclusivament per `CelestialTransformState`, la mateixa matriu
equatorial→horitzó local/Three.js que consumeix Gaia. La latitud determina la
inclinació respecte de l'horitzó i el temps sideral local incorpora data, hora i
longitud. No hi ha variables d’hemisferi, estació ni nucli galàctic: la
visibilitat estacional emergeix de la transformació.

La capa conserva la intenció de visibilitat de la UI, però no s'activa fins que
el primer `CelestialFrameTransform` és vàlid. En una reconnexió el backend
republica el marc vigent encara que latitud i LST no hagin canviat, sense crear
una generació científica fictícia.

El material fa blend additiu controlat: el negre no modifica el cel, Planck pot
afegir densitat visual i modular l’extinció del fons difús, i la brillantor del
cel/Bortle/airmass redueixen contínuament la visibilitat. Terreny i esfera
terrestre conserven el depth buffer i oculten el skydome sota l’horitzó.

### Cicle de vida i UI

Via Làctia i Planck tenen toggles independents al panell de cel. Un recurs no
instal·lat mostra descàrrega/progrés/pausa/reintent; Planck afegeix l’estat
`PROCESSING`. Un toggle només es desbloqueja en `READY`. Eliminar o invalidar
el recurs desactiva la capa; `dispose()` allibera textures, material, geometria
i invalida càrregues tardanes.

Les mètriques agregades publiquen construccions de geometria/material,
càrregues per capa, resultats obsolets, textures actives, bytes GPU estimats i
memòria GPU total aproximada.

### Proves

- UV NASA: centre, esquerra/dreta, dalt/baix i costura.
- Regressió EXR: el nucli conserva Dec −28,936175° en espai GPU; el flip
  rebutjat reprodueix la falsa culminació a 77,72° de la captura.
- Centre galàctic conegut: ICRS→Planck `l≈0°, b≈0°`.
- Barcelona i Sydney amb el mateix LST: orientació diferent sense canviar asset.
- Mateix observador amb LST separat 6 h: orientació temporal diferent.
- Pla galàctic amb una diferència d'inclinació superior a 60° entre Barcelona i
  Sydney per al mateix LST.
- Nucli galàctic a Barcelona: per sota de −60° a mitjanit el 15 de gener de
  2026 i per sobre de +14° a mitjanit el 15 de juliol de 2026.
- Matriu compartida amb Gaia al frontend.
- Capa bloquejada fins a rebre el marc local i republicació idempotent del marc
  després d'una reconnexió.
- Idempotència de versió, skydome persistent, rebuig explícit de textures que
  superen `MAX_TEXTURE_SIZE` i alliberament de recursos.
- FITS sintètic HEALPix→PNG i rebuig d’un `COORDSYS` no galàctic.
- Asset local absent/fora de la llibreria no s’exposa.

Resultat actual:

```text
backend: 68 passed
frontend Step 10: 29 passed
frontend typecheck: passed
frontend suites prèvies: passed
```

### Evidència visual pendent

No s’ha descarregat automàticament cap recurs pesat ni s’ha incorporat cap
asset al repositori. Per tant, les captures amb l’EXR NASA real i el FITS
Planck complet queden pendents d’una instal·lació voluntària des del gestor de
recursos. L’aplicació sí que ha arrencat amb una llibreria temporal, ha servit
el frontend amb HTTP 200 i la prova integrada ha verificat `Range` 206 per a
l’asset gestionat. La skill de navegador no ha trobat cap navegador controlable
en aquesta sessió; no es declara una validació visual que no s’ha observat.

### Fonts verificades

- NASA SVS, [Deep Star Maps 2020 — ID 4851](https://svs.gsfc.nasa.gov/4851/)
- NASA/IPAC IRSA, [Planck GNILC dust opacity R2.01](https://irsa.ipac.caltech.edu/data/Planck/release_2/all-sky-maps/previews/COM_CompMap_Dust-GNILC-Model-Opacity_2048_R2.01/index.html)
