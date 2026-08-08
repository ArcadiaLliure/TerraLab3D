# Pas 8.5 — validació de superfície i orientació lunar

## Resultat implementat

La Lluna és una esfera persistent dins de `celestialRoot`. `MoonSurfaceRenderer`
és propietari de `moonRoot`, `moonBodyRoot`, `moonSurfaceCalibration`, geometria,
material, albedo, normal map i lifecycle. Els snapshots només actualitzen posició,
mida angular, quaternion body-fixed, direcció Moon→Sun, visibilitat i uniforms.

La representació anterior del Pas 8 continua sent el fallback geomètric. L’albedo
LRO només s’activa quan el manifest local és vàlid **i** l’orientació
`MOON_ME_DE421` és precisa. La fase no forma part de l’albedo ni de l’alpha: el
terminador surt del producte entre la normal de superfície i la mateixa geometria
solar autoritativa del Pas 8.

## Fonts i procedència

- NASA SVS CGI Moon Kit: <https://svs.gsfc.nasa.gov/4720/>.
- Albedo mestre: `lroc_color_16bit_srgb_8k.tif`, mapa LROC 2025 sRGB, 8192×4096,
  SHA-256 `db7808e878b6a55eb409bb231eab8deb477f84b5c9d7396d76ff73e5d54992d9`.
- DEM: `ldem_16.tif`, LOLA float en quilòmetres respecte del radi 1737,4 km,
  SHA-256 `1ea42bf44f7e9d694f79c3afa7145f97fbf06cc67372067d9fe73dce43bad796`.
- Frame: `MOON_ME_DE421`, definit per `moon_080317.tf`, SHA-256
  `78732477b96f9863e7b0d65bcee3c22b8707ca5ed0db56d1173319cb2e8c7993`.
- Orientació: `moon_pa_de421_1900-2050.bpc`, SHA-256
  `656f90616403d75a75f0cd6c8830fc5b44f8cb4facb5ccb8915e752b397520cf`.
- Rang validat del PCK: `[1900-01-01, 2051-01-01)` UTC. Fora de rang s’emet
  `orientationQuality = out_of_range` sense extrapolació.

Crèdit mostrat al manifest i a la UI: NASA's Scientific Visualization Studio;
Ernie Wright (USRA); Noah Petro (NASA/GSFC); LROC WAC / Arizona State
University; Lunar Reconnaissance Orbiter Laser Altimeter (LOLA).

El manifest reproduïble és
[`docs/manifests/nasa-cgi-moon-kit-lro-lola-2025.json`](manifests/nasa-cgi-moon-kit-lro-lola-2025.json)
i el contracte és
[`contracts/schemas/moon-surface-manifest.schema.json`](../contracts/schemas/moon-surface-manifest.schema.json).

## Instal·lació explícita de la capa

No hi ha descàrregues en runtime. La instal·lació només es produeix amb:

```powershell
python -m pip install -r tools/requirements-moon-assets.txt
python tools/prepare_moon_surface_assets.py --data-root I:\TerraLab
```

El resultat queda a `I:\TerraLab\data\sky\moon` en aquest equip. El catàleg
`ManagedMoonSurfaceAssets` valida noms, mida i SHA-256 una vegada a l’arrencada.
El servidor només exposa els noms acceptats pel manifest sota `/moon-assets/`.
El bridge envia el descriptor i les URLs locals; `moon_bridge_texture_bytes = 0`.

No s’ha adoptat KTX2 perquè el projecte no inclou encara un encoder Basis ni el
transcoder local necessari. El pipeline actual genera JPEG sRGB 8K/4K i PNG
lineal per al normal map, amb mipmaps creats una sola vegada per Three.js.

## Convencions científiques i UV

- El PCK produeix ICRF→body; la transposada produeix body→ICRF.
- `ITRS.rotation_at(t)` i la localització geodèsica produeixen ICRF→ENU.
- `bodyToENUQuaternion` és `(x,y,z,w)` i usa eixos dretans East/North/Up.
- Els vectors del wire conserven l’ordre històric TerraLab3D East/Up/North.
- Una única conversió porta ENU a Three.js: `+X East`, `+Y Up`, `-Z North`.
- El mapa és equirectangular, centrat a longitud 0°, nord a dalt i longitud
  positiva cap a l’est.
- La calibració fixa és `Rx(+90°)` de la malla al body frame: longitud 0°→`+X`,
  nord→`+Z`, est→`+Y`. No depèn de data, observador ni càmera.

Accidents usats per a la inspecció del mapa: Copernicus (9,6°N, 20,1°O), Tycho
(43,3°S, 11,4°O), Aristarchus (23,7°N, 47,5°O) i Mare Crisium (~17°N, 59°E).
La cara propera queda centrada a 0° i el seam queda a ±180°.

## Rendiment i lifecycle

Memòria GPU aproximada per RGBA8 amb mipmaps (la compressió JPEG/PNG només
redueix disc i xarxa local):

| Configuració | Albedo | Normal LOLA | Total aproximat |
|---|---:|---:|---:|
| 8K + normal 4K | 170,67 MiB | 42,67 MiB | 213,33 MiB |
| fallback 4K + normal 4K | 42,67 MiB | 42,67 MiB | 85,33 MiB |

`renderer.capabilities.maxTextureSize` selecciona 8K o 4K. Les mètriques
separen construccions, càrregues d’albedo/normal, bytes estimats pujats i bytes
de textura pel bridge. `dispose()` invalida callbacks tardans, desconnecta el
root i allibera textures, material i geometria.

## Proves automatitzades

- Fixture oficial Skyfield: 2019-12-20 11:05 UTC dona libració `+1,520°` en
  longitud i `−6,749°` en latitud.
- El punt subobservador, transformat pel quaternion, coincideix amb la direcció
  Moon→observador amb error inferior a `3e-6` en vector unitari.
- Observadors en hemisferis diferents comparteixen sub-Earth però tenen
  sub-observer i quaternion local diferents.
- Missing kernel i out-of-range mantenen la Lluna del Pas 8.
- El mapping fixa longitude zero, nord i est sense flips.
- El límit GPU selecciona el fallback 4K; timeline no recarrega ni re-puja.
- Shutdown disposa totes les textures; manifest invàlid conserva fallback.
- El bridge no emet cap payload binari lunar.

Ordres de verificació:

```powershell
python -m pytest backend/tests -q
npm --prefix frontend run typecheck
npm --prefix frontend test
python tools/validate_skeleton.py
```

La inspecció visual dels derivats 4K confirma l’albedo neutre centrat a 0° i un
normal map LOLA coherent, sense ombres ni fase pre-renderitzades. La captura del
canvas i el vídeo de timeline queden com a evidència manual pendent perquè la
sessió d’implementació no disposava de cap navegador controlable; no se simulen
ni se substitueixen per una imatge sintètica.
