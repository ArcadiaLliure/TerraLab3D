# Núcleo arquitectónico de TerraLab3D

## Finalidad

Este documento forma parte del núcleo de `terralab-manel-style`. Fusiona la huella de programación de Manel con las restricciones arquitectónicas de TerraLab3D, sin trasladar literalmente una aplicación Spring a TypeScript, Python o Three.js.

La regla central es:

> La arquitectura de TerraLab3D fija las fronteras; el estilo de Manel determina cómo se implementan las capacidades dentro de ellas.

## Compatibilidad con la huella general

Coincidencias directas:

- desarrollo mediante capacidades funcionales completas;
- recorrido principal legible de arriba abajo;
- contratos en fronteras reales;
- nombres del dominio;
- integraciones aisladas;
- configuración explícita;
- errores contextualizados;
- refactorización pragmática sin abstracción ornamental.

Restricciones adicionales del proyecto:

- escena Three.js persistente;
- actualización incremental;
- cálculo científico independiente del render;
- workers para tareas pesadas;
- resultados asíncronos versionados;
- ciclo de vida explícito de recursos GPU;
- unidades y sistemas de coordenadas explícitos.

## Capas y responsabilidades

### Dominio científico

Contiene conceptos, reglas y value objects:

- coordenadas celestes y geográficas;
- instante y localización del observador;
- estrella, cuerpo celeste, constelación;
- perfiles, visibilidad, elevación y distancias;
- magnitudes, unidades y tolerancias.

No conoce Three.js, DOM, WebGL, filesystem, red ni workers.

### Aplicación

Contiene casos de uso y orquestadores:

- carga de catálogos;
- cambio de observador o instante;
- construcción de una escena celeste;
- activación de capas;
- ejecución y cancelación de cálculos;
- publicación de snapshots o deltas.

Coordina; no implementa algoritmos gráficos ni detalles de infraestructura.

### Cálculo

Implementa proyecciones, efemérides, geometría, muestreo y demás algoritmos científicos.

Puede ofrecer implementaciones alternativas, por ejemplo exacta, aproximada, CPU, worker o futura aceleración. La interfaz se define por entradas y resultados científicos, no por el backend tecnológico.

### Estado de escena

Mantiene el estado lógico que el render necesita:

- capas activas;
- revisiones de datos;
- snapshots vigentes;
- deltas pendientes;
- estado de cámara serializable;
- invalidaciones.

No posee necesariamente los recursos Three.js. Es posible reconstruir el render a partir de este estado.

### Adaptador de render

Traduce snapshots y deltas a:

- `Object3D`;
- `Points`;
- `BufferGeometry`;
- materiales;
- texturas;
- atributos GPU.

Gestiona actualización incremental y delega el ciclo de vida a propietarios explícitos por subsistema.

### Infraestructura

Incluye catálogos, persistencia, filesystem, red, caché, loaders y configuración. Traduce errores de librerías a errores propios.

### Workers

Ejecutan tareas pesadas mediante mensajes y DTO serializables. No reciben objetos Three.js ni dependencias de UI.

## Patrón de una capacidad

Ejemplo: **mostrar una estrella desde coordenadas ecuatoriales**.

1. El comando recibe estrella, instante y observador.
2. El caso de uso valida unidades y entradas.
3. El motor calcula o transforma la posición.
4. El proyector produce una posición en la esfera celeste.
5. Se construye un `ProjectedStarDto` o delta de escena.
6. El estado de escena aumenta su revisión.
7. El adaptador actualiza el buffer estelar persistente.
8. El render loop dibuja la escena ya preparada.

La función está terminada cuando puede demostrarse y probarse sin mezclar el cálculo con Three.js.

## Regla de invalidación

Cada dato derivado debe declarar de qué depende. Ejemplo:

| Resultado | Se invalida cuando cambia |
|---|---|
| proyección estelar | catálogo, instante, observador, modelo de precesión/proyección |
| brillo aparente | catálogo, atmósfera, contaminación lumínica, configuración visual |
| geometría de terreno | DEM, extensión, resolución, algoritmo de muestreo |
| color de terreno | capa categórica/ortofoto, paleta, configuración de mezcla |
| posición de cámara | interacción o comando de cámara |

No recalcular un subsistema porque «se ha renderizado otro frame».

## Contratos recomendados

Contratos razonables:

- `StarCatalog`;
- `CelestialProjector`;
- `EphemerisEngine`;
- `TerrainDataSource`;
- `SceneRenderer`;
- `SceneStateStore`;
- `WorkerExecutor`;
- `Clock`;
- `AssetLoader`.

Contratos probablemente ceremoniales salvo variabilidad real:

- `NormalizeMagnitudeService` con una única función pura;
- `VectorConverterServiceImpl` sin frontera ni alternativa;
- interfaces espejo para cada clase de aplicación.

## Reglas de rendimiento

1. Medir antes de introducir complejidad difícil de mantener.
2. Diseñar para actualizaciones por lotes y buffers contiguos.
3. Evitar asignaciones por elemento en recorridos masivos cuando sean relevantes.
4. Preferir arrays tipados y transferibles en fronteras con workers.
5. Evitar sincronización CPU↔GPU innecesaria.
6. Separar frecuencia de simulación, frecuencia de actualización de datos y frecuencia de render.
7. Degradar calidad de forma explícita y configurable, no mediante resultados científicos silenciosamente incorrectos.

## Reglas de revisión

Una revisión de TerraLab3D debe responder:

- ¿Qué capacidad funcional añade?
- ¿Qué estado cambia y qué subsistemas invalida?
- ¿Se ejecuta algún cálculo pesado por frame?
- ¿Se reconstruyen recursos que podrían persistir?
- ¿El dominio importa Three.js o infraestructura?
- ¿Los mensajes de worker tienen versión y pueden quedar obsoletos?
- ¿Quién destruye cada recurso creado?
- ¿Las unidades y marcos de coordenadas son inequívocos?
- ¿Existe una prueba científica y una demostración visual?

## Antipatrones específicos

- render tonto alimentado frame a frame con todos los cálculos;
- cálculo científico dentro de componentes o clases de Three.js;
- reconstrucción completa de escena ante cualquier cambio;
- modelos de dominio que contienen `Vector3`, `Mesh` o `BufferGeometry`;
- un worker que responde sin correlación con la solicitud vigente;
- eventos emitidos por cada elemento de un catálogo masivo;
- logging por frame;
- recursos GPU sin propietario ni `dispose`;
- optimizaciones que cambian el significado científico sin documentarlo.
