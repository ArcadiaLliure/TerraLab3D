# Arquitectura d'integració a TerraLab3D

## 1. Mapa del codi real

El backend ja segueix domini/aplicació/infraestructura/scene. Existeixen `domain/light_pollution`, `domain/atmosphere`, `domain/horizon`, `domain/terrain`, `application/horizon_coordinator.py`, `application/terrain_mesh_builder.py`, adaptadors DEM/cache/workers/weather i bridge WebSocket. El frontend ja té `AtmosphereRenderer.ts`, `skyShader.ts`, contractes de `SkyEnvironmentSnapshot`, `ScienceBridge`/`WebSocketBridge`, `ThreeSceneHostImpl`, `RenderLoopImpl` i renderers retinguts. El nou sistema s'ha d'integrar aquí; no s'ha de crear un runtime paral·lel.

## 2. Classificació REUSE/ADAPT/REWRITE/NEW

- REUSE: coordenades, observador, DEM/horizon, bridge, workers, lifecycle, resource registry, escena persistent.
- ADAPT: `domain/light_pollution` com a namespace de domini; `SkyEnvironmentSnapshot`; scheduler d'actualitzacions; infraestructura cache.
- REWRITE progressiu: l'ús de Bortle com a font de `u_artificialBrightness` al shader.
- NEW: model VIIRS, `EmissionRegion`, `RadiancePatch`, espectre, òptica atmosfèrica, kernel, cache física, `DomeProfile`, benchmark/reference solver.
- DISCARD només al final de migració: glow Bortle artístic com a autoritat física. Es pot conservar temporalment com a fallback explícit.

## 3. Components proposats

~~~mermaid
flowchart LR
  V[VIIRS/VNL/Black Marble] --> A[adaptador light_pollution]
  A --> S[SourceModelBuilder]
  S --> ER[EmissionRegion + RadiancePatch]
  MET[Atmosfera estàndard / ERA5 / CAMS] --> AP[AtmosphericOpticsProvider]
  AP --> OF[OpticalField tiled]
  DEM[DEM + horizon] --> K[PropagationKernel]
  ER --> K
  OF --> K
  OBS[Observer] --> K
  K --> PR[PropagationResult]
  PR --> DP[DomeProfile compressor]
  DP --> BR[Bridge DTO versionat]
  BR --> RT[SkyglowRuntime TS]
  RT --> GPU[Three.js DomeSkyglowRenderer]
~~~

## 4. Fronteres de responsabilitat

Python és autoritatiu per ciència, ingestió de dades, segmentació, radiometria, òptica, propagació, incertesa i decisions de cache científica. TypeScript és autoritatiu per scheduling de presentació, recepció de revisions, doble buffer, interpolació PCHIP si es decideix enviar mostres en lloc de LUT final, estat de renderer i observabilitat de frontend. GLSL només avalua la representació ja resolta; no calcula transferència radiativa.

## 5. Lifecycle

~~~mermaid
sequenceDiagram
  participant UI
  participant TS as SkyglowRuntime
  participant B as ScienceBridge
  participant PY as SkyglowCoordinator
  participant K as PropagationKernel
  participant R as Renderer
  UI->>TS: observer/time/layer change
  TS->>B: request revision N
  B->>PY: command correlated N
  PY->>PY: topology + cache guards
  alt cache valid
    PY-->>B: cached PropagationResult N
  else recompute
    PY->>K: evaluate directions
    K-->>PY: radiance + deps + uncertainty
    PY-->>B: DomeProfile revision N
  end
  B-->>TS: result N
  TS->>TS: discard if stale
  TS->>R: upload inactive buffer
  R->>R: atomic swap next frame
~~~

## 6. Cache lifecycle

~~~mermaid
flowchart TD
  Q[Request] --> O{occlusion topology changed?}
  O -- yes --> I[INVALID]
  O -- no --> T{quadtree/domain topology changed?}
  T -- yes --> I
  T -- no --> G{inside geometric validity envelope?}
  G -- no --> I
  G -- yes --> D[estimate ΔB geometry + atmosphere]
  D --> E{error budget exceeded?}
  E -- yes --> I
  E -- no --> H[HIT + optional first-order correction]
~~~

## 7. Actualització atmosfèrica

~~~mermaid
sequenceDiagram
  participant P as Provider
  participant F as OpticalField
  participant C as Cache
  participant K as Kernel
  P->>F: publish tile version + per-field provenance
  F->>C: changed tile IDs
  C->>C: intersect dependency sets
  C->>C: discontinuity/uncertainty guard
  C->>K: recompute only affected entries
~~~

## 8. Render frontend

~~~mermaid
flowchart LR
  DTO[DomeProfile DTO] --> V[validate version/units]
  V --> P[PCHIP/log reconstruction or sampled texture]
  P --> DB[Double buffer]
  DB --> SH[skyglow shader]
  SH --> SUM[linear-radiance sum]
  SUM --> EXP[exposure/tone mapping]
  EXP --> PIX[pixel]
~~~

## 9. Terreny i curvatura

El kernel ha de reutilitzar l'autoritat geodèsica/DEM existent, però no assumir que el perfil d'horitzó 2D és suficient per a tots els raigs font→node. `domain/horizon` és útil per observer→sky i visibilitat local; els trajectes source→P poden requerir consultes DEM/geodèsiques pròpies amb la mateixa convenció d'el·lipsoide i elevació. Cal una ADR específica si s'introdueix una acceleració de visibilitat.

## 10. Workers

Els càlculs llargs han d'usar el patró existent de correlació, cancel·lació cooperativa i descart de revisions obsoletes. No s'envien rasters, malles ni `OpticalField` complet pel bridge. El bridge publica resultats compactes i deltes.

## 11. Persistència

RSR, LUT de gas, biblioteques SPD/aerosol/núvol i productes VIIRS són recursos versionats gestionats. Han de seguir el model del Pas 24 quan aquest estigui disponible: checksum, origen, llicència, instal·lació atòmica i estat de disponibilitat. Fins aleshores, el benchmark pot usar fixtures petites versionades amb llicència compatible.

## 12. Compatibilitat

Els controls Bortle/magnitud existents es mantenen durant shadow mode. El nou resultat físic s'afegeix com a font `physical_model`; la UI ha de distingir `manual`, `legacy_dataset`, `physical_model` i `unavailable`. No es canvia silenciosament la semàntica d'un camp existent.