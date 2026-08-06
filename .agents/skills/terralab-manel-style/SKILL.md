---
name: terralab-manel-style
description: Diseña, implementa, amplía o revisa TerraLab3D siguiendo una síntesis explícita entre la arquitectura científico-gráfica del proyecto y la forma de programar de Manel: capacidades funcionales verticales, responsabilidades claras, contratos en fronteras reales, orquestadores legibles, cálculo desacoplado, escena persistente, workers coordinados y render GPU incremental. Aplícalo también a componentes auxiliares en Python, TypeScript, Java u otros lenguajes cuando formen parte de TerraLab3D.
---

# TerraLab Manel Style

## Objetivo

Guiar el desarrollo de **TerraLab3D** mediante una combinación deliberada de su arquitectura objetivo y la forma de tomar decisiones observada en el código de Manel. No es un perfil general y neutro de Manel: es su estilo ya adaptado a las necesidades científicas, gráficas y de rendimiento de TerraLab3D.

La prioridad es que el resultado parezca construido por Manel específicamente para TerraLab3D. Por tanto:

- piensa primero en la función que debe existir;
- separa responsabilidades con nombres explícitos;
- deja visible el recorrido completo del caso de uso;
- encapsula integraciones, persistencia y utilidades;
- prefiere código directo y rastreable antes que abstracciones ornamentales;
- refactoriza y endurece el sistema después de conseguir una capacidad funcional verificable.

## Regla principal

**La arquitectura de TerraLab3D fija las fronteras y las restricciones de rendimiento; el estilo de Manel fija cómo se expresan, organizan e implementan las capacidades.**

Preserva la intención arquitectónica y moderniza la mecánica del lenguaje y del framework.

No reproduzcas automáticamente prácticas heredadas como inyección por campos, excepciones excesivamente amplias, clases generadas, constantes gigantes o ausencia de pruebas.

## Proceso obligatorio antes de escribir código

1. Identifica la **capacidad funcional concreta** que se incorpora.
2. Define su punto de entrada y su resultado observable.
3. Decide qué responsabilidad corresponde a cada capa o componente.
4. Localiza las fronteras reales: sistema externo, persistencia, render, filesystem, red, criptografía, reloj u otra infraestructura.
5. Crea contratos únicamente para esas fronteras o cuando exista una sustitución razonable.
6. Implementa un recorrido principal claro y secuencial.
7. Añade traducción de errores, trazabilidad y limpieza de recursos.
8. Comprueba que el cambio constituye un entregable funcional independiente.

## Huella arquitectónica

### 1. Organizar por responsabilidad y capacidad

Agrupa el código por lo que hace dentro del sistema, no por categorías genéricas sin significado.

Patrón preferente:

- entrada o adaptador: recibe la petición, comando o evento;
- aplicación/orquestación: coordina el caso de uso;
- servicios de capacidad: realizan transformaciones o reglas cohesionadas;
- integración: encapsula servicios externos;
- datos/repositorios: encapsulan persistencia;
- modelo/DTO: representan información del dominio o del contrato;
- configuración: construye dependencias y clientes;
- utilidades: solo operaciones puras o transversales realmente reutilizables.

Evita una carpeta `utils` usada como vertedero.

### 2. Contrato e implementación solo donde aporten una frontera

Manel tiende a hacer explícita la separación entre interfaz e implementación. Conserva esa intención en:

- servicios de aplicación que puedan sustituirse;
- integraciones externas;
- repositorios;
- motores de cálculo o render;
- proveedores de filesystem, reloj, red o configuración.

No crees una interfaz por cada clase. Si solo existe una implementación trivial, no hay sustitución prevista y no se protege ninguna frontera, usa una clase directa.

Convenciones orientativas:

- Java: `XService` + `XServiceImpl`, `XRepository`, `XClient` o `XAdapter`.
- Python: `Protocol` o `ABC` + implementación concreta con nombre funcional.
- TypeScript: `XService`/`XPort` + `XAdapter` o implementación concreta.

### 3. Orquestadores legibles y lineales

El método de aplicación puede mostrar el flujo completo del caso de uso. Prefiere una secuencia fácil de seguir:

1. validar y obtener configuración;
2. registrar inicio;
3. obtener entradas;
4. ejecutar transformaciones;
5. persistir o publicar;
6. construir respuesta;
7. registrar finalización;
8. traducir errores y limpiar recursos.

Extrae detalles técnicos a métodos privados o servicios, pero no pulverices el flujo en llamadas minúsculas que oculten la historia funcional.

Usa comentarios de etapa cuando ayuden a leer un proceso largo. Los comentarios explican **qué fase funcional ocurre**, no repiten la sintaxis.

### 4. Servicios con responsabilidad reconocible

Los servicios deben corresponder a capacidades nombrables: gestionar ficheros, generar metadatos, transformar documentos, verificar firmas, registrar trazabilidad, calcular efemérides, proyectar coordenadas o cargar estrellas.

Un servicio puede contener varios métodos si todos pertenecen a la misma capacidad. Evita tanto la clase monolítica como el microservicio de una sola línea.

### 5. Vocabulario de dominio visible

Usa nombres concretos, verbales y cercanos al lenguaje del problema.

Preferencias:

- métodos: verbo + objeto o resultado (`obtenerDocumento`, `generarMetadatos`, `verificarFirma`, `registrarTraza`);
- clases: responsabilidad explícita (`FitxersService`, `SignParserService`, `TracabilitatService`);
- booleanos: preguntas o estados (`is...`, `has...`, `...Enabled`, `...Active`);
- evitar `Manager`, `Helper`, `Processor` o `Data` cuando exista un nombre de dominio más preciso.

Respeta el idioma dominante del proyecto. No traduzcas conceptos del dominio de forma inconsistente.

### 6. Integraciones aisladas

Toda comunicación con sistemas externos debe quedar detrás de un componente específico. La capa de aplicación no debe conocer detalles de SOAP, HTTP, SQL, SFTP, Three.js, OpenGL, proveedores cloud o formatos concretos salvo los DTO necesarios.

La configuración del cliente, timeouts, certificados, endpoints, proxy y autenticación pertenece a infraestructura/configuración.

### 7. Configuración externa y explícita

No incrustes valores de entorno en el código. Agrupa configuración por subsistema y usa nombres jerárquicos o estructuras tipadas.

La lógica debe recibir configuración validada. Los valores por defecto solo se usan cuando su significado funcional esté claro.

### 8. Errores de negocio normalizados

Traduce errores técnicos a una excepción o resultado de aplicación con:

- código estable;
- mensaje contextual;
- causa original;
- datos necesarios para trazabilidad.

Captura excepciones en la capa capaz de añadir contexto o decidir la respuesta. No captures para ignorar.

No uses `catch Exception` o equivalente salvo en la frontera superior, donde debe registrarse, traducirse y cerrarse correctamente el flujo.

### 9. Trazabilidad integrada en el caso de uso

Registra los puntos importantes del proceso, especialmente inicio, transformación, persistencia, error y finalización.

Los logs deben incluir contexto funcional: identificador de petición, operación, recurso o etapa. No registrar secretos, credenciales, documentos completos ni datos personales innecesarios.

La trazabilidad es parte de la responsabilidad del sistema, no un añadido posterior.

### 10. Pragmatismo antes que pureza

El diseño debe ser entendible por un desarrollador que abre el proyecto sin conocerlo.

Prefiere:

- flujo directo;
- clases con nombres explícitos;
- dependencias visibles;
- métodos auxiliares con una razón funcional;
- patrones solo cuando resuelven una necesidad concreta.

Evita:

- arquitectura ceremonial;
- factories o builders sin necesidad;
- capas espejo que solo reenvían llamadas;
- abstracciones especulativas;
- fragmentación extrema para alcanzar métricas artificiales.

## Perfiles de aplicación y reglas de precedencia

Este skill contiene una huella general y puede contener perfiles explícitos para proyectos concretos.

Orden de precedencia:

1. requisitos funcionales y restricciones expresas del proyecto;
2. fronteras arquitectónicas irreversibles definidas por el perfil del proyecto;
3. reglas generales del estilo de Manel;
4. convenciones idiomáticas del lenguaje y del framework;
5. preferencias locales de implementación.

Un perfil específico no sustituye la huella general. La concreta donde el dominio exige decisiones que no pueden inferirse de los proyectos históricos.

## Núcleo científico-gráfico de TerraLab3D

Estas reglas se aplican siempre al trabajar con TerraLab3D. Consulta `references/terralab3d-profile.md` antes de diseñar o modificar cualquier capacidad científica, de simulación o de renderizado.

### 1. Capacidad funcional como corte vertical

Cada hito debe añadir una función observable de extremo a extremo, por ejemplo:

- proyectar una estrella desde coordenadas ecuatoriales;
- cargar y mostrar un catálogo estelar;
- cambiar el observador y actualizar el cielo;
- activar una capa de constelaciones;
- calcular y representar un perfil de terreno.

El hito puede tocar varias capas, pero solo implementará las piezas necesarias para demostrar esa capacidad. No se consideran hitos autónomos «crear carpetas», «añadir interfaces» o «configurar Three.js» si todavía no producen comportamiento verificable.

### 2. Fronteras obligatorias desde el primer hito

Aunque el estilo general permita refactorizar después de hacer funcionar una capacidad, en este perfil deben respetarse desde el inicio estas separaciones:

- dominio y cálculo científico independientes de Three.js, WebGL y la UI;
- estado de simulación separado del estado y los recursos de render;
- escena persistente en lugar de reconstrucción completa por frame;
- trabajo científico o de preparación pesada fuera del bucle de render;
- ciclo de vida y propietario explícito para geometrías, materiales, texturas, buffers, workers y suscripciones;
- contratos de coordenadas, unidades, precisión y marcos de referencia explícitos.

No se permite introducir una dependencia «provisional» de Three.js en cálculo o dominio con la intención de extraerla más adelante.

### 3. Flujo arquitectónico preferente

```text
Entrada o comando
    ↓
Caso de uso / orquestador
    ↓
Dominio y motores de cálculo
    ↓
Snapshot, DTO o delta de escena
    ↓
Gestor de estado de escena
    ↓
Adaptador de render
    ↓
Recursos persistentes de GPU
```

El adaptador gráfico traduce datos preparados a Three.js. No decide reglas astronómicas, geográficas ni científicas.

### 4. Bucle de render mínimo

El `requestAnimationFrame` o equivalente solo puede:

1. leer estado ya preparado;
2. aplicar deltas pendientes y cambios de cámara;
3. actualizar animaciones estrictamente visuales;
4. renderizar;
5. recopilar métricas ligeras cuando proceda.

No debe cargar catálogos, ejecutar efemérides pesadas, consultar persistencia, reconstruir toda la escena, publicar procesos de negocio ni registrar una traza por elemento o frame.

### 5. Escena persistente y actualización incremental

La escena se construye una vez por subsistema y se actualiza por cambios explícitos. Prefiere:

- dirty flags o invalidación por dependencia;
- deltas de escena;
- snapshots versionados;
- actualización parcial de `BufferGeometry` y atributos;
- reutilización de materiales, texturas y buffers;
- doble buffer solo cuando resuelva una necesidad medida;
- eliminación explícita de recursos abandonados.

Reconstruir una geometría completa es aceptable únicamente cuando el volumen sea pequeño, la frecuencia baja y la decisión esté justificada o medida.

### 6. Cálculo científico independiente y reproducible

Los motores científicos deben:

- recibir entradas tipadas y explícitas;
- declarar unidades y sistema de coordenadas;
- evitar depender del reloj global, UI o estado mutable del render;
- producir resultados deterministas para las mismas entradas, salvo aleatoriedad explícita y controlada;
- separar cálculo exacto, aproximación y optimización;
- documentar tolerancias y dominio de validez;
- permitir ejecución síncrona en pruebas aunque en producción se deleguen a workers.

No mezclar en una misma función cálculo científico, conversión a buffers GPU y mutación de objetos Three.js.

### 7. Workers, cancelación y resultados obsoletos

Toda tarea pesada debe modelarse como una operación identificable y cancelable cuando sea razonable.

Cada resultado asíncrono debe incluir la versión, revisión o identificador de la solicitud que lo originó. Antes de aplicarlo:

- comprobar que sigue siendo vigente;
- descartar resultados obsoletos sin tratarlos como fallos;
- liberar transferibles o recursos asociados;
- registrar duración y tamaño de forma agregada;
- conservar la causa si el worker falla.

No permitir que una respuesta tardía sobrescriba un estado de escena más reciente.

### 8. Comandos, eventos y DTO con semántica real

Usa comandos para expresar intención (`SetObserverLocation`, `LoadStarCatalog`) y eventos para hechos ya ocurridos (`ObserverLocationChanged`, `StarCatalogLoaded`).

Crea DTO, snapshots o deltas cuando crucen una frontera entre cálculo, worker, persistencia, UI o render. No dupliques modelos solo para satisfacer una plantilla de capas.

Los objetos de Three.js, manejadores de worker y recursos GPU no deben aparecer en modelos de dominio ni DTO científicos.

### 9. Propiedad y ciclo de vida de recursos

Cada recurso de larga duración debe tener un propietario claro responsable de:

- creación;
- actualización;
- sustitución;
- desconexión de listeners;
- cancelación de tareas;
- `dispose` o liberación equivalente;
- recuperación o degradación ante pérdida del contexto gráfico.

Una capacidad no está terminada si crea recursos que no sabe destruir.

### 10. Errores y estados no excepcionales

Distingue al menos:

- error de validación;
- error de datos científicos;
- error de cálculo o proyección;
- error de carga o persistencia;
- error de worker;
- error de recurso gráfico;
- capacidad gráfica no disponible;
- pérdida de contexto WebGL;
- operación cancelada;
- resultado obsoleto descartado.

Cancelación y obsolescencia suelen ser estados esperados, no errores que deban ensuciar la traza como fallos.

### 11. Observabilidad agregada

Registra cambios funcionales y métricas de subsistema, no cada estrella, vértice o frame.

Métricas útiles:

- elementos cargados o proyectados;
- duración del cálculo;
- duración y cola de workers;
- actualizaciones y bytes enviados a GPU;
- invalidaciones de escena;
- memoria aproximada y recursos activos;
- frames lentos y pérdida de contexto.

La instrumentación no debe alterar perceptiblemente el rendimiento ni invadir la lógica científica.

### 12. Pruebas mínimas por hito

Cada capacidad científico-gráfica debe incluir, según corresponda:

- prueba del cálculo con entradas conocidas;
- prueba de unidades, coordenadas y tolerancias;
- prueba del caso de uso sin Three.js real;
- prueba de traducción de snapshot o delta al adaptador de render;
- prueba de descarte de resultados obsoletos;
- prueba de liberación de recursos;
- demostración visual o prueba de integración del resultado observable.

La prueba visual no sustituye la prueba numérica, y la prueba numérica no sustituye la integración del render.

## Forma de desarrollar cambios

Cada hito debe corresponder a **una capacidad nueva observable y verificable**. No uses hitos basados únicamente en tareas internas como “crear carpetas” o “configurar dependencias”, salvo que sean requisito de una función ejecutable.

Secuencia preferente:

1. capacidad mínima funcional;
2. separación de responsabilidades que ya hayan aparecido;
3. endurecimiento de errores y recursos;
4. trazabilidad y observabilidad;
5. limpieza estática y simplificación;
6. documentación útil.

No asignes plazos salvo que el usuario los solicite.

## Adaptación por lenguaje

Consulta `references/cross-language-mapping.md` antes de aplicar el estilo fuera de Java.

Principios generales:

- usa los mecanismos idiomáticos del lenguaje;
- conserva responsabilidades, nombres y fronteras;
- no traduzcas literalmente patrones Spring a otro ecosistema;
- prefiere composición e inyección explícita;
- usa tipos y DTO cuando aclaren contratos;
- mantén el recorrido principal del caso de uso visible.

## Criterio para código nuevo

Antes de finalizar, verifica:

- ¿La nueva función se puede nombrar y demostrar?
- ¿El punto de entrada coordina en lugar de ejecutar detalles de infraestructura?
- ¿Cada servicio tiene una responsabilidad reconocible?
- ¿Las integraciones y la persistencia están aisladas?
- ¿Los nombres pertenecen al dominio?
- ¿Los errores conservan causa y contexto?
- ¿El flujo principal se entiende de arriba abajo?
- ¿La solución evita abstracciones que todavía no necesita?
- ¿La mecánica es moderna e idiomática para el lenguaje usado?

Usa `references/review-checklist.md` para revisiones formales.

## Límites de inferencia

El código analizado aporta evidencia fuerte sobre arquitectura, nomenclatura, orquestación, configuración, errores y trazabilidad. No aporta evidencia suficiente para asumir preferencias definitivas sobre:

- estrategia de pruebas;
- programación funcional;
- concurrencia y asincronía;
- arquitectura distribuida moderna;
- estilo de frontend;
- rendimiento científico o gráfico.

En esas materias, aplica buenas prácticas actuales sin presentarlas como preferencias históricas de Manel. Las reglas de concurrencia, cálculo científico y gráficos de TerraLab3D son decisiones explícitas y nucleares del proyecto, no inferencias extraídas del código Spring analizado.
