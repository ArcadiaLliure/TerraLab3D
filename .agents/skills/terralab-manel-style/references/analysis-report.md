# Informe de análisis del estilo de programación de Manel

## Alcance

Se analizaron dos ZIP entregados por Manel:

1. ECOPIA, con varios módulos Spring Boot y librerías de cliente.
2. PICA NTBroker, servicio Spring Boot orientado a integración SOAP.

El objetivo no fue auditar la corrección funcional ni la seguridad del producto, sino extraer decisiones repetidas de arquitectura, responsabilidades, nomenclatura y forma de evolucionar el código.

## Depuración de la muestra

Se excluyeron de la inferencia principal:

- clases JAXB y WSDL generadas;
- clientes Swagger generados;
- entidades creadas automáticamente por Hibernate Tools cuando no aportaban una decisión manual clara;
- documentación HTML generada;
- binarios, certificados, artefactos de compilación y metadatos Git;
- valores concretos de configuración, credenciales, endpoints y datos internos.

Cuando el historial Git estaba disponible, se ponderaron especialmente los archivos y líneas atribuidos al autor del proyecto.

## Muestra útil

Sobre el subconjunto manual principal se identificaron aproximadamente:

- 64 archivos de aplicación analizados en detalle;
- 41 clases y 23 interfaces;
- 7 pares claros `Service` / `ServiceImpl` en el núcleo de ECOPIA;
- 212 métodos detectados en el análisis estructural principal;
- mediana aproximada de 8 líneas por método;
- percentil 90 aproximado de 21 líneas;
- unos pocos orquestadores considerablemente mayores que concentran el flujo completo de un caso de uso.

Estas cifras no pretenden ser métricas de calidad. Sirven para distinguir una preferencia por métodos normalmente contenidos junto con orquestadores explícitos cuando el proceso funcional lo requiere.

## Patrones de alta confianza

### Separación por capas y responsabilidades

La estructura repite fronteras reconocibles:

- `wss` o controladores como entrada;
- servicios de negocio por capacidad;
- `integration` para sistemas externos;
- repositorios y modelos JPA para datos;
- configuración de clientes e infraestructura;
- constantes, errores y utilidades transversales.

### Contratos explícitos

Aparece de forma sistemática la pareja interfaz/implementación en servicios de transformación, ficheros, firmas, metadatos, trazabilidad e integración.

La intención subyacente es proteger la responsabilidad y permitir sustitución, aunque la mecánica concreta de Spring usada en la época no debe copiarse literalmente.

### Casos de uso como secuencias visibles

Los métodos de entrada muestran el proceso funcional en orden, con comentarios de etapa y llamadas a servicios especializados. El lector puede reconstruir el negocio de arriba abajo.

### Servicios nombrados por capacidad

Los nombres describen acciones reales del dominio y evitan abstraer demasiado pronto: transformación de documentos, gestión de ficheros, firma, parseo, metadatos, trazabilidad o conectores concretos.

### Configuración externalizada

Endpoints, timeouts, certificados, rutas, flags y parámetros de integración se sitúan en configuración por entorno, no dispersos por el código.

### Errores contextualizados

El sistema emplea códigos de error estables, excepciones de negocio y traducción desde fallos técnicos. La respuesta de la frontera se construye con contexto funcional.

### Trazabilidad explícita

La auditoría no se limita a logs genéricos: se registran etapas funcionales como inicio, transformación, firma, almacenamiento y finalización, con estados de éxito o error.

### Pragmatismo

El código usa abstracciones cuando existe una responsabilidad reconocible, pero conserva métodos directos, condicionales claros y secuencias imperativas. No hay una búsqueda sistemática de pureza académica.

## Patrones de evolución del código

El historial disponible muestra una secuencia repetida:

1. organización inicial y exposición de servicios;
2. desarrollo por etapas funcionales;
3. extracción de servicios y reorganización de paquetes;
4. control de errores y tiempos;
5. refactorizaciones específicas;
6. limpieza Sonar y vulnerabilidades;
7. logs, documentación y JavaDoc;
8. correcciones operativas y workarounds concretos.

Esto respalda una forma de trabajar incremental: primero conseguir una capacidad completa, después separar, endurecer, limpiar y documentar.

## Rasgos que no deben fosilizarse

Algunos elementos observados son propios de la época, el framework o las restricciones corporativas y no deben convertirse en reglas personales:

- inyección de dependencias mediante campos;
- anotaciones Spring sobre interfaces;
- `public` redundante en métodos de interfaz;
- capturas amplias de `Exception`;
- `printStackTrace` en zonas antiguas;
- clases o métodos excesivamente largos;
- grandes catálogos de constantes;
- mezcla ocasional de catalán, castellano e inglés;
- ausencia de una muestra suficiente de pruebas automatizadas.

El skill conserva la intención y reemplaza esos mecanismos por alternativas actuales.

## Nivel de confianza

### Alto

- organización por responsabilidad;
- contratos e implementaciones en fronteras;
- servicios orientados a capacidades;
- orquestación secuencial;
- vocabulario de dominio;
- configuración externa;
- errores de negocio y trazabilidad;
- evolución por incrementos funcionales y refactor posterior.

### Medio

- preferencia por comentarios de etapa;
- tolerancia a orquestadores largos cuando cuentan una historia funcional;
- preferencia por código imperativo y directo;
- uso de utilidades estáticas para transformaciones transversales.

### No determinado

- cobertura y estrategia de pruebas;
- preferencia por TDD;
- estilo de concurrencia;
- programación funcional;
- frontend y UX;
- arquitectura de eventos moderna;
- optimización numérica o gráfica.
