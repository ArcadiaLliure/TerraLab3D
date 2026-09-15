# Pas 19 — Modes d'observació: ull nu, càmera fotogràfica i telescopi/Scope

> Estat: **pendent**. Aquest pas replanteja l'antic Pas 19 i **absorbeix completament l'antic Pas 20**. El número 20 queda reservat com a traça històrica i no es renumera la resta del pla.

## Decisió de producte

El zoom/FOV global de TerraLab3D ja és prou potent per cobrir visualment l'ús a ull nu, amb prismàtics i amb telescopi. Per tant:

- **no existeix un mode prismàtics**;
- **no es crea un segon motor de zoom** per a càmera o telescopi;
- el FOV visual continua sent responsabilitat de la càmera Three.js existent;
- els modes instrumentals aporten **enquadrament, paràmetres, fotometria i navegació instrumental**, no una càmera 3D paral·lela.

El nou selector d'observació té exactament tres estats:

```ts
type ObservationMode = "eye" | "camera" | "telescope";
```

## Estat actual verificat

- [x] El `CameraRig` ja proporciona el zoom/FOV visual global i permet arribar a camps extremadament estrets; aquest mecanisme es conserva.
- [x] Hi ha models de domini per `InstrumentKind.CAMERA`, `InstrumentKind.TELESCOPE`, `SensorFormat`, `OpticalInstrument`, `ExposureSettings` i `FieldOfView`.
- [x] Existeixen `OpticsPanel`, `ScopeLayerRenderer` i `ImagingPreviewLayerRenderer` com a fronteres reutilitzables.
- [x] El Pas 12 ja aporta cerca/focus d'objectes i el Pas 13 selecció/inspecció.
- [x] El Pas 14 ja aporta traces temporals reutilitzables.
- [x] El Pas 7 ja aporta atmosfera, contaminació lumínica i magnitud límit a ull nu.
- [ ] No existeix encara un `ObservationModeController` funcional connectat al runtime.
- [ ] No hi ha selector `ull / càmera / telescopi` al costat del botó `Caminar / Avió`.
- [ ] No hi ha visor rectangular de càmera dependent del sensor ni perfils personals persistents.
- [ ] No hi ha previsualització fotogràfica que modifiqui el cel segons els paràmetres de captura.
- [ ] No hi ha mode telescopi/Scope integrat amb GoTo i paràmetres instrumentals.

## Resultat funcional

L'usuari disposa, al costat del control `Caminar / Avió`, d'un segon botó quadrat i intercanviable amb el mateix llenguatge visual. El botó alterna:

1. **Ull nu** — comportament actual.
2. **Càmera** — visor rectangular, configuració fotogràfica, perfil de càmera i previsualització de magnitud límit.
3. **Telescopi** — Scope circular/reticle, paràmetres òptics, moviment fi i GoTo a qualsevol objecte conegut per TerraLab3D.

Canviar de mode **no recrea l'escena ni la càmera**, no modifica la ubicació de l'observador i no produeix salts de pose.

---

# 1. UI del selector d'observació

## 1.1 Ubicació

El control s'afegeix a `LocationPage.ts`, a la mateixa fila del botó existent `nav-mode-toggle`.

Representació conceptual:

```text
Navegació
[ caminar/avió ] [ ull/càmera/telescopi ]  ...
```

Tots dos botons han de compartir:

- `36 × 36 px`;
- radi, border, hover i variables CSS;
- `aria-label`;
- `title`;
- navegació per teclat;
- estat visual actiu coherent.

## 1.2 Icones

Afegir SVG inline coherents amb `WALK_SVG` i `FLIGHT_SVG`:

```ts
const EYE_SVG = `...`;
const CAMERA_SVG = `...`;
const TELESCOPE_SVG = `...`;
```

No cal cap dependència d'icones externa.

El botó mostra sempre la icona del mode actiu.

## 1.3 Semàntica

Clic:

```text
eye → camera → telescope → eye
```

No s'ha d'introduir `binoculars`.

La UI pot mostrar una etiqueta textual del mode actiu, però l'estat autoritatiu és `ObservationMode`.

---

# 2. Separació obligatòria entre FOV visual i camp instrumental

S'han de mantenir dues magnituds diferents:

```ts
interface VisualCameraState {
  visualFovDeg: number;
}

interface InstrumentField {
  widthDeg: number;
  heightDeg: number;
  shape: "rectangle" | "circle";
}
```

## Regla

`visualFovDeg`:

- és el zoom real que ja existeix;
- continua controlat pels gestos actuals;
- no depèn del mode instrumental.

`InstrumentField`:

- es calcula amb focal, sensor, ocular o paràmetres equivalents;
- només determina el rectangle/cercle projectat a pantalla;
- no substitueix el FOV global.

Això permet que un camp instrumental de 2° es vegi gran o petit segons el zoom visual actual sense alterar el seu valor científic.

Opcionalment es pot oferir una acció **«Ajustar vista al camp»** que estableixi el FOV visual perquè el visor ocupi una fracció còmoda de la pantalla. És una drecera de càmera, no un segon sistema de zoom.

---

# 3. Mode ull nu

És exactament el comportament actual.

En entrar a `eye`:

- s'amaga qualsevol marc instrumental;
- es desactiva qualsevol filtre fotogràfic;
- es conserva la pose;
- es conserva el FOV visual;
- es conserva picking, cerca, HUD, atmosfera i capes;
- no s'aplica cap preset instrumental.

No hi ha paràmetres propis.

---

# 4. Mode càmera

## 4.1 Objectiu

Simular **què entraria al sensor i fins a quina profunditat fotogràfica és raonable arribar** amb una configuració donada, sense convertir el Pas 19 en un simulador RAW ni en un laboratori complet d'electrònica de sensors.

La vista és rectangular.

L'exterior del rectangle pot quedar enfosquit lleugerament, mantenint visible el context de l'escena.

## 4.2 Tipus inicials de sensor

Presets geomètrics obligatoris:

```text
APS-C genèric   23,6 × 15,7 mm
Full Frame      36,0 × 24,0 mm
```

`APS-C genèric` és deliberadament una aproximació. Un perfil personal pot substituir aquestes dimensions per les reals del model.

No es manté el preset `1/2.8"` com a opció principal de producte.

## 4.3 Camp rectangular

Per cada dimensió del sensor:

```text
FOV = 2 · atan(sensor_mm / (2 · focal_mm))
```

Cal calcular:

- FOV horitzontal;
- FOV vertical;
- diagonal;
- relació d'aspecte;
- superfície angular aproximada.

El rectangle es projecta sobre l'escena celeste al centre de la vista.

## 4.4 Controls de captura

Controls mínims de sessió:

- càmera/perfil;
- ISO;
- temps d'exposició;
- focal de l'objectiu en mm;
- obertura en nombre f;
- tracking `on/off`.

El temps d'exposició és obligatori: sense temps no es pot caracteritzar una captura.

## 4.5 Perfil de càmera

Separar **dades del cos/sensor** de **paràmetres de la presa**.

```ts
interface CameraProfile {
  id: string;
  name: string;
  sensorFormat: "aps_c" | "full_frame" | "custom";
  sensorWidthMm: number;
  sensorHeightMm: number;
  pixelPitchUm: number | null;
  resolutionWidthPx?: number | null;
  resolutionHeightPx?: number | null;
  quantumEfficiency?: number | null;
  readNoiseElectrons?: number | null;
  fullWellElectrons?: number | null;
  maxIso?: number | null;
  source: "builtin" | "user";
  schemaVersion: number;
}
```

Els camps avançats són opcionals perquè una càmera personal s'ha de poder crear encara que l'usuari no conegui totes les especificacions.

## 4.6 Càmeres personals

La primera versió **ha de permetre crear, editar, seleccionar i eliminar perfils personals**.

Flux:

```text
Càmera
└── Perfil
    ├── APS-C genèric
    ├── Full Frame
    ├── Les meves càmeres
    │   ├── Nikon ...
    │   └── Canon ...
    └── + Nova càmera
```

Crear una càmera personal demana com a mínim:

- nom;
- format del sensor;
- amplada/altura exactes si és `custom`;
- mida de píxel, si es coneix.

La persistència és versionada i sobreviu a reinicis.

L'usuari **no ha de tornar a introduir les dades estàtiques del sensor cada vegada**.

Els últims paràmetres de captura poden persistir per perfil com a preferència, però no formen part de la identitat científica del model de càmera.

## 4.7 Base de dades pública futura

La futura base de dades de models comercials **no és dependència del Pas 19**.

Quan existeixi, haurà d'emplenar el mateix `CameraProfile` que avui emplena l'usuari manualment.

Això permet evolucionar de:

```text
Nova càmera → dades manuals
```

a:

```text
Fabricant → model → perfil autocompletat
```

sense canviar el motor fotogràfic.

Una futura base de dades d'objectius pot seguir el mateix patró, però queda fora d'aquest pas.

## 4.8 Escala de píxel

Quan `pixelPitchUm` sigui conegut:

```text
arcsecPerPixel = 206.265 · pixelPitchUm / focalMm
```

Mostrar:

- arcsec/px;
- mostreig estimat;
- dimensions angulars totals del sensor.

La mida del píxel **no determina per si sola** la magnitud límit.

## 4.9 Magnitud límit fotogràfica

Cal distingir dos nivells.

### Nivell A — estimació bàsica

Disponible sempre que hi hagi:

- focal;
- obertura;
- ISO;
- exposició;
- atmosfera/contaminació lumínica.

Pot reutilitzar i recalibrar el comportament del motor de TerraLab com a oracle funcional.

El resultat s'etiqueta:

```text
Magnitud límit estimada
```

No s'ha de presentar com una mesura física exacta.

### Nivell B — sensor-aware

Quan el perfil disposi de prou dades instrumentals, el model pot incorporar:

- mida de píxel;
- eficiència quàntica;
- read noise;
- full well;
- brillantor de fons;
- extinció atmosfèrica.

Aquest nivell pot derivar SNR i un llindar de detecció explícit.

**No bloqueja el Pas 19.**

## 4.10 Tractament d'ISO

ISO no es modela com si augmentés linealment el nombre de fotons capturats.

El model ha de separar:

```text
flux capturat
≠
guany electrònic / ISO
≠
mapatge visual de pantalla
```

Si el model bàsic conserva una aproximació empírica heretada de TerraLab, aquesta aproximació ha d'estar identificada i coberta per proves de monotonicitat i límits.

## 4.11 Aplicació al cel

La previsualització fotogràfica:

- calcula una magnitud límit estimada;
- actualitza visibilitat/brillantor de les estrelles sense modificar el catàleg font;
- reutilitza atmosfera i contaminació lumínica existents;
- demana Gaia més profund només si la profunditat necessària no és resident;
- manté l'escena interactiva durant aquesta consulta.

No s'ha d'aplicar una regla falsa d'integrated magnitude als objectes extensos de cel profund. La seva fotometria superficial queda fora fins que hi hagi un model adequat.

## 4.12 Exposició i traces

Si `tracking = false`:

- una exposició prou llarga reutilitza la geometria temporal del Pas 14;
- la longitud de la trace depèn de temps i moviment aparent.

Si `tracking = true`:

- s'anul·la la trace estel·lar de la previsualització;
- no s'està simulant encara una muntura física real.

---

# 5. Mode telescopi / Scope

## 5.1 Objectiu

Recuperar el comportament útil del mode Scope de TerraLab sobre la nova arquitectura 3D, sense duplicar el zoom.

El visor és circular, amb exterior enfosquit, reticle central i HUD lleuger.

## 5.2 Paràmetres mínims

- focal del telescopi en mm;
- obertura/diàmetre en mm;
- focal de l'ocular en mm;
- camp aparent de l'ocular, si es coneix.

Derivats:

```text
augment = focal_telescopi / focal_ocular

pupil·la_sortida = obertura_mm / augment

FOV_real ≈ AFOV_ocular / augment
```

Si no hi ha AFOV d'ocular, es pot utilitzar un valor per defecte explícit i mostrar-lo com a estimació.

## 5.3 HUD

Mostrar com a mínim:

- objecte/centre actual;
- RA/Dec;
- azimut/elevació, quan sigui aplicable;
- FOV instrumental;
- augment;
- pupil·la de sortida.

No cal duplicar al HUD dades que ja siguin visibles en un altre panell.

## 5.4 GoTo

El telescopi ha de poder fer **GoTo a qualsevol objecte resolt pel cercador existent**.

Flux:

```text
usuari selecciona objecte
→ cerca/focus existent resol identitat i coordenades
→ ObservationModeController demana centrat
→ CameraRig orienta la vista
→ Scope centra el reticle
```

El GoTo:

- no canvia latitud/longitud de l'observador;
- no crea una segona càmera;
- no necessita un catàleg propi;
- no bloqueja la UI mentre resol dades;
- usa request/revision i `latest-wins`.

Conservar també entrada manual RA/Dec com a control avançat.

## 5.5 Moviment del Scope

Conservar del comportament TerraLab:

- arrossegament del reticle/camp;
- moviment fi;
- moviment ràpid;
- pas curt;
- hold rate;
- centrat coherent després d'un GoTo.

La roda continua controlant **el zoom visual global** segons la semàntica actual de TerraLab3D.

No s'ha de recuperar el vell comportament de tenir un zoom intern independent del Scope.

---

# 6. Arquitectura

## 6.1 Estat

Afegir un estat independent de la càmera:

```ts
interface ObservationState {
  mode: ObservationMode;
  cameraProfileId: string | null;
  cameraSettings: CameraCaptureSettings | null;
  telescopeSettings: TelescopeSettings | null;
  revision: number;
}
```

## 6.2 Controlador

Responsabilitat conceptual:

```text
UI
→ ObservationModeController
   ├── Eye
   ├── Camera configuration
   ├── Telescope configuration
   ├── GoTo intent
   └── persistence intent
→ Python/domain calculations
→ scene delta
→ retained renderer
```

El controlador no fa càlculs científics.

## 6.3 Domini

Ampliar `domain/optics` per a:

- perfils de càmera;
- paràmetres de telescopi;
- FOV instrumental;
- escala de píxel;
- magnituds òptiques derivades.

`domain/imaging` queda reduït al necessari per a la previsualització fotogràfica:

- sessió de captura;
- estimació de profunditat;
- opcionalment estimació sensor-aware;
- tracking;
- snapshot reproduïble de previsualització.

No és requisit del Pas 19 exportar PNG/JPEG.

## 6.4 Renderer

Reutilitzar:

- `ScopeLayerRenderer.ts` per a camp/reticle instrumental;
- `ImagingPreviewLayerRenderer.ts` per a la previsualització fotogràfica;
- `StarTrailLayerRendererImpl.ts` per a traces ja existents.

Cap renderer decideix magnitud límit ni calcula fotometria.

## 6.5 Gaia profunda

Quan la magnitud límit de càmera requereixi estrelles no residents:

```text
preview revision N
→ depth request N
→ Gaia async
→ resposta N
→ comprovar que N continua vigent
→ actualitzar buffers
```

Canviar ISO/exposició/configuració abans de completar la consulta invalida la revisió anterior.

La càmera, reticle, terreny i resta de l'escena continuen funcionant.

---

# 7. Codi existent a reutilitzar

## Backend

- [`domain/optics/models.py`](../../backend/src/terralab3d/domain/optics/models.py)
- [`domain/optics/calculations.py`](../../backend/src/terralab3d/domain/optics/calculations.py)
- [`application/use_cases/optics.py`](../../backend/src/terralab3d/application/use_cases/optics.py)
- [`domain/imaging/models.py`](../../backend/src/terralab3d/domain/imaging/models.py)
- [`domain/imaging/calculations.py`](../../backend/src/terralab3d/domain/imaging/calculations.py)
- [`application/star_coordinator.py`](../../backend/src/terralab3d/application/star_coordinator.py)
- atmosfera/contaminació lumínica del Pas 7
- traces del Pas 14

## Frontend

- [`LocationPage.ts`](../../frontend/src/view/ui/drawer_pages/LocationPage.ts)
- [`OpticsPanel.ts`](../../frontend/src/view/ui/panels/OpticsPanel.ts)
- [`ScopeLayerRenderer.ts`](../../frontend/src/view/three/layers/ScopeLayerRenderer.ts)
- [`ImagingPreviewLayerRenderer.ts`](../../frontend/src/view/three/layers/ImagingPreviewLayerRenderer.ts)
- [`StarTrailLayerRendererImpl.ts`](../../frontend/src/view/three/layers/StarTrailLayerRendererImpl.ts)
- [`CameraRigImpl.ts`](../../frontend/src/view/three/CameraRigImpl.ts)
- [`InputMapper.ts`](../../frontend/src/view/ui/InputMapper.ts)
- picking/selecció/cerca ja existents

## Oracle TerraLab

Consultar només com a referència de comportament:

- `TerraLab/widgets/telescope_scope_mode.py`
- `TerraLab/widgets/scope_ui_manager.py`
- `TerraLab/widgets/telescope_runtime.py`
- `TerraLab/widgets/visual_magnitude_engine.py`
- `TerraLab/widgets/optica_telescopica.py`
- controls Scope de `TerraLab/ui/widget_controls_builder.py`

No copiar l'arquitectura Qt/QPainter.

---

# 8. Treball pendent

## Mode i UI

- [ ] Introduir `ObservationMode = eye | camera | telescope`.
- [ ] Afegir el botó intercanviable al costat de `Caminar / Avió`.
- [ ] Afegir `EYE_SVG`, `CAMERA_SVG` i `TELESCOPE_SVG`.
- [ ] Fer `OpticsPanel` sensible al mode actiu.
- [ ] Canviar de mode sense salt de pose ni canvi del FOV visual.

## Càmera

- [ ] Implementar presets geomètrics APS-C i Full Frame.
- [ ] Implementar FOV rectangular H/V/diagonal.
- [ ] Implementar controls ISO, exposició, focal, f-number i tracking.
- [ ] Implementar `CameraProfile`.
- [ ] Crear/editar/eliminar/seleccionar càmeres personals.
- [ ] Persistir perfils amb esquema versionat.
- [ ] Calcular escala de píxel quan `pixelPitchUm` sigui disponible.
- [ ] Implementar magnitud límit estimada i aplicar-la a la previsualització estel·lar.
- [ ] Integrar atmosfera/contaminació lumínica sense duplicar càlculs.
- [ ] Llançar Gaia profunda cancel·lable quan calgui.
- [ ] Reutilitzar traces del Pas 14 quan tracking estigui desactivat.

## Telescopi

- [ ] Implementar visor circular, màscara exterior i reticle.
- [ ] Implementar focal, obertura, ocular i AFOV.
- [ ] Calcular augment, pupil·la i FOV real.
- [ ] Implementar moviment fi/ràpid, drag i hold.
- [ ] Integrar GoTo amb el cercador existent.
- [ ] Mantenir entrada manual RA/Dec.
- [ ] Implementar HUD instrumental.

## Neteja de l'antic disseny

- [ ] Eliminar qualsevol referència funcional a `binoculars`.
- [ ] Eliminar qualsevol semàntica de zoom intern del Scope.
- [ ] No implementar `Fer foto`, exportació PNG/JPEG, regla 500 o NPF com a criteri de sortida d'aquest pas.
- [ ] No exigir SNR/full-well/QE per poder utilitzar la càmera.
- [ ] No fer dependre el pas d'una base de dades pública de càmeres.

---

# 9. Errors, cancel·lació i recursos

- Paràmetres no finits, focal ≤ 0, exposició ≤ 0 o dimensions de sensor ≤ 0 són errors de validació.
- Un perfil personal corrupte no impedeix iniciar en mode ull nu.
- La consulta Gaia profunda és cancel·lable i `latest-wins`.
- Un GoTo obsolet no reorienta la càmera quan arriba tard.
- Canviar de mode invalida previews incompatibles però conserva els perfils.
- Resize i DPR no alteren el FOV científic del marc.
- Tots els materials/targets del visor tenen propietari i `dispose`.
- La simulació fotogràfica no pot degradar el pan/zoom normal amb round-trips per frame.

---

# 10. Proves

## Matemàtica

- APS-C i Full Frame contra valors de FOV de referència.
- FOV decreix quan augmenta la focal.
- escala arcsec/px correcta per fixtures coneguts.
- augment, pupil·la i FOV real de telescopi.
- magnitud límit monotònica respecte d'exposició i obertura dins del model declarat.
- ISO no s'interpreta com a flux fotònic lineal.

## UI

- cicle `eye → camera → telescope → eye`;
- icona, label, title i aria correctes;
- canvi de mode sense salt de pose;
- el zoom global funciona igual en tots tres modes;
- rectangle/cercle mantenen camp angular en canviar el zoom visual;
- persistència de càmera personal després de reinici.

## Integració

- GoTo d'estrella, planeta i objecte OpenNGC.
- GoTo manual RA/Dec.
- consulta Gaia profunda substituïda per una de nova.
- tracking on/off amb exposició llarga.
- atmosfera/Bortle afecten la profunditat fotogràfica.
- context loss, resize i DPR.

## Rendiment

- camp Gaia dens;
- canvi ràpid d'ISO/exposició;
- drag del Scope durant consulta profunda;
- cap reconstrucció completa de buffers per frame.

---

# 11. Criteri de sortida

El Pas 19 es considera complet quan:

1. existeix el botó `ull / càmera / telescopi` al costat de `Caminar / Avió`;
2. ull nu conserva exactament el comportament actual;
3. càmera mostra un rectangle físicament derivat del sensor/focal;
4. l'usuari pot crear i reutilitzar una càmera personal;
5. ISO, exposició, focal i obertura modifiquen una previsualització fotogràfica reproduïble;
6. quan existeix `pixelPitchUm`, es mostra escala angular per píxel;
7. el telescopi ofereix Scope, paràmetres, HUD i GoTo;
8. el FOV visual continua sent l'únic sistema de zoom;
9. no existeix cap mode prismàtics;
10. cap base de dades comercial és necessària;
11. l'escena continua interactiva durant GoTo i Gaia profunda;
12. les proves i evidències del pas són reproduïbles.

---

# 12. Evidències

- [ ] Captura dels tres estats del botó.
- [ ] Captura de càmera APS-C i Full Frame amb el mateix objectiu/focal.
- [ ] Perfil personal creat, reinici i reutilització.
- [ ] Taula focal/sensor → FOV.
- [ ] Taula focal/pixel pitch → arcsec/px.
- [ ] Comparativa de magnitud límit amb dues exposicions i dues obertures.
- [ ] Vídeo de GoTo a estrella, planeta i objecte de cel profund.
- [ ] Vídeo de drag/moviment fi del Scope.
- [ ] Prova que el zoom global no canvia de semàntica.
- [ ] Prova de cancel·lació Gaia `latest-wins`.
- [ ] Mètriques de frame durant una consulta profunda.

---

# 13. Fora d'abast

- mode prismàtics;
- segon motor de zoom;
- base de dades pública/comercial de càmeres;
- base de dades d'objectius;
- control de muntures ASCOM/Alpaca/INDI;
- plate solving;
- exportació RAW;
- pipeline complet de revelatge;
- HDR/autoexposure físic complet;
- calibratge fotomètric absolut;
- model obligatori de QE/read-noise/full-well;
- simulació detallada de resposta espectral del sensor.

---

# 14. Instrucció per a Codex

Replanteja els antics passos 19 i 20 com una única vertical executable. No implementis prismàtics ni cap zoom instrumental paral·lel. Mantén el `CameraRig` actual com a única autoritat de FOV visual; afegeix només el camp instrumental projectat.

Comença per l'estat `eye/camera/telescope` i el botó al costat de `Caminar / Avió`. Després implementa càmera rectangular amb perfils personals persistents i previsualització de magnitud límit. Finalment implementa el Scope de telescopi amb GoTo reutilitzant la cerca existent.

TerraLab és oracle de comportament per a Scope i fotometria bàsica, no una arquitectura a copiar.
