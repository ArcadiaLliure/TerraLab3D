# Matriz de paridad DEM: TerraLab → TerraLab3D

Estado: en ejecución. TerraLab (`E:\Desarrollo\TerraLab`) se usa sólo como
oráculo de comportamiento; no se modifica desde este repositorio.

## Hallazgo inicial

El perfil de horizonte publicado por TerraLab3D ya procede del DEM real: para
el observador de referencia se ha medido cobertura 100 %, 720 rayos y un perfil
no plano. La representación del relieve es una malla DEM residente. Cuando no
hay DEM, la ausencia se comunica visualmente con una boira transparente cuyo
borde superior está a 0°, no mediante una pared negra.

El progreso automático quedaba en 5 % porque `HorizonCoordinator` publicaba la
fase `sampling` antes del trabajo síncrono de fondo y no comunicaba el avance de
los bloques de azimut. Se corrige como parte de esta entrega.

## Extensió Vertical 2

El DEM ja no depèn d'una extensió o producte concret. `RasterioRasterReader` publica descriptors neutrals, conserva el dtype font i exposa bandes, subdatasets, màscares, escala, offset, unitats i overviews. L'adaptador d'elevació aplica NoData i màscara abans d'escala/offset i converteix a metres `float32` només a la frontera DEM.

`data_sources.json` governa ara la cadena ordenada: el DEM importat guanya dins la cobertura i les fonts anteriors resolen NoData o exterior. El canvi recarrega un port estable, cancel·la treball obsolet i invalida les caches dependents del fingerprint. La regressió `test_managed_mi_dem_asc_bundle_publishes_real_mesh_source_after_restart` demostra importació, reinici i graella de terreny real.

| Comportamiento observado en TerraLab | Implementación actual de TerraLab3D | Prueba / estado de paridad |
| --- | --- | --- |
| Raíz de datos y catálogo configurables | `data_location.json` resuelve la biblioteca; DEM en `data/earth/elevation`. Falta consumir el catálogo de superficies. | `test_horizon_step15.py::test_configured_elevation_directory_comes_from_data_root`; ampliación pendiente para `data_sources.json`. |
| Cadena DEM, CRS nativo, ventanas y nodata | `RasterioElevationAdapter` descubre conjuntamente todos los DEM de la biblioteca configurada y los agrupa por resolución real. Para cada muestra gana la banda más precisa, con independencia de que sea NPY, GeoTIFF u otro ráster; una muestra fuera de cobertura o `nodata` continúa subsidiariamente en la siguiente banda. Los datasets y ventanas de distintas fuentes comparten LRU acotadas, por lo que Catalunya y EUDEM pueden permanecer abiertos simultáneamente. Los sentinelas persistidos `-9999` y `-8888` se excluyen antes de interpolar; la frontera de malla los valida de nuevo y omite sus triángulos. | `test_dem_chain_prefers_precision_and_falls_back_after_npy_nodata`; `test_dem_chain_does_not_give_npy_priority_over_a_finer_raster`; `test_mesh_builder_never_turns_nodata_sentinels_into_cliffs`. |
| Elevación bilineal | `RasterioElevationAdapter` interpola las cuatro muestras alrededor del centro de píxel y rechaza nodata interior; replica bordes válidos sin crear una costura nodata. | `test_dem_elevation_uses_bilinear_interpolation_without_inventing_nodata`. |
| Ojo = DEM + offset + 1,7 m | El frontend/bridge entrega la altura de ojo al request científico. | `test_horizon_step15.py` y regresión geodésica pendiente. |
| Curvatura/refracción | `R=6_371_000` y, con refracción, `R_eff=7R/6`. El perfil usa la elevación aparente y la malla visual conserva X/Z ENU, mientras baja cada vértice sobre la esfera efectiva. | `test_curvature_and_refraction_match_terralab_parity`; `test_visual_dem_mesh_uses_spherical_coordinates_at_long_range`. |
| Rango auto y precarga | El radio manual solicitado por la UI se conserva exactamente de 1 a 530 km, incluido 530 km; no existe un recorte científico a 150 km. Falta la precarga de vuelo por tiles. | `test_settings_validate_without_silent_degradation`. |
| Muestreo científico y ocho nodata | Rayos 0,005°–5°, por defecto 0,25°, límite de muestras y corte tras ocho ausencias están implementados; el refinado adaptativo exacto aún no. | `test_angular_precision…`, `test_eight_consecutive…`; ampliación pendiente. |
| Perfil y oclusión celeste | Perfil binario versionado e interpolación angular para cuerpos/estrellas. La ausencia global de autoridad DEM se expresa como boira visual transparente a 0°; un perfil DEM real o parcial nunca dispara una cortina de boira a pantalla completa. | `horizon_step15.test.ts`; comprobación visual del perfil DEM real. |
| Parche ENU 160×160 m + malla polar v3 | `TerrainMeshBuilder` produce el parche simétrico de −80 a +80 m y la malla polar solapada; se publica como buffer binario Three.js con `X=E,Y=Up,Z=−N`. | `dem_terrain_layer.test.ts`; smoke real de 1 km y 150 km. |
| Anillos LOD, normales y triángulos válidos | Zonas 40 m–5/25/100/250 km–radio final, topes 150/100/75/45/25; triángulos sólo cuando los cuatro vértices DEM son válidos y costura angular explícita. | Pruebas de renderer y smoke real; fixtures de cresta/nadir cuantitativos pendientes. |
| Navegación y coordenadas del observador | La cámara de vuelo colisiona contra los atributos de posición/normal de la misma malla DEM residente, con consulta directa de parche/anillos y sin raycast por triángulo en cada frame; sondea el recorrido a intervalos de 4 m y no permite atravesarla ni continuar fuera de cobertura. Un borde de boira de espacio mundo se construye desde esos mismos índices válidos, por lo que señala exactamente el límite que detiene la navegación y su borde superior sigue la altura de 0° del observador. El menú contextual de una intersección DEM transforma el punto ENU al mismo WGS84 azimutal-equidistante del ancla de malla y ordena un vuelo Goto continuo con velocidad adaptada a la distancia 3D para llegar en 10 s; conserva el mismo barrido de colisión y no se cancela al girar la cámara. Sólo `Esc` lo cancela explícitamente; un nuevo Goto sustituye el destino. El límite manual de 250 m/s no cambia. «Reubicar» aplica la misma proyección inversa: si el destino está en el DEM residente inicia ese vuelo sin invalidar ni recargar la malla; si no hay malla residente, conserva la reubicación completa existente. Los campos de Ubicación son configuración explícita del usuario y no reciben las coordenadas GPS vivas; éstas pertenecen exclusivamente al HUD. Al volver a persona conserva Este/Norte y aterriza en el DEM de esa posición. El HUD recibe inmediatamente el GPS derivado del ENU antes de esperar la consulta de elevación DEM. Aterrizar o detenerse no programa un perfil ni una malla. | `navigation.test.ts`; `terrain_goto.test.ts`; `dem_terrain_layer.test.ts`; `test_predictive_flight_refresh_never_starts_when_stationary`. |
| Superficie RGB/categórica independiente del DEM | Desactivada explícitamente en la ruta visible: `TerrainMeshBuilder` usa sólo las elevaciones del DEM y su material de relieve local. No abre ni mezcla `data_sources.json`, CLCPlus u ortofotos; `class ID` y `source ID` se publican vacíos. El adaptador de superficies queda aislado y probado, pero no integrado hasta que se active una capa superficial. | Prueba de malla DEM exclusiva en `test_horizon_step15.py`; `test_terrain_surface_step16.py` cubre el adaptador aislado, no el render activo. |
| Paletas Original/Vibrant, luz, atmósfera, eclipse | Paleta Original de fallback y material Three.js con las luces astronómicas persistentes. La paridad de Vibrant, bruma métrica y sombras de cresta aún es pendiente. | Pendiente de goldens GPU. |
| Invalidación y streaming visual | Horizonte: por observador, DEM y ajustes; luz/cámara no invalidan el perfil. La malla Three.js amplia permanece residente en VRAM. El primer bake completo tiene propiedad exclusiva hasta publicar la malla; un perfil predictivo de vuelo no puede cancelarlo. Después, chunks DEM detallados de 25 km se preparan en segundo plano cuando la distancia al borde preciso es menor que el margen calculado con la velocidad ENU y P50/P95 de preparación. Cada chunk publicado se añade a la escena persistente sin destruir el anterior; render y colisión consultan todos los retenidos, del más nuevo al más antiguo, y finalmente la malla amplia. La caché GPU es LRU acotada por defecto a 12 chunks y 256 MiB, con sesgo de profundidad independiente para evitar z-fighting en los solapes. Si el vuelo conserva una dirección compatible, el worker termina su barrido aunque se alcance el límite detallado; sólo se cancela por un giro mayor de 60° que vuelve inútil el destino del chunk. Al detenerse no se inicia trabajo. | `test_full_terrain_request_marks_the_resident_world_mesh_ready`; `test_visual_stream_keeps_a_useful_sweep_and_cancels_only_after_route_divergence`; `dem_terrain_layer.test.ts`; `test_streamed_dem_chunk_keeps_its_global_enu_center_and_binary_contract`. |

## Referencias inspeccionadas

- `TerraLab/terrain/README.md`: separación estricta DEM/geometría y
  superficie/apariencia, topología v3, paletas, caches y estados.
- `docs/terrain_render_pipeline_analysis.md` y
  `docs/terrain_render_delivery.md`: arrays de malla, orden
  color → Lambert → atmósfera, invalidación y medidas de referencia.
- `docs/architecture/terrain_visibility_range.md`: radio automático, límites,
  refracción y precarga.
- `terrain/raycast/baker.py`, `sampling.py`, `domain/curvature.py`,
  `data/visibility_range.py`, `mesh/normals.py` y `persistence/profile_npz.py`:
  fórmulas y contratos de la malla v3.

Las pruebas de referencia indicadas por la petición se usarán como especificación
de fixtures, no como valores recalculados por la misma implementación que se
prueba.

## Medición con el DEM configurado

Escena: `41.21240330896238, 0.8072721734579367`, radio manual 150 km,
paso 0,5°, DEM del catálogo configurado. Tras la interpolación bilineal:

| Métrica | Resultado |
| --- | ---: |
| Cobertura perfil DEM | 100 % |
| Rayos científicos | 720 |
| Tiempo de horneado de horizonte | 20,436 s |
| Tiempo total, incluida malla | 33,243 s |
| Vértices malla | 268.209 |
| Índices / triángulos | 1.604.184 / 534.728 |
| Transferencia de malla | 14.999.424 B |
| Pico RSS proceso | 379.854.848 B |

El progreso publicado se midió entre 5–85 % para los rayos y 86–94 % para la
malla. El restante corresponde a publicación/activación de los buffers.

## Diferencias aún conocidas

- Falta portar el refinamiento adaptativo completo, el objetivo automático de
  8.849 m y la precarga separada de 25 km.
- Las categorías todavía no tienen reducción modal LOD ni picking de escena;
  los atributos semánticos ya están en GPU, sin interpolarse.
- Falta portar literalmente Vibrant, la atmósfera métrica por shader, oclusión
  solar detrás de crestas, pérdidas de contexto y goldens comparativos.
- La navegación usa las mallas DEM visibles como colisionador cuando están listas;
  el parche técnico sólo permanece como fallback de inicio. El streaming conserva
  varios chunks detallados concurrentes, aunque aún no usa una cuadrícula fija de
  clipmap multiresolución.
