# Pas 8.7 — Informe de validació de la il·luminació física de l'escena

Data de validació: 2026-08-10

## Estat

La capacitat vertical del Pas 8.7 està implementada i supera la regressió
automàtica completa. El bridge i el lifecycle també s'han provat amb una
instància real en un port aïllat. Queda pendent l'evidència visual comparativa
i la mesura GPU en navegador real; per tant, aquest document no presenta com a
observades captures o mètriques que aquesta sessió no ha pogut obtenir.

El Pas 9 no s'ha començat. L'únic punt preparat per al pas següent és
`directSolarVisibilityFactor`, publicat amb valor `1.0`.

## Invariant lunar prioritari

La fase i l'aparença lunar continuen sota el camí específic Lluna→Sol del Pas
8/8.5, independent de les llums globals de l'escena:

- el subarbre lunar no conté cap `Light`;
- el shader lunar elimina completament l'acumulació de llums globals;
- el vector Lluna→Sol existent continua governant fase i terminador;
- la normal map LRO continua afectant la resposta superficial;
- la cara no il·luminada conserva exactament el terme atmosfèric d'opacitat
  `0.015`, de manera que l'atmosfera predomina i no apareix una pilota negra;
- el vel diürn neutre, l'orientació, la libració, els fallbacks i el lifecycle
  existents es mantenen;
- canviar el vector Lluna→Sol no pot mutar ni il·luminar el terreny local.

La Lluna sí aporta ara llum direccional al món local segons magnitud aparent,
altitud i extinció. És una escala visual PBR explícita, no lux. La referència de
Lluna plena alta dona `0.1118816576`: prou visible sobre el terreny tècnic fosc,
però molt inferior a la referència solar `3.0`. No s'ha afegit cap halo lunar.

## Halo solar

L'halo sol·licitat s'ha integrat en el shader atmosfèric del Pas 7, no com una
textura, un sprite o un lens flare:

- comparteix la direcció solar autoritativa;
- combina un nucli Mie compacte i una aurèola exterior suau;
- la terbolesa controla l'amplada angular;
- el color s'escalfa amb el Sol baix;
- desapareix quan el Sol és físicament sota l'horitzó;
- no afegeix cap dada, llum o efecte a la Lluna.

La prova numèrica comprova que la intensitat cau de forma monòtona entre
`0°`, `2°` i `8°`, que és zero a `-2°` d'altitud solar i que una terbolesa més
alta eixampla l'aurèola a `5°`.

## Arquitectura implementada

### Domini i bridge

- `LightingEnvironmentComposer` deriva un DTO renderer-neutral dels snapshots
  existents de cel i sistema solar, sense recalcular efemèrides.
- La direcció de cada llum és ENU `[East, Up, North]`, normalitzada i validada.
- La magnitud aparent lunar no es torna a multiplicar per fase i distància; el
  fallback només usa aquests factors quan la magnitud no existeix.
- La paleta lineal de cel és compartida per atmosfera i llum difusa.
- Bortle/SQM no crea cap llum local fictícia.
- El missatge `lighting_environment_snapshot` és JSON compacte i no transporta
  textures, geometries ni recursos Gaia.

### Escena persistent

- Existeix un únic `lightingRoot` persistent.
- Conté un `DirectionalLight` solar, un `DirectionalLight` lunar i un
  `HemisphereLight` difús encapsulat com a aproximació renderer-side.
- No s'utilitza `AmbientLight`.
- Els snapshots obsolets es descarten i els canvis normals s'interpolen durant
  un segon; els salts temporals grans i els canvis d'activació fan snap.
- La càmera només mou la regió local d'ombres i mai altera el vector científic.
- `dispose()` retira les llums i allibera els shadow maps de forma idempotent.

### PBR, color i ombres

- El terreny tècnic i només els objectes locals explícits utilitzen
  `MeshStandardMaterial`; no hi ha conversió indiscriminada de l'escena.
- Terreny: `metalness=0`, `roughness=0.92`.
- Les textures d'albedo es marquen sRGB i les normal/roughness/metalness/AO
  queden en `NoColorSpace`.
- El renderer usa color management explícit, sortida sRGB, `NoToneMapping` i
  exposició estàtica `1.0`, evitant una regressió de la capa celeste existent.
- Les qualitats d'ombra són `off`, `low=512`, `medium=1024` i `high=2048`.
- Les ombres solars tenen prioritat; les lunars queden opcionals/desactivades
  sense desactivar la llum lunar.
- La shadow camera local es recentra per texels i només s'invalida per direcció,
  canvi de regió, geometria o qualitat.

## Evidència automàtica

Execució final:

```text
backend:  40 passed
frontend typecheck: passed
frontend grid: 69 passed
frontend navigation: 18 passed
frontend solar system: 71 passed
frontend Step 8.6: 29 passed
frontend Step 8.7: 41 passed
frontend build: passed
```

Cobertura específica del Pas 8.7:

- Sol/Lluna alts, baixos i sota l'horitzó;
- Lluna plena, quart i nova, inclòs fallback sense magnitud;
- absència de doble aplicació de fase/distància lunar;
- hook acotat del Pas 9 amb valor base `1.0`;
- rebuig de NaN, infinits i vectors degenerats;
- coherència exacta de la paleta cel/difusa;
- direcció `DirectionalLight` coherent amb ENU→Three.js;
- 100 actualitzacions de timeline sense reconstruir llums ni materials;
- zero snapshots científics durant 120 moviments de càmera;
- descarte de generacions stale;
- PBR diferent per pla, pendent nord, pendent sud i vertical;
- qualitat i lifecycle d'ombres;
- color management i etiquetatge de textures;
- independència lunar respecte de les llums globals;
- independència del terreny respecte del vector Lluna→Sol;
- cara fosca lunar atmosfèrica amb opacitat base `0.015`;
- perfil físic-visual de l'halo solar.

## Prova integrada del bridge

Es va arrencar l'aplicació actual en `127.0.0.1:14408`, sense interferir amb la
instància de l'usuari de `14398`, i es va tancar amb `shutdown_complete`.

Resultat:

```text
lighting_environment_snapshot: 964 bytes
assets dins el snapshot: false
missatges lighting després de camera_changed amb temps pausat: 0
bytes binaris després de camera_changed amb temps pausat: 0
shutdown: net
```

Els `1,650,244` bytes binaris observats durant el handshake corresponen als
catàlegs inicials d'estrelles (`fallback` i `general`), no al snapshot ni a una
actualització d'il·luminació.

## Evidència visual i GPU pendent

No s'han pogut generar honestament des d'aquesta sessió:

- captures amb Sol alt i baix;
- captures Lluna plena/nova i nit fosca;
- comparació visual `shadows off/medium/high`;
- vídeo de sortida o posta;
- P50/P95 i memòria GPU mesurats en les quatre qualitats.

El navegador integrat no estava disponible per a automatització. Els comptadors
i la instrumentació necessaris sí que han quedat implementats al diagnòstic i al
missatge `frontend_performance_metrics`, però cal una passada visual/GPU en una
sessió WebGL real per completar aquesta part de l'evidència obligatòria.

## Fallbacks i límits

- Sense Sol vàlid: llum solar directa desactivada; cel/difusa continuen segons
  el snapshot disponible.
- Sense Lluna: llum lunar `unavailable`; la resta de l'entorn continua usable.
- Sense atmosfera: component difusa i halo atmosfèric desactivats.
- Sense shadow maps o amb pressupost insuficient: qualitat `off`, PBR disponible.
- `HemisphereLight` és una aproximació substituïble, no una dada científica.
- No hi ha autoexposure, HDR fotogràfic, scattering volumètric nou ni eclipsis.

